from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from google.api_core.exceptions import BadRequest
from starlette.middleware.sessions import SessionMiddleware

from app import routes
from app.db import get_db
from app.security import hash_password
from app.services import auth_identity


def repository():
    repo = Mock(settings=SimpleNamespace(gcp_project_id='test-project'))
    repo.table.side_effect = lambda name: 'test-project.finance.' + name
    return repo


def test_tokens_are_hashed_and_not_returned(monkeypatch):
    repo = repository()
    sender = Mock()
    monkeypatch.setattr(auth_identity, 'delivery_ready', lambda: None)
    monkeypatch.setattr(auth_identity, 'send_link', sender)
    assert auth_identity.issue(repo, 'user', 'user@example.test', 'verify') is None
    token = sender.call_args.args[1]
    sql, params = repo.query.call_args.args
    values = {p.name: p.value for p in params}
    assert token not in sql and token not in values.values()
    assert values['hash'] == auth_identity.digest(token)
    assert 'INTERVAL 30 MINUTE' in sql


@pytest.mark.parametrize('reason', ['Invalid auth token', 'Transaction aborted due to concurrent update'])
def test_expired_replayed_or_concurrent_tokens_fail(reason):
    repo = repository()
    repo.query.side_effect = BadRequest(reason)
    with pytest.raises(HTTPException) as exc:
        auth_identity.consume(repo, 'x' * 43, 'verify')
    assert exc.value.status_code == 422


def test_reset_revokes_sessions_and_consumes_other_recovery_links():
    repo = repository()
    auth_identity.consume(repo, 'x' * 43, 'reset', 'StrongPassword123', 'StrongPassword123')
    sql, params = repo.query.call_args.args
    assert 'session_version=COALESCE(session_version,0)+1' in sql
    assert 'expires_at>CURRENT_TIMESTAMP()' in sql
    assert 'consumed_at IS NULL' in sql
    assert 'purpose=@purpose' in sql
    assert 'COMMIT TRANSACTION' in sql
    assert 'StrongPassword123' not in [p.value for p in params]


def test_missing_delivery_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(auth_identity, 'get_settings', lambda: SimpleNamespace(auth_public_url='', smtp_host='', smtp_sender=''))
    with pytest.raises(HTTPException) as exc:
        auth_identity.delivery_ready()
    assert exc.value.status_code == 503


def test_unverified_login_cannot_create_session_and_legacy_signup_is_disabled(monkeypatch):
    repo = repository()
    user = SimpleNamespace(id='u', password_hash=hash_password('StrongPassword123'), email_verified=False, is_active=True)
    monkeypatch.setattr(routes, 'fr', lambda _: SimpleNamespace(user_by_email=lambda _: user))
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key='test-only')
    app.include_router(routes.router)
    app.dependency_overrides[get_db] = lambda: repo
    client = TestClient(app)
    result = client.post('/api/auth/login', json={'email':'user@example.test', 'password':'StrongPassword123'})
    assert result.status_code == 403
    assert 'session' not in client.cookies
    assert client.post('/signup', data={'email':'a@example.test'}).status_code == 410


def test_shared_rate_limit_returns_429():
    repo = repository()
    repo.query.side_effect = BadRequest('Auth rate limit')
    with pytest.raises(HTTPException) as exc:
        auth_identity.throttle(repo, 'login:user@example.test')
    assert exc.value.status_code == 429
    assert 'user@example.test' not in str(repo.query.call_args)
