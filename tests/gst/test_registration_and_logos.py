from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from PIL import Image

from app.services.registration import register
from app.services.gst import account
from app.db import get_db
from app.routes import current_user


def test_registration_creates_only_own_membership(profile):
    repo=Mock(settings=SimpleNamespace(gcp_project_id='test-project'))
    repo.table.side_effect=lambda name:'test-project.finance.'+name
    body=dict(email=' New@Example.com ',full_name='New User',business_name='New Business',gstin=profile['gstin'],password='StrongPassword123',confirm='StrongPassword123',country_code='+91',mobile_number='9876543210')
    result=register(repo,body)
    sql,params=repo.query.call_args.args
    values={p.name:p.value for p in params}
    assert values['email']=='new@example.com'
    assert result['client_id']==values['cid'] and result['id']==values['uid']
    assert "VALUES (@mid,@cid,@uid,'client'" in sql
    assert "'admin'" not in sql and 'COMMIT TRANSACTION' in sql
    assert values['password']!=body['password']
    assert 'LOWER(email)=@email' in sql


@pytest.mark.parametrize('change',[{'email':'bad'},{'password':'weak'},{'gstin':'invalid'},{'full_name':''},{'mobile_number':''},{'confirm':'different'}])
def test_invalid_registration_does_not_write(profile,change):
    repo=Mock()
    body=dict(email='a@example.com',full_name='Name',business_name='Business',gstin=profile['gstin'],password='StrongPassword123',confirm='StrongPassword123',country_code='+91',mobile_number='9876543210')
    with pytest.raises(HTTPException) as exc:register(repo,{**body,**change})
    assert exc.value.status_code==422
    repo.query.assert_not_called()


def test_logo_validates_content_permissions_and_normalizes(monkeypatch):
    user=SimpleNamespace(id='u',role='client');blob=Mock()
    monkeypatch.setattr(account,'active_client',lambda *a:SimpleNamespace(id='only-this-client'))
    monkeypatch.setattr(account,'can',lambda user,*a:user.role=='client')
    factory=Mock(return_value=blob);monkeypatch.setattr(account,'logo_blob',factory)
    app=FastAPI();app.include_router(account.router)
    app.dependency_overrides[get_db]=lambda:object()
    app.dependency_overrides[current_user]=lambda:user
    client=TestClient(app);url='/api/settings/profile/logo'
    assert client.post(url,files={'file':('logo.png',b'<svg/>','image/png')}).status_code==422
    assert client.post(url,files={'file':('logo.png',b'x'*(2*1024*1024+1),'image/png')}).status_code==413
    output=BytesIO();Image.new('RGB',(20,20)).save(output,format='JPEG')
    user.role='viewer'
    assert client.post(url,files={'file':('logo.jpg',output.getvalue(),'image/jpeg')}).status_code==403
    user.role='client'
    assert client.post(url,files={'file':('logo.jpg',output.getvalue(),'image/jpeg')}).status_code==200
    assert factory.call_args.args==('only-this-client',)
    assert blob.upload_from_string.call_args.args[0].startswith(b'\x89PNG')
