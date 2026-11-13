import json
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

from fastapi import HTTPException

from app.services.gst.future_providers import GATES, enabled, require_enabled
from app.services.gst.method_a import assess, build_package


def test_method_a_uses_confirmed_invoice_and_marks_unverified_portal_schema(invoice, profile):
    profile['registration_type']='Regular'
    invoice.status='confirmed'
    result=assess([invoice],profile,[],'2026-09')
    assert result['valid'] is True
    assert result['confirmed_invoice_count']==1
    assert result['summary']['totals']['output_tax']==Decimal('0')
    assert any(w['code']=='PORTAL_SCHEMA_NOT_VERIFIED' for w in result['warnings'])
    assert result['submission_method'].startswith('taxpayer completes')


def test_method_a_blocks_nonregular_and_unresolved_invoice(invoice, profile):
    invoice.status='needs_review'
    result=assess([invoice],profile,[],'2026-09')
    codes={row['code'] for row in result['blockers']}
    assert not result['valid']
    assert 'TAXPAYER_TYPE_UNSUPPORTED' in codes
    assert 'INVOICES_NEED_REVIEW' in codes


def test_method_a_blocks_material_gstr2b_amount_mismatch(invoice, profile):
    profile['registration_type']='Regular'
    invoice.status='confirmed'
    statement=[{'supplier_gstin':invoice.supplier_gstin,'invoice_number':invoice.invoice_number,
        'invoice_date':invoice.invoice_date.isoformat(),'taxable_value':'1200.00','cgst':'108.00',
        'sgst':'108.00','igst':'0.00','cess':'0.00'}]
    result=assess([invoice],profile,statement,'2026-09')
    assert not result['valid']
    assert any(row['code']=='RECONCILIATION_AMOUNT_MISMATCH' for row in result['blockers'])


def test_filing_package_is_a_guided_worksheet_not_gstn_upload(invoice, profile):
    profile['registration_type']='Regular'
    invoice.status='confirmed'
    result=assess([invoice],profile,[],'2026-09')
    snapshot={'period':'2026-09','gstin':profile['gstin'],'invoices':[invoice.model_dump(mode='json')]}
    payload=build_package(snapshot,result,'snapshot-1','hash-1')
    with ZipFile(BytesIO(payload)) as package:
        manifest=json.loads(package.read('manifest.json'))
        readme=package.read('README.txt').decode()
        purchases=package.read('purchase_and_itc_review_worksheet.csv').decode('utf-8-sig')
        assert manifest['portal_upload_file'] is False
        assert manifest['package_type']=='GST_EASY_METHOD_A_GUIDED_WORKSHEETS'
        assert 'not an official GST Portal upload file' in readme
        assert invoice.invoice_number in purchases


def test_future_providers_fail_closed_even_when_config_flag_is_true():
    class Settings:
        pass
    for gate in GATES.values():
        settings=Settings()
        setattr(settings,gate.setting,True)
        assert enabled(gate.name,settings) is False
        try:
            require_enabled(gate.name,settings)
        except HTTPException as exc:
            assert exc.status_code==404
        else:
            raise AssertionError(f'{gate.name} unexpectedly enabled')
