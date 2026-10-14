import json
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

import pytest
from pydantic import ValidationError
from app.gst.file_checks import validate_file
from app.gst.matching import parse_gstr2b
from app.gst.report import calculate
from app.gst.schemas.invoice import LineItem
from app.gst.template import template_bytes


def test_four_scenarios_and_mixed_invoice(invoice,profile):
    invoice.status='confirmed'
    invoice.line_items.append(LineItem(description='Office',hsn_sac='998313',taxable_value='100',gst_rate='18',cgst='9',sgst='9'))
    invoice.totals.taxable_value+=Decimal('100');invoice.totals.cgst+=Decimal('9');invoice.totals.sgst+=Decimal('9');invoice.totals.invoice_total+=Decimal('118')
    sale=invoice.model_copy(deep=True);sale.invoice_id='sale';sale.direction='sale';sale.invoice_number='SALE'
    row={'supplier_gstin':invoice.supplier_gstin,'invoice_number':invoice.invoice_number,'invoice_date':str(invoice.invoice_date),'itc_available':True,**invoice.totals.model_dump()}
    result=calculate([invoice,sale],{**profile,'business_nature':'trading'},[row])
    assert result['totals']['eligible_credit']==Decimal('18')
    assert result['scenarios']=={'recorded':Decimal('0'),'matched':Decimal('0'),'eligible':Decimal('180'),'noCredit':Decimal('198')}
    assert result['totals']['non_gst']==Decimal('1180')
    assert result['matches']['matched']==1
    absent=calculate([invoice,sale],profile,[])
    assert absent['totals']['eligible_credit']==0 and absent['scenarios']['matched']==198


def test_sample_and_review_records_never_count(invoice,profile):
    assert calculate([invoice],profile,[])['confirmed_count']==0


def test_unmatched_credit_note_still_reduces_credit(invoice,profile):
    invoice.status='confirmed'
    note=invoice.model_copy(deep=True);note.invoice_id='note';note.invoice_number='CN-1';note.invoice_type='credit_note'
    row={'supplier_gstin':invoice.supplier_gstin,'invoice_number':invoice.invoice_number,'invoice_date':str(invoice.invoice_date),'itc_available':True,**invoice.totals.model_dump()}
    result=calculate([invoice,note],profile,[row])
    assert result['totals']['eligible_credit']==Decimal('0')
    assert result['matches']=={'matched':1,'unmatched':1,'amount_mismatch':0}
    invoice.status='confirmed';invoice.sample=True
    assert calculate([invoice],profile,[])['confirmed_count']==0


def test_gstr2b_period_tenant_and_tax(invoice,profile):
    payload={'data':{'gstin':profile['gstin'],'rtnprd':'092026','docdata':{'b2b':[
        {'ctin':invoice.supplier_gstin,'inv':[{'inum':invoice.invoice_number,'dt':'01-09-2026','txval':'1000','cgst':'90','sgst':'90','igst':'0','cess':'0'}]}]}}}
    rows=parse_gstr2b(json.dumps(payload),profile,'2026-09')
    assert rows[0]['cgst']==Decimal('90')
    assert rows[0]['invoice_date']=='2026-09-01'
    assert rows[0]['itc_available'] is False
    assert len(rows[0]['source_sha256'])==64
    with pytest.raises(ValueError):parse_gstr2b(json.dumps(payload),profile,'2026-10')
    with pytest.raises(ValueError):parse_gstr2b(json.dumps(payload),{**profile,'gstin':invoice.supplier_gstin},'2026-09')
    payload['sample']=True
    with pytest.raises(ValueError):parse_gstr2b(json.dumps(payload),profile,'2026-09')


@pytest.mark.parametrize('change',[{'invoice_date':'2025-09-01'},{'invoice_date':''},{'invoice_number':'INV1'}])
def test_probable_or_wrong_date_match_does_not_grant_credit(invoice,profile,change):
    invoice.status='confirmed'
    row={'supplier_gstin':invoice.supplier_gstin,'invoice_number':invoice.invoice_number,
         'invoice_date':str(invoice.invoice_date),'itc_available':True,**invoice.totals.model_dump(),**change}
    result=calculate([invoice],profile,[row])
    assert result['matches']['unmatched']==1
    assert result['totals']['eligible_credit']==0


def test_duplicate_statement_candidates_and_missing_availability_fail_closed(invoice,profile):
    invoice.status='confirmed'
    row={'supplier_gstin':invoice.supplier_gstin,'invoice_number':invoice.invoice_number,
         'invoice_date':str(invoice.invoice_date),'itc_available':True,**invoice.totals.model_dump()}
    assert calculate([invoice],profile,[row])['totals']['eligible_credit']==Decimal('180')
    assert calculate([invoice],profile,[row,row])['totals']['eligible_credit']==0
    row.pop('itc_available')
    assert calculate([invoice],profile,[row])['totals']['eligible_credit']==0


def test_unsupported_statement_sections_are_not_silently_discarded(profile):
    payload={'data':{'gstin':profile['gstin'],'rtnprd':'092026','docdata':{'b2b':[],'cdnr':[{'note':'unsupported'}]}}}
    with pytest.raises(ValueError,match='not yet supported'):
        parse_gstr2b(json.dumps(payload),profile,'2026-09')


@pytest.mark.parametrize('content,name',[(b'not a pdf','bill.pdf'),(b'not a photo','bill.png'),(b'bad zip','bill.xlsx'),(b'\x00text','bill.csv')])
def test_signature_validation(content,name):
    with pytest.raises((ValueError,OSError)):validate_file(content,name)


def test_xlsx_template_signature_and_external_link():
    validate_file(template_bytes(),'bills.xlsx')
    buffer=BytesIO()
    with ZipFile(buffer,'w') as archive:
        archive.writestr('[Content_Types].xml','x');archive.writestr('xl/workbook.xml','x');archive.writestr('xl/externalLinks/link.xml','x')
    with pytest.raises(ValueError):validate_file(buffer.getvalue(),'bills.xlsx')


@pytest.mark.parametrize('value',['garbage','NaN','Infinity',1.1])
def test_invalid_money_is_validation_error(value):
    with pytest.raises(ValidationError):LineItem(taxable_value=value)
