import csv
import hashlib
import json
import os
from pathlib import Path
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from google.cloud import bigquery

from ...db import get_db
from ...routes import active_client, current_user
from ...config import get_settings
from ...repository import FinanceRepository
from ...services.documents import GCSObjectStore
from ...services.tasks import verify_cloud_tasks_request
from .reporting import gstr_rows
from .profiles import prepare_profile, validate_gstin
from .itc_engine import compute_itc

router = APIRouter(tags=["GST reports"])


@router.post("/api/gst/demo/compute")
async def demo_itc_compute(request: Request):
    """Stage-safe, unauthenticated fixture used only when DEMO_MODE=1."""
    payload = await request.json()
    if os.getenv("DEMO_MODE") != "1" or str(payload.get("gstin", "")).upper() != "27AAPFU0939F1ZV":
        raise HTTPException(404, "Demo fixture is not enabled.")
    fixture = Path(__file__).with_name("fixtures").joinpath("demo-27AAPFU0939F1ZV.json")
    try:
        result = json.loads(fixture.read_text(encoding="utf-8"))
        return {"status": "demo", "message": "Showing the August 2026 demonstration register.", **result}
    except Exception as exc:
        return {"status": "degraded", "message": "Demo fixture could not load; refresh the page or contact the demo operator.", "detail": str(exc)}


def _client_or_403(client_id: str, request, repo, user):
    selected = active_client(request, repo, user)
    if str(selected.id) != str(client_id) and not FinanceRepository(repo).can_access_client(user.id, client_id):
        raise HTTPException(403, "You do not have access to this client.")
    return client_id


@router.post("/api/gst/clients/{client_id}/validate")
async def validate_client_gstin(client_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _client_or_403(client_id, request, repo, user)
    return validate_gstin((await request.json()).get("gstin"))


@router.get("/api/gst/clients/{client_id}")
def current_client_profile(client_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _client_or_403(client_id, request, repo, user)
    row = repo.one(f"SELECT * FROM `{repo.table('gst_client_profile')}` WHERE client_id=@client_id AND is_current=TRUE ORDER BY effective_from DESC LIMIT 1", [bigquery.ScalarQueryParameter("client_id", "STRING", client_id)])
    if not row: raise HTTPException(404, "GST profile not found.")
    return dict(row.items())


@router.get("/api/gst/clients/{client_id}/history")
def client_profile_history(client_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _client_or_403(client_id, request, repo, user)
    rows = repo.query(f"SELECT * FROM `{repo.table('gst_client_profile')}` WHERE client_id=@client_id ORDER BY effective_from DESC", [bigquery.ScalarQueryParameter("client_id", "STRING", client_id)])
    return [dict(row.items()) for row in rows]


@router.post("/api/gst/clients")
async def upsert_client_profile(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    payload = await request.json(); client_id = str(payload.get("client_id", ""))
    _client_or_403(client_id, request, repo, user)
    try: row = prepare_profile(payload, client_id, str(user.id))
    except ValueError as exc: raise HTTPException(422, {"code": str(exc)})
    # BigQuery's insert API serializes JSON fields correctly. The preceding close is version-safe;
    # profile_id makes retries idempotent at the caller boundary.
    repo.update("gst_client_profile", "effective_to=CURRENT_TIMESTAMP(), is_current=FALSE", "client_id=@client_id AND is_current=TRUE", [bigquery.ScalarQueryParameter("client_id", "STRING", client_id)])
    repo.insert("gst_client_profile", row, row["profile_id"])
    return {"profile_id": row["profile_id"], "client_id": client_id, "gstin": row["gstin"], "is_current": True}


@router.post("/api/gst/itc/compute")
async def itc_compute(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    payload = await request.json(); client_id = str(payload.get("client_id", ""))
    if not client_id:
        client_id = str(active_client(request, repo, user).id)
        payload["client_id"] = client_id
    _client_or_403(client_id, request, repo, user)
    result = compute_itc(payload); encoded = json.dumps(result, sort_keys=True, default=str); run_id = hashlib.sha256(encoded.encode()).hexdigest()
    profile = payload.get("profile") or {}; period = payload.get("period") or {}
    repo.insert("gst_itc_runs", {"run_id": run_id, "client_id": client_id, "gstin": profile.get("gstin", ""), "ret_period": str(period.get("month", ""))+str(period.get("year", "")), "scenario_name": (payload.get("scenario") or {}).get("name", "fully_compliant"), "input_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest(), "result": json.dumps(result, default=str), "created_by": str(user.id), "created_at": date.today().isoformat()}, run_id)
    return {"run_id": run_id, **result}


@router.post("/api/gst/itc/scenarios")
async def itc_scenarios(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    payload = await request.json(); client_id = str(payload.get("client_id", ""))
    if not client_id:
        client_id = str(active_client(request, repo, user).id)
        payload["client_id"] = client_id
    _client_or_403(client_id, request, repo, user)
    presets = [{"name":"as_booked","allow_unmatched_2b":True}, {"name":"2b_restricted"}, {"name":"fully_compliant"}, {"name":"suppliers_file_late","allow_unmatched_2b":True}]
    return {"scenarios": [{"name": p["name"], "result": compute_itc({**payload, "scenario": p})} for p in presets]}


@router.get("/api/reports/gstr")
def api_gstr_report(request: Request, start: date | None = None, end: date | None = None, repo=Depends(get_db), user=Depends(current_user)):
    client = active_client(request, repo, user)
    return {"client_id": client.id, "rows": gstr_rows(repo, client.id, start, end)}


@router.get("/api/documents/{document_id}/review-url")
def document_review_url(document_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client = active_client(request, repo, user)
    document = FinanceRepository(repo).document(document_id, client.id)
    if not document:
        from fastapi import HTTPException
        raise HTTPException(404, "Document not found.")
    url = GCSObjectStore(document.bucket_name).signed_url(document.object_path)
    return {"document_id": document_id, "url": url}


@router.get("/api/v1/reports/gstr")
def v1_gstr_report(request: Request, start: date | None = None, end: date | None = None, repo=Depends(get_db), user=Depends(current_user)):
    return api_gstr_report(request, start, end, repo, user)


@router.get("/reports/gstr.csv")
def gstr_report_csv(request: Request, start: date | None = None, end: date | None = None, repo=Depends(get_db), user=Depends(current_user)):
    client = active_client(request, repo, user)
    columns = ["supplier_gstin", "invoice_number", "invoice_date", "taxable_value", "cgst", "sgst", "igst", "total_amount", "classification", "reverse_charge", "irn"]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in gstr_rows(repo, client.id, start, end):
        writer.writerow({key: row.get(key) for key in columns})
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{client.code}_gstr_register.csv"'})


@router.post("/internal/tasks/scan")
async def internal_scan_task(request: Request):
    settings = get_settings()
    queue_header = request.headers.get("x-cloudtasks-queuename", "")
    expected_queue = settings.cloud_tasks_queue.rsplit("/", 1)[-1] if settings.cloud_tasks_queue else ""
    if (not settings.cloud_tasks_queue or queue_header not in {expected_queue, settings.cloud_tasks_queue} or not verify_cloud_tasks_request(request, settings.cloud_tasks_service_url, settings.cloud_tasks_service_account)):
        raise HTTPException(403, "Cloud Tasks authentication required.")
    body = await request.json()
    from ...routes import run_scan_job
    from ...db import get_repository
    completed = run_scan_job(str(body["document_id"]), get_repository(), str(body.get("user_id", "")), str(body["client_id"]))
    if not completed:
        # A non-2xx response lets Cloud Tasks apply its configured retry policy.
        raise HTTPException(500, "Scan failed; Cloud Tasks will retry the task.")
    return {"ok": True}
