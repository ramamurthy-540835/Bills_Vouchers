"""Exact source-event reconciliation. Never creates financial invoices."""
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from .validate_invoice import financial_year

INVOICE_TYPES = {'invoice': 'tax_invoice', 'credit_note': 'credit_note', 'debit_note': 'debit_note'}
AMOUNTS = {'taxable_amount': 'taxable_value', 'cgst': 'cgst', 'sgst': 'sgst',
           'igst': 'igst', 'cess': 'cess', 'invoice_total': 'invoice_total'}


def identity(record):
    """Both parties and financial year are mandatory; amounts are not identity."""
    day = date.fromisoformat(record.get('invoice_date', ''))
    kind = INVOICE_TYPES.get(record.get('event_type'))
    fields = [str(record.get(key, '')).strip().upper()
              for key in ('supplier_gstin', 'customer_gstin', 'invoice_number')]
    if not kind or not all(fields):
        raise ValueError('Missing invoice identity')
    return (*fields, financial_year(day), kind)


def canonical_identity(invoice):
    return (invoice.supplier_gstin.strip().upper(), invoice.recipient_gstin.strip().upper(),
            invoice.invoice_number.strip().upper(), financial_year(invoice.invoice_date),
            invoice.invoice_type)


def reconcile(records, related, invoices, client_id, period):
    """Inputs are already scoped/bounded; defend tenant scope again for invoices."""
    canonical = defaultdict(list)
    for invoice in invoices:
        if invoice.client_id != client_id:
            raise ValueError('Cross-business invoice data')
        if invoice.invoice_date and invoice.invoice_date.isoformat()[:7] == period:
            canonical[canonical_identity(invoice)].append(invoice)

    # Resolve source identity to the latest version; never silently select one
    # of two different payloads claiming the same source identity/version.
    versions: dict[tuple[str, str], dict[tuple[int, str], dict[str, Any]]] = defaultdict(dict)
    for row in [*related, *records]:
        record = row['payload']
        source_key = (record['source_system'], record['source_record_id'])
        key = (int(record['source_version']), record['source_hash'])
        versions[source_key][key] = record
    current = {}
    conflicts = set()
    for source_key, choices in versions.items():
        maximum = max(version for version, _ in choices)
        latest = [record for (version, _), record in choices.items() if version == maximum]
        if len(latest) != 1:
            conflicts.add(source_key)
        else:
            current[source_key] = latest[0]

    def invoice_case(record):
        try:
            key = identity(record)
        except (ValueError, TypeError):
            return {'status': 'insufficient_identity', 'message': 'Invoice date, number, document type and both GSTINs are required.'}
        if record['invoice_date'][:7] != period:
            return {'status': 'outside_period', 'message': 'Select the invoice reporting period.'}
        candidates = canonical.get(key, [])
        if len(candidates) > 1:
            return {'status': 'ambiguous_invoice', 'message': 'Multiple canonical invoices share this identity; resolve duplicates.'}
        if not candidates:
            return {'status': 'source_only', 'message': 'No canonical invoice with this identity. Upload and review the original bill.'}
        invoice = candidates[0]
        link = {'invoice_id': invoice.invoice_id, 'invoice_version': invoice.version,
                'invoice_status': invoice.status,
                'href': f'/bills?period={period}&invoice={invoice.invoice_id}'}
        if invoice.status == 'rejected':
            return {**link, 'status': 'rejected_invoice', 'message': 'The matching bill is rejected; no financial approval is implied.'}
        missing = [field for field in AMOUNTS if field not in record]
        differences = {}
        for source_field, target_field in AMOUNTS.items():
            if source_field in record:
                delta = Decimal(record[source_field]) - getattr(invoice.totals, target_field)
                if delta:
                    differences[source_field] = str(delta)
        if invoice.invoice_date.isoformat() != record['invoice_date']:
            differences['invoice_date'] = 'Source and canonical dates differ.'
        if differences:
            return {**link, 'status': 'details_mismatch', 'differences': differences,
                    'message': 'Identity matches, but source values differ. Review the evidence.'}
        if missing:
            return {**link, 'status': 'incomplete_amounts', 'missing_fields': missing,
                    'message': 'Identity matches; missing source amounts prevent full comparison.'}
        return {**link, 'status': 'matched' if invoice.status == 'confirmed' else 'invoice_needs_review',
                'message': 'Source values match the canonical invoice; its review status is unchanged.'}

    # A trip/booking reference can connect a nonfinancial event only through an
    # unambiguous source invoice with a complete, exact canonical match.
    references = defaultdict(list)
    for source_key, record in current.items():
        if source_key in conflicts or record.get('event_type') not in INVOICE_TYPES:
            continue
        case = invoice_case(record)
        for field in ('trip_id', 'booking_id'):
            if record.get(field):
                references[(field, record[field])].append(case)
    for source_key in conflicts:
        for record in versions[source_key].values():
            if record.get('event_type') in INVOICE_TYPES:
                for field in ('trip_id', 'booking_id'):
                    if record.get(field):
                        references[(field, record[field])].append({'status': 'source_conflict'})

    results = []
    for row in records:
        record = row['payload']
        source_key = (record['source_system'], record['source_record_id'])
        result = {key: record.get(key) for key in ('source_system', 'source_record_id', 'source_version', 'source_hash', 'event_type')}
        current_record = current.get(source_key)
        if source_key in conflicts:
            case = {'status': 'source_conflict', 'message': 'Conflicting payloads have the same source identity and version.'}
        elif current_record and int(record['source_version']) < int(current_record['source_version']):
            case = {'status': 'superseded_source', 'message': 'A newer source version exists. Review that import instead.'}
        elif row.get('status') == 'duplicate_or_conflict':
            case = {'status': 'duplicate_source', 'message': 'This staged row was marked duplicate/conflicting and requires review.'}
        elif record.get('event_type') in INVOICE_TYPES:
            case = invoice_case(record)
        else:
            reference_groups = [references.get((field, record[field]), [])
                                for field in ('trip_id', 'booking_id') if record.get(field)]
            candidates = [case for group in reference_groups for case in group]
            ids = {case['invoice_id'] for case in candidates if case.get('invoice_id')}
            if candidates and all(reference_groups) and len(ids) == 1 and all(case['status'] == 'matched' for case in candidates):
                matched = candidates[0]
                case = {**{key: matched[key] for key in ('invoice_id', 'invoice_version', 'invoice_status', 'href')},
                        'status': 'linked_event', 'message': 'Reference linked to an invoice; this event does not create tax or prove payment.'}
            elif candidates:
                case = {'status': 'ambiguous_reference', 'message': 'Trip/booking references do not resolve to one fully matched invoice.'}
            else:
                case = {'status': 'unlinked_event', 'message': 'No verified invoice reference. This event remains separate from financial invoices.'}
        results.append({**result, **case})
    return {'period': period, 'records': results, 'counts': dict(Counter(r['status'] for r in results)),
            'financial_records_created': 0, 'financial_records_changed': 0,
            'policy': 'Exact identity and Decimal comparison only. No invoice approval, payment confirmation or ITC decision.'}
