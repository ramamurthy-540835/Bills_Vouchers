from app.security import hash_password, login_allowed, password_is_strong, record_login_failure, record_login_success, same_origin, verify_password
import pytest


def test_csrf_cookie_is_refreshed_after_session_reset(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.routes import current_user
    app = create_app()
    app.dependency_overrides[current_user] = lambda: object()
    client = TestClient(app)
    client.cookies.set('csrf_token', 'old-session-token', domain='testserver.local', path='/')
    response = client.get('/api/auth/csrf')
    assert response.status_code == 200
    assert response.json()['token'] != 'old-session-token'
    assert response.cookies['csrf_token'] == response.json()['token']


@pytest.mark.parametrize('endpoint', ['/login', '/api/auth/login'])
def test_login_replaces_expired_session(monkeypatch, endpoint):
    from time import time
    from types import SimpleNamespace
    from fastapi import Depends, FastAPI, Request
    from fastapi.testclient import TestClient
    from starlette.middleware.sessions import SessionMiddleware
    from app import routes
    from app.db import get_db

    user = SimpleNamespace(id='user-1', email='test@example.test', full_name='Test',
                           password_hash=hash_password('test-password'), role='client',
                           session_version=2, must_change_password=False)
    repo = SimpleNamespace(user_by_email=lambda email: user,
                           user_by_id=lambda uid: user if uid == user.id else None,
                           audit=lambda *args: None)
    monkeypatch.setattr(routes, 'fr', lambda _: repo)
    monkeypatch.setattr(routes, 'FinanceRepository', lambda _: repo)
    monkeypatch.setattr(routes, 'get_settings', lambda: SimpleNamespace(
        session_idle_timeout=1800, medallion_enabled=False))
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key='test-only')
    app.dependency_overrides[get_db] = lambda: repo
    app.include_router(routes.router)

    @app.get('/seed-old-session')
    def seed(request: Request):
        request.session.update(user_id='old-user', last_seen=str(time()-3600),
                               client_id='old-client', csrf_token='old-token', session_version=1)
        return {'ok': True}

    @app.get('/check-session')
    def check(request: Request, current=Depends(routes.current_user)):
        return {'user': current.id, 'session': dict(request.session)}

    with TestClient(app) as client:
        client.get('/seed-old-session')
        credentials = {'email': user.email, 'password': 'test-password'}
        response = client.post(endpoint, **({'json': credentials} if endpoint.startswith('/api') else {'data': credentials}), follow_redirects=False)
        assert response.status_code in (200, 303)
        response = client.get('/check-session')
        assert response.status_code == 200
        session = response.json()['session']
        assert session['user_id'] == user.id and session['session_version'] == 2
        assert 'client_id' not in session and 'csrf_token' not in session


def test_password_policy():
    assert password_is_strong("Strong-password-123")
    assert not password_is_strong("short1A")
    assert not password_is_strong("lowercase-password-1")


def test_passwords_are_hashed_and_verified():
    encoded = hash_password("A-long-password-123")
    assert encoded != "A-long-password-123"
    assert verify_password("A-long-password-123", encoded)
    assert not verify_password("wrong", encoded)


def test_login_throttle_resets_after_success():
    key = "test-rate-limit-unique"
    for _ in range(5):
        record_login_failure(key)
    assert not login_allowed(key)
    record_login_success(key)
    assert login_allowed(key)


def test_same_origin_accepts_full_referer_path():
    assert same_origin("https://bills-voucher.example/documents/upload", "https://bills-voucher.example/")
    assert not same_origin("https://untrusted.example/documents/upload", "https://bills-voucher.example/")



def test_mcp_sql_guard_rejects_writes():
    from app.services.mcp_server import validate_read_only_sql
    assert validate_read_only_sql("SELECT 1;") == "SELECT 1"
    for statement in ("SELECT 1; DELETE FROM t", "WITH x AS (SELECT 1) DELETE FROM t", "UPDATE t SET x=1"):
        try:
            validate_read_only_sql(statement)
        except ValueError:
            pass
        else:
            raise AssertionError("write query was accepted")


def test_last_admin_cannot_be_removed():
    from fastapi import HTTPException
    from app.models import Role, ns
    from app.routes import assert_not_last_admin

    class Repo:
        def table(self, name):
            return name

        def one(self, sql, params):
            return ns(n=0)

    try:
        assert_not_last_admin(Repo(), ns(id="admin-1", role="admin", is_active=True), Role.ACCOUNTANT, True)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "last active Admin" in str(exc.detail)
    else:
        raise AssertionError("last admin change was accepted")


def test_admin_change_allowed_when_another_admin_exists():
    from app.models import Role, ns
    from app.routes import assert_not_last_admin

    class Repo:
        def table(self, name):
            return name

        def one(self, sql, params):
            return ns(n=1)

    assert_not_last_admin(Repo(), ns(id="admin-1", role="admin", is_active=True), Role.ACCOUNTANT, True)
