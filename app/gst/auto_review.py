"""Opt-in confirmation. A known rate slab is NOT proof of rate applicability."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from google.api_core.exceptions import NotFound

from .validate_invoice import validate_invoice


def now():
    return datetime.now(timezone.utc).isoformat()


def approved_rules(store, invoice):
    try:
        return store.query(f'''SELECT policy FROM {store.table('ops','gst_auto_review_rules')}
            WHERE client_id=@client_id AND enabled=TRUE''')
    except NotFound:
        return []  # Missing migration/approved rules must never authorize confirmation.


def evaluate(store, previous, profile):
    invoice = validate_invoice(previous, profile, store.list())
    reasons = list(invoice.review_reasons)
    if previous.correction_state != 'none':
        reasons.append('Corrected or resubmitted bills require authorized manual approval through the correction workflow.')
    if not all((invoice.supplier_address.strip(), invoice.recipient_address.strip(), invoice.recipient_legal_name.strip())):
        reasons.append('Complete supplier address, recipient legal name and recipient address before Auto Review.')
    if any(not line.description.strip() for line in invoice.line_items):
        reasons.append('Every invoice line requires an item or service description.')
    checks = {'required_fields': not reasons, 'duplicate': 'duplicate_invoice' not in reasons}
    if previous.sample:
        reasons.append('Illustration invoices cannot be auto-confirmed.')
    if previous.invoice_type != 'tax_invoice' or previous.reverse_charge or previous.totals.cess:
        reasons.append('This document type, reverse-charge or cess scenario requires manual review.')
    # Auto confirmation uses rounded exact cents, stricter than manual review tolerance.
    arithmetic = True
    for line in invoice.line_items:
        tax = line.taxable_value * line.gst_rate / 100
        half = (tax / 2).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        full = tax.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        actual = (line.cgst, line.sgst, line.igst)
        expected = (half, half, Decimal(0)) if invoice.supply_type == 'intra' else (Decimal(0), Decimal(0), full)
        arithmetic = arithmetic and actual == expected and not line.cess
    heads = ('taxable_value', 'cgst', 'sgst', 'igst', 'cess')
    totals = all(sum((getattr(line, h) for line in invoice.line_items), Decimal(0)) == getattr(invoice.totals, h) for h in heads)
    totals = totals and sum((getattr(invoice.totals, h) for h in heads), Decimal(0)) == invoice.totals.invoice_total
    checks.update(gst_calculation=arithmetic, invoice_total=totals)
    if not arithmetic:
        reasons.append('GST amounts must match the independently calculated tax heads to the paisa.')
    if not totals:
        reasons.append('Invoice totals must exactly match the line amounts and tax heads.')
    try:
        checks['original_evidence'] = bool(previous.extraction.raw_ref and store.download_object(previous.extraction.raw_ref))
    except Exception:
        checks['original_evidence'] = False
    if not checks['original_evidence']:
        reasons.append('Original evidence is unavailable. Restore authorized evidence access and retry.')
    import json
    policies = [json.loads(row['policy']) if isinstance(row['policy'], str) else row['policy'] for row in approved_rules(store, invoice)]
    rule_ids = []
    day = invoice.invoice_date.isoformat() if invoice.invoice_date else ''
    for line in invoice.line_items:
        matching = [p for p in policies if
            p.get('review_status') == 'approved' and p.get('approved_by') and p.get('official_source')
            and p.get('identity_evidence') and p.get('policy_id')
            and p.get('supplier_gstin') == invoice.supplier_gstin and p.get('recipient_gstin') == invoice.recipient_gstin
            and p.get('hsn_sac') == line.hsn_sac and p.get('direction') == invoice.direction
            and p.get('supply_type') == invoice.supply_type and p.get('place_of_supply') == invoice.place_of_supply_state_code
            and p.get('invoice_type') == invoice.invoice_type and str(p.get('rate')) == str(line.gst_rate)
            and p.get('effective_from', '9999') <= day <= p.get('effective_to', '')
            and p.get('review_expires_at', '') > now()]
        if len(matching) != 1:
            reasons.append(f'HSN/SAC {line.hsn_sac}: no unique current approved rate, supply and identity policy. Manual review required.')
        else:
            rule_ids.append(matching[0]['policy_id'])
    checks['gst_policy'] = bool(invoice.line_items) and len(rule_ids) == len(invoice.line_items)
    return invoice, list(dict.fromkeys(reasons)), checks, rule_ids


def review_invoice(store, profile, actor, invoice_id, version):
    previous = store.get(invoice_id)
    if previous.version != version or not previous.auto_review.enabled or previous.status in {'confirmed', 'rejected'}:
        return previous  # Cancellation, edit or manual decision won the version race.
    period = previous.invoice_date.strftime('%Y-%m') if previous.invoice_date else previous.selected_period
    store.assert_writable(period)
    invoice, reasons, checks, rules = evaluate(store, previous, profile)
    invoice.auto_review.status = 'manual_required' if reasons else 'auto_confirmed'
    invoice.auto_review.reasons = reasons
    invoice.auto_review.checks = checks
    invoice.auto_review.rule_ids = rules
    invoice.auto_review.completed_at = now()
    invoice.status = 'needs_review' if reasons else 'confirmed'
    invoice.version = previous.version + 1
    store.save(invoice, actor, 'auto_review_decision', previous, period)
    return invoice


def process_review_job(store, profile, actor, job):
    try:
        result = review_invoice(store, profile, actor, job['invoice_id'], job['invoice_version'])
        job['result'] = result.auto_review.status
    except HTTPException as exc:
        if exc.status_code not in (404, 409):
            raise
        job['result'] = 'cancelled'
    job['status'] = 'completed'
    store.job(job['job_id'], job)
    return job
