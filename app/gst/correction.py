"""Explicit correction metadata; canonical financial statuses remain compatible."""

from datetime import datetime, timezone
from fastapi import HTTPException

REASONS = {
    "duplicate_invoice",
    "invalid_gstin",
    "incorrect_rate",
    "gst_amount_mismatch",
    "invoice_total_mismatch",
    "missing_number",
    "missing_date",
    "supplier_mismatch",
    "customer_mismatch",
    "incorrect_tax_head",
    "low_quality",
    "incomplete_document",
    "wrong_business",
    "unsupported_document",
    "other",
}


def transition(invoice, action, actor, reason):
    if not isinstance(reason, str) or not 3 <= len(reason.strip()) <= 1000:
        raise HTTPException(422, "Record a reason between 3 and 1000 characters.")
    state = invoice.correction_state
    if action == "request-correction":
        if invoice.status != "rejected" or state not in {"none", "rejected"}:
            raise HTTPException(409, "Only a rejected bill can enter the correction queue.")
        target = "correction_requested"
    elif action == "resubmit":
        if state != "corrected":
            raise HTTPException(409, "Save corrected bill details before resubmitting.")
        target = "resubmitted"
    else:
        raise HTTPException(422, "Unsupported correction action.")
    updated = invoice.model_copy(deep=True)
    updated.correction_state = target
    updated.correction_actor = str(actor)
    updated.correction_reason = reason.strip()
    updated.correction_at = datetime.now(timezone.utc).isoformat()
    updated.status = "needs_review" if target == "resubmitted" else "rejected"
    updated.version += 1
    return updated
