from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from sqlalchemy.orm import Session
from ..models import Document, DocumentExtraction, DocumentLineItem, DocumentStatus

def decimal_or_none(value: str | None) -> Decimal | None:
    if not value: return None
    try: return Decimal(value.replace(",", "").replace("₹", "").strip())
    except (InvalidOperation, AttributeError): return None

def entity_map(document: Any) -> dict[str, list[Any]]:
    output: dict[str,list[Any]]={}
    for entity in document.entities: output.setdefault(entity.type_.lower(),[]).append(entity)
    return output

def value(entities: dict[str,list[Any]], *names: str) -> str | None:
    for name in names:
        found=entities.get(name.lower(),[])
        if found: return found[0].mention_text or None
    return None

def process_result(db: Session, source: Document, result: Any) -> DocumentExtraction:
    """Persist only fields Document AI reported; unavailable values remain NULL."""
    e=entity_map(result)
    extraction=source.extraction or DocumentExtraction(document_id=source.id)
    extraction.vendor_name=value(e,"supplier_name","vendor_name","merchant_name")
    extraction.vendor_address=value(e,"supplier_address","vendor_address","merchant_address")
    extraction.invoice_number=value(e,"invoice_id","invoice_number","receipt_number")
    extraction.gstin=value(e,"supplier_tax_id","gstin")
    extraction.subtotal=decimal_or_none(value(e,"net_amount","subtotal"))
    extraction.tax_amount=decimal_or_none(value(e,"total_tax_amount","tax_amount"))
    extraction.cgst=decimal_or_none(value(e,"cgst")); extraction.sgst=decimal_or_none(value(e,"sgst")); extraction.igst=decimal_or_none(value(e,"igst"))
    extraction.total_amount=decimal_or_none(value(e,"total_amount","amount_due")); extraction.currency=value(e,"currency") or "INR"
    extraction.payment_method=value(e,"payment_method")
    extraction.ocr_text=getattr(result,"text",None)
    extraction.ocr_confidence=None
    if not source.extraction: db.add(extraction); db.flush()
    for item in list(extraction.line_items): db.delete(item)
    for entity in e.get("line_item",[]):
        fields={child.type_.split("/")[-1].lower():child.mention_text for child in entity.properties}
        extraction.line_items.append(DocumentLineItem(item_name=fields.get("description"),quantity=decimal_or_none(fields.get("quantity")),unit_price=decimal_or_none(fields.get("unit_price")),total=decimal_or_none(fields.get("amount"))))
    source.status=DocumentStatus.NEEDS_REVIEW; source.processing_error=None
    db.commit(); db.refresh(extraction); return extraction

def review_update(db: Session, extraction: DocumentExtraction, values: dict[str, str | None]) -> None:
    for field in ("vendor_name","invoice_number","gstin","currency","payment_method"):
        if field in values: setattr(extraction,field,values[field] or None)
    for field in ("subtotal","tax_amount","cgst","sgst","igst","discount_amount","total_amount"):
        if field in values: setattr(extraction,field,decimal_or_none(values[field]))
    db.commit()
