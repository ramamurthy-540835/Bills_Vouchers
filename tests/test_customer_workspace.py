from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import ServiceUnavailable

from app.services import customer_workspace as service


def setup(monkeypatch):
    storage = Mock()
    monkeypatch.setattr(service, 'provision_storage', storage)
    repo = Mock()
    repo.table.side_effect = lambda name: 'project.dataset.' + name
    user = SimpleNamespace(id='owner', role='client', email='owner@example.com', full_name='Owner')
    body = dict(request_id=str(uuid4()), legal_name='Example business', website_url='https://example.com')
    return repo, user, body, storage


def test_retries_keep_customer_identity_and_transaction(monkeypatch):
    repo, user, body, storage = setup(monkeypatch)
    first = service.create_customer(repo, user, body)
    assert service.create_customer(repo, user, body) == first
    sql, params = repo.query.call_args.args
    assert 'BEGIN TRANSACTION' in sql and 'COMMIT TRANSACTION' in sql
    assert 'IF NOT EXISTS' in sql and "access_role='owner' AND is_active=TRUE" in sql
    assert 'profile_audit' in sql and 'FALSE' in sql
    assert {p.name: p.value for p in params}['uid'] == user.id
    storage.assert_called_with(first['client_id'])
    user.id = 'other-owner'
    assert service.create_customer(repo, user, body)['client_id'] != first['client_id']


@pytest.mark.parametrize('field,value', [('legal_name',''),('website_url','javascript:alert(1)'),('gstin','invalid'),('request_id','../other')])
def test_invalid_input_creates_nothing(monkeypatch, field, value):
    repo, user, body, storage = setup(monkeypatch)
    body[field] = value
    with pytest.raises(HTTPException) as exc:
        service.create_customer(repo, user, body)
    assert exc.value.status_code == 422
    storage.assert_not_called()
    repo.query.assert_not_called()


def test_viewer_cannot_create(monkeypatch):
    repo, user, body, storage = setup(monkeypatch)
    user.role = 'viewer'
    with pytest.raises(HTTPException) as exc:
        service.create_customer(repo, user, body)
    assert exc.value.status_code == 403
    storage.assert_not_called()


def test_storage_failure_does_not_create_database_profile(monkeypatch):
    repo, user, body, storage = setup(monkeypatch)
    storage.side_effect = ServiceUnavailable('unavailable')
    with pytest.raises(HTTPException) as exc:
        service.create_customer(repo, user, body)
    assert exc.value.status_code == 503
    repo.query.assert_not_called()


@pytest.mark.parametrize('code,phrase', [('BUSINESS_GSTIN_EXISTS', 'invitation'), ('BUSINESS_REQUEST_CHANGED', 'different details')])
def test_creation_conflicts_are_actionable(monkeypatch, code, phrase):
    from google.api_core.exceptions import BadRequest
    repo, user, body, _ = setup(monkeypatch)
    repo.query.side_effect = BadRequest(code)
    with pytest.raises(HTTPException) as exc:
        service.create_customer(repo, user, body)
    assert exc.value.status_code == 409
    assert phrase in exc.value.detail


@pytest.mark.parametrize('body', [None, [], {'legal_name': None}, {'website_url': []}])
def test_malformed_body_has_no_side_effects(monkeypatch, body):
    repo, user, _, storage = setup(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        service.create_customer(repo, user, body)
    assert exc.value.status_code == 422
    storage.assert_not_called()
    repo.query.assert_not_called()


def test_duplicate_checks_are_inside_serialized_transaction(monkeypatch):
    repo, user, body, _ = setup(monkeypatch)
    service.create_customer(repo, user, body)
    sql = repo.query.call_args.args[0]
    assert sql.index('UPDATE') < sql.index('BUSINESS_GSTIN_EXISTS') < sql.index('INSERT INTO')
    assert 'BUSINESS_REQUEST_CHANGED' in sql


def test_route_preserves_selected_business(monkeypatch):
    import asyncio
    from app.services import auth_identity
    from app.services.gst.account import create_customer
    from starlette.requests import Request
    request = Request({'type': 'http', 'session': {'client_id': 'original'}})
    async def body():
        return {}
    request.json = body
    monkeypatch.setattr(service, 'create_customer', lambda *args: {'client_id': 'new', 'saved': True})
    monkeypatch.setattr(auth_identity, 'throttle', lambda *args: None)
    assert (asyncio.run(create_customer(request, object(), SimpleNamespace(id='owner'))))['client_id'] == 'new'
    assert request.session['client_id'] == 'original'



def test_creation_rate_limit_prevents_provisioning(monkeypatch):
    import asyncio
    from app.services import auth_identity
    from app.services.gst.account import create_customer
    from starlette.requests import Request
    request = Request({'type': 'http', 'session': {'client_id': 'original'}})
    async def body():
        return {}
    request.json = body
    provision = Mock()
    monkeypatch.setattr(service, 'create_customer', provision)
    limiter = Mock(side_effect=HTTPException(429, 'Please wait before retrying.'))
    monkeypatch.setattr(auth_identity, 'throttle', limiter)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(create_customer(request, object(), SimpleNamespace(id='owner')))
    assert exc.value.status_code == 429
    assert exc.value.headers['X-Request-ID']
    assert limiter.call_args.args[1] == 'business-create:owner'
    provision.assert_not_called()
    assert request.session['client_id'] == 'original'
