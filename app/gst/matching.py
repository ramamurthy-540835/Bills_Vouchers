import json
from datetime import datetime
from decimal import Decimal

from app.services.gst.profiles import validate_gstin
from app.services.gst.validation import normalize_invoice_number


def parse_gstr2b(content, profile, period):
    payload = json.loads(content, parse_float=Decimal)
    if not isinstance(payload, dict) or payload.get('sample') or payload.get('mode') == 'sample':
        raise ValueError('Choose your downloaded GSTR-2B JSON, not an illustration.')
    own = profile.get('gstin')
    if not own or not validate_gstin(own)['valid']:
        raise ValueError('Add your business GSTIN before importing GSTR-2B.')
    root = payload.get('data', payload)
    if root.get('gstin', payload.get('gstin')) != own:
        raise ValueError('The GSTR-2B GSTIN does not match your business.')
    if root.get('rtnprd', payload.get('rtnprd')) != datetime.strptime(period, '%Y-%m').strftime('%m%Y'):
        raise ValueError('Choose the GSTR-2B statement for the selected return period.')
    suppliers = root.get('docdata', root).get('b2b', [])
    records = []
    seen = set()
    for supplier in suppliers:
        gstin = supplier.get('ctin', '')
        if not validate_gstin(gstin)['valid']:
            raise ValueError('A supplier GSTIN in the statement is invalid.')
        for invoice in supplier.get('inv', []):
            number = str(invoice.get('inum', ''))
            key = (gstin, normalize_invoice_number(number))
            if not number or key in seen:
                raise ValueError('The statement contains missing or repeated invoice numbers.')
            seen.add(key)
            amounts = {h: Decimal('0') for h in ('taxable_value', 'cgst', 'sgst', 'igst', 'cess')}
            details = invoice.get('items', invoice.get('itms', []))
            # GST portal exports use either item arrays or invoice-level totals.
            details = details or [invoice]
            for item in details:
                item = item.get('itm_det', item)
                for field, source in [('taxable_value', 'txval'), ('cgst', 'cgst'), ('sgst', 'sgst'), ('igst', 'igst'), ('cess', 'cess')]:
                    fallback = {'cgst':'camt','sgst':'samt','igst':'iamt','cess':'csamt'}.get(source, source)
                    amount = Decimal(str(item.get(source, item.get(fallback, '0'))))
                    if not amount.is_finite() or amount < 0:
                        raise ValueError('Check the amounts in the GSTR-2B statement.')
                    amounts[field] += amount
            records.append({'supplier_gstin': gstin, 'invoice_number': number,
                            'itc_available': str(invoice.get('itcavl', 'Y')).upper() == 'Y', **amounts})
    if len(records) > 10000:
        raise ValueError('Import at most 10,000 statement invoices at once.')
    return records
