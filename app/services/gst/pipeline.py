import hashlib
import re
from datetime import date
from decimal import InvalidOperation
from pathlib import Path

from fastapi import HTTPException

from ...config import get_settings
from ...models import ns
from ..documents import GCSObjectStore
from ..gemini import scan_document
from .medallion import Medallion, clean, encode, live_only, now, param
from .rules import HEADS, ZERO, amount, heads
from .validation import valid_gstin


def normalise_extraction(data):
    """Normalise OCR presentation; ambiguous values go to review, never guessed."""
    data = dict(data)
    errors = []
    fields = set(HEADS) | {"subtotal", "total_amount", "taxable_value", "gst_rate", "tax_rate", "confidence", "extraction_confidence", "quantity", "unit_price", "rate"}
    def normalize(row):
        row = dict(row)
        for key in fields.intersection(row):
            value = row[key]
            if value is None or str(value).strip() == '':
                row[key] = None
                continue
            text = re.sub(r'^(?:INR|Rs\.?|₹)\s*', '', str(value).strip(), flags=re.I).replace(',', '')
            percent = text.endswith('%')
            text = text.removesuffix('%').strip()
            try:
                parsed = amount(text)
                if key in {'confidence','extraction_confidence'} and percent:
                    parsed /= amount('100')
                if parsed < ZERO:
                    errors.append('NEGATIVE_AMOUNT_' + key.upper())
                row[key] = str(parsed)
            except (ValueError, InvalidOperation):
                row[key] = None
                errors.append('UNREADABLE_' + key.upper())
        return row
    data = normalize(data)
    data['line_items'] = [normalize(row) for row in data.get('line_items') or []]
    data['_normalization_errors'] = errors
    return data


def category(description):
    text = str(description or "").lower()
    if any(x in text for x in ("petrol", "diesel")):
        return "fuel"
    if any(x in text for x in ("insurance", "repair", "servicing")):
        return "insurance_repair"
    if any(x in text for x in ("motor vehicle", "passenger vehicle", "motor car")):
        return "vehicle"
    return "other"


def land(store, payload, filename, mime, actor, objects=None):
    store.source_writable()
    digest = hashlib.sha256(payload).hexdigest()
    # Deterministic tenant/content ID + GCS generation precondition also dedupe concurrent retries.
    existing = store.rows("bronze_document", "AND content_hash=@hash LIMIT 1", [param("hash", digest)], period=False)
    if existing:
        return {**clean(existing[0]), "duplicate": True}
    doc_id = hashlib.sha256((store.client_id + ":" + digest).encode()).hexdigest()[:32]
    extension = Path(filename).suffix.lower()
    path = f"bronze/{store.client_id}/{store.period.replace('-', '/')}/{doc_id}{extension}"
    objects = objects or GCSObjectStore(get_settings().gcs_bucket_name)
    uri = objects.upload(path, payload, mime)
    stamp = now()
    row = {"doc_id": doc_id, "client_id": store.client_id, "period": store.period,
           "gcs_uri": uri, "content_hash": digest, "mime_type": mime, "byte_size": len(payload),
           "source_channel": "web", "original_filename": filename, "uploaded_by": actor,
           "uploaded_at": stamp, "ingest_date": stamp[:10]}
    store.upsert("bronze_document", row, ["client_id", "doc_id"])
    return {**row, "duplicate": False}


def validate_extraction(data, period, duplicate=False):
    errors = list(data.get('_normalization_errors') or [])
    gstin = data.get("supplier_gstin") or data.get("gstin") or ""
    if not valid_gstin(gstin):
        errors.append("GSTIN_CHECKSUM")
    if not data.get("invoice_number"):
        errors.append("INVOICE_NUMBER_MISSING")
    try:
        dt = date.fromisoformat(str(data.get("invoice_date"))[:10])
        year, month = map(int, period.split("-"))
        if abs(dt.year * 12 + dt.month - year * 12 - month) > 1:
            errors.append("INVOICE_OUTSIDE_PERIOD")
    except (ValueError, TypeError):
        errors.append("INVOICE_DATE_MISSING")
    confidence = amount(data.get("confidence", data.get("extraction_confidence", "0")))
    if confidence < amount("0.85"):
        errors.append("LOW_CONFIDENCE")
    taxes = heads(data)
    if taxes["igst"] and (taxes["cgst"] or taxes["sgst"]):
        errors.append("TAX_SPLIT_INCONSISTENT")
    if taxes["cgst"] != taxes["sgst"]:
        errors.append("CENTRAL_STATE_TAX_DIFFER")
    taxable = amount(data.get("subtotal", data.get("taxable_value", 0)))
    rate = data.get("gst_rate", data.get("tax_rate"))
    if rate is not None and abs(taxable * amount(rate) / amount("100") - sum(taxes.values(), ZERO)) > amount("1"):
        errors.append("TAX_RATE_INCONSISTENT")
    if duplicate:
        errors.append("DUPLICATE_INVOICE")
    return errors


def silver(store, doc, data, engine="gemini", actor=None):
    store.source_writable()
    supplier = str(data.get("supplier_gstin") or data.get("gstin") or "").strip().upper()
    number = str(data.get("invoice_number") or "")
    duplicates = store.rows("silver_invoice_header", "AND supplier_gstin=@supplier AND invoice_no=@number AND doc_id!=@doc_id", [param("supplier", supplier), param("number", number), param("doc_id", doc["doc_id"])], period=False)
    errors = validate_extraction(data, store.period, bool(duplicates))
    stamp = now()
    try:
        dt = date.fromisoformat(str(data.get("invoice_date"))[:10]).isoformat()
    except (ValueError, TypeError):
        dt = None
    taxes = heads(data)
    header = {"doc_id": doc["doc_id"], "client_id": store.client_id, "period": store.period,
              "supplier_gstin": supplier, "supplier_name": str(data.get("vendor_name") or ""),
              "invoice_no": number, "invoice_date": dt, "place_of_supply": data.get("place_of_supply"),
              "taxable_value": amount(data.get("subtotal", data.get("taxable_value", 0))), **taxes,
              "total": amount(data.get("total_amount", 0)), "extraction_confidence": amount(data.get("confidence", "0")),
              "extraction_engine": engine, "extracted_at": stamp,
              "validation_status": "needs_review" if errors else "validated", "validation_errors": errors,
              "reviewed_by": actor, "reviewed_at": stamp if actor else None}
    store.upsert("silver_invoice_header", header, ["client_id", "doc_id"])
    # Replace only this tenant/document's derived lines, never source evidence.
    store.repo.query(f"DELETE FROM `{store.repo.table('silver_invoice_line')}` WHERE client_id=@client_id AND period=@period AND doc_id=@doc_id", store.params + [param("doc_id", doc["doc_id"])])
    items = data.get("line_items") or [{"description": data.get("classification") or "Invoice", "taxable_value": header["taxable_value"], **taxes}]
    totals = {h: ZERO for h in HEADS}
    for i, item in enumerate(items, 1):
        description = str(item.get("description") or item.get("item_name") or "Invoice line")
        values = heads(item)
        if len(items) == 1 and not any(values.values()):
            values = taxes
        for h in HEADS:
            totals[h] += values[h]
        line = {"doc_id": doc["doc_id"], "client_id": store.client_id, "period": store.period, "line_no": i,
                "description": description, "hsn_sac": str(item.get("hsn_sac") or item.get("hsn") or item.get("sac") or ""),
                "qty": amount(item.get("quantity", 1)), "rate": amount(item.get("unit_price", 0)),
                "tax_rate": amount(item.get("rate", 0)), "taxable_value": amount(item.get("taxable_value", 0)), **values,
                "itc_category": item.get("itc_category") or category(description), "seating_capacity": int(item.get("seating_capacity") or 13),
                "unpaid_days": int(item.get("unpaid_days") or 0), "blocked_clause": item.get("blocked_clause"),
                "common_credit": bool(item.get("common_credit", False)), "capital_goods": bool(item.get("capital_goods", False)),
                "invoice_date": dt, "extracted_at": stamp}
        store.upsert("silver_invoice_line", line, ["client_id", "doc_id", "line_no"])
    if any(abs(totals[h] - taxes[h]) > amount("1") for h in HEADS):
        header["validation_errors"].append("LINE_TAX_TOTAL_MISMATCH")
        header["validation_status"] = "needs_review"
        store.upsert("silver_invoice_header", header, ["client_id", "doc_id"])
    GCSObjectStore(get_settings().gcs_bucket_name).upload(f"silver/{store.client_id}/{doc['doc_id']}.json", encode(clean(header)).encode(), "application/json")
    if header["validation_status"] == "validated":
        store.recompute()
    return clean(header)


def process_document(repo, client_id, period, doc_id):
    store = Medallion(repo, client_id, period)
    store.source_writable()
    docs = store.rows("bronze_document", "AND doc_id=@doc_id LIMIT 1", [param("doc_id", doc_id)])
    if not docs:
        raise HTTPException(404, "Document not found.")
    doc = docs[0]
    existing = store.rows("silver_invoice_header", "AND doc_id=@doc_id LIMIT 1", [param("doc_id", doc_id)])
    if existing and existing[0]["validation_status"] != "failed":
        return clean(existing[0])
    uri = doc["gcs_uri"].removeprefix("gs://").split("/", 1)
    payload = GCSObjectStore(uri[0]).download(uri[1])
    try:
        data = normalise_extraction(scan_document(ns(mime_type=doc["mime_type"], id=doc_id), payload))
        return silver(store, doc, data)
    except Exception:
        store.upsert("silver_invoice_header", {"client_id": client_id, "period": period, "doc_id": doc_id,
                     "validation_status": "failed", "validation_errors": ["EXTRACTION_FAILED"], "extracted_at": now()}, ["client_id", "doc_id"])
        raise


def publish(doc):
    live_only(doc)
    topic = get_settings().document_landed_topic
    if not topic:
        return False
    from google.cloud import pubsub_v1  # type: ignore[attr-defined]
    publisher = pubsub_v1.PublisherClient()
    publisher.publish(topic, encode({k: doc[k] for k in ("client_id", "period", "doc_id")}).encode()).result(timeout=30)
    return True
