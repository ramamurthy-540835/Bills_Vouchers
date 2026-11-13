"""Taxpayer-controlled GST portal preparation. No endpoint in this module files returns."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from decimal import Decimal
from collections.abc import Sequence
from zipfile import ZIP_DEFLATED, ZipFile

from app.gst.reconciliation import compare
from app.gst.report import calculate
from app.gst.schemas.invoice import GstInvoice
from app.services.gst.validation import valid_gstin


def assess(invoices: list[GstInvoice], profile: dict, statement: list[dict], period: str) -> dict:
    """Return review blockers and warnings for a human-prepared portal return."""
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def add(target, code, message):
        target.append({'code': code, 'message': message})

    if not valid_gstin(str(profile.get('gstin') or '')):
        add(blockers, 'GSTIN_REQUIRED', 'Complete the business profile with a structurally valid GSTIN.')
    if str(profile.get('registration_type') or '').strip().lower() not in {'regular', 'regular taxpayer'}:
        add(blockers, 'TAXPAYER_TYPE_UNSUPPORTED', 'This filing preparation currently supports regular taxpayers only.')
    pending = [invoice for invoice in invoices if invoice.status in {'needs_review', 'extracted'}]
    rejected = [invoice for invoice in invoices if invoice.status == 'rejected']
    if pending:
        add(blockers, 'INVOICES_NEED_REVIEW', f'{len(pending)} invoice(s) still need review or confirmation.')
    if rejected:
        add(blockers, 'REJECTED_INVOICES_UNRESOLVED', f'{len(rejected)} rejected invoice(s) need resolution or an approved exclusion decision.')
    if any(invoice.status not in {'confirmed', 'rejected', 'needs_review', 'extracted'} for invoice in invoices):
        add(blockers, 'INVOICE_STATE_UNSUPPORTED', 'Resolve invoices with an incomplete or unsupported processing state.')
    confirmed = [invoice for invoice in invoices if invoice.status == 'confirmed' and not invoice.sample]
    if not confirmed:
        add(blockers, 'NO_CONFIRMED_INVOICES', 'No confirmed invoices are available; nil-return preparation is not supported in this workflow.')
    for invoice in confirmed:
        if invoice.invoice_date and invoice.invoice_date.strftime('%Y-%m') != period:
            add(blockers, 'PERIOD_MISMATCH', f'Invoice {invoice.invoice_number or invoice.invoice_id} is outside the selected period.')
    summary = calculate(confirmed, profile, statement) if confirmed else None
    recon = compare(confirmed, statement) if confirmed else {'counts': {}, 'cases': []}
    counts = recon.get('counts', {})
    for status in ('amount_mismatch', 'ambiguous', 'incomplete_amounts', 'incomplete_identity', 'date_mismatch'):
        if counts.get(status, 0):
            add(blockers, 'RECONCILIATION_' + status.upper(), f'Resolve {counts[status]} GSTR-2B reconciliation issue(s) before preparing this return.')
    if not statement and any(invoice.direction == 'purchase' for invoice in confirmed):
        add(warnings, 'GSTR2B_NOT_IMPORTED', 'No taxpayer-provided GSTR-2B is imported. The package does not establish ITC availability; verify the portal record and do not claim unestablished credit.')
    if counts.get('missing_statement', 0):
        add(warnings, 'PURCHASES_NOT_IN_GSTR2B', f'{counts["missing_statement"]} confirmed purchase invoice(s) have no matching statement record.')
    if counts.get('missing_book', 0):
        add(warnings, 'STATEMENT_ONLY_ITEMS', f'{counts["missing_book"]} statement record(s) have no matching confirmed purchase invoice.')
    if counts.get('unsupported_document', 0):
        add(warnings, 'UNSUPPORTED_RECONCILIATION_DOCUMENT', f'{counts["unsupported_document"]} document(s) use a statement section not supported by the current importer.')
    add(warnings, 'PORTAL_SCHEMA_NOT_VERIFIED', 'The package contains guided worksheets, not GST Portal upload files. Confirm current portal values and complete filing on gst.gov.in.')
    return {'valid': not blockers, 'period': period, 'gstin': profile.get('gstin', ''),
            'confirmed_invoice_count': len(confirmed), 'blockers': blockers, 'warnings': warnings,
            'summary': summary, 'reconciliation': recon,
            'submission_method': 'taxpayer completes the official portal steps; GST Easy does not submit or verify filing'}


def _csv(rows: Sequence[Sequence[object]]) -> bytes:
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue().encode('utf-8-sig')


def _text(value: object) -> str:
    text = str(value or '')
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text


def build_package(snapshot: dict, assessment: dict, snapshot_id: str, source_hash: str) -> bytes:
    """Build private, reviewed filing worksheets. Never emits a government-schema payload."""
    if not assessment.get('valid') or assessment.get('period') != snapshot.get('period'):
        raise ValueError('A current validated snapshot is required.')
    invoices = [GstInvoice.model_validate(row) for row in snapshot.get('invoices', [])]
    summary = assessment.get('summary') or {}
    files: dict[str, bytes] = {}
    files['approved_snapshot.json'] = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2, default=str).encode('utf-8')
    files['validation_and_reconciliation.json'] = json.dumps(assessment, ensure_ascii=False, sort_keys=True, indent=2, default=str).encode('utf-8')
    sales = [['Invoice number', 'Date', 'Document type', 'Recipient GSTIN', 'Place of supply', 'HSN/SAC',
              'Description', 'Taxable value', 'GST rate', 'IGST', 'CGST', 'SGST', 'Cess',
              'Invoice total (invoice-level; do not sum across lines)']]
    purchases = [['Invoice number', 'Date', 'Supplier GSTIN', 'Supplier', 'Document type', 'Taxable value',
                  'IGST', 'CGST', 'SGST', 'Cess', 'Invoice total']]
    for invoice in invoices:
        sign = Decimal('-1') if invoice.invoice_type == 'credit_note' else Decimal('1')
        if invoice.direction == 'sale':
            for line in invoice.line_items:
                sales.append([_text(invoice.invoice_number), str(invoice.invoice_date or ''), _text(invoice.invoice_type),
                    _text(invoice.recipient_gstin), _text(invoice.place_of_supply_state_code), _text(line.hsn_sac),
                    _text(line.description), str(line.taxable_value * sign), str(line.gst_rate),
                    str(line.igst * sign), str(line.cgst * sign), str(line.sgst * sign), str(line.cess * sign),
                    str(invoice.totals.invoice_total * sign)])
        elif invoice.direction == 'purchase':
            purchases.append([_text(invoice.invoice_number), str(invoice.invoice_date or ''), _text(invoice.supplier_gstin),
                _text(invoice.supplier_legal_name), _text(invoice.invoice_type), str(invoice.totals.taxable_value * sign),
                str(invoice.totals.igst * sign), str(invoice.totals.cgst * sign), str(invoice.totals.sgst * sign),
                str(invoice.totals.cess * sign), str(invoice.totals.invoice_total * sign)])
    files['gstr1_sales_entry_worksheet.csv'] = _csv(sales)
    files['purchase_and_itc_review_worksheet.csv'] = _csv(purchases)
    gstr3b = [['Section', 'Tax head', 'Prepared value (INR)', 'Source / review note']]
    heads = summary.get('heads') or {}
    for head in ('igst', 'cgst', 'sgst', 'cess'):
        gstr3b.append(['3.1 outward tax summary', head.upper(), str((heads.get('output') or {}).get(head, '0.00')), 'Derived from confirmed sales; review portal table mapping'])
        gstr3b.append(['4 eligible credit summary', head.upper(), str((heads.get('credit') or {}).get(head, '0.00')), 'After current bill and imported statement checks; verify in portal'])
        gstr3b.append(['Estimated cash after credit', head.upper(), str((heads.get('cash') or {}).get(head, '0.00')), 'Estimate only; excludes unverified ledger balances, payments and final portal adjustments'])
    files['gstr3b_portal_entry_worksheet.csv'] = _csv(gstr3b)
    checks = [['Severity', 'Code', 'Message']]
    checks.extend([['BLOCKER', row['code'], row['message']] for row in assessment.get('blockers', [])])
    checks.extend([['WARNING', row['code'], row['message']] for row in assessment.get('warnings', [])])
    files['checks.csv'] = _csv(checks)
    readme = f'''GST Easy Method A filing preparation package\n\nBusiness GSTIN: {snapshot.get('gstin','')}\nPeriod: {snapshot.get('period','')}\nSnapshot ID: {snapshot_id}\nSnapshot source hash: {source_hash}\n\nThis is a preparation and review package, not an official GST Portal upload file, payment receipt, acknowledgement, or proof of filing. GSTR-1 and GSTR-3B worksheets are for manual review and entry. Check the current portal, tax period, applicability, legal rules, balances, payment and acknowledgements at https://www.gst.gov.in/. GST Easy does not log into the portal, submit returns, pay tax, use OTP/DSC/EVC, or verify customer-entered filing evidence.\n\nIncluded files: approved snapshot, sales entry worksheet, purchase/ITC worksheet, GSTR-3B entry worksheet, checks, and reconciliation/validation data. Have the responsible tax professional review all mapping, eligibility, rates, adjustments, and exceptions before portal entry.\n'''
    files['README.txt'] = readme.encode('utf-8')
    manifest = {'package_type': 'GST_EASY_METHOD_A_GUIDED_WORKSHEETS', 'portal_upload_file': False,
                'period': snapshot.get('period'), 'gstin': snapshot.get('gstin'), 'snapshot_id': snapshot_id,
                'source_hash': source_hash, 'sha256': {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()}}
    files['manifest.json'] = json.dumps(manifest, indent=2, sort_keys=True).encode('utf-8')
    output = io.BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return output.getvalue()
