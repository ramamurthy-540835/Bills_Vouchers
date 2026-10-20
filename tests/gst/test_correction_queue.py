from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.db import get_db
from app.routes import current_user
from app.routers import gst_bills
from app.gst.store import BillStore


def test_store_bounds_and_scopes_queue(invoice):
    calls=[]
    payload=invoice.model_dump(mode='json')
    # Older persisted invoices need not contain any correction metadata.
    for key in list(payload):
        if key.startswith('correction_'):
            del payload[key]
    payload['status']='rejected'
    repo=SimpleNamespace(settings=SimpleNamespace(gcp_project_id='test-project'),
        query=lambda sql,params:(calls.append((sql,params)) or [
            {'payload':payload,'correction_stage':'rejected'} for _ in range(51)]))
    result=BillStore(repo,'business-a').correction_queue('2026-09','active',50)
    assert len(result['invoices'])==50 and result['has_more']
    assert result['invoices'][0]['correction_stage']=='rejected'
    assert result['invoices'][0]['correction_state']=='none'
    sql,params=calls[0]
    values={p.name:p.value for p in params}
    assert values=={'client_id':'business-a','period':'2026-09','state':'active','offset':50}
    assert 'WHERE client_id=@client_id AND period=@period' in sql
    assert 'LIMIT 51 OFFSET @offset' in sql
    assert not any(word in sql for word in ('INSERT','UPDATE','DELETE'))


@pytest.fixture
def queue_api(monkeypatch,invoice):
    calls=[]
    def scoped(request,repo,user):
        if user.id=='unauthorized':
            raise HTTPException(403)
        class Store:
            def correction_queue(self,period,state,offset):
                calls.append((period,state,offset))
                return {'invoices':[],'has_more':False}
        return SimpleNamespace(id='business-a'),Store()
    monkeypatch.setattr(gst_bills,'scope',scoped)
    monkeypatch.setattr(gst_bills,'selected_period',lambda request,client,store,period:period or '2026-09')
    user=SimpleNamespace(id='viewer',role='viewer')
    app=FastAPI()
    app.include_router(gst_bills.router)
    app.dependency_overrides[get_db]=lambda:None
    app.dependency_overrides[current_user]=lambda:user
    return TestClient(app),user,calls


def test_queue_readonly_and_non_cached(queue_api):
    client,_,calls=queue_api
    response=client.get('/api/gst/bills/corrections?period=2026-09&state=corrected&offset=50')
    assert response.status_code==200
    assert response.headers['cache-control']=='private, no-store'
    assert response.json()['next_offset'] is None
    assert calls==[('2026-09','corrected',50)]


@pytest.mark.parametrize('query',['state=unrecognized','offset=-1','offset=100001','offset=abc'])
def test_queue_rejects_invalid_filter(queue_api,query):
    client,_,calls=queue_api
    assert client.get('/api/gst/bills/corrections?'+query).status_code==422
    assert not calls


def test_queue_requires_authorized_scope(queue_api):
    client,user,calls=queue_api
    user.id='unauthorized'
    assert client.get('/api/gst/bills/corrections').status_code==403
    assert not calls
