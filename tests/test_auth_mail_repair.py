from types import SimpleNamespace
from unittest.mock import Mock
import json
import sys

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import AlreadyExists, Conflict, NotFound

from app.services import auth_mail, auth_mail_repair


@pytest.fixture
def setup(monkeypatch):
    repo = Mock()
    repo.table.side_effect = lambda name: 'test.v3.'+name
    settings = SimpleNamespace(auth_mail_queue='projects/test/locations/test/queues/v3-auth',
                               auth_worker_url='https://v3.example.test',
                               auth_worker_audience='https://v3.example.test',
                               auth_worker_account='v3-worker@example.test')
    client = Mock()
    factory = Mock(return_value=client)
    # Local contract fake: never load credentials or contact a real task queue.
    monkeypatch.setitem(sys.modules, 'google.cloud.tasks_v2', SimpleNamespace(
        CloudTasksClient=factory, HttpMethod=SimpleNamespace(POST=1)))
    return repo, settings, client, factory


def test_budget_reservation_is_guarded_and_filters_terminal_active_and_old_mail(setup):
    repo, settings, client, factory = setup
    repo.query.return_value = []
    assert auth_mail_repair.repair(repo, settings, auth_mail.TERMINAL) == 0
    factory.assert_not_called()
    sql = repo.query.call_args.args[0]
    assert 'BEGIN TRANSACTION' in sql and 'COMMIT TRANSACTION' in sql
    assert "WHERE id='identity'" in sql and 'ASSERT @@row_count=1' in sql
    assert 'COALESCE(r.attempts,0)<3' in sql and 'COALESCE(r.pending,0)=0' in sql
    assert 'INTERVAL 10 MINUTE' in sql and 'INTERVAL 1 DAY' in sql
    assert 'm.lease_until<CURRENT_TIMESTAMP()' in sql
    assert auth_mail.TERMINAL in sql and 'LIMIT 50' in sql


@pytest.mark.parametrize('outcome', [None, AlreadyExists('already queued')])
def test_repair_preserves_identity_and_only_marks_queue_acceptance(setup, outcome):
    repo, settings, client, _ = setup
    repo.query.side_effect = [[{'mail_id': 'mail-a', 'attempt': 1}], []]
    client.create_task.side_effect = outcome
    assert auth_mail_repair.repair(repo, settings, auth_mail.TERMINAL) == 1
    task = client.create_task.call_args.kwargs['request']['task']
    assert task['name'].startswith(settings.auth_mail_queue+'/tasks/')
    assert task['http_request']['oidc_token']['service_account_email'] == settings.auth_worker_account
    assert json.loads(task['http_request']['body']) == {'mail_id': 'mail-a'}
    update = repo.query.call_args.args[0]
    assert "SET state='queued'" in update
    assert 'provider_accepted' not in update and 'auth_outbox' not in update


def test_unknown_enqueue_result_reuses_same_reservation_and_logs_no_secret(setup, caplog):
    repo, settings, client, _ = setup
    repo.query.return_value = [{'mail_id': 'mail-a', 'attempt': 1}]
    client.create_task.side_effect = TimeoutError('private provider details')
    for _ in range(2):
        assert auth_mail_repair.repair(repo, settings, auth_mail.TERMINAL) == 0
    assert client.create_task.call_args_list[0] == client.create_task.call_args_list[1]
    assert repo.query.call_count == 2  # No successful enqueue update.
    assert 'private provider details' not in caplog.text


def test_one_failure_does_not_prevent_other_reserved_mail(setup):
    repo, settings, client, _ = setup
    repo.query.side_effect = [[{'mail_id':'a','attempt':1}, {'mail_id':'b','attempt':2}], []]
    client.create_task.side_effect = [TimeoutError(), None]
    assert auth_mail_repair.repair(repo, settings, auth_mail.TERMINAL) == 1
    assert client.create_task.call_count == 2


@pytest.mark.parametrize('error', [NotFound('secret table details'), Conflict('conflict')])
def test_missing_migration_or_concurrent_reservation_fails_closed(setup, error):
    repo, settings, client, factory = setup
    repo.query.side_effect = error
    with pytest.raises(HTTPException) as caught:
        auth_mail_repair.repair(repo, settings, auth_mail.TERMINAL)
    assert caught.value.status_code == 503
    assert 'secret table details' not in str(caught.value.detail)
    factory.assert_not_called()


def test_write_failure_after_enqueue_reuses_task_id_on_retry(setup):
    repo, settings, client, _ = setup
    row = {'mail_id':'a','attempt':1}
    repo.query.side_effect = [[row], RuntimeError('storage unavailable'), [row], []]
    with pytest.raises(RuntimeError):
        auth_mail_repair.repair(repo, settings, auth_mail.TERMINAL)
    client.create_task.side_effect = AlreadyExists('existing task')
    assert auth_mail_repair.repair(repo, settings, auth_mail.TERMINAL) == 1
    assert client.create_task.call_args_list[0] == client.create_task.call_args_list[1]
