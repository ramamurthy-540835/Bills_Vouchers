"""Two-sided reconciliation evidence. Never grants or overrides tax credit."""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

FIELDS = ('taxable_value', 'cgst', 'sgst', 'igst', 'cess')


def identity(row):
    return (str(row.get('supplier_gstin', '')).strip().upper(),
            str(row.get('invoice_number', '')).strip().upper())


def amounts(row):
    result = {}
    for field in FIELDS:
        try:
            value = Decimal(str(row[field]))
            result[field] = value if value.is_finite() else None
        except (KeyError, TypeError, ValueError, InvalidOperation):
            result[field] = None
    return result


def compare(invoices, statements):
    """Keep every statement row, with date-only candidates explicitly unapproved."""
    books = [inv for inv in invoices if inv.status == 'confirmed' and not inv.sample
             and inv.direction == 'purchase']
    by_identity = defaultdict(list)
    book_counts = Counter((inv.supplier_gstin.strip().upper(), inv.invoice_number.strip().upper(),
                           str(inv.invoice_date or '')) for inv in books)
    for position, row in enumerate(statements):
        by_identity[identity(row)].append(position)
    used = set()
    cases = []
    for inv in sorted(books, key=lambda item: item.invoice_id):
        key = (inv.supplier_gstin.strip().upper(), inv.invoice_number.strip().upper())
        candidates = by_identity.get(key, [])
        exact = [pos for pos in candidates if str(statements[pos].get('invoice_date', '')) == str(inv.invoice_date or '')]
        supported = inv.invoice_type == 'tax_invoice'
        selected = (exact or candidates) if supported else []
        used.update(selected)
        duplicate = book_counts[(*key, str(inv.invoice_date or ''))] > 1 or len(selected) > 1
        values = amounts(inv.totals.model_dump())
        statement = statements[selected[0]] if len(selected) == 1 else None
        statement_values = amounts(statement) if statement else None
        delta = {field: values[field] - statement_values[field]
                 if values[field] is not None and statement_values[field] is not None else None
                 for field in FIELDS} if statement_values else None
        if not supported:
            status = 'unsupported_document'
        elif not all(key) or not inv.invoice_date:
            status = 'incomplete_identity'
        elif duplicate:
            status = 'ambiguous'
        elif not selected:
            status = 'missing_statement'
        elif not exact:
            status = 'date_mismatch'
        elif delta is None or any(value is None for value in delta.values()):
            status = 'incomplete_amounts'
        elif any(abs(value) > Decimal('1') for value in delta.values() if value is not None):
            status = 'amount_mismatch'
        elif any(value != 0 for value in delta.values()):
            status = 'within_tolerance'
        else:
            status = 'exact'
        cases.append({'id': 'bill:' + inv.invoice_id, 'invoice_id': inv.invoice_id,
                      'supplier_gstin': inv.supplier_gstin, 'invoice_number': inv.invoice_number,
                      'invoice_date': str(inv.invoice_date or ''), 'status': status,
                      'book_amounts': values, 'statement_amounts': statement_values, 'differences': delta,
                      'statement_candidates': [public_statement(statements[pos], pos) for pos in selected]})
    for position, row in enumerate(statements):
        if position not in used:
            cases.append({'id': f'statement:{position}', 'invoice_id': None,
                          'supplier_gstin': row.get('supplier_gstin', ''),
                          'invoice_number': row.get('invoice_number', ''),
                          'invoice_date': str(row.get('invoice_date', '')),
                          'status': 'missing_book', 'book_amounts': None,
                          'statement_amounts': amounts(row), 'differences': None,
                          'statement_candidates': [public_statement(row, position)]})
    return {'cases': cases, 'counts': dict(Counter(case['status'] for case in cases)),
            'confirmed_purchase_count': len(books), 'statement_count': len(statements),
            'tolerance_per_head': '1.00', 'financial_override': False}


def public_statement(row, position):
    return {**{key: row.get(key) for key in ('supplier_gstin', 'invoice_number', 'invoice_date',
                                           'source_sha256', 'statement_period', 'itc_available')},
            'position': position, 'amounts': amounts(row)}
