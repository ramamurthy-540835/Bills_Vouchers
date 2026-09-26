from types import SimpleNamespace
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.db import get_db
from app.routes import current_user
from app.config import get_settings
from app.routers import gst_bills


@pytest.fixture
def api(monkeypatch,invoice,profile):
    monkeypatch.setenv('GST_BILLS_ENABLED','true');get_settings.cache_clear()
    repo=SimpleNamespace()
    user=SimpleNamespace(id='u',role='viewer')
    items={invoice.invoice_id:invoice}
    class Store:
        def __init__(self,repo,client_id):self.client_id=client_id
        def list(self,*args):return [i for i in items.values() if i.client_id==self.client_id]
        def get(self,id):
            inv=items.get(id)
            if not inv or inv.client_id!=self.client_id:raise HTTPException(404,'Bill not found.')
            return inv
        def save(self,inv,*args,**kwargs):items[inv.invoice_id]=inv
    monkeypatch.setattr(gst_bills,'BillStore',Store)
    monkeypatch.setattr(gst_bills,'active_client',lambda *a:SimpleNamespace(id='a'))
    monkeypatch.setattr(gst_bills,'profile_for',lambda *a:profile)
    import app.services.gst.account as account
    monkeypatch.setattr(account,'FinanceRepository',lambda _:SimpleNamespace(can_access_client=lambda uid,cid:cid=='a'))
    app=FastAPI();app.include_router(gst_bills.router)
    app.dependency_overrides[get_db]=lambda:repo
    app.dependency_overrides[current_user]=lambda:user
    yield TestClient(app),user,items
    get_settings.cache_clear()


def test_viewer_read_export_but_no_writes(api,invoice):
    client,user,_=api
    assert client.get('/api/gst/bills?period=2026-09').status_code==200
    assert client.get('/api/gst/bills/export?period=2026-09&format=csv').status_code==200
    assert client.get('/api/gst/bills/template.xlsx').status_code==200
    assert client.post('/api/gst/bills/upload?period=2026-09',files={'files':('bill.csv',b'csv','text/csv')}).status_code==403
    assert client.post(f'/api/gst/bills/{invoice.invoice_id}/confirm').status_code==403
    assert client.patch(f'/api/gst/bills/{invoice.invoice_id}',json={'invoice_number':'CHANGE'}).status_code==403


def test_cross_client_id_is_not_found(api,invoice):
    client,user,items=api
    other=invoice.model_copy(deep=True);other.invoice_id='other';other.client_id='b';items['other']=other
    for role in ('viewer','client','admin','tax_admin'):
        user.role=role
        assert client.get('/api/gst/bills/other').status_code==404
        assert client.get('/api/gst/bills/other/original').status_code==404
        assert 'other' not in client.get('/api/gst/bills?period=2026-09').text
    assert client.post('/api/gst/bills/other/confirm').status_code==404
    assert client.patch('/api/gst/bills/other',json={'invoice_number':'X'}).status_code==404


def test_client_can_confirm_but_not_change_tenant(api,invoice):
    client,user,items=api;user.role='client'
    assert client.patch(f'/api/gst/bills/{invoice.invoice_id}',json={'client_id':'b'}).status_code==422
    response=client.post(f'/api/gst/bills/{invoice.invoice_id}/confirm')
    assert response.status_code==200 and response.json()['status']=='confirmed'
    assert isinstance(response.json()['totals']['invoice_total'],str)


def test_sample_export_blocked(api,invoice):
    client,user,items=api;invoice.sample=True
    response=client.get('/api/gst/bills/export?period=2026-09')
    assert response.status_code==403 and response.json()['detail']['code']=='sample_data_blocked'


def test_missing_profile_prevents_confirmation(api,invoice,monkeypatch):
    client,user,_=api;user.role='client'
    monkeypatch.setattr(gst_bills,'profile_for',lambda *a:{})
    assert client.post(f'/api/gst/bills/{invoice.invoice_id}/confirm').status_code==409
