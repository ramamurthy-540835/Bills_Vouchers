"""Bounded, deterministic search over already tenant-scoped evidence."""
import re

from fastapi import HTTPException

from .rules import amount


def search_evidence(documents, q='', status='', minimum=None, maximum=None, offset=0, limit=20):
    if len(q) > 250 or status not in ('', 'validated', 'needs_review', 'failed'):
        raise HTTPException(422, 'Invalid search query or status')
    try:
        low = amount(minimum) if minimum not in (None, '') else None
        high = amount(maximum) if maximum not in (None, '') else None
    except (ValueError, ArithmeticError):
        raise HTTPException(422, 'Amounts must be valid decimal values')
    if low is not None and high is not None and low > high:
        raise HTTPException(422, 'Minimum amount exceeds maximum')
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, 'Invalid pagination')
    terms = re.findall(r'[\w-]+', q.casefold())
    result = []
    for doc in documents:
        header = doc.get('silver') or {}
        haystack = ' '.join(str(value or '') for value in [doc.get('original_filename'), doc.get('stage'),
            header.get('supplier_name'), header.get('supplier_gstin'), header.get('invoice_no'),
            header.get('invoice_date'), doc.get('search_text')]).casefold()
        if not all(term in haystack for term in terms):
            continue
        if status and header.get('validation_status') != status:
            continue
        total = header.get('total')
        if (low is not None or high is not None) and total is None:
            continue
        value = amount(total)
        if low is not None and value < low or high is not None and value > high:
            continue
        result.append(doc)
    return {'results': result[offset:offset+limit], 'total': len(result), 'offset': offset,
            'limit': limit, 'searched_count': len(documents)}
