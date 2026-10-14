import re
from pathlib import PurePosixPath


def bill_filename(invoice):
    extension = PurePosixPath(invoice.extraction.raw_ref).suffix.lower()
    gstin = invoice.supplier_gstin.strip().upper() or 'GSTIN-pending'
    number = invoice.invoice_number.strip() or f'invoice-pending-{invoice.invoice_id[:8]}'
    return re.sub(r'[^A-Za-z0-9._-]', '_', f'{gstin}_{number}')[:160] + extension
