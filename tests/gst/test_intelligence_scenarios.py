"""Executable deterministic cases; unimplemented visual/legal cases explicitly skip."""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.gst.auto_review import evaluate, review_invoice
from app.gst.comparison import price_breakdown
from app.gst.extract import parse_response
from app.gst.schemas.invoice import GstInvoice, LineItem, Totals
from app.gst.validate_invoice import duplicate_key
from app.services.gst.validation import BASE36
from tests.gst.test_auto_review import store as store_fixture

CASES=json.loads((Path(__file__).parents[1]/'fixtures/auto_review/scenario_manifest.json').read_text())
EXECUTABLE={'B01','B02','B03','B04','B05','B07','B08','B09','C01','C02','C03','C04','C06','C09','C10',
            'D01','E01','E02','E03','E04','E10','F02','F03','F04','F05','F07','F08','G01','G03',
            'H02','H03','H04','H05','H06','H08','I07','J07','K01','K03','K04','K08','L03','L04','L05','L06','L07','L09'}
EXECUTABLE |= {'F01','G06','I01','I02','I03','I04','I05','J01','J02','J03','J04','J05','J06','J08'}


def _gstin(prefix):
    total, factor = 0, 2
    for char in reversed(prefix):
        product = BASE36.index(char) * factor
        total += product // 36 + product % 36
        factor = 1 if factor == 2 else 2
    return prefix + BASE36[(36 - total % 36) % 36]


@pytest.fixture
def profile():
    return {'gstin': _gstin('33ABCDE1234F1Z'), 'business_nature': 'passenger_transport'}


@pytest.fixture
def invoice(profile):
    return GstInvoice(
        client_id='a', source_doc_id='doc', supplier_gstin=_gstin('33BCDEF2345G1Z'),
        supplier_legal_name='Supplier', recipient_gstin=profile['gstin'], invoice_number='INV-1',
        invoice_date=date(2026, 9, 1), place_of_supply_state_code='33',
        line_items=[LineItem(description='Vehicle', hsn_sac='8703', taxable_value='1000.00',
                             gst_rate='18', cgst='90.00', sgst='90.00')],
        totals=Totals(taxable_value='1000.00', cgst='90.00', sgst='90.00', invoice_total='1180.00'),
    )


@pytest.fixture
def store(invoice):
    return store_fixture.__wrapped__(invoice)


@pytest.mark.parametrize('case',CASES,ids=[c['scenario_id'] for c in CASES])
def test_scenario(case,store,profile):
    code=case['scenario_id'];inv=store.state.current
    if code not in EXECUTABLE:
        pytest.skip('Specialized extraction, valuation, integration or legal fixture not implemented; see coverage matrix')
    if code in {'I01','I02','I03'}:
        from io import BytesIO
        from openpyxl import Workbook
        from app.gst.template import HEADERS,parse_template
        workbook=Workbook();sheet=workbook.active;sheet.title='Bills';sheet.append(HEADERS)
        first=[inv.supplier_gstin,'GROUP-1','01-09-2026','8703','Synthetic','100','18','9','9','0','0','236','33','N']
        sheet.append(first)
        second=list(first)
        if code=='I02':second[11]='235'
        if code=='I03':second[5]='=100+1'
        sheet.append(second)
        if code=='I01':
            third=list(first);third[1]='GROUP-2';third[11]='118';sheet.append(third)
        stream=BytesIO();workbook.save(stream)
        if code!='I01':
            with pytest.raises(ValueError):parse_template(stream.getvalue(),'.xlsx','a','doc',profile,'original')
        else:
            values=parse_template(stream.getvalue(),'.xlsx','a','doc',profile,'original')
            assert len(values)==2 and len(values[0].line_items)==2
            assert values[0].totals.taxable_value==Decimal('200') and values[0].totals.invoice_total==Decimal('236')
            assert all(v.extraction.raw_ref=='original' for v in values)
        return
    if code in {'I04','I05'}:
        from app.gst.file_checks import validate_file
        with pytest.raises(ValueError):validate_file(b'not a supported document','unsafe.zip' if code=='I04' else 'corrupt.pdf')
        return
    if code=='G06':
        from app.gst.report import calculate
        inv.status='rejected'
        assert calculate([inv],profile,[])['confirmed_count']==0
        assert calculate([inv],profile,[])['totals']['output_tax']==Decimal('0')
        return
    if code in {'J01','J02','J03','J04','J05','J08'}:
        from app.gst.reconciliation import compare
        inv.status='confirmed'
        row={'supplier_gstin':inv.supplier_gstin,'invoice_number':inv.invoice_number,
             'invoice_date':str(inv.invoice_date),**inv.totals.model_dump()}
        if code=='J04':row['cgst']='87'
        if code=='J05':inv.invoice_type='credit_note'
        if code=='J08':row['invoice_number']='INV1'
        result=compare([] if code=='J03' else [inv],[] if code=='J02' else [row])
        expected={'J01':{'exact':1},'J02':{'missing_statement':1},'J03':{'missing_book':1},
                  'J04':{'amount_mismatch':1},'J05':{'unsupported_document':1,'missing_book':1},
                  'J08':{'missing_statement':1,'missing_book':1}}
        assert result['counts']==expected[code] and not result['financial_override']
        if code=='J04':assert result['cases'][0]['differences']['cgst']==Decimal('3')
        return
    if code=='J06':
        from app.gst.matching import parse_gstr2b
        with pytest.raises(ValueError,match='selected return period'):
            parse_gstr2b(json.dumps({'gstin':profile['gstin'],'rtnprd':'082026','b2b':[]}),profile,'2026-09')
        return
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
    if code=='F01':
        inv.place_of_supply_state_code='29';inv.line_items[0].igst=Decimal('180')
        inv.line_items[0].cgst=Decimal('0');inv.line_items[0].sgst=Decimal('0')
        inv.totals.igst=Decimal('180');inv.totals.cgst=Decimal('0');inv.totals.sgst=Decimal('0')
        store.query.return_value[0]['policy'].update(supply_type='inter',place_of_supply='29')
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
    if code in {'C01','E01','F01','F02','J07','L04'}:
        assert reasons==[] and all(checks.values())
        if code=='J07':assert result.itc.eligibility=='blocked_17_5'
    else:
        assert reasons, code+' must never auto-confirm'


@pytest.mark.parametrize('inclusive,discount,expected',[(True,'0','1000.00'),(False,'0','1180.00'),(True,'118','900.00')])
def test_price_basis_uses_independent_expected_decimal_values(inclusive,discount,expected):
    assert price_breakdown('1180','18',inclusive,discount)['taxable_value']==expected
