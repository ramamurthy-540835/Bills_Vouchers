from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.services import auth_mail


def repository():
    repo = Mock()
    repo.table.side_effect = lambda name: 'project.test.' + name
    return repo


def test_request_path_never_queries_account_existence(monkeypatch):
    repo = repository()
    monkeypatch.setattr(auth_mail, 'ready', lambda: None)
    schedule = Mock();monkeypatch.setattr(auth_mail, 'schedule', schedule)
    auth_mail.request_link(repo, 'unknown@example.test', 'reset')
    assert repo.query.call_count == 1
    assert 'INSERT INTO' in repo.query.call_args.args[0]
    assert 'users' not in repo.query.call_args.args[0]
    schedule.assert_called_once()


def test_unknown_account_is_ignored_by_worker_without_sending(monkeypatch):
    repo = repository()
    repo.query.side_effect = [[{'status':'pending','email':'unknown@example.test','purpose':'reset'}], [], [], []]
    monkeypatch.setattr(auth_mail, 'ready', lambda: SimpleNamespace(app_secret_key='s'*32))
    send = Mock();monkeypatch.setattr(auth_mail.auth_identity, 'send_link', send)
    auth_mail.process(repo, 'mail-id')
    send.assert_not_called()
    assert "status='ignored'" in repo.query.call_args.args[0]


def test_delivery_failure_does_not_mark_outbox_sent(monkeypatch):
    repo = repository()
    repo.query.side_effect = [[{'status':'pending','email':'user@example.test','purpose':'verify'}], [], [{'id':'u','email_verified':False}], [], [{'usable':1}]]
    monkeypatch.setattr(auth_mail, 'ready', lambda: SimpleNamespace(app_secret_key='s'*32))
    monkeypatch.setattr(auth_mail.auth_identity, 'send_link', Mock(side_effect=HTTPException(503, 'unavailable')))
    with pytest.raises(HTTPException):
        auth_mail.process(repo, 'mail-id')
    assert not any("status='sent'" in call.args[0] for call in repo.query.call_args_list)


def test_completed_outbox_is_idempotent(monkeypatch):
    repo = repository();repo.query.return_value = [{'status':'sent'}]
    monkeypatch.setattr(auth_mail, 'ready', lambda: None)
    send = Mock();monkeypatch.setattr(auth_mail.auth_identity, 'send_link', send)
    auth_mail.process(repo, 'mail-id')
    assert repo.query.call_count == 1
    send.assert_not_called()
