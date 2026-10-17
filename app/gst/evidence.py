"""Read-only adapters; canonical evidence is never merged with legacy totals."""
from urllib.parse import urlencode
from decimal import Decimal

from .naming import bill_filename


def documents(invoices,period):
    return [{'doc_id':inv.invoice_id,'original_filename':bill_filename(inv),'stage':inv.status,
             'href':'/bills?'+urlencode({'period':period,'invoice':inv.invoice_id}),
             'search_text':' '.join([inv.recipient_legal_name, inv.recipient_gstin,
                                    *(line.description for line in inv.line_items)]),
             'silver':{'supplier_name':inv.supplier_legal_name,'supplier_gstin':inv.supplier_gstin,
                       'invoice_no':inv.invoice_number,'invoice_date':str(inv.invoice_date or ''),
                       'total':str(inv.totals.invoice_total),'validation_status':
                       'validated' if inv.status=='confirmed' else 'failed' if inv.status=='rejected' else 'needs_review',
                       'validation_errors':inv.review_reasons}} for inv in invoices]


def confirmed_summary(invoices):
    """Explicit register totals for grounded answers, excluding pending/rejected rows."""
    confirmed=[inv for inv in invoices if inv.status=='confirmed' and not inv.sample]
    return {**{f'confirmed_{label}':str(sum((inv.totals.invoice_total *
                    (Decimal('-1') if inv.invoice_type=='credit_note' else Decimal('1'))
                    for inv in confirmed if inv.direction==direction),Decimal('0')))
               for direction,label in [('sale','sales'),('purchase','purchases')]},
            'pending_review_count':sum(inv.status in {'extracted','needs_review'} for inv in invoices)}


def reconciliation_context(invoices, statements, imported):
    from .reconciliation import compare
    by_id={inv.invoice_id:inv for inv in invoices}
    return {'statement_imported':imported,
            'cases':[{**{key:case[key] for key in ('invoice_id','invoice_number','supplier_gstin','status')},
                      'supplier_name':by_id[case['invoice_id']].supplier_legal_name if case['invoice_id'] in by_id else 'Not recorded'}
                     for case in compare(invoices,statements)['cases']] if imported else []}
