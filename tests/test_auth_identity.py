from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from google.api_core.exceptions import BadRequest, Conflict
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
    assert exc.value.headers['Retry-After'] == '900'
    assert repo.query.call_count == 1
    assert 'user@example.test' not in str(repo.query.call_args)


@pytest.mark.parametrize('failure', [BadRequest('Transaction aborted due to concurrent update'), Conflict('transaction conflict')])
def test_transient_identity_contention_retries_without_false_lockout(monkeypatch, failure):
    repo = repository()
    repo.query.side_effect = [failure, []]
    wait = Mock()
    monkeypatch.setattr(auth_identity.time, 'sleep', wait)
    auth_identity.throttle(repo, 'login:user@example.test')
    assert repo.query.call_count == 2
    wait.assert_called_once()
    assert repo.query.call_args_list[0] == repo.query.call_args_list[1]


def test_exhausted_identity_contention_is_recoverable_not_rate_limited(monkeypatch):
    repo = repository()
    repo.query.side_effect = Conflict('transaction conflict')
    monkeypatch.setattr(auth_identity.time, 'sleep', lambda _: None)
    with pytest.raises(HTTPException) as caught:
        auth_identity.throttle(repo, 'login:user@example.test')
    assert repo.query.call_count == 3
    assert caught.value.status_code == 503
    assert caught.value.headers['Retry-After'] == '2'


def test_identity_storage_errors_are_not_disguised_as_rate_limits():
    repo = repository()
    repo.query.side_effect = BadRequest('Missing auth guard table')
    with pytest.raises(BadRequest):
        auth_identity.throttle(repo, 'login:user@example.test')
    assert repo.query.call_count == 1


def test_successful_login_releases_only_its_own_reservation():
    repo = repository()
    receipt = auth_identity.throttle(repo, 'login:user@example.test')
    auth_identity.complete_login(repo, 'user', receipt)
    sql, params = repo.query.call_args.args
    values = {p.name:p.value for p in params}
    assert 'BEGIN TRANSACTION' in sql and 'COMMIT TRANSACTION' in sql
    assert 'key_hash=@key AND created_at=@attempt_at' in sql
    assert values['key'] == receipt[0]
    assert values['attempt_at'] == receipt[1]
    assert values['id'] == 'user'


def test_login_bookkeeping_contention_returns_retryable_error(monkeypatch):
    repo = repository()
    repo.query.side_effect = Conflict('transaction conflict')
    monkeypatch.setattr(auth_identity.time, 'sleep', lambda _: None)
    with pytest.raises(HTTPException) as caught:
        auth_identity.complete_login(repo, 'user', None)
    assert caught.value.status_code == 503
    assert repo.query.call_count == 3


def test_shared_demo_allows_repeated_success_without_erasing_failed_attempts():
    from datetime import datetime, timezone
    from google.api_core.exceptions import BadRequest

    class Attempts:
        def __init__(self):
            self.rows = [(auth_identity.digest('login:demo@example.test'), datetime.now(timezone.utc))]
        def table(self, name):
            return 'test.' + name
        def query(self, sql, params):
            values = {p.name:p.value for p in params}
            row = (values['key'], values['attempt_at'])
            if 'INSERT INTO' in sql:
                if sum(key == row[0] for key, _ in self.rows) >= 5:
                    raise BadRequest('Auth rate limit')
                self.rows.append(row)
            else:
                self.rows.remove(row)

    repo = Attempts()
    original_failure = repo.rows[0]
    for _ in range(7):
        receipt = auth_identity.throttle(repo, 'login:demo@example.test')
        auth_identity.complete_login(repo, 'demo-user', receipt)
        assert repo.rows == [original_failure]
    for _ in range(4):
        auth_identity.throttle(repo, 'login:demo@example.test')
    with pytest.raises(HTTPException) as caught:
        auth_identity.throttle(repo, 'login:demo@example.test')
    assert caught.value.status_code == 429


def test_api_error_response_preserves_retry_after():
    from app.main import create_app
    app = create_app()

    @app.get('/api/test/identity-busy')
    def busy():
        raise HTTPException(503, 'Sign-in services are busy.', headers={'Retry-After':'2'})

    response = TestClient(app).get('/api/test/identity-busy')
    assert response.status_code == 503
    assert response.headers['retry-after'] == '2'
    assert response.json()['error']['message'] == 'Sign-in services are busy.'


@pytest.mark.parametrize('active,verified,code', [(True,False,'email_verification_required'), (False,True,None)])
def test_unverified_and_inactive_identities_do_not_create_login_sessions(monkeypatch, active, verified, code):
    repo = repository()
    user = SimpleNamespace(id='u', password_hash=hash_password('StrongPassword123'), email_verified=verified, is_active=active)
    monkeypatch.setattr(routes, 'fr', lambda _: SimpleNamespace(user_by_email=lambda _: user))
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key='test-only')
    app.include_router(routes.router)
    app.dependency_overrides[get_db] = lambda: repo
    client = TestClient(app)
    result = client.post('/api/auth/login', json={'email':'new-user@example.test', 'password':'StrongPassword123'})
    assert result.status_code == 403
    if code:
        assert result.json()['detail']['code'] == code
    else:
        assert 'inactive' in result.json()['detail']
    assert 'session' not in client.cookies
