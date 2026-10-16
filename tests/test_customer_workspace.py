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
