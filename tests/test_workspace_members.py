import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import BadRequest

from app.services.gst import workspace_members as members
from app.services.gst.membership_permissions import is_owner


class Request:
    def __init__(self, body=None):
        self.body = body or {}
        self.session = {}

    async def json(self):
        return self.body


@pytest.fixture
def setup(monkeypatch):
    repo = Mock();repo.table.side_effect = lambda name: 'project.test.' + name
    user = SimpleNamespace(id='owner',email='owner@example.test',role='client',email_verified=True)
    monkeypatch.setattr(members, 'active_client', lambda *args: SimpleNamespace(id='own-client'))
    monkeypatch.setattr(members, 'is_owner', lambda *args: True)
    monkeypatch.setattr(members.auth_mail, 'ready', lambda: None)
    monkeypatch.setattr(members.auth_mail, 'schedule', Mock())
    monkeypatch.setattr(members, 'throttle', Mock())
    return repo,user


def test_ownership_requires_active_explicit_membership():
    repo=Mock();repo.table.return_value='test.members'
    repo.query.return_value=[{'access_role':'client'}]
    assert not is_owner(repo,SimpleNamespace(id='u'),'client')
    sql,params=repo.query.call_args.args
    assert 'user_id=@uid AND client_id=@cid AND is_active=TRUE' in sql
    assert {p.name:p.value for p in params} == {'uid':'u','cid':'client'}


def test_non_owner_cannot_invite(setup,monkeypatch):
    repo,user=setup
    monkeypatch.setattr(members,'is_owner',lambda *args:False)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(members.invite(Request({'email':'other@example.test','role':'viewer'}),repo,user))
    assert exc.value.status_code==403
    repo.query.assert_not_called()


@pytest.mark.parametrize('role',['admin','owner','superuser','client'])
def test_invitation_cannot_escalate_role(setup,role):
    repo,user=setup
    with pytest.raises(HTTPException) as exc:
        asyncio.run(members.invite(Request({'email':'other@example.test','role':role}),repo,user))
    assert exc.value.status_code==422
    repo.query.assert_not_called()


def test_unverified_identity_cannot_accept(setup):
    repo,user=setup;user.email_verified=False
    with pytest.raises(HTTPException) as exc:
        asyncio.run(members.accept(Request({'token':'a'*64}),repo,user))
    assert exc.value.status_code==403
    repo.query.assert_not_called()


def test_acceptance_is_email_bound_and_expiring(setup):
    repo,user=setup;repo.query.return_value=[{'client_id':'invited-client'}]
    request=Request({'token':'a'*64})
    assert asyncio.run(members.accept(request,repo,user))=={'accepted':True}
    sql,params=repo.query.call_args.args
    assert 'email=@email' in sql and 'expires_at>CURRENT_TIMESTAMP()' in sql
    assert 'accepted_at IS NULL AND revoked_at IS NULL' in sql
    assert next(p.value for p in params if p.name=='email')==user.email
    assert request.session['client_id']=='invited-client'
    assert 'a'*64 not in [p.value for p in params]


@pytest.mark.parametrize('reason',['Invalid invitation','Already a member','Transaction aborted'])
def test_expired_replayed_or_conflicting_invitation_fails(setup,reason):
    repo,user=setup;repo.query.side_effect=BadRequest(reason)
    request=Request({'token':'a'*64})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(members.accept(request,repo,user))
    assert exc.value.status_code==409
    assert 'client_id' not in request.session


def test_owner_cannot_revoke_self(setup):
    repo,user=setup
    with pytest.raises(HTTPException) as exc:
        members.revoke_member(user.id,Request(),repo,user)
    assert exc.value.status_code==422
    repo.query.assert_not_called()


@pytest.mark.parametrize('reason',['Owner required','Invitation changed','Transaction aborted'])
def test_invitation_revocation_conflict_is_not_reported_as_success(setup,reason):
    repo,user=setup;repo.query.side_effect=BadRequest(reason)
    with pytest.raises(HTTPException) as exc:
        members.revoke_invitation('invitation',Request(),repo,user)
    assert exc.value.status_code==409
