import base64
import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from ...config import get_settings
from ...db import get_db, get_repository
from ...repository import FinanceRepository
from ...routes import active_client, current_user
from ..documents import GCSObjectStore, validate_upload
from .medallion import Medallion, clean, clear_cache, encode, live_only, now, param, period_value
from .pipeline import land, process_document, publish, silver
from .rules import HEADS, amount

router = APIRouter()


async def body_json(request):
    try:
        return json.loads(await request.body(), parse_float=Decimal)
    except (ValueError, TypeError):
        raise HTTPException(422, "Invalid JSON.")


@router.get("/api/pipeline/search")
def search(request: Request, q: str, repo=Depends(get_db), user=Depends(current_user)):
    store = selected(request, repo, user)
    query = q.strip().casefold()
    if not query or len(query) > 250:
        raise HTTPException(422, "Enter a search between 1 and 250 characters.")
    return {"results": [d for d in store.workspace()["documents"] if query in (d["original_filename"] + " " + str(d.get("silver") or {})).casefold()]}


@router.get("/api/pipeline/documents/{doc_id}")
def document_detail(doc_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    store = selected(request, repo, user)
    docs = store.rows("bronze_document", "AND doc_id=@doc_id", [param("doc_id", doc_id)])
    if not docs:
        raise HTTPException(404, "Document not found.")
    headers = store.rows("silver_invoice_header", "AND doc_id=@doc_id", [param("doc_id", doc_id)])
    lines = store.rows("silver_invoice_line", "AND doc_id=@doc_id ORDER BY line_no", [param("doc_id", doc_id)])
    return clean({"bronze": docs[0], "header": headers[0] if headers else None, "lines": lines})


def selected(request, repo, user, period=None):
    client = active_client(request, repo, user)
    value = period or request.query_params.get("period") or request.session.get("period")
    if not value:
        rows = repo.query(f"SELECT period FROM `{repo.table('gst_filing_status')}` WHERE client_id=@client_id AND is_current=TRUE AND state!='locked' ORDER BY period DESC LIMIT 1", [param("client_id", client.id)])
        value = rows[0].period if rows else date.today().strftime("%Y-%m")
    return Medallion(repo, client.id, value)


def write_access(user):
    live_only()
    if user.role not in {"admin", "tax_admin", "client"}:
        raise HTTPException(403, "Viewer access is read-only.")


@router.get("/api/workspace")
def workspace(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    store = selected(request, repo, user)
    result = store.workspace()
    result["user"] = {"full_name": user.full_name, "email": user.email, "role": user.role}
    result["clients"] = [{"id": c.id, "name": c.name} for c in FinanceRepository(repo).clients(user.id)]
    result["demo_fallback"] = get_settings().demo_fallback
    return result


@router.post("/api/workspace/period")
async def choose_period(request: Request, user=Depends(current_user)):
    request.session["period"] = period_value((await body_json(request)).get("period"))
    return {"period": request.session["period"]}


@router.post("/api/workspace/client")
async def choose_client(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client_id = str((await body_json(request)).get("client_id", ""))
    if not FinanceRepository(repo).can_access_client(user.id, client_id):
        raise HTTPException(403, "Client access denied.")
    request.session["client_id"] = client_id
    return {"ok": True}


@router.get("/gst/filing")
def filing_page(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    store = selected(request, repo, user)
    from ...routes import page
    return page("filing.html", request, user=user, workspace=store.workspace(), client=active_client(request, repo, user), clients=FinanceRepository(repo).clients(user.id))


@router.post("/api/pipeline/upload")
async def upload(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), repo=Depends(get_db), user=Depends(current_user)):
    write_access(user)
    store = selected(request, repo, user)
    payload, filename, mime = await validate_upload(file)
    doc = land(store, payload, filename, mime, user.email)
    if not doc["duplicate"]:
        if not publish(doc):
            background_tasks.add_task(process_document, repo, store.client_id, store.period, doc["doc_id"])
    return clean(doc)


@router.post("/api/pipeline/documents/{doc_id}/retry")
def retry_document(doc_id: str, request: Request, background_tasks: BackgroundTasks, repo=Depends(get_db), user=Depends(current_user)):
    write_access(user)
    store = selected(request, repo, user)
    store.writable()
    docs = store.rows("bronze_document", "AND doc_id=@doc_id", [param("doc_id", doc_id)])
    if not docs:
        raise HTTPException(404, "Document not found.")
    if not publish(docs[0]):
        background_tasks.add_task(process_document, repo, store.client_id, store.period, doc_id)
    return {"queued": True}


@router.get("/api/pipeline/documents/{doc_id}/file")
def evidence(doc_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    store = selected(request, repo, user)
    docs = store.rows("bronze_document", "AND doc_id=@doc_id", [param("doc_id", doc_id)])
    if not docs:
        raise HTTPException(404, "Document not found.")
    bucket, path = docs[0]["gcs_uri"].removeprefix("gs://").split("/", 1)
    return Response(GCSObjectStore(bucket).download(path), media_type=docs[0]["mime_type"], headers={"Cache-Control": "private, no-store"})


@router.post("/api/pipeline/documents/{doc_id}/review")
async def review(doc_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    write_access(user)
    store = selected(request, repo, user)
    store.writable()
    docs = store.rows("bronze_document", "AND doc_id=@doc_id", [param("doc_id", doc_id)])
    if not docs:
        raise HTTPException(404, "Document not found.")
    data = await body_json(request)
    live_only(data)
    return silver(store, docs[0], {**data, "confidence": "1"}, engine="human_review", actor=user.email)


@router.post("/api/gst/filing/recompute")
def recompute(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    write_access(user)
    return selected(request, repo, user).recompute()


@router.post("/api/gst/filing/import-2b")
async def import_2b(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    write_access(user)
    store = selected(request, repo, user)
    store.writable()
    data = await body_json(request)
    live_only(data)
    rows = data.get("invoices")
    # Accept the GST portal b2b invoice section as well as the documented normalised format.
    if rows is None:
        rows = []
        source = data.get("data", data).get("docdata", {}).get("b2b", [])
        for supplier in source:
            for inv in supplier.get("inv", []):
                items = [item.get("itm_det", item) for item in inv.get("items", [])]
                rows.append({"supplier_gstin": supplier.get("ctin"), "invoice_no": inv.get("inum"),
                             "invoice_date": inv.get("dt"), "taxable_value": sum((amount(i.get("txval")) for i in items), amount()),
                             **{h: sum((amount(i.get(code)) for i in items), amount()) for h, code in zip(HEADS, ("igst", "cgst", "sgst", "cess"))}})
    if not isinstance(rows, list) or not rows or len(rows) > 5000:
        raise HTTPException(422, "Provide between 1 and 5,000 GSTR-2B invoices.")
    normalized = []
    for row in rows:
        from .validation import valid_gstin
        if not valid_gstin(str(row.get("supplier_gstin", ""))) or not row.get("invoice_no"):
            raise HTTPException(422, "Each invoice needs a valid supplier GSTIN and invoice number.")
        try:
            from datetime import datetime
            text = str(row["invoice_date"])
            dt = datetime.strptime(text, "%d-%m-%Y").date() if re.fullmatch(r"\d{2}-\d{2}-\d{4}", text) else date.fromisoformat(text)
            normalized.append({"supplier_gstin": row["supplier_gstin"], "invoice_no": str(row["invoice_no"]), "invoice_date": dt.isoformat(),
                               "taxable_value": amount(row.get("taxable_value")), **{h: amount(row.get(h)) for h in HEADS}})
        except (ValueError, KeyError):
            raise HTTPException(422, "Invalid invoice dates or amounts. Money must be decimal strings.")
    raw = encode(data).encode()
    digest = hashlib.sha256(raw).hexdigest()
    import_id = digest[:32]
    uri = GCSObjectStore(get_settings().gcs_bucket_name).upload(f"bronze/{store.client_id}/gstr2b/{store.period}/{import_id}.json", raw, "application/json")
    stamp = now()
    store.upsert("bronze_gstr2b_import", {"import_id": import_id, "client_id": store.client_id, "period": store.period, "gcs_uri": uri, "content_hash": digest, "imported_by": user.email, "imported_at": stamp}, ["client_id", "period", "import_id"])
    for row in normalized:
        store.upsert("silver_gstr2b_invoice", {**row, "client_id": store.client_id, "period": store.period, "import_id": import_id, "imported_at": stamp}, ["client_id", "period", "supplier_gstin", "invoice_no"])
    store.recompute()
    return {"imported": len(rows), "import_id": import_id}


@router.post("/api/gst/filing/outward")
async def import_outward(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    write_access(user)
    store = selected(request, repo, user)
    store.writable()
    data = await body_json(request)
    live_only(data)
    rows = data.get("invoices", [])
    if not rows or len(rows) > 5000:
        raise HTTPException(422, "Provide 1 to 5,000 outward invoices.")
    normalized = []
    for row in rows:
        try:
            dt = date.fromisoformat(row["invoice_date"])
            if dt.strftime("%Y-%m") != store.period or not row["invoice_no"]:
                raise ValueError()
            normalized.append({"client_id": store.client_id, "period": store.period, "invoice_no": str(row["invoice_no"]), "invoice_date": dt.isoformat(),
                               "recipient_gstin": row.get("recipient_gstin"), "place_of_supply": row.get("place_of_supply"),
                               "sac": str(row.get("sac", "9964")), "eco_9_5": bool(row.get("eco_9_5", False)),
                               "taxable_value": amount(row.get("taxable_value")), **{h: amount(row.get(h)) for h in HEADS}, "created_at": now()})
        except (ValueError, KeyError):
            raise HTTPException(422, "Invalid outward invoice or period.")
    for row in normalized:
        store.upsert("silver_outward_invoice", row, ["client_id", "period", "invoice_no"])
    store.recompute()
    return {"imported": len(normalized)}


def transition(store, actor, target, arn=None, filed_at=None, uri=None, digest=None):
    store.writable()
    state = store.status()["state"]
    allowed = {"draft": "validated", "validated": "json_generated", "json_generated": "filed", "filed": "locked"}
    if allowed.get(state) != target:
        raise HTTPException(409, f"Cannot transition from {state} to {target}.")
    if target in {"filed", "locked"} and actor.role not in {"admin", "tax_admin"}:
        raise HTTPException(403, "Only a tax administrator may file or lock a return.")
    if target == "filed":
        if not re.fullmatch(r"[A-Z0-9]{15}", str(arn or "")):
            raise HTTPException(422, "ARN must contain 15 uppercase letters or digits.")
        try:
            if date.fromisoformat(str(filed_at)) > date.today():
                raise ValueError()
        except ValueError:
            raise HTTPException(422, "A valid, non-future filing date is required.")
    params = store.params + [param("expected", state), param("target", target), param("actor", actor.email),
                            param("arn", arn), param("filed_at", filed_at, "DATE"), param("audit_id", str(uuid4())), param("uri", uri), param("hash", digest)]
    store.repo.query(f"""BEGIN TRANSACTION;
      ASSERT COALESCE((SELECT state FROM `{store.repo.table('gst_filing_status')}` WHERE client_id=@client_id AND period=@period AND is_current=TRUE LIMIT 1),'draft')=@expected AS 'FILING_STATE_CONFLICT';
      UPDATE `{store.repo.table('gst_filing_status')}` SET is_current=FALSE,effective_to=CURRENT_TIMESTAMP() WHERE client_id=@client_id AND period=@period AND is_current=TRUE;
      INSERT INTO `{store.repo.table('gst_filing_status')}` (client_id,period,state,arn,filed_at,actor_email,effective_from,is_current)
        VALUES (@client_id,@period,@target,@arn,@filed_at,@actor,CURRENT_TIMESTAMP(),TRUE);
      INSERT INTO `{store.repo.table('gst_filing_audit')}` (audit_id,client_id,period,from_state,to_state,actor_email,artefact_uri,content_hash,created_at)
        VALUES (@audit_id,@client_id,@period,@expected,@target,@actor,@uri,@hash,CURRENT_TIMESTAMP());
      COMMIT TRANSACTION;""", params)
    clear_cache(store.client_id, store.period)
    return {"state": target}


@router.post("/api/gst/filing/transition")
async def filing_transition(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    write_access(user)
    data = await body_json(request)
    live_only(data)
    store = selected(request, repo, user)
    target = data.get("state")
    if target == "json_generated":
        raise HTTPException(409, "Generate the return artefact to advance this state.")
    if target == "validated":
        store.validate_filing()
    return transition(store, user, target, data.get("arn"), data.get("filed_at"))


@router.post("/api/gst/filing/generate/{kind}")
def generate(kind: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    write_access(user)
    store = selected(request, repo, user)
    store.writable()
    w = store.validate_filing()
    if kind not in {"gstr3b", "gstr1"}:
        raise HTTPException(404, "Unknown return type.")
    if w["filing"]["state"] not in {"validated", "json_generated"}:
        raise HTTPException(409, "Validate this period first.")
    s = w["summary"]
    # Explicit preparer format; never claim an unverified portal schema is upload-ready.
    result = {"schema_version": get_settings().gst_schema_version, "draft": True, "gstin": w["profile"]["gstin"], "period": store.period, "return_type": kind}
    if kind == "gstr3b":
        result.update({"3.1": s["output_by_head"], "3.1.1": s["eco_by_head"] if w["profile"].get("is_eco_9_5") else {},
                       "4(A)": s["eligible_by_head"], "4(B)": {h: str(sum((amount(r.get('reversal_' + h)) for r in w['ledger']), amount())) for h in HEADS},
                       "4(D)": {h: str(sum((amount(r.get('blocked_' + h)) for r in w['ledger']), amount())) for h in HEADS}})
    else:
        result["outward_invoices"] = clean(store.rows("silver_outward_invoice"))
    raw = encode(result).encode()
    digest = hashlib.sha256(raw).hexdigest()
    uri = GCSObjectStore(get_settings().gcs_bucket_name).upload(f"gold/{store.client_id}/filings/{store.period}/{kind}_{digest}.json", raw, "application/json")
    if w["filing"]["state"] == "validated":
        transition(store, user, "json_generated", uri=uri, digest=digest)
    return Response(raw, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{kind}_{store.period}_draft.json"'})


@router.post("/internal/pipeline/document")
async def pipeline_push(request: Request):
    settings = get_settings()
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token
    try:
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        claims = id_token.verify_oauth2_token(token, GoogleRequest(), audience=settings.pipeline_push_audience)
        if not settings.pipeline_push_service_account or claims.get("email") != settings.pipeline_push_service_account or not claims.get("email_verified"):
            raise ValueError()
    except Exception:
        raise HTTPException(403, "Pipeline authentication required.")
    body = await body_json(request)
    message = json.loads(base64.b64decode(body["message"]["data"]))
    process_document(get_repository(), message["client_id"], message["period"], message["doc_id"])
    return {"ok": True}
