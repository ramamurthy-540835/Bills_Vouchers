from decimal import Decimal
from types import SimpleNamespace
from pathlib import Path
import ast

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.db import get_db
from app.routes import current_user
from app.fixtures.red_taxi_sample import generate, use_sample, sample_dashboard
from app.services.gst.medallion import Medallion
from app.services.gst.rules import HEADS, ZERO, amount
from app.services.gst.filing_workspace import working_papers, prepare_report
from app.services.gst.account import can, phone
from app.services.gst import workbench
from test_v5 import MemoryRepo, Row


@pytest.fixture
def repo(monkeypatch):
    monkeypatch.setenv('DEMO_FALLBACK','true')
    get_settings.cache_clear()
    result = MemoryRepo()
    result.tables['gst_client_profile'] = [Row(client_id=c,legal_name=name,is_current=True,gstin='',filing_frequency='monthly') for c,name in [('a','Red Taxi'),('b','Other client')]]
    yield result
    get_settings.cache_clear()


def test_fixture_counts_decimal_splits_and_setoff():
    t = generate('2026-09','a')['tables']
    assert len(t['silver_invoice_header'])==120
    assert len(t['silver_outward_invoice'])==13
    assert sum(r['igst']>ZERO for r in t['silver_invoice_header'])==1
    assert all(r['cgst']==r['sgst'] for r in t['silver_invoice_header'])
    assert sum(r['itc_category']=='vehicle' for r in t['silver_invoice_line'])==2
    assert sum(r['rule_ref']=='R37' for r in t['gold_itc_ledger'])==1
    assert any('17(5)(a)' in r['rule_ref'] for r in t['gold_itc_ledger'])
    assert any('17(5)(ab)' in r['rule_ref'] for r in t['gold_itc_ledger'])
    s = t['gold_filing_summary'][0]
    assert s['non_gst']>ZERO and s['cash_required']>=ZERO
    assert sum(s['cash_by_head'].values(),ZERO)==s['cash_required']
    for head in HEADS:
        assert s['eligible_by_head'][head]==sum((r['eligible_'+head] for r in t['gold_itc_ledger']),ZERO)
        assert s['output_by_head'][head]==sum((r[head] for r in t['silver_outward_invoice']),ZERO)
    assert all(isinstance(r['total'],Decimal) for r in t['silver_invoice_header'])
    assert all(not (u['from']=='cgst' and u['to']=='sgst') and not (u['from']=='sgst' and u['to']=='cgst') for u in s['utilisation'])
    with pytest.raises(ValueError):
        amount(1.1)


def test_fallback_is_tenant_period_bound_and_real_summary_wins(repo,monkeypatch):
    a,b = Medallion(repo,'a','2026-09'),Medallion(repo,'b','2026-09')
    assert use_sample(a) and not use_sample(b)
    result = sample_dashboard(a)
    assert result['sample'] and result['validated_invoices']==120
    assert result['client_id']=='a' and result['period']=='2026-09'
    assert 'Umesh' not in str(result) and '27AAPFU0939F1ZV' not in str(result)
    repo.tables['gold_filing_summary']=[Row(client_id='b',period='2026-09',run_id='real-other-client')]
    assert use_sample(a)
    repo.tables['gold_filing_summary'].append(Row(client_id='a',period='2026-09',run_id='real-current'))
    assert not use_sample(a)
    assert use_sample(Medallion(repo,'a','2026-10'))
    monkeypatch.setenv('DEMO_FALLBACK','false');get_settings.cache_clear()
    assert not use_sample(Medallion(repo,'a','2026-10'))
    repo.tables['gold_filing_summary'].append(Row(client_id='a',period='2026-10',run_id='synthetic_redtaxi_previous'))
    assert use_sample(Medallion(repo,'a','2026-10'))


def test_sample_write_and_export_guards(repo):
    with pytest.raises(HTTPException) as error:
        Medallion(repo,'a','2026-09').writable()
    assert error.value.status_code==403 and error.value.detail['code']=='sample_data_blocked'
    fixture=generate('2026-09','a')
    report=prepare_report('a','2026-09','month',['2026-09'],'2026-09',fixture['profile'],fixture['tables'])
    report['sample']=True
    with pytest.raises(HTTPException) as error:
        working_papers(report)
    assert error.value.detail['code']=='sample_data_blocked'


def test_cross_client_document_and_json_guard(repo,monkeypatch):
    app=FastAPI()
    app.add_middleware(SessionMiddleware,secret_key='unit-test')
    app.include_router(workbench.router)
    app.dependency_overrides[get_db]=lambda:repo
    app.dependency_overrides[current_user]=lambda:SimpleNamespace(id='u',email='u@example.test',role='client')
    monkeypatch.setattr(workbench,'active_client',lambda *args:SimpleNamespace(id='b'))
    with TestClient(app) as client:
        response=client.get('/api/pipeline/documents/sample-redtaxi-2026-09-001?period=2026-09&client_id=a')
        assert response.status_code==404
        monkeypatch.setattr(workbench,'active_client',lambda *args:SimpleNamespace(id='a'))
        response=client.post('/api/gst/filing/generate/gstr3b?period=2026-09')
        assert response.status_code==403 and response.json()['detail']['code']=='sample_data_blocked'


def test_phone_and_profile_permissions(monkeypatch):
    from app.services.gst.account import FinanceRepository
    monkeypatch.setattr(FinanceRepository,'can_access_client',lambda self,user,client:client=='a')
    user=SimpleNamespace(id='u',role='client')
    assert can(user,'edit_profile','a',object())
    assert not can(user,'edit_profile','b',object())
    assert not can(SimpleNamespace(id='v',role='viewer'),'edit_profile','a',object())
    assert phone('+919876543210')=='+919876543210'
    for invalid in ['9876543210','+91','abc','+0123456789']:
        with pytest.raises(HTTPException):phone(invalid)


def test_fixture_has_no_persistence_or_float_literals():
    source=Path('app/fixtures/red_taxi_sample.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    assert not any(isinstance(n,ast.Constant) and isinstance(n.value,float) for n in ast.walk(tree))
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
            assert node.func.attr not in {'insert','upsert','upload','query','execute','write_text','write_bytes'}


def test_sql_binds_tenant(repo):
    store=Medallion(repo,'a','2026-09')
    use_sample(store)
    for sql,params in repo.queries:
        assert 'client_id=@client_id' in sql
        assert any(p.name=='client_id' and p.value=='a' for p in params)
    tree=ast.parse(Path('app/services/gst/account.py').read_text())
    queries=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='query']
    for call in queries:
        sql=ast.unparse(call.args[0])
        assert ('WHERE id=@id' in sql or 'client_id=@client_id' in sql) and len(call.args)>1


def test_real_summary_displaces_previously_seeded_sample(repo):
    from app.services.gst.dashboard import customer_dashboard
    repo.tables['gold_filing_summary']=[
        Row(client_id='a',period='2026-09',run_id='synthetic_old',cash_required='999999'),
        Row(client_id='a',period='2026-09',run_id='real',cash_required='12.34')]
    store=Medallion(repo,'a','2026-09')
    assert not use_sample(store)
    assert customer_dashboard(store)['summary']['run_id']=='real'
    assert customer_dashboard(store)['totals']['cash_required']=='12.34'
    store.writable()  # The deployment flag does not block this real period.


def test_profile_update_rejects_client_override_and_parameterizes_values(monkeypatch):
    import asyncio
    from app.services.gst import account
    calls=[]
    class Repo:
        def table(self,name):return 'test.'+name
        def query(self,sql,params):calls.append((sql,params))
    class Request:
        def __init__(self,body):self.body=body
        async def json(self):return self.body
    monkeypatch.setattr(account,'active_client',lambda *args:SimpleNamespace(id='a'))
    monkeypatch.setattr(account,'can',lambda *args:True)
    monkeypatch.setattr(account.Medallion,'profile',lambda self:{'profile_id':'old','legal_name':'Red Taxi'})
    user=SimpleNamespace(id='u',role='client')
    with pytest.raises(HTTPException):
        asyncio.run(account.save_profile(Request({'client_id':'b','legal_name':'Bad'}),Repo(),user))
    assert not calls
    name="Business'; DELETE FROM users; --"
    asyncio.run(account.save_profile(Request({'client_id':'a','legal_name':name,'role':'admin'}),Repo(),user))
    sql,params=calls[0]
    assert name not in sql and 'role' not in sql
    assert next(p.value for p in params if p.name=='legal_name')==name
    assert 'BEGIN TRANSACTION' in sql and 'COMMIT TRANSACTION' in sql


def test_otp_required_stub_does_not_write(monkeypatch):
    import asyncio
    from app.services.gst import account
    monkeypatch.setattr(account,'get_settings',lambda:SimpleNamespace(require_otp=True))
    class Request:
        async def json(self):return {'full_name':'A User','mobile_number':'+919876543210'}
    with pytest.raises(HTTPException) as error:
        asyncio.run(account.save_account(Request(),object(),SimpleNamespace(mobile_number='')))
    assert error.value.status_code==409 and error.value.detail['code']=='otp_verification_required'
