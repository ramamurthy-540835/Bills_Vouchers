"""Executable deterministic cases; unimplemented visual/legal cases explicitly skip."""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.gst.auto_review import evaluate, review_invoice
from app.gst.comparison import price_breakdown
from app.gst.extract import parse_response
from app.gst.validate_invoice import duplicate_key
from tests.gst.test_auto_review import store as store_fixture

CASES=json.loads((Path(__file__).parents[1]/'fixtures/auto_review/scenario_manifest.json').read_text())
EXECUTABLE={'B01','B02','B03','B04','B05','B07','B08','B09','C01','C02','C03','C04','C06','C09','C10',
            'D01','E01','E02','E03','E04','E10','F02','F03','F04','F05','F07','F08','G01','G03',
            'H02','H03','H04','H05','H06','H08','I07','J07','K01','K03','K04','K08','L03','L04','L05','L06','L07','L09'}


@pytest.fixture
def store(invoice):
    return store_fixture.__wrapped__(invoice)


@pytest.mark.parametrize('case',CASES,ids=[c['scenario_id'] for c in CASES])
def test_scenario(case,store,profile):
    code=case['scenario_id'];inv=store.state.current
    if code not in EXECUTABLE:
        pytest.skip('Specialized extraction, valuation, integration or legal fixture not implemented; see coverage matrix')
    if code=='D01':
        assert price_breakdown('1180','18',True,'118')['total']=='1062.00'
        assert price_breakdown('1000','18',False,'100')['total']=='1062.00'
        return
    if code=='K01':
        with pytest.raises(ValueError):parse_response('not json','a','doc','original')
        return
    if code in {'H05','H06'}:
        other=inv.model_copy(deep=True)
        if code=='H05':other.invoice_date=date(2025,9,1)
        else:other.supplier_gstin=profile['gstin']
        assert duplicate_key(inv)!=duplicate_key(other)
        return
    if code in {'L03','L05','L06','L07','L09'}:
        if code in {'L03','L05'}:inv.status='confirmed'
        if code=='L06':store.state.locked=True
        if code=='L07':inv.auto_review.enabled=False
        if code=='L09':inv.version=2
        if code=='L06':
            from fastapi import HTTPException
            with pytest.raises(HTTPException):review_invoice(store,profile,'owner',inv.invoice_id,1)
        else:review_invoice(store,profile,'owner',inv.invoice_id,1)
        store.save.assert_not_called()
        return
    if code=='B01':inv.invoice_number=''
    if code=='B02':inv.invoice_date=None
    if code=='B03':inv.supplier_gstin='invalid'
    if code in {'B04','B09'}:inv.recipient_gstin=inv.supplier_gstin
    if code=='B05':inv.supplier_gstin,inv.recipient_gstin=inv.recipient_gstin,inv.supplier_gstin
    if code=='B07':inv.selected_period='2026-10'
    if code=='B08':inv.place_of_supply_state_code=''
    if code=='C02':inv.line_items[0].gst_rate=Decimal('12')
    if code in {'C03','C09'}:inv.line_items[0].cgst=Decimal('89.99')
    if code in {'C04','C10'}:inv.totals.invoice_total=Decimal('1181')
    if code=='C06':inv.totals.taxable_value=Decimal('999')
    if code=='E02':inv.line_items[0].hsn_sac='abc'
    if code=='E03':store.query.return_value*=2
    if code=='E04':store.query.return_value[0]['policy']['effective_from']='2027-01-01'
    if code=='E10':store.query.return_value[0]['policy']['identity_evidence']=''
    if code=='F03':inv.place_of_supply_state_code='29'
    if code=='F04':inv.line_items[0].igst=Decimal('180');inv.line_items[0].cgst=Decimal(0);inv.line_items[0].sgst=Decimal(0)
    if code=='F05':inv.line_items[0].cgst=Decimal('91');inv.line_items[0].sgst=Decimal('89')
    if code=='F07':inv.reverse_charge=True
    if code=='F08':inv.line_items[0].cess=Decimal('5');inv.totals.cess=Decimal('5')
    if code=='G01':inv.invoice_type='credit_note'
    if code=='G03':inv.invoice_type='debit_note'
    if code in {'H02','H03','H04'}:
        other=inv.model_copy(deep=True);other.invoice_id='duplicate';other.source_doc_id='different-bytes';store.list.side_effect=lambda:[inv,other]
    if code=='H08':inv.correction_state='resubmitted'
    if code=='I07':store.download_object.return_value=b''
    if code=='K03':inv.totals.taxable_value,inv.totals.invoice_total=inv.totals.invoice_total,inv.totals.taxable_value
    if code=='K04':inv.line_items[0].cgst=Decimal('900')
    if code=='K08':inv.supplier_legal_name=''
    if code=='J07':profile={**profile,'business_nature':'other'}
    result,reasons,checks,_=evaluate(store,inv,profile)
    if code in {'C01','E01','F02','J07','L04'}:
        assert reasons==[] and all(checks.values())
        if code=='J07':assert result.itc.eligibility=='blocked_17_5'
    else:
        assert reasons, code+' must never auto-confirm'


@pytest.mark.parametrize('inclusive,discount,expected',[(True,'0','1000.00'),(False,'0','1180.00'),(True,'118','900.00')])
def test_price_basis_uses_independent_expected_decimal_values(inclusive,discount,expected):
    assert price_breakdown('1180','18',inclusive,discount)['taxable_value']==expected
