from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, Conflict, DeadlineExceeded

from app.gst.store import BillStore


@pytest.fixture
def store(monkeypatch):
    repo = Mock(settings=SimpleNamespace(gcp_project_id='test-project'))
    monkeypatch.setattr('app.gst.store.time.sleep', Mock())
    return BillStore(repo, 'business-a')


@pytest.mark.parametrize('error_type', [BadRequest, Conflict])
def test_only_explicitly_aborted_transaction_replays_with_same_tenant(store, error_type):
    error = error_type('Transaction is aborted due to concurrent update against table')
    store.repo.query.side_effect = [error, ['saved']]
    assert store.query('BEGIN TRANSACTION; SELECT 1; COMMIT TRANSACTION;') == ['saved']
    assert store.repo.query.call_count == 2
    first, second = store.repo.query.call_args_list
    assert first == second
    assert first.args[1][0].name == 'client_id'
    assert first.args[1][0].value == 'business-a'


def test_contention_retry_is_bounded(store):
    store.repo.query.side_effect = BadRequest('Transaction is aborted due to concurrent update')
    with pytest.raises(BadRequest):
        store.query('BEGIN TRANSACTION; COMMIT TRANSACTION;')
    assert store.repo.query.call_count == 3


@pytest.mark.parametrize('error', [
    DeadlineExceeded('Unknown commit outcome'),
    Conflict('Job already exists'),
    BadRequest('Bill changed; reload'),
    BadRequest('Duplicate invoice'),
    BadRequest('Storage guard missing'),
    BadRequest('Syntax error'),
])
def test_unknown_outcomes_and_business_conflicts_never_replay(store, error):
    store.repo.query.side_effect = error
    with pytest.raises(type(error)):
        store.query('BEGIN TRANSACTION; COMMIT TRANSACTION;')
    assert store.repo.query.call_count == 1


@pytest.mark.parametrize('message,error_type', [
    ('Worker claim lost', RuntimeError), ('Filing period frozen', HTTPException),
])
def test_retry_cannot_bypass_fence_or_period_lock(store, message, error_type):
    store.repo.query.side_effect = [
        BadRequest('Transaction is aborted due to concurrent update'), BadRequest(message)]
    with pytest.raises(error_type):
        store.query('BEGIN TRANSACTION; COMMIT TRANSACTION;')
    assert store.repo.query.call_count == 2


def test_nontransaction_write_never_replays(store):
    store.repo.query.side_effect = BadRequest('Transaction is aborted due to concurrent update')
    with pytest.raises(BadRequest):
        store.query('INSERT INTO example SELECT 1')
    assert store.repo.query.call_count == 1
