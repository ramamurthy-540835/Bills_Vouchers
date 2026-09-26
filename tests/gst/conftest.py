from datetime import date
import pytest
from app.gst.schemas.invoice import GstInvoice, LineItem, Totals
from app.services.gst.validation import BASE36


def gstin(prefix):
    total, factor = 0, 2
    for char in reversed(prefix):
        product = BASE36.index(char)*factor
        total += product//36 + product%36
        factor = 1 if factor == 2 else 2
    return prefix+BASE36[(36-total%36)%36]


@pytest.fixture
def profile():
    return {'gstin': gstin('33ABCDE1234F1Z'), 'business_nature': 'passenger_transport'}


@pytest.fixture
def invoice(profile):
    return GstInvoice(client_id='a',source_doc_id='doc',supplier_gstin=gstin('33BCDEF2345G1Z'),
        supplier_legal_name='Supplier',recipient_gstin=profile['gstin'],invoice_number='INV-1',
        invoice_date=date(2026,9,1),place_of_supply_state_code='33',
        line_items=[LineItem(description='Vehicle',hsn_sac='8703',taxable_value='1000.00',gst_rate='18',cgst='90.00',sgst='90.00')],
        totals=Totals(taxable_value='1000.00',cgst='90.00',sgst='90.00',invoice_total='1180.00'))
