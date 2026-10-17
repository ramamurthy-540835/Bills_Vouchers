from types import SimpleNamespace
from decimal import Decimal
import json
from pathlib import Path
import pytest
from app.gst.store import BillStore
from app.services import demo_identity
from app.services.gst.profiles import validate_gstin
from app.gst.matching import parse_gstr2b
from app.gst.schemas.invoice import GstInvoice, LineItem, Totals
from app.gst.validate_invoice import validate_invoice


def test_canonical_tables_are_isolated_and_default_unchanged():
    for prefix in ['', 'gst_easy_v2_']:
        repo=SimpleNamespace(settings=SimpleNamespace(gcp_project_id='test-project',gst_dataset_prefix=prefix))
        assert BillStore(repo,'client').table('gold','gst_invoice')==f'`test-project.{prefix}gold.gst_invoice`'
    repo.settings.gst_dataset_prefix='invalid.prefix'
    with pytest.raises(ValueError):BillStore(repo,'client').table('gold','gst_invoice')


@pytest.mark.parametrize('email', ['naturelabs@demo.com', 'naturelabs1@demo.com'])
def test_operator_activation_is_not_email_verification(monkeypatch, email):
    settings=SimpleNamespace(demo_operator_identity_enabled=True,bigquery_dataset='gst_easy_v2_finance_analytics',gst_dataset_prefix='gst_easy_v2_',gcs_bucket_name='aidirac-503309-gst-easy-v2-documents')
    monkeypatch.setattr(demo_identity,'get_settings',lambda:settings)
    user=SimpleNamespace(email=email,role='client',email_verified=False,demo_operator_activated=True,identity_provenance='SYNTHETIC_TEST_ONLY')
    assert demo_identity.identity_can_sign_in(user)
    assert user.email_verified is False
    for field,value in [('demo_operator_identity_enabled',False),('bigquery_dataset','finance_analytics'),('gst_dataset_prefix',''),('gcs_bucket_name','production')]:
        previous=getattr(settings,field);setattr(settings,field,value)
        assert not demo_identity.identity_can_sign_in(user)
        setattr(settings,field,previous)
    for field,value in [('email','someone@example.test'),('role','admin'),('demo_operator_activated',False),('identity_provenance','')]:
        previous=getattr(user,field);setattr(user,field,value)
        assert not demo_identity.identity_can_sign_in(user)
        setattr(user,field,previous)


def test_generated_invoices_and_statements_have_reproducible_decimal_totals():
    manifest=json.loads(Path('demo bills/TEST_MANIFEST.json').read_text(encoding='utf-8'))
    assert len(manifest['businesses'])==3 and len(manifest['invoices'])==28
    businesses={b['key']:b for b in manifest['businesses']}
    for inv in manifest['invoices']:
        b=businesses[inv['business']]
        assert validate_gstin(inv['supplier']['gstin'])['valid']
        assert validate_gstin(inv['recipient']['gstin'])['valid']
        for line in inv['line_items']:
            assert Decimal(line['quantity'])*Decimal(line['unit_price'])==Decimal(line['taxable_value'])
        model=GstInvoice(client_id=b['key'],source_doc_id=inv['invoice_number'],direction=inv['direction'],
            supplier_gstin=inv['supplier']['gstin'],recipient_gstin=inv['recipient']['gstin'],
            supplier_legal_name=inv['supplier']['legal_name'],recipient_legal_name=inv['recipient']['legal_name'],
            invoice_number=inv['invoice_number'],invoice_date=inv['invoice_date'],invoice_type=inv['invoice_type'],
            place_of_supply_state_code=inv['place_of_supply_state_code'],
            line_items=[LineItem(**{k:v for k,v in line.items() if k!='unit_price'}) for line in inv['line_items']],totals=Totals(**inv['totals']))
        validate_invoice(model,b)
        assert not model.review_reasons, model.review_reasons
    for b in businesses.values():
        rows=parse_gstr2b(Path('demo bills/gstr2b',b['key']+'.json').read_text(),b,'2026-10')
        assert len(rows)==4



def test_v2_report_view_permission_does_not_grant_platform_access(monkeypatch):
    from app.services import access
    monkeypatch.setattr(access, 'isolated_v2_demo', lambda: True)
    permissions=access.navigation_permissions(SimpleNamespace(role='client'),True,SimpleNamespace(is_test=True))
    assert 'view_reports' in permissions and 'platform_admin' not in permissions
