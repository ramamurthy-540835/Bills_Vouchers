from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
from time import time

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import routes
from app.config import get_settings
from app.services.access import navigation_permissions
from app.services.gst import account


@pytest.mark.parametrize('role,owner,platform,expected', [
    ('client', True, False, {'edit_profile','create_customer','manage_members','edit_gstin'}),
    ('client', False, False, {'edit_profile','create_customer'}),
    ('viewer', False, False, set()),
    ('tax_admin', False, False, {'edit_profile','create_customer','edit_gstin'}),
    ('admin', False, True, {'edit_profile','create_customer','edit_gstin','platform_admin'}),
])
def test_permission_matrix(role, owner, platform, expected):
    user = SimpleNamespace(role=role, is_platform_admin=platform)
    assert set(navigation_permissions(user, owner)) == expected | {'view_workspace','manage_own_account','view_reports'}


@pytest.mark.parametrize('role', ['client','tax_admin','viewer','admin'])
def test_workspace_role_alone_never_grants_platform_api(role, caplog):
    repo = Mock()
    with pytest.raises(HTTPException) as exc:
        account.admin_workspace(Mock(), repo, SimpleNamespace(id='u', role=role, is_platform_admin=False))
    assert exc.value.status_code == 403
    repo.query.assert_not_called()
    assert 'platform_access_denied' in caplog.text


def test_platform_api_only_reads_selected_membership(monkeypatch):
    monkeypatch.setattr(account, 'active_client', lambda *args: SimpleNamespace(id='authorized'))
    repo = Mock();repo.table.side_effect=lambda name:'test.'+name;repo.query.return_value=[]
    assert account.admin_workspace(Mock(),repo,SimpleNamespace(id='u',is_platform_admin=True)) == {'members':[],'events':[]}
    for call in repo.query.call_args_list:
        sql, params = call.args
        assert 'client_id=@client_id' in sql
        assert params[0].value == 'authorized'


def test_membership_downgrade_overrides_stale_role_and_switch(monkeypatch):
    monkeypatch.setenv('MEDALLION_ENABLED','true');monkeypatch.setenv('REQUIRE_OTP','false');get_settings.cache_clear()
    identity=SimpleNamespace(id='u',email='u@example.invalid',role='client',session_version=0)
    roles={'a':'owner','b':'viewer'}
    finance=SimpleNamespace(user_by_id=lambda uid:deepcopy(identity),clients=lambda uid:[SimpleNamespace(id=key) for key in roles])
    monkeypatch.setattr(routes,'FinanceRepository',lambda repo:finance)
    def one(sql, params):
        assert 'client_memberships' in sql and 'is_active=TRUE' in sql
        return SimpleNamespace(role=roles[params[0].value])
    repo=SimpleNamespace(table=lambda name:'test.'+name,one=one)
    request=Request({'type':'http','method':'GET','path':'/api/settings/account','headers':[],'query_string':b'',
                     'session':{'user_id':'u','client_id':'a'},'server':('test',80),'scheme':'http'})
    try:
        assert routes.current_user(request,repo).role=='client'
        roles['a']='viewer'
        assert routes.current_user(request,repo).role=='viewer'
        request=Request({**request.scope,'method':'POST','path':'/api/settings/profile'})
        with pytest.raises(HTTPException) as exc:routes.current_user(request,repo)
        assert exc.value.status_code==403
        request=Request({**request.scope,'method':'GET'});request.session['client_id']='b'
        assert routes.current_user(request,repo).role=='viewer'
        del roles['b']
        assert routes.current_user(request,repo).role=='viewer'
        assert request.session['client_id']=='a'
    finally:get_settings.cache_clear()


def test_revoked_membership_blocks_even_platform_admin(monkeypatch):
    monkeypatch.setattr(routes,'fr',lambda repo:SimpleNamespace(clients=lambda uid:[]))
    with pytest.raises(HTTPException) as exc:
        account.admin_workspace(Mock(),Mock(),SimpleNamespace(id='u',is_platform_admin=True))
    assert exc.value.status_code==403


def test_worker_rechecks_membership_instead_of_old_global_role(monkeypatch):
    import asyncio
    from app.routers import gst_bills
    monkeypatch.setattr(gst_bills,'get_settings',lambda:SimpleNamespace(gst_bills_enabled=True,gst_bills_worker_audience='audience',gst_bills_worker_account='worker'))
    monkeypatch.setattr(gst_bills,'verify_cloud_tasks_request',lambda *args:True)
    store=Mock(client_id='a');store.job.return_value={'actor_id':'u'}
    monkeypatch.setattr(gst_bills,'BillStore',lambda *args:store)
    monkeypatch.setattr(gst_bills,'FinanceRepository',lambda repo:SimpleNamespace(user_by_id=lambda uid:SimpleNamespace(id='u',role='admin')))
    run=Mock();monkeypatch.setattr(gst_bills,'run_job',run)
    repo=Mock();repo.table.return_value='test.client_memberships';repo.one.return_value=SimpleNamespace(role='viewer')
    class Request:
        async def json(self):return {'client_id':'a','job_id':'job'}
    with pytest.raises(HTTPException) as exc:asyncio.run(gst_bills.worker(Request(),repo))
    assert exc.value.status_code==403
    assert 'is_active=TRUE' in repo.one.call_args.args[0]
    run.assert_not_called()


def test_background_permissions_do_not_extend_idle_session(monkeypatch):
    monkeypatch.setenv('MEDALLION_ENABLED','false');monkeypatch.setenv('REQUIRE_OTP','false');get_settings.cache_clear()
    user=SimpleNamespace(id='u',email='u@example.invalid',role='client',session_version=0)
    monkeypatch.setattr(routes,'FinanceRepository',lambda repo:SimpleNamespace(user_by_id=lambda uid:deepcopy(user)))
    previous=str(time()-30)
    scope={'type':'http','method':'GET','path':'/api/settings/account','headers':[(b'x-permission-refresh',b'1')],
           'session':{'user_id':'u','last_seen':previous},'query_string':b'','server':('test',80),'scheme':'http'}
    try:
        routes.current_user(Request(scope),Mock())
        assert scope['session']['last_seen']==previous
        routes.current_user(Request({**scope,'headers':[]}),Mock())
        assert float(scope['session']['last_seen'])>float(previous)
    finally:get_settings.cache_clear()


def test_test_business_reports_permission_matches_backend_restriction():
    user = SimpleNamespace(role='viewer')
    assert 'view_reports' in navigation_permissions(user, client=SimpleNamespace(is_test=False))
    assert 'view_reports' not in navigation_permissions(user, client=SimpleNamespace(is_test=True))


@pytest.mark.parametrize('destination,allowed', [('b', True), ('inactive', False), ('foreign', False)])
def test_switch_requires_active_authorized_business(monkeypatch, destination, allowed):
    import asyncio
    from app.services.gst import workbench
    async def body(request):return {'client_id':destination}
    monkeypatch.setattr(workbench,'body_json',body)
    monkeypatch.setattr(workbench,'FinanceRepository',lambda repo:SimpleNamespace(clients=lambda uid:[SimpleNamespace(id='a'),SimpleNamespace(id='b')]))
    request=SimpleNamespace(session={'client_id':'a','period':'2026-10'})
    if allowed:
        asyncio.run(workbench.choose_client(request,Mock(),SimpleNamespace(id='u')))
        assert request.session=={'client_id':'b','period':'2026-10'}
    else:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(workbench.choose_client(request,Mock(),SimpleNamespace(id='u')))
        assert exc.value.status_code==403
        assert request.session['client_id']=='a'
