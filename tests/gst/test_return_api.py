from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import get_db
from app.routes import current_user
from app.routers import gst_returns


@pytest.fixture
def api(monkeypatch,invoice,profile):
    client=SimpleNamespace(id='a',is_test=False)
    user=SimpleNamespace(id='maker',role='client')
    store=Mock();store.list.return_value=[invoice];store.matching_rows.return_value=[]
    store.query.return_value=[]
    invoice.status='confirmed'
    monkeypatch.setattr(gst_returns,'scope',lambda *args:(client,store))
    monkeypatch.setattr(gst_returns,'profile_for',lambda *args:profile)
    monkeypatch.setattr(gst_returns.returns,'fingerprint',lambda *args:'stable')
    write=Mock(return_value={'state':'prepared','version':1})
    monkeypatch.setattr(gst_returns.returns,'change',write)
    app=FastAPI();app.include_router(gst_returns.router)
    app.dependency_overrides[get_db]=lambda:object()
    app.dependency_overrides[current_user]=lambda:user
    return TestClient(app),client,invoice,write


def test_preparation_uses_canonical_snapshot_not_portal_claim(api):
    http,client,invoice,write=api
    result=http.post('/api/gst/returns/prepare?period=2026-09',json={'version':0})
    assert result.status_code==200
    payload=write.call_args.args[6]
    assert payload['draft'] and not payload['portal_upload_ready']
    assert payload['invoices'][0]['invoice_id']==invoice.invoice_id
    assert payload['summary']['confirmed_count']==1


def test_pending_or_synthetic_records_cannot_prepare(api):
    http,client,invoice,write=api
    invoice.status='needs_review'
    assert http.post('/api/gst/returns/prepare?period=2026-09',json={'version':0}).status_code==409
    invoice.status='confirmed';client.is_test=True
    assert http.post('/api/gst/returns/prepare?period=2026-09',json={'version':0}).status_code==403
    write.assert_not_called()


@pytest.mark.parametrize('body',[{}, {'version':True}, {'version':-1}, {'version':0,'reason':None}])
def test_return_mutation_requires_valid_version_and_reason(api,body):
    http,_,_,write=api
    assert http.post('/api/gst/returns/prepare?period=2026-09',json=body).status_code==422
    write.assert_not_called()
