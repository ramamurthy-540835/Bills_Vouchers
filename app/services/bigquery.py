from ..config import get_settings
from .retry import retry_call
from typing import Any


def publish_document(document: Any, extraction: Any) -> None:
    """Publishes a JSON row; BigQuery table schema uses NUMERIC, never FLOAT."""
    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise RuntimeError("Install the cloud dependency group to publish BigQuery analytics.") from exc
    settings = get_settings()
    if not settings.gcp_project_id:
        raise RuntimeError("GCP_PROJECT_ID is required for BigQuery.")
    table = f"{settings.gcp_project_id}.{settings.bigquery_dataset}.document_extractions"
    row = {
        "document_id": document.id,
        "document_type": document.document_type.value,
        "vendor_name": extraction.vendor_name,
        "invoice_number": extraction.invoice_number,
        "invoice_date": str(extraction.invoice_date) if extraction.invoice_date else None,
        "subtotal": str(extraction.subtotal) if extraction.subtotal is not None else None,
        "cgst": str(extraction.cgst) if extraction.cgst is not None else None,
        "sgst": str(extraction.sgst) if extraction.sgst is not None else None,
        "igst": str(extraction.igst) if extraction.igst is not None else None,
        "total_amount": str(extraction.total_amount) if extraction.total_amount is not None else None,
        "currency": extraction.currency,
        "payment_method": extraction.payment_method,
        "gcs_uri": document.gcs_uri,
        "ocr_text": extraction.ocr_text,
        "status": document.status.value,
        "uploaded_at": document.uploaded_at.isoformat(),
    }
    errors = retry_call(lambda: bigquery.Client(project=settings.gcp_project_id).insert_rows_json(table, [row], row_ids=[document.id], timeout=settings.query_timeout_seconds))
    if errors:
        raise RuntimeError(f"BigQuery insert failed: {errors}")
