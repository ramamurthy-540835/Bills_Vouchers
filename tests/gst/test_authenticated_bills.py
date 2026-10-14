from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from app import routes
from app.config import get_settings


@pytest.mark.parametrize('role,expected', [('client',None),('tax_admin',None),('admin',None),('viewer',403)])
def test_real_auth_allows_customer_upload_while_legacy_sample_is_read_only(monkeypatch,role,expected):
    monkeypatch.setenv('GST_BILLS_ENABLED','true');monkeypatch.setenv('MEDALLION_ENABLED','true');get_settings.cache_clear()
    user=SimpleNamespace(id='u',email='u@example.test',role=role,session_version=1,must_change_password=False)
    client=SimpleNamespace(id='a')
    monkeypatch.setattr(routes,'FinanceRepository',lambda repo:SimpleNamespace(user_by_id=lambda uid:user,clients=lambda uid:[client]))
    repo=SimpleNamespace(table=lambda t:'test.'+t,one=lambda *args:SimpleNamespace(role=role))
    from app.services.gst.medallion import Medallion
    def sample_guard(self):raise HTTPException(403,{'code':'sample_data_blocked'})
    monkeypatch.setattr(Medallion,'writable',sample_guard)
    def request(path):return Request({'type':'http','method':'POST','path':path,'headers':[], 'query_string':b'period=2026-09','session':{'user_id':'u','session_version':1},'server':('test',80),'scheme':'http'})
    if expected:
        with pytest.raises(HTTPException) as exc:routes.current_user(request('/api/gst/bills/upload'),repo)
        assert exc.value.status_code==expected
    else:
        resolved=routes.current_user(request('/api/gst/bills/upload'),repo)
        assert resolved.role==('client' if role=='admin' else role)
        assert resolved.is_platform_admin is False
        with pytest.raises(HTTPException):routes.current_user(request('/api/pipeline/upload'),repo)
    get_settings.cache_clear()


@pytest.mark.parametrize('path',['/api/gst/filing/generate/gstr3b','/api/gst/filing/transition'])
def test_test_workspace_cannot_generate_or_file(monkeypatch,path):
    monkeypatch.setenv('MEDALLION_ENABLED','true');get_settings.cache_clear()
    user=SimpleNamespace(id='u',role='client',session_version=1,must_change_password=False)
    client=SimpleNamespace(id='a',is_test=True)
    monkeypatch.setattr(routes,'FinanceRepository',lambda repo:SimpleNamespace(user_by_id=lambda uid:user,clients=lambda uid:[client]))
    request=Request({'type':'http','method':'POST','path':path,'headers':[], 'query_string':b'', 'session':{'user_id':'u','session_version':1},'server':('test',80),'scheme':'http'})
    with pytest.raises(HTTPException) as error:routes.current_user(request,SimpleNamespace())
    assert error.value.status_code==403 and error.value.detail['code']=='sample_data_blocked'
    get_settings.cache_clear()
