import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ...db import get_db
from ...routes import active_client, current_user
from ...repository import FinanceRepository
from ...services.documents import GCSObjectStore
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
