import csv
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

router = APIRouter(tags=["GST reports"])


@router.post("/api/gst/demo/compute")
async def demo_itc_compute(request: Request, user=Depends(current_user)):
    raise HTTPException(403, {"code": "sample_data_blocked", "message": "Samples are available in the UI only."})


def _client_or_403(client_id: str, request, repo, user):
    selected = active_client(request, repo, user)
    if str(selected.id) != str(client_id):
        raise HTTPException(403, "Select this client before accessing its records.")
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
    from .medallion import live_only, clear_cache
    live_only()
    if user.role not in {"tax_admin", "admin"}:
        raise HTTPException(403, "Only a tax administrator can change GST profile settings.")
    payload = await request.json(); client_id = str(payload.get("client_id", ""))
    _client_or_403(client_id, request, repo, user)
    try: row = prepare_profile(payload, client_id, str(user.id))
    except ValueError as exc: raise HTTPException(422, {"code": str(exc)})
    # BigQuery's insert API serializes JSON fields correctly. The preceding close is version-safe;
    # profile_id makes retries idempotent at the caller boundary.
    repo.update("gst_client_profile", "effective_to=CURRENT_TIMESTAMP(), is_current=FALSE", "client_id=@client_id AND is_current=TRUE", [bigquery.ScalarQueryParameter("client_id", "STRING", client_id)])
    repo.insert("gst_client_profile", row, row["profile_id"])
    clear_cache(client_id)
    return {"profile_id": row["profile_id"], "client_id": client_id, "gstin": row["gstin"], "is_current": True}


@router.post("/api/gst/itc/compute")
async def itc_compute(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    from .workbench import selected, write_access
    write_access(user)
    return selected(request, repo, user).recompute()


@router.post("/api/gst/itc/scenarios")
async def itc_scenarios(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    from .workbench import selected
    return {"summary": selected(request, repo, user).workspace()["summary"]}


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
