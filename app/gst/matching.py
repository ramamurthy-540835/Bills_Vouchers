import json
import hashlib
from datetime import datetime
from decimal import Decimal

from app.services.gst.profiles import validate_gstin


def parse_gstr2b(content, profile, period):
    payload = json.loads(content, parse_float=Decimal)
    if not isinstance(payload, dict) or payload.get('sample') or payload.get('mode') == 'sample':
        raise ValueError('Choose your downloaded GSTR-2B JSON, not an illustration.')
    own = profile.get('gstin')
    if not own or not validate_gstin(own)['valid']:
        raise ValueError('Add your business GSTIN before importing GSTR-2B.')
    root = payload.get('data', payload)
    if not isinstance(root,dict):
        raise ValueError('Invalid GSTR-2B data object.')
    if root.get('gstin', payload.get('gstin')) != own:
        raise ValueError('The GSTR-2B GSTIN does not match your business.')
    if root.get('rtnprd', payload.get('rtnprd')) != datetime.strptime(period, '%Y-%m').strftime('%m%Y'):
        raise ValueError('Choose the GSTR-2B statement for the selected return period.')
    documents=root.get('docdata',root)
    if not isinstance(documents,dict) or not isinstance(documents.get('b2b'),list):
        raise ValueError('This importer requires a supported B2B statement section.')
    metadata={'b2b','gstin','rtnprd','version','gen_dt','chksum'}
    if any(value for key,value in documents.items() if key not in metadata):
        raise ValueError('This statement has sections not yet supported by the B2B importer.')
    suppliers = documents['b2b']
    source_hash=hashlib.sha256(content.encode() if isinstance(content,str) else content).hexdigest()
    records = []
    seen = set()
    for supplier in suppliers:
        if not isinstance(supplier,dict) or not isinstance(supplier.get('inv'),list):
            raise ValueError('Invalid supplier invoices.')
        gstin = supplier.get('ctin', '')
        if not validate_gstin(gstin)['valid']:
            raise ValueError('A supplier GSTIN in the statement is invalid.')
        for invoice in supplier.get('inv', []):
            if not isinstance(invoice,dict):
                raise ValueError('Invalid invoice record.')
            number = str(invoice.get('inum', ''))
            invoice_date=datetime.strptime(str(invoice.get('dt','')),'%d-%m-%Y').date().isoformat()
            key = (gstin, number.strip().upper(),invoice_date)
            if not number or key in seen:
                raise ValueError('The statement contains missing or repeated invoice numbers.')
            seen.add(key)
            amounts = {h: Decimal('0') for h in ('taxable_value', 'cgst', 'sgst', 'igst', 'cess')}
            details = invoice.get('items', invoice.get('itms', []))
            # GST portal exports use either item arrays or invoice-level totals.
            details = details or [invoice]
            if not isinstance(details,list):
                raise ValueError('Invalid invoice items.')
            for item in details:
                if not isinstance(item,dict):
                    raise ValueError('Invalid invoice item.')
                item = item.get('itm_det', item)
                if not isinstance(item,dict):
                    raise ValueError('Invalid invoice item details.')
                for field, source in [('taxable_value', 'txval'), ('cgst', 'cgst'), ('sgst', 'sgst'), ('igst', 'igst'), ('cess', 'cess')]:
                    fallback = {'cgst':'camt','sgst':'samt','igst':'iamt','cess':'csamt'}.get(source, source)
                    amount = Decimal(str(item.get(source, item.get(fallback, '0'))))
                    if not amount.is_finite() or amount < 0:
                        raise ValueError('Check the amounts in the GSTR-2B statement.')
                    amounts[field] += amount
            records.append({'supplier_gstin': gstin, 'invoice_number': number,'invoice_date':invoice_date,
                            'recipient_gstin':own,'statement_period':period,'source_sha256':source_hash,
                            'parser_version':'b2b-2','source_section':'b2b',
                            'itc_available': str(invoice.get('itcavl', '')).upper() == 'Y', **amounts})
    if len(records) > 10000:
        raise ValueError('Import at most 10,000 statement invoices at once.')
    return records
