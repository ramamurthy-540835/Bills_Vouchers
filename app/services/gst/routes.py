import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse

from ...db import get_db
from ...routes import active_client, current_user
from ...config import get_settings
from ...repository import FinanceRepository
from ...services.documents import GCSObjectStore
from ...services.tasks import verify_cloud_tasks_request
from .reporting import gstr_rows

router = APIRouter(tags=["GST reports"])


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
