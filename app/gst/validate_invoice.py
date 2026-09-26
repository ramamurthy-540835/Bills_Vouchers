"""Pure, Decimal-only canonical GST invoice validation."""
import re
from decimal import Decimal

from app.services.gst.profiles import validate_gstin
from app.services.gst.rules import rule
from app.services.gst.validation import VALID_STATE_CODES
from .schemas.invoice import GstInvoice, Itc

RATES = {Decimal(s) for s in ('0', '0.1', '0.25', '1', '1.5', '3', '5', '6', '7.5', '12', '18', '28')}
HEADS = ('cgst', 'sgst', 'igst', 'cess')
TOLERANCE = Decimal('1.00')


def financial_year(day):
    return day.year if day.month >= 4 else day.year - 1


def duplicate_key(invoice):
    return (invoice.client_id, invoice.supplier_gstin.upper(), invoice.invoice_number.strip().upper(),
            financial_year(invoice.invoice_date) if invoice.invoice_date else None)


def validate_invoice(invoice: GstInvoice, profile: dict, existing=(), human_review=False):
    inv = invoice.model_copy(deep=True)
    reasons = []
    inv.supplier_gstin = inv.supplier_gstin.strip().upper()
    inv.recipient_gstin = inv.recipient_gstin.strip().upper()
    own = str(profile.get('gstin') or '').upper()
    if not own:
        reasons.append('client_gstin_missing')
    if inv.direction == 'purchase' and own and inv.recipient_gstin != own:
        reasons.append('recipient_gstin_mismatch')
    if inv.direction == 'sale' and own and inv.supplier_gstin != own:
        reasons.append('supplier_gstin_mismatch')
    for field in ('supplier_gstin', 'recipient_gstin'):
        value = getattr(inv, field)
        if not validate_gstin(value)['valid'] and not (inv.invoice_type == 'bill_of_supply' and field == 'supplier_gstin' and not value):
            reasons.append(field + '_invalid')
    inv.supplier_state_code = inv.supplier_gstin[:2] or inv.supplier_state_code
    inv.recipient_state_code = inv.recipient_gstin[:2] or inv.recipient_state_code
    if inv.place_of_supply_state_code not in VALID_STATE_CODES:
        reasons.append('place_of_supply_invalid')
    inv.supply_type = 'intra' if inv.supplier_state_code == inv.place_of_supply_state_code else 'inter'
    if not inv.invoice_date or not re.fullmatch(r'[A-Za-z0-9/\-]{1,16}', inv.invoice_number):
        reasons.append('invoice_identity_missing')
    if not inv.supplier_legal_name or not inv.line_items:
        reasons.append('invoice_details_missing')
    for line in inv.line_items:
        if not re.fullmatch(r'(?:\d{4}|\d{6}|\d{8})', line.hsn_sac) or (line.hsn_sac.startswith('99') and len(line.hsn_sac) != 6):
            reasons.append('hsn_invalid')
        if line.gst_rate not in RATES:
            reasons.append('rate_invalid')
        if min(line.taxable_value, line.cgst, line.sgst, line.igst, line.cess, line.quantity) < 0:
            reasons.append('negative_amount')
        tax = line.taxable_value * line.gst_rate / Decimal('100')
        if inv.supply_type == 'intra':
            if line.igst != 0 or abs(line.cgst-line.sgst) > TOLERANCE:
                reasons.append('tax_head_mismatch')
            if abs(line.cgst-tax/2) > TOLERANCE or abs(line.sgst-tax/2) > TOLERANCE:
                reasons.append('tax_arithmetic')
        else:
            if line.cgst != 0 or line.sgst != 0:
                reasons.append('tax_head_mismatch')
            if abs(line.igst-tax) > TOLERANCE:
                reasons.append('tax_arithmetic')
    for key in ('taxable_value', *HEADS):
        if abs(sum((getattr(line, key) for line in inv.line_items), Decimal('0')) - getattr(inv.totals, key)) > TOLERANCE:
            reasons.append('totals_mismatch')
    if abs(inv.totals.invoice_total-inv.totals.taxable_value-sum((getattr(inv.totals, h) for h in HEADS), Decimal('0'))) > TOLERANCE:
        reasons.append('invoice_total_mismatch')
    if inv.extraction.confidence < Decimal('0.85') and not human_review:
        reasons.append('low_confidence')
    buckets = []
    for line in inv.line_items:
        category = 'vehicle' if line.hsn_sac.startswith('87') else 'insurance_repair' if line.hsn_sac.startswith(('9971', '9987')) else 'other'
        if line.gst_rate == 0:
            buckets.append(('non_gst', 'No GST charged'))
        else:
            buckets.append(rule({'itc_category': category}, profile))
    blocked = next((ref for bucket, ref in buckets if bucket == 'blocked'), '')
    inv.itc = Itc(eligibility='blocked_17_5' if blocked else 'ineligible_non_gst' if buckets and all(b == 'non_gst' for b, _ in buckets) else 'eligible', blocked_reason=blocked)
    if inv.reverse_charge:
        reasons.append('reverse_charge_review')
    inv.review_reasons = list(dict.fromkeys(reasons))
    inv.status = 'needs_review' if reasons else 'extracted'
    if reasons:
        inv.itc.eligibility = 'pending_review'
    if any(other.invoice_id != inv.invoice_id and other.status != 'rejected' and duplicate_key(other) == duplicate_key(inv) for other in existing):
        inv.status = 'rejected'
        inv.review_reasons.append('duplicate_invoice')
    return inv
