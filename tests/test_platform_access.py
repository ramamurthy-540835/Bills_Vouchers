from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from app import routes
from app.config import get_settings
from app.db import get_db


@pytest.fixture
def access(monkeypatch):
    monkeypatch.setenv('MEDALLION_ENABLED', 'false')
    monkeypatch.setenv('PLATFORM_ADMIN_EMAILS', 'admin@example.test')
    monkeypatch.setenv('REQUIRE_OTP', 'false')
    get_settings.cache_clear()
    user = SimpleNamespace(id='u', email='admin@example.test', role='admin', is_active=True,
                           email_verified=True, password_hash='hash', full_name='Test', session_version=0)
    grant = {'active': True}
    repo = SimpleNamespace(table=lambda name: 'test.' + name,
                           query=lambda *args: [], one=lambda *args: {'user_id': 'u'} if grant['active'] else None)
    finance = SimpleNamespace(user_by_id=lambda uid: deepcopy(user) if uid == 'u' else None,
                              user_by_email=lambda email: deepcopy(user), audit=lambda *args: None)
    monkeypatch.setattr(routes, 'FinanceRepository', lambda _: finance)
    monkeypatch.setattr(routes, 'fr', lambda _: finance)
    monkeypatch.setattr(routes, 'verify_password', lambda *args: True)
    monkeypatch.setattr(routes.auth_identity, 'throttle', lambda *args: None)
    monkeypatch.setattr(routes, 'login_allowed', lambda *args: True)
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key='synthetic-test-secret')
    app.include_router(routes.router)
    app.dependency_overrides[get_db] = lambda: repo

    @app.get('/test/access')
    def permissions(current=Depends(routes.current_user)):
        return {'role': current.role, 'admin': current.is_platform_admin}

    @app.get('/test/legacy-session')
    def old_cookie(request: Request):
        request.session.update(user_id='u', session_version=0)
        return {}

    yield TestClient(app), user, grant
    get_settings.cache_clear()


def test_normal_login_never_grants_admin_even_to_legacy_admin(access):
    http, _, _ = access
    response = http.post('/api/auth/login', json={'email': 'admin@example.test', 'password': 'x', 'access_mode': 'admin', 'role': 'admin'})
    assert response.json()['role'] == 'client'
    assert response.json()['access_mode'] == 'client'
    assert http.get('/test/access').json() == {'role': 'client', 'admin': False}
    assert http.get('/users').status_code == 403


def test_legacy_cookie_does_not_inherit_admin(access):
    http, _, _ = access
    http.get('/test/legacy-session')
    assert http.get('/test/access').json() == {'role': 'client', 'admin': False}


@pytest.mark.parametrize('problem', ['unverified', 'no_grant', 'not_allowlisted'])
def test_admin_login_requires_all_provisioning_conditions(access, problem):
    http, user, grant = access
    if problem == 'unverified':
        user.email_verified = None
    elif problem == 'no_grant':
        grant['active'] = False
    else:
        user.email = 'client@example.test'
    assert http.post('/api/auth/admin/login', json={'email': user.email, 'password': 'x'}).status_code == 403


def test_provisioned_admin_grant_is_independent_of_workspace_role_and_rechecked(access):
    http, user, grant = access
    user.role = 'viewer'
    assert http.post('/api/auth/admin/login', json={'email': user.email, 'password': 'x'}).status_code == 200
    assert http.get('/test/access').json() == {'role': 'admin', 'admin': True}
    grant['active'] = False
    assert http.get('/test/access').status_code == 403
    assert http.get('/test/access').status_code == 401


def test_workspace_admin_mapping_cannot_grant_platform_access():
    from app.services.access import workspace_role
    assert workspace_role('admin') == workspace_role('owner') == 'client'
    assert workspace_role(None) == 'viewer'
    assert workspace_role('accountant') == 'tax_admin'
