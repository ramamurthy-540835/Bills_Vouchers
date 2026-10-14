from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import BadRequest

from app.services import mobile_verification as mobile


@pytest.fixture
def setup(monkeypatch):
    repo = Mock()
    repo.table.side_effect = lambda name: 'project.test.' + name
    user = SimpleNamespace(id='user-1', mobile_number='+919876543210', mobile_verified=False)
    monkeypatch.setattr(mobile, 'throttle', Mock())
    return repo, user


def test_missing_provider_never_verifies(monkeypatch):
    monkeypatch.setattr(mobile, 'get_settings', lambda: SimpleNamespace(twilio_verify_service_sid='', twilio_api_key='', twilio_api_secret=''))
    with pytest.raises(HTTPException) as exc:
        mobile.provider_request('Verifications', {})
    assert exc.value.status_code == 503


def test_start_records_only_pending_provider_response(setup, monkeypatch):
    repo, user = setup
    monkeypatch.setattr(mobile, 'provider_request', lambda *args: {'status':'pending','sid':'VE'+'a'*32,'to':user.mobile_number})
    result = mobile.start(repo, user)
    assert result['expires_in'] == 600
    assert 'mobile_verified=TRUE' not in repo.query.call_args.args[0]


@pytest.mark.parametrize('status', ['pending','expired','failed','canceled','max_attempts_reached'])
def test_only_approved_response_updates_user(setup, monkeypatch, status):
    repo, user = setup
    repo.query.return_value = [{'provider_sid':'VE'+'a'*32}]
    monkeypatch.setattr(mobile, 'provider_request', lambda *args: {'status':status,'sid':'VE'+'a'*32,'to':user.mobile_number})
    with pytest.raises(HTTPException) as exc:
        mobile.check(repo, user, 'a'*8+'-'+ 'a'*4+'-'+ 'a'*4+'-'+ 'a'*4+'-'+ 'a'*12, '123456')
    assert exc.value.status_code == 422
    assert repo.query.call_count == 1


def test_expired_or_replayed_local_challenge_never_calls_provider(setup, monkeypatch):
    repo, user = setup
    repo.query.return_value = []
    provider = Mock();monkeypatch.setattr(mobile, 'provider_request', provider)
    with pytest.raises(HTTPException):
        mobile.check(repo, user, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '123456')
    provider.assert_not_called()


def test_phone_change_race_cannot_mark_different_phone_verified(setup, monkeypatch):
    repo, user = setup
    repo.query.side_effect = [[{'provider_sid':'VE'+'a'*32}], BadRequest('Mobile challenge changed')]
    monkeypatch.setattr(mobile, 'provider_request', lambda *args: {'status':'approved','sid':'VE'+'a'*32,'to':user.mobile_number})
    with pytest.raises(HTTPException) as exc:
        mobile.check(repo, user, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '123456')
    assert exc.value.status_code == 409


def test_provider_approval_is_bound_to_user_and_phone(setup, monkeypatch):
    repo, user = setup
    repo.query.side_effect = [[{'provider_sid':'VE'+'a'*32}], []]
    monkeypatch.setattr(mobile, 'provider_request', lambda *args: {'status':'approved','sid':'VE'+'a'*32,'to':user.mobile_number})
    assert mobile.check(repo, user, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '123456') == {'mobile_verified':True}
    sql, params = repo.query.call_args.args
    assert 'WHERE id=@uid AND mobile_number=@mobile AND is_active=TRUE' in sql
    assert 'expires_at>CURRENT_TIMESTAMP()' in sql and 'consumed_at IS NULL' in sql
    assert {p.name:p.value for p in params}['uid'] == user.id
