import json
from datetime import date
from typing import Any

from google.cloud import bigquery

from .gst import normalize_invoice_number, validate_document
from .ocr import decimal_or_none
from .retry import retry_call

FIELDS = [
    "vendor_name",
    "vendor_address",
    "invoice_number",
    "invoice_date",
    "due_date",
    "gstin",
    "subtotal",
    "tax_amount",
    "cgst",
    "sgst",
    "igst",
    "discount_amount",
    "total_amount",
    "currency",
    "payment_method",
    "ocr_text",
    "classification",
    "reverse_charge",
    "irn",
    "acknowledgement_number",
    "acknowledgement_date",
    "signed_qr_detected",
    "field_confidence",
]
SCHEMA: dict[str, Any] = {"type": "OBJECT", "properties": {k: {"type": "STRING"} for k in FIELDS}}
SCHEMA["properties"]["field_confidence"] = {"type": "OBJECT", "additionalProperties": {"type": "STRING"}}
SCHEMA["properties"]["line_items"] = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            k: {"type": "STRING"}
            for k in ["item_name", "description", "quantity", "unit", "unit_price", "taxable_value", "rate", "tax", "discount", "total", "hsn", "sac"]
        },
    },
}


def scan_document(document, payload):
    from google import genai
    from google.genai import types

    s = __import__("app.config", fromlist=["get_settings"]).get_settings()
    c = (
        genai.Client(api_key=s.gemini_api_key)
        if s.gemini_api_key
        else genai.Client(vertexai=True, project=s.gcp_project_id, location=s.gcp_region)
    )
    prompt = """Extract this Indian bill or voucher exactly as structured JSON. Inspect the entire image, including the bottom of a long receipt. The final payable TOTAL / GRAND TOTAL is mandatory whenever a visible rupee amount exists; do not leave total_amount blank. Capture subtotal before round-off when shown, and use the final amount after round-off as total_amount. For non-GST grocery receipts, set CGST, SGST and IGST to 0 when no tax lines are printed. Extract all visible line items and preserve useful receipt text in ocr_text. Never invent a number that is not visible."""
    r = retry_call(lambda: c.models.generate_content(
        model=s.gemini_model,
        contents=[types.Part.from_bytes(data=payload, mime_type=document.mime_type), prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=SCHEMA, temperature=0
        ),
    ))
    try:
        if not r.text:
            raise ValueError("empty response")
        return json.loads(r.text)
    except Exception as exc:
        raise RuntimeError("Gemini returned invalid structured output.") from exc


def process_with_gemini(repo, document, payload):
    def update_document(set_sql, params=None):
        try:
            repo.bq.update(
                "documents",
                set_sql,
                "id=@id",
                (params or []) + [bigquery.ScalarQueryParameter("id", "STRING", document.id)],
            )
        except Exception as exc:
            if "streaming buffer" not in str(exc).lower():
                raise

    update_document("status='scanning', processing_error=NULL")
    try:
        data = scan_document(document, payload)
    except Exception as exc:
        try:
            repo.bq.update(
                "documents",
                "status='scan_failed', processing_error=@err",
                "id=@id",
                [
                    bigquery.ScalarQueryParameter("id", "STRING", document.id),
                    bigquery.ScalarQueryParameter("err", "STRING", str(exc)[:2000]),
                ],
            )
        except Exception as update_exc:
            if "streaming buffer" not in str(update_exc).lower():
                raise
        raise

    def dt(x):
        try:
            return date.fromisoformat(str(x)[:10]).isoformat() if x else None
        except ValueError:
            return None

    def numeric(value):
        parsed = decimal_or_none(value)
        return str(parsed) if parsed is not None else None

    def boolean(value):
        if isinstance(value, bool):
            return value
        normalized = str(value or "").strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
        return None

    invoice_date = dt(data.get("invoice_date"))
    invoice_date_obj = date.fromisoformat(invoice_date) if invoice_date else None
    normalized_invoice = normalize_invoice_number(data.get("invoice_number"))
    duplicate = False
    if (data.get("supplier_gstin") or data.get("gstin")) and normalized_invoice and invoice_date_obj:
        fy_start_year = invoice_date_obj.year if invoice_date_obj.month >= 4 else invoice_date_obj.year - 1
        duplicate = repo.bq.one(
            f"""SELECT 1 FROM `{repo.bq.table('document_extractions')}` e
            JOIN `{repo.bq.table('documents')}` d ON d.id=e.document_id
            WHERE e.document_id != @document_id AND UPPER(COALESCE(e.supplier_gstin, e.gstin))=@gstin
              AND REGEXP_REPLACE(UPPER(e.invoice_number), r'[^A-Z0-9]', '')=@invoice
              AND e.invoice_date BETWEEN @fy_start AND @fy_end LIMIT 1""",
            [
                bigquery.ScalarQueryParameter("document_id", "STRING", document.id),
                bigquery.ScalarQueryParameter("gstin", "STRING", str(data.get("supplier_gstin") or data.get("gstin")).strip().upper()),
                bigquery.ScalarQueryParameter("invoice", "STRING", normalized_invoice),
                bigquery.ScalarQueryParameter("fy_start", "DATE", date(fy_start_year, 4, 1)),
                bigquery.ScalarQueryParameter("fy_end", "DATE", date(fy_start_year + 1, 3, 31)),
            ],
        ) is not None
    validation = validate_document(data, duplicate=duplicate, confidence_threshold=__import__("app.config", fromlist=["get_settings"]).get_settings().extraction_confidence_threshold)
    row = {
        "id": document.id,
        "document_id": document.id,
        **{
            k: data.get(k)
            for k in [
                "vendor_name",
                "vendor_address",
                "invoice_number",
                "gstin",
                "supplier_gstin",
                "recipient_gstin",
                "supplier_state_code",
                "place_of_supply",
                "currency",
                "payment_method",
                "ocr_text",
                "classification",
                "irn",
                "acknowledgement_number",
            ]
        },
        "b2b": boolean(data.get("b2b")),
        "reverse_charge": boolean(data.get("reverse_charge")),
        "signed_qr_detected": boolean(data.get("signed_qr_detected")),
        "invoice_date": invoice_date,
        "due_date": dt(data.get("due_date")),
        "acknowledgement_date": dt(data.get("acknowledgement_date")),
        "subtotal": numeric(data.get("subtotal")),
        "tax_amount": numeric(data.get("tax_amount")),
        "cgst": numeric(data.get("cgst")),
        "sgst": numeric(data.get("sgst")),
        "igst": numeric(data.get("igst")),
        "discount_amount": numeric(data.get("discount_amount")),
        "total_amount": numeric(data.get("total_amount")),
        "ocr_confidence": None,
        "field_confidence": json.dumps(data.get("field_confidence") or {}, separators=(",", ":")),
        "validation_report": json.dumps(validation, separators=(",", ":")),
        "created_at": str(document.uploaded_at),
    }
    repo.bq.query(
        f"DELETE FROM `{repo.bq.table('document_extractions')}` WHERE document_id=@id",
        [bigquery.ScalarQueryParameter("id", "STRING", document.id)],
    )
    repo.bq.insert("document_extractions", row, document.id)
    repo.bq.query(
        f"DELETE FROM `{repo.bq.table('document_line_items')}` WHERE extraction_id=@id",
        [bigquery.ScalarQueryParameter("id", "STRING", document.id)],
    )
    for i, x in enumerate(data.get("line_items") or []):
        repo.bq.insert(
            "document_line_items",
            {
                "id": f"{document.id}-{i}",
                "extraction_id": document.id,
                "line_number": i,
                **{k: x.get(k) for k in ["item_name", "description", "unit", "hsn", "sac"]},
                "quantity": numeric(x.get("quantity")),
                "unit_price": numeric(x.get("unit_price")),
                "taxable_value": numeric(x.get("taxable_value")),
                "rate": numeric(x.get("rate")),
                "tax": numeric(x.get("tax")),
                "discount": numeric(x.get("discount")),
                "total": numeric(x.get("total")),
            },
            f"{document.id}-{i}",
        )
    update_document(
        "validation_status=@status",
        [bigquery.ScalarQueryParameter("status", "STRING", validation["validation_status"])],
    )
    update_document("status='needs_review', processing_error=NULL")
    return repo.extraction(document.id)
