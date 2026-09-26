from datetime import date
from decimal import Decimal
import pytest
from pydantic import ValidationError
from app.gst.validate_invoice import validate_invoice, duplicate_key, RATES
from app.gst.schemas.invoice import LineItem


def test_valid_checksum_and_passenger_exception(invoice, profile):
    result=validate_invoice(invoice,profile)
    assert result.status=='extracted' and result.itc.eligibility=='eligible'
    invoice.supplier_gstin=invoice.supplier_gstin[:-1]+'!'
    assert 'supplier_gstin_invalid' in validate_invoice(invoice,profile).review_reasons


def test_trader_blocked_and_rate_restrictions(invoice, profile):
    assert validate_invoice(invoice,{**profile,'business_nature':'trading'}).itc.eligibility=='blocked_17_5'
    assert validate_invoice(invoice,{**profile,'itc_rate_restricted':True}).itc.eligibility=='blocked_17_5'


@pytest.mark.parametrize('hsn',['997134','998714','8708'])
def test_insurance_repairs_exception(invoice, profile, hsn):
    invoice.line_items[0].hsn_sac=hsn
    assert validate_invoice(invoice,profile).itc.eligibility=='eligible'
    assert validate_invoice(invoice,{**profile,'business_nature':'trading'}).itc.eligibility=='blocked_17_5'


def test_missing_gstin_and_mismatch(invoice, profile):
    result=validate_invoice(invoice,{})
    assert result.itc.eligibility=='pending_review' and 'client_gstin_missing' in result.review_reasons
    assert 'recipient_gstin_mismatch' in validate_invoice(invoice,{**profile,'gstin':'different'}).review_reasons


def test_interstate_and_head_mismatch(invoice, profile):
    invoice.place_of_supply_state_code='29'
    result=validate_invoice(invoice,profile)
    assert result.supply_type=='inter' and 'tax_head_mismatch' in result.review_reasons
    invoice.line_items[0].cgst=invoice.line_items[0].sgst=Decimal('0')
    invoice.line_items[0].igst=Decimal('180')
    invoice.totals.cgst=invoice.totals.sgst=Decimal('0')
    invoice.totals.igst=Decimal('180')
    assert not validate_invoice(invoice,profile).review_reasons


def test_tolerance(invoice, profile):
    invoice.totals.invoice_total+=Decimal('1.00')
    assert 'invoice_total_mismatch' not in validate_invoice(invoice,profile).review_reasons
    invoice.totals.invoice_total+=Decimal('0.01')
    assert 'invoice_total_mismatch' in validate_invoice(invoice,profile).review_reasons


def test_financial_year_duplicate(invoice, profile):
    other=invoice.model_copy(deep=True);other.invoice_id='other'
    invoice.invoice_date=date(2026,3,31);other.invoice_date=date(2026,4,1)
    assert duplicate_key(invoice)!=duplicate_key(other)
    assert validate_invoice(invoice,profile,[other]).status!='rejected'
    other.invoice_date=date(2026,3,1)
    assert validate_invoice(invoice,profile,[other]).review_reasons==['duplicate_invoice']
    other.client_id='b'
    assert validate_invoice(invoice,profile,[other]).status!='rejected'


@pytest.mark.parametrize('code',['123','12345','9912','99001234','abcd'])
def test_hsn(invoice,profile,code):
    invoice.line_items[0].hsn_sac=code
    assert 'hsn_invalid' in validate_invoice(invoice,profile).review_reasons


def test_rate_list_and_decimal(invoice,profile):
    assert len(RATES)==12
    invoice.line_items[0].gst_rate=Decimal('17')
    assert 'rate_invalid' in validate_invoice(invoice,profile).review_reasons
    with pytest.raises(ValidationError):
        LineItem(taxable_value=1.01)
    assert isinstance(invoice.totals.invoice_total,Decimal)
    assert isinstance(invoice.model_dump(mode='json')['totals']['invoice_total'],str)
