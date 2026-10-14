"""Read-only adapters; canonical evidence is never merged with legacy totals."""
from urllib.parse import urlencode

from .naming import bill_filename


def documents(invoices,period):
    return [{'doc_id':inv.invoice_id,'original_filename':bill_filename(inv),'stage':inv.status,
             'href':'/bills?'+urlencode({'period':period,'invoice':inv.invoice_id}),
             'search_text':' '.join(line.description for line in inv.line_items),
             'silver':{'supplier_name':inv.supplier_legal_name,'supplier_gstin':inv.supplier_gstin,
                       'invoice_no':inv.invoice_number,'invoice_date':str(inv.invoice_date or ''),
                       'total':str(inv.totals.invoice_total),'validation_status':
                       'validated' if inv.status=='confirmed' else 'failed' if inv.status=='rejected' else 'needs_review',
                       'validation_errors':inv.review_reasons}} for inv in invoices]
