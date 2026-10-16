from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.db import get_db
from app.routes import current_user
from app.services.gst import account, taxpayer_routes as routes
from app.services.gst import taxpayer_provider as providers
from app.services.gst.taxpayer_provider import ProviderRecord, ProviderFailure
from app.services.gst.taxpayer_verification import assess, fingerprint, presentation, verify, EvidenceStore

PROFILE = {'gstin':'33ABCDE1234F1Z7','legal_name':'Test Company','profile_id':'v1'}


def record(**changes):
    return ProviderRecord(**{'gstin':PROFILE['gstin'],'found':True,'registration_status':'active','legal_name':'Test Company',**changes})


class Store:
    def __init__(self):
        self.evidence = None
        self.events = []
    def latest(self):
        return self.evidence
    def begin(self, profile, actor, provider):
        if self.events:
            raise HTTPException(429,'cooldown')
        self.events.append('pending')
        return 'attempt'
    def finish(self, attempt, profile, actor, provider, result):
        self.events.append(result['state'])
        self.evidence = {'profile_hash':fingerprint(profile),'created_at':result['checked_at'],'result':result}


@pytest.mark.parametrize('changes,state',[
    ({},'verified'),({'found':False,'registration_status':'unknown','legal_name':''},'not_found'),
    ({'registration_status':'cancelled'},'inactive'),({'registration_status':'suspended'},'inactive'),
    ({'legal_name':'Another Company'},'mismatch'),({'registration_status':'unknown'},'failed'),
])
def test_evidence_outcomes(changes,state):
    result = assess(PROFILE,record(**changes))
    assert result['state'] == state
    assert result['ownership_verified'] is False and result['kyc_verified'] is False


def test_address_mismatch_and_unknown_fields():
    assert assess({**PROFILE,'principal_address':'One'},record(address='Two'))['state']=='mismatch'
    assert assess(PROFILE,record())['comparisons']['principal_address'] is None


@pytest.mark.parametrize('bad', ['invalid','33ABCDE1234F1Z5',''])
def test_invalid_checksum_never_calls_provider(bad):
    provider=Mock();store=Store()
    with pytest.raises(HTTPException) as error:
        verify(store,{**PROFILE,'gstin':bad},'actor','test',provider)
    assert error.value.status_code==422
    provider.lookup.assert_not_called();assert not store.events


def test_result_identity_and_schema_are_untrusted():
    with pytest.raises(ProviderFailure):assess(PROFILE,record(gstin='33BCDEF2345G1ZS'))
    with pytest.raises(ProviderFailure):assess(PROFILE,record(legal_name=''))
    provider=Mock();provider.lookup.return_value={'found':'true','secret':'never return this'}
    result=verify(Store(),PROFILE,'actor','test',provider)
    assert result['state']=='failed' and 'secret' not in str(result)


@pytest.mark.parametrize('error,code',[(TimeoutError('private token'),'timeout'),(ProviderFailure('rate_limited'),'rate_limited'),(RuntimeError('private token'),'invalid_response')])
def test_provider_errors_are_safe_and_audited(error,code):
    provider=Mock();provider.lookup.side_effect=error;store=Store()
    result=verify(store,PROFILE,'actor','test',provider)
    assert result['state']=='failed' and result['error_code']==code
    assert 'private token' not in str(result)
    assert store.events==['pending','failed']


def test_repeated_lookup_reuses_fresh_evidence():
    store=Store();provider=Mock();provider.lookup.return_value=record()
    verify(store,PROFILE,'actor','test',provider)
    result=verify(store,PROFILE,'actor','test',provider)
    assert result['cached'] and provider.lookup.call_count==1
    provider.lookup.assert_called_once_with(PROFILE['gstin'],timeout_seconds=10)


def test_staleness_changes_and_pending_expiry():
    now=datetime.now(timezone.utc)
    evidence={'profile_hash':fingerprint(PROFILE),'created_at':now-timedelta(hours=25),'result':{'state':'verified'}}
    assert presentation(PROFILE,evidence,True,'gsp',now)['state']=='stale'
    evidence['created_at']=now
    assert presentation({**PROFILE,'legal_name':'Changed'},evidence,True,'gsp',now)['state']=='stale'
    assert presentation({**PROFILE,'gstin':'invalid'},evidence,True,'gsp',now)['checksum_valid'] is False
    evidence['result']={'state':'pending'};evidence['created_at']=now-timedelta(minutes=3)
    assert presentation(PROFILE,evidence,True,'gsp',now)['error_code']=='interrupted'


def test_unconfigured_and_missing_credentials_never_invent_adapter(monkeypatch):
    settings=SimpleNamespace(gst_verification_mode='manual')
    assert providers.integration(settings)==(None,'manual')
    settings=SimpleNamespace(gst_verification_mode='gsp',gst_verification_live_enabled=True,gst_verification_storage_enabled=True,gst_verification_provider='approved-test',gst_verification_secret_version='')
    factory=Mock();monkeypatch.setitem(providers.ADAPTERS,'approved-test',factory)
    assert providers.integration(settings)==(None,'unavailable');factory.assert_not_called()


def test_store_queries_are_scoped_rate_limited_and_append_only():
    repo=Mock();repo.table.side_effect=lambda name:'test.'+name;repo.query.return_value=[]
    store=EvidenceStore(repo,'client-A');assert store.latest() is None
    assert repo.query.call_args.args[1][0].value=='client-A'
    store.begin(PROFILE,'actor','approved-test')
    sql,params=repo.query.call_args.args
    assert 'BEGIN TRANSACTION' in sql and 'Verification cooldown' in sql and 'Verification rate limit' in sql
    assert any(p.name=='client' and p.value=='client-A' for p in params)
    store.finish('attempt',PROFILE,'actor','approved-test',{'state':'failed'})
    sql=repo.query.call_args.args[0]
    assert 'INSERT INTO' in sql and 'gstin_verified' not in sql


@pytest.fixture
def api(monkeypatch):
    app=FastAPI();app.include_router(routes.router)
    user=SimpleNamespace(id='user-A',role='client');client=SimpleNamespace(id='client-A',is_test=False)
    repo=Mock();app.dependency_overrides[get_db]=lambda:repo
    app.dependency_overrides[current_user]=lambda:user
    monkeypatch.setattr(routes,'active_client',lambda *args:client)
    monkeypatch.setattr(account,'can',lambda user,*args:user.role=='client')
    monkeypatch.setattr(routes.Medallion,'profile',lambda *args:dict(PROFILE))
    settings=SimpleNamespace(gst_verification_mode='manual',gst_verification_storage_enabled=False,gst_verification_provider='test')
    monkeypatch.setattr(routes,'get_settings',lambda:settings)
    return TestClient(app),user,repo,app,client


def test_manual_mode_and_unauthorized_endpoint(api):
    client,user,repo,app,_=api
    response=client.get('/api/businesses/current/gstin-verification')
    assert response.json()['state']=='not_configured'
    assert client.post('/api/businesses/current/verify-gstin').status_code==503
    repo.query.assert_not_called()
    user.role='viewer'
    assert client.post('/api/businesses/current/verify-gstin').status_code==403
    def deny():raise HTTPException(401,'Sign in')
    app.dependency_overrides[current_user]=deny
    assert client.get('/api/businesses/current/gstin-verification').status_code==401


def test_cannot_substitute_business_or_supplier(api):
    client,_,repo,_,_=api
    assert client.post('/api/businesses/current/verify-gstin',json={'client_id':'foreign','gstin':'33BCDEF2345G1ZS'}).status_code==422
    assert client.post('/api/businesses/current/verify-gstin?client_id=foreign').status_code==422
    repo.query.assert_not_called()


def test_configured_endpoint_uses_saved_profile_and_blocks_demo(api,monkeypatch):
    client,_,_,_,business=api
    provider=Mock();provider.lookup.return_value=record();store=Store()
    monkeypatch.setattr(routes,'integration',lambda settings:(provider,'gsp'))
    monkeypatch.setattr(routes,'EvidenceStore',lambda *args:store)
    result=client.post('/api/businesses/current/verify-gstin')
    assert result.status_code==200 and result.json()['state']=='verified'
    business.is_test=True
    assert client.get('/api/businesses/current/gstin-verification').json()['can_verify'] is False
    assert client.post('/api/businesses/current/verify-gstin').status_code==403
    assert provider.lookup.call_count==1


def test_secret_access_and_failure_are_safe(monkeypatch):
    import google.cloud
    secret_client=Mock()
    secret_client.access_secret_version.return_value=SimpleNamespace(payload=SimpleNamespace(data=b'private-credential'))
    monkeypatch.setattr(google.cloud,'secretmanager',SimpleNamespace(SecretManagerServiceClient=lambda:secret_client),raising=False)
    adapter=Mock();factory=Mock(return_value=adapter)
    monkeypatch.setitem(providers.ADAPTERS,'approved-test',factory)
    settings=SimpleNamespace(gst_verification_mode='gsp',gst_verification_live_enabled=True,gst_verification_storage_enabled=True,gst_verification_provider='approved-test',gst_verification_secret_version='projects/test/secrets/gsp/versions/1')
    assert providers.integration(settings)==(adapter,'gsp')
    factory.assert_called_once_with('private-credential')
    secret_client.access_secret_version.assert_called_once_with(request={'name':settings.gst_verification_secret_version},timeout=5,retry=None)
    secret_client.access_secret_version.side_effect=RuntimeError('private credential')
    assert providers.integration(settings)==(None,'unavailable')


def test_membership_denial_prevents_any_provider_lookup(api,monkeypatch):
    client,_,repo,_,_=api
    def denied(*args):raise HTTPException(403,'Not a member')
    monkeypatch.setattr(routes,'active_client',denied)
    integration=Mock();monkeypatch.setattr(routes,'integration',integration)
    assert client.post('/api/businesses/current/verify-gstin').status_code==403
    integration.assert_not_called();repo.query.assert_not_called()


def test_inflight_profile_change_is_stale(api,monkeypatch):
    client,_,_,_,_=api;provider=Mock();provider.lookup.return_value=record()
    monkeypatch.setattr(routes,'integration',lambda settings:(provider,'gsp'))
    monkeypatch.setattr(routes,'EvidenceStore',lambda *args:Store())
    profiles=iter([dict(PROFILE),{**PROFILE,'legal_name':'Changed during request'}])
    monkeypatch.setattr(routes.Medallion,'profile',lambda *args:next(profiles))
    assert client.post('/api/businesses/current/verify-gstin').json()['state']=='stale'


def test_database_conflict_is_rate_limited():
    from google.api_core.exceptions import Conflict
    repo=Mock();repo.table.side_effect=lambda name:'test.'+name
    repo.query.side_effect=Conflict('concurrent update')
    with pytest.raises(HTTPException) as error:EvidenceStore(repo,'own').begin(PROFILE,'actor','test')
    assert error.value.status_code==429
