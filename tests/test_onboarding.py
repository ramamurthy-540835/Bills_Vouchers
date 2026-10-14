import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, PreconditionFailed

from app.services.gst import account


class Request:
    def __init__(self,body):self.body=body
    async def json(self):return self.body


@pytest.fixture
def setup(monkeypatch):
    profile={'profile_id':'version-1','legal_name':'Business','registration_type':'Unregistered','gstin':''}
    repo=Mock();repo.table.side_effect=lambda name:'test.'+name
    user=SimpleNamespace(id='owner',role='client')
    monkeypatch.setattr(account,'active_client',lambda *args:SimpleNamespace(id='own-client'))
    monkeypatch.setattr(account,'can',lambda *args:True)
    monkeypatch.setattr(account,'is_owner',lambda *args:True)
    monkeypatch.setattr(account.Medallion,'profile',lambda *args:profile)
    return repo,user,profile


def test_onboarding_can_save_incomplete_progress(setup):
    repo,user,_=setup
    asyncio.run(account.save_profile(Request({'client_id':'own-client','legal_name':'Draft business'}),repo,user))
    params=repo.query.call_args.args[1]
    assert next(p.value for p in params if p.name=='onboarding') is False


def test_complete_onboarding_requires_contact_and_business_fields(setup):
    repo,user,_=setup
    with pytest.raises(HTTPException) as exc:
        asyncio.run(account.save_profile(Request({'client_id':'own-client','complete_onboarding':True,'legal_name':'Business'}),repo,user))
    assert exc.value.status_code==422
    repo.query.assert_not_called()


def test_unregistered_business_can_complete_without_gstin(setup):
    repo,user,_=setup
    body={'client_id':'own-client','profile_id':'version-1','complete_onboarding':True,'legal_name':'Business',
          'constitution':'Proprietorship','registration_type':'Unregistered','gstin':'','state_code':'33',
          'principal_address':'Synthetic address','contact_person':'Owner','contact_email':'owner@example.test',
          'contact_phone':'+919876543210','filing_frequency':'monthly'}
    asyncio.run(account.save_profile(Request(body),repo,user))
    sql,params=repo.query.call_args.args
    assert next(p.value for p in params if p.name=='onboarding') is True
    assert 'profile_audit' in sql and 'is_current=FALSE' in sql


def test_stale_profile_does_not_overwrite(setup):
    repo,user,_=setup
    with pytest.raises(HTTPException) as exc:
        asyncio.run(account.save_profile(Request({'client_id':'own-client','profile_id':'older','legal_name':'Overwrite'}),repo,user))
    assert exc.value.status_code==409
    repo.query.assert_not_called()


def test_profile_transaction_conflict_is_actionable(setup):
    repo,user,_=setup;repo.query.side_effect=BadRequest('Profile changed; reload')
    with pytest.raises(HTTPException) as exc:
        asyncio.run(account.save_profile(Request({'client_id':'own-client','legal_name':'Changed'}),repo,user))
    assert exc.value.status_code==409


def test_logo_remove_preserves_archive_and_uses_generation(setup,monkeypatch):
    repo,user,_=setup
    blob=Mock();blob.generation=9
    monkeypatch.setattr(account,'logo_blob',lambda client_id:blob)
    assert account.remove_logo(Request({}),repo,user)=={'removed':True}
    blob.bucket.copy_blob.assert_called_once()
    blob.delete.assert_called_once_with(if_generation_match=9)
    assert repo.query.call_count==2
    assert all(next(p.value for p in call.args[1] if p.name=='client_id')=='own-client' for call in repo.query.call_args_list)


def test_logo_remove_conflict_preserves_new_logo(setup,monkeypatch):
    repo,user,_=setup
    blob=Mock();blob.generation=9;blob.delete.side_effect=PreconditionFailed('changed')
    monkeypatch.setattr(account,'logo_blob',lambda client_id:blob)
    with pytest.raises(HTTPException) as exc:
        account.remove_logo(Request({}),repo,user)
    assert exc.value.status_code==409
    assert repo.query.call_count==1  # intent only; never claim completion
