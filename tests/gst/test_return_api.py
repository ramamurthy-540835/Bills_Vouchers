from types import SimpleNamespace
from unittest.mock import Mock
import json
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import get_db
from app.routes import current_user
from app.routers import gst_returns


@pytest.fixture
def api(monkeypatch,invoice,profile):
    profile['registration_type']='Regular'
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


def test_validate_is_read_only_and_returns_human_readable_summary(api):
    http,_,invoice,write=api
    response=http.post('/api/gst/returns/validate?period=2026-09',json={'version':0})
    assert response.status_code==200
    body=response.json()
    assert body['valid'] is True
    assert body['confirmed_invoice_count']==1
    assert any(item['code']=='PORTAL_SCHEMA_NOT_VERIFIED' for item in body['warnings'])
    write.assert_not_called()


def test_validate_rejects_stale_version(api):
    http,_,_,write=api
    assert http.post('/api/gst/returns/validate?period=2026-09',json={'version':4}).status_code==409
    write.assert_not_called()


def test_approved_method_a_package_is_private_and_explicitly_not_portal_json(api,monkeypatch):
    http,client,invoice,_=api
    invoice.status='confirmed'
    approved_store=Mock();approved_store.list.return_value=[invoice];approved_store.matching_rows.return_value=[]
    approved_store.query.return_value=[];approved_store.upload_object.return_value='gs://private-bucket/private/key'
    monkeypatch.setattr(gst_returns,'scope',lambda *args:(client,approved_store))
    state={'state':'approved','snapshot_id':'snapshot-1','source_hash':'stable'}
    monkeypatch.setattr(gst_returns.returns,'current',lambda *args:state)
    monkeypatch.setattr(gst_returns.returns,'snapshot',lambda *args:{'period':'2026-09','gstin':'33ABCDE1234F1Z7','invoices':[invoice.model_dump(mode='json')]})
    package=http.get('/api/gst/returns/filing-package?period=2026-09')
    assert package.status_code==200
    assert package.headers['content-type'].startswith('application/zip')
    assert package.headers['cache-control']=='private, no-store'
    with ZipFile(BytesIO(package.content)) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        assert manifest['portal_upload_file'] is False
    audit_details=json.loads(approved_store.query.call_args.args[1][-1].value)
    assert audit_details['portal_upload_file'] is False
    assert approved_store.upload_object.call_args.args[3]=='filing-packages'


@pytest.mark.parametrize('body',[{}, {'version':True}, {'version':-1}, {'version':0,'reason':None}])
def test_return_mutation_requires_valid_version_and_reason(api,body):
    http,_,_,write=api
    assert http.post('/api/gst/returns/prepare?period=2026-09',json=body).status_code==422
    write.assert_not_called()
