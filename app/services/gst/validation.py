"""Pure Indian GST validation helpers. No network or database access."""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

ALLOWED_GST_RATES = frozenset(Decimal(str(x)) for x in (0, 0.1, 0.25, 1, 1.5, 3, 5, 7.5, 12, 18, 28))
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
VALID_STATE_CODES = {f"{i:02d}" for i in range(1, 39)} | {"97", "99"}
BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalize_invoice_number(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def indian_financial_year(value: date) -> str:
    start = value.year if value.month >= 4 else value.year - 1
    return f"{start:04d}-{(start + 1) % 100:02d}"


def valid_gstin(value: str | None) -> bool:
    if not value:
        return False
    gstin = value.strip().upper()
    if not GSTIN_RE.fullmatch(gstin) or gstin[:2] not in VALID_STATE_CODES:
        return False
    total = 0
    factor = 2
    for char in reversed(gstin[:14]):
        product = BASE36.index(char) * factor
        total += product // 36 + product % 36
        factor = 1 if factor == 2 else 2
    return BASE36[(36 - total % 36) % 36] == gstin[14]


def _issue(bucket: list[dict[str, Any]], code: str, field: str, message: str, severity: str) -> None:
    bucket.append({"code": code, "field": field, "message": message, "severity": severity})


def validate_document(data: dict[str, Any], *, duplicate: bool = False) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for field in ("supplier_gstin", "recipient_gstin", "gstin"):
        value = data.get(field)
        if value and not valid_gstin(str(value)):
            _issue(errors, "invalid_gstin", field, "GSTIN format or checksum is invalid.", "error")
    if duplicate:
        _issue(
            errors,
            "duplicate_invoice",
            "invoice_number",
            "Supplier invoice already exists for the Indian financial year.",
            "error",
        )
    invoice = normalize_invoice_number(data.get("invoice_number"))
    if data.get("invoice_number") and not invoice:
        _issue(
            errors, "empty_invoice_number", "invoice_number", "Invoice number contains no usable characters.", "error"
        )
    if data.get("irn") and len(str(data["irn"]).strip()) != 64:
        _issue(errors, "invalid_irn", "irn", "IRN must be a 64-character hash.", "error")
    rate = data.get("gst_rate")
    if rate is not None:
        try:
            rate = Decimal(str(rate))
        except (InvalidOperation, ValueError):
            rate = None
        if rate is None or rate not in ALLOWED_GST_RATES:
            _issue(
                warnings,
                "unsupported_gst_rate",
                "gst_rate",
                "GST rate is outside the configured rate slabs.",
                "warning",
            )
    for field, length in (("hsn", (4, 6, 8)), ("sac", (6,))):
        value = data.get(field)
        if value and (not str(value).isdigit() or len(str(value)) not in length):
            _issue(
                errors,
                "invalid_hsn_sac",
                field,
                f"{field.upper()} must contain {'/'.join(map(str, length))} digits.",
                "error",
            )
    supplier_state = str(data.get("supplier_state_code") or "")[:2]
    place = str(data.get("place_of_supply") or "")[:2]
    if supplier_state and place:
        intra = supplier_state == place
        cgst, sgst, igst = (Decimal(str(data.get(k) or 0)) for k in ("cgst", "sgst", "igst"))
        if intra and (igst != 0 or cgst != sgst):
            _issue(
                errors,
                "intra_state_tax_mismatch",
                "tax",
                "Intra-state supply requires equal CGST and SGST and no IGST.",
                "error",
            )
        if not intra and (cgst != 0 or sgst != 0):
            _issue(
                errors, "inter_state_tax_mismatch", "tax", "Inter-state supply requires IGST and no CGST/SGST.", "error"
            )
    lines = data.get("line_items") or []
    for index, line in enumerate(lines):
        line_rate = line.get("rate")
        if line_rate is not None:
            try:
                parsed_line_rate = Decimal(str(line_rate))
            except (InvalidOperation, ValueError):
                parsed_line_rate = None
            if parsed_line_rate is None or parsed_line_rate not in ALLOWED_GST_RATES:
                _issue(warnings, "unsupported_gst_rate", f"line_items[{index}].rate", "Line GST rate is outside the configured rate slabs.", "warning")
        for field, length in (("hsn", (4, 6, 8)), ("sac", (6,))):
            value = line.get(field)
            if value and (not str(value).isdigit() or len(str(value)) not in length):
                _issue(errors, "invalid_hsn_sac", f"line_items[{index}].{field}", f"{field.upper()} has an invalid format.", "error")
        if line.get("taxable_value") is not None and line.get("rate") is not None and line.get("tax") is not None:
            try:
                expected = (Decimal(str(line["taxable_value"])) * Decimal(str(line["rate"])) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if abs(expected - Decimal(str(line["tax"]))) > Decimal("0.50"):
                    _issue(errors, "line_tax_mismatch", f"line_items[{index}].tax", "Line tax does not match taxable value multiplied by rate.", "error")
            except (InvalidOperation, TypeError):
                _issue(errors, "invalid_tax_math", f"line_items[{index}]", "Line tax fields must be numeric.", "error")
    stated = data.get("total_amount")
    if lines and stated is not None:
        try:
            line_total = sum((Decimal(str(x.get("total") or 0)) for x in lines), Decimal(0)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if abs(line_total - Decimal(str(stated))) > Decimal("0.50"):
                _issue(
                    errors,
                    "line_total_mismatch",
                    "total_amount",
                    "Invoice total does not match the line-item total.",
                    "error",
                )
        except (InvalidOperation, TypeError):
            _issue(errors, "invalid_tax_math", "line_items", "Line amounts must be numeric.", "error")
    if stated is not None and data.get("subtotal") is not None:
        try:
            expected_invoice = Decimal(str(data["subtotal"])) + sum((Decimal(str(data.get(k) or 0)) for k in ("cgst", "sgst", "igst")), Decimal(0))
            if abs(expected_invoice - Decimal(str(stated))) > Decimal("0.50"):
                _issue(errors, "invoice_tax_total_mismatch", "total_amount", "Invoice total does not match subtotal plus tax heads.", "error")
        except (InvalidOperation, TypeError):
            _issue(errors, "invalid_tax_math", "total_amount", "Invoice totals must be numeric.", "error")
    if data.get("classification") in {"tax_invoice", "debit_note"} and data.get("b2b") and not data.get("irn"):
        _issue(warnings, "possible_einvoice_gap", "irn", "B2B document has no IRN.", "warning")
    return {
        "passed": not errors,
        "warnings": warnings,
        "errors": errors,
        "normalized_invoice_number": invoice,
        "validation_status": "passed" if not errors else "needs_review",
    }
