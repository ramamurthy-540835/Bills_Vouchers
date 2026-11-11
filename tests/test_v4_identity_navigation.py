import asyncio
import secrets
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from app import routes
from app.db import get_db


def identity_app(repo):
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))
    app.include_router(routes.router)
    app.dependency_overrides[get_db] = lambda: repo
    return app


@pytest.mark.parametrize('endpoint', ['login', 'register', 'request-link', 'verify-email', 'reset-password'])
@pytest.mark.parametrize('body', [[], {'email': []}, {'token': {}}, {'password': 123}])
def test_bad_identity_payload_is_validation_error_not_server_crash(endpoint, body):
    repo = Mock()
    response = TestClient(identity_app(repo)).post('/api/auth/' + endpoint, json=body)
    assert response.status_code == 422
    repo.query.assert_not_called()


@pytest.mark.parametrize('purpose', ['verify', 'reset'])
def test_recovery_messages_preserve_purpose_and_account_privacy(monkeypatch, purpose):
    repo = Mock()
    monkeypatch.setattr(routes.auth_mail, 'ready', lambda: None)
    monkeypatch.setattr(routes.auth_identity, 'throttle', Mock())
    queued = Mock()
    monkeypatch.setattr(routes.auth_mail, 'request_link', queued)
    client = TestClient(identity_app(repo))
    responses = [client.post('/api/auth/request-link', json={'email': email, 'purpose': purpose})
        for email in ['known@example.test', 'unknown@example.test']]
    assert all(r.status_code == 200 for r in responses)
    assert responses[0].json() == responses[1].json()
    assert responses[0].json()['purpose'] == purpose
    assert responses[0].json()['status'] == 'requested'
    assert ('password reset' if purpose == 'reset' else 'Verification') in responses[0].json()['message']
    assert queued.call_args.args[2] == purpose
    repo.query.assert_not_called()


def test_slow_login_storage_does_not_block_other_async_requests(monkeypatch):
    entered, release = Event(), Event()
    def throttle(*_):
        entered.set()
        if not release.wait(3):
            raise RuntimeError('Storage blocked the event loop')
    user = SimpleNamespace(id='synthetic', email='synthetic@example.test', full_name='Test', role='client',
        password_hash='not-a-real-hash', is_active=True, email_verified=True, session_version=0)
    monkeypatch.setattr(routes.auth_identity, 'throttle', throttle)
    monkeypatch.setattr(routes.auth_identity, 'complete_login', lambda *_: None)
    monkeypatch.setattr(routes, 'fr', lambda _: SimpleNamespace(user_by_email=lambda _: user, audit=lambda *_: None))
    monkeypatch.setattr(routes, 'verify_password', lambda *_: True)
    app = identity_app(Mock())
    @app.get('/probe')
    async def probe():
        return {'healthy': True}
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            login = asyncio.create_task(client.post('/api/auth/login', json={
                'email': user.email, 'password': secrets.token_urlsafe(20)}))
            try:
                assert await asyncio.to_thread(entered.wait, 2)
                assert (await asyncio.wait_for(client.get('/probe'), 1)).status_code == 200
            finally:
                release.set()
            assert (await login).status_code == 200
    asyncio.run(exercise())


def test_membership_reuse_is_request_bound_and_never_reused_after_revocation(monkeypatch):
    user, repo = SimpleNamespace(id='user'), object()
    memberships = Mock(side_effect=[['authorized'], [], []])
    monkeypatch.setattr(routes, 'fr', lambda _: SimpleNamespace(clients=memberships))
    first = Request({'type': 'http', 'method': 'GET', 'path': '/'})
    assert routes.request_clients(first, repo, user) == ['authorized']
    assert routes.request_clients(first, repo, user) == ['authorized']
    assert memberships.call_count == 1
    second = Request({'type': 'http', 'method': 'GET', 'path': '/'})
    assert routes.request_clients(second, repo, user) == []
    assert routes.request_clients(second, repo, SimpleNamespace(id='another-user')) == []
    assert memberships.call_count == 3


def test_mutation_requests_always_read_memberships_fresh(monkeypatch):
    memberships = Mock(return_value=[])
    monkeypatch.setattr(routes, 'fr', lambda _: SimpleNamespace(clients=memberships))
    request = Request({'type': 'http', 'method': 'POST', 'path': '/'})
    for _ in range(2):
        routes.request_clients(request, object(), SimpleNamespace(id='user'))
    assert memberships.call_count == 2


def test_navigation_context_does_not_calculate_financial_totals(monkeypatch):
    from app.routers import gst_bills
    request = Request({'type': 'http', 'method': 'GET', 'path': '/', 'session': {}})
    client = SimpleNamespace(id='authorized', is_test=False)
    monkeypatch.setattr(gst_bills, 'scope', lambda *_: (client, object()))
    monkeypatch.setattr(gst_bills, 'selected_period', lambda *args: '2026-10')
    monkeypatch.setattr(gst_bills, 'profile_for', lambda _, cid, __: {'client_id': cid})
    monkeypatch.setattr(gst_bills, 'can', lambda *_: False)
    financial = Mock(side_effect=AssertionError('Unnecessary financial calculation'))
    monkeypatch.setattr(gst_bills.dashboard_report, 'build', financial)
    response = gst_bills.workspace_context(request, repo=object(), user=object())
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'private, no-store'
    financial.assert_not_called()
