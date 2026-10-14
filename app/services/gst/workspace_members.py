"""Owner-managed invitations; acceptance is bound to a verified email identity."""
import hashlib
import hmac
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from google.api_core.exceptions import BadRequest, Conflict

from app.config import get_settings
from app.db import get_db
from app.routes import active_client, current_user
from app.services import auth_mail
from app.services.auth_identity import digest, throttle
from .membership_permissions import is_owner
from .medallion import clean, param

router = APIRouter()
ROLES = {'accountant':'tax_admin', 'tax_admin':'tax_admin', 'viewer':'viewer'}


def invite_token(invitation_id):
    return hmac.new(get_settings().app_secret_key.encode(), ('gst-easy-invitation:' + invitation_id).encode(), hashlib.sha256).hexdigest()


def owner_client(request, repo, user):
    client = active_client(request, repo, user)
    if not is_owner(repo, user, client.id):
        raise HTTPException(403, 'Only the business owner can manage workspace access.')
    return client


@router.get('/api/settings/members')
def members(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client = owner_client(request, repo, user)
    params = [param('cid', str(client.id))]
    people = repo.query(f'''SELECT m.user_id,u.full_name,u.email,m.access_role FROM `{repo.table('client_memberships')}` m
        JOIN `{repo.table('users')}` u ON u.id=m.user_id WHERE m.client_id=@cid AND m.is_active=TRUE''', params)
    invites = repo.query(f'''SELECT id,email,role,expires_at,accepted_at,revoked_at FROM `{repo.table('workspace_invitations')}`
        WHERE client_id=@cid ORDER BY created_at DESC LIMIT 100''', params)
    return clean({'members':[dict(row) for row in people], 'invitations':[dict(row) for row in invites]})


@router.post('/api/settings/invitations')
async def invite(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client = owner_client(request, repo, user)
    auth_mail.ready()
    body = await request.json()
    email = str(body.get('email', '')).strip().lower()
    role = str(body.get('role', ''))
    if role not in ROLES or len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise HTTPException(422, 'Enter a valid email and choose an available role.')
    if email == user.email.lower():
        raise HTTPException(422, 'You already own this workspace.')
    throttle(repo, 'invite:' + str(user.id))
    invitation_id = str(uuid4())
    params = [param('id', invitation_id), param('cid', str(client.id)), param('email', email),
              param('role', role), param('hash', digest(invite_token(invitation_id))), param('actor', str(user.id))]
    try:
        repo.query(f'''BEGIN TRANSACTION;
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        ASSERT EXISTS(SELECT 1 FROM `{repo.table('client_memberships')}` WHERE client_id=@cid AND user_id=@actor AND access_role='owner' AND is_active=TRUE) AS 'Owner required';
        ASSERT NOT EXISTS(SELECT 1 FROM `{repo.table('client_memberships')}` m JOIN `{repo.table('users')}` u ON u.id=m.user_id WHERE m.client_id=@cid AND m.is_active=TRUE AND LOWER(u.email)=@email) AS 'Already a member';
        UPDATE `{repo.table('workspace_invitations')}` SET revoked_at=CURRENT_TIMESTAMP() WHERE client_id=@cid AND email=@email AND accepted_at IS NULL AND revoked_at IS NULL;
        INSERT INTO `{repo.table('workspace_invitations')}` VALUES (@id,@cid,@email,@role,@hash,@actor,CURRENT_TIMESTAMP(),TIMESTAMP_ADD(CURRENT_TIMESTAMP(),INTERVAL 48 HOUR),NULL,NULL,NULL);
        INSERT INTO `{repo.table('auth_outbox')}` VALUES (@id,@email,'invite','pending',CURRENT_TIMESTAMP(),NULL,NULL);
        INSERT INTO `{repo.table('profile_audit')}` VALUES (GENERATE_UUID(),@cid,@actor,'member_invited',NULL,JSON_OBJECT('email',@email,'role',@role),CURRENT_TIMESTAMP());
        COMMIT TRANSACTION;''', params)
    except (BadRequest, Conflict) as exc:
        if any(word in str(exc).lower() for word in ('already a member','owner required','concurrent','aborted')):
            raise HTTPException(409, 'Access changed or this person is already a member. Refresh before retrying.') from None
        raise
    auth_mail.schedule(invitation_id)
    return {'invited':True}


@router.post('/api/settings/invitations/accept')
async def accept(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    if getattr(user, 'email_verified', None) is not True:
        raise HTTPException(403, 'Verify your email before accepting an invitation.')
    body = await request.json()
    token = str(body.get('token', ''))
    if not re.fullmatch(r'[0-9a-f]{64}', token):
        raise HTTPException(422, 'Invalid invitation.')
    throttle(repo, 'accept-invite:' + str(user.id))
    params = [param('hash',digest(token)),param('email',user.email.lower()),param('uid',str(user.id)),param('mid',str(uuid4()))]
    try:
        rows = repo.query(f'''DECLARE invitation STRUCT<id STRING,client_id STRING,role STRING>;
        BEGIN TRANSACTION;
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        SET invitation=(SELECT AS STRUCT id,client_id,role FROM `{repo.table('workspace_invitations')}` WHERE token_hash=@hash AND email=@email AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at>CURRENT_TIMESTAMP());
        ASSERT invitation.id IS NOT NULL AS 'Invalid invitation';
        ASSERT invitation.role IN ('accountant','tax_admin','viewer') AS 'Invalid invitation';
        ASSERT NOT EXISTS(SELECT 1 FROM `{repo.table('client_memberships')}` WHERE client_id=invitation.client_id AND user_id=@uid AND is_active=TRUE) AS 'Already a member';
        INSERT INTO `{repo.table('client_memberships')}` (id,client_id,user_id,access_role,is_active,created_at)
        VALUES (@mid,invitation.client_id,@uid,invitation.role,TRUE,CURRENT_TIMESTAMP());
        UPDATE `{repo.table('client_user_role')}` SET is_current=FALSE,effective_to=CURRENT_TIMESTAMP() WHERE client_id=invitation.client_id AND email=@email AND is_current=TRUE;
        INSERT INTO `{repo.table('client_user_role')}` (email,client_id,role,effective_from,effective_to,is_current)
        VALUES (@email,invitation.client_id,IF(invitation.role='viewer','viewer','tax_admin'),CURRENT_TIMESTAMP(),NULL,TRUE);
        UPDATE `{repo.table('workspace_invitations')}` SET accepted_by=@uid,accepted_at=CURRENT_TIMESTAMP() WHERE id=invitation.id;
        INSERT INTO `{repo.table('profile_audit')}` VALUES (GENERATE_UUID(),invitation.client_id,@uid,'invitation_accepted',NULL,JSON_OBJECT('role',invitation.role),CURRENT_TIMESTAMP());
        COMMIT TRANSACTION;
        SELECT invitation.client_id AS client_id;''', params)
    except (BadRequest, Conflict) as exc:
        if any(word in str(exc).lower() for word in ('invalid invitation','already a member','concurrent','aborted')):
            raise HTTPException(409, 'This invitation expired, was already used or no longer applies to your account.') from None
        raise
    request.session['client_id'] = rows[0]['client_id']
    return {'accepted':True}


@router.delete('/api/settings/members/{member_id}')
def revoke_member(member_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client = owner_client(request, repo, user)
    if member_id == str(user.id):
        raise HTTPException(422, 'The owner cannot revoke their own membership.')
    params = [param('cid',str(client.id)),param('uid',member_id),param('actor',str(user.id))]
    try:
        repo.query(f'''BEGIN TRANSACTION;
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        ASSERT EXISTS(SELECT 1 FROM `{repo.table('client_memberships')}` WHERE client_id=@cid AND user_id=@actor AND access_role='owner' AND is_active=TRUE) AS 'Owner required';
        ASSERT NOT EXISTS(SELECT 1 FROM `{repo.table('client_memberships')}` WHERE client_id=@cid AND user_id=@uid AND access_role='owner' AND is_active=TRUE) AS 'Owner protected';
        UPDATE `{repo.table('client_memberships')}` SET is_active=FALSE WHERE client_id=@cid AND user_id=@uid AND is_active=TRUE;
        ASSERT @@row_count>0 AS 'Member not found';
        UPDATE `{repo.table('client_user_role')}` SET is_current=FALSE,effective_to=CURRENT_TIMESTAMP() WHERE client_id=@cid AND email IN (SELECT email FROM `{repo.table('users')}` WHERE id=@uid) AND is_current=TRUE;
        INSERT INTO `{repo.table('profile_audit')}` VALUES (GENERATE_UUID(),@cid,@actor,'member_revoked',JSON_OBJECT('user_id',@uid),NULL,CURRENT_TIMESTAMP());
        COMMIT TRANSACTION;''', params)
    except (BadRequest, Conflict) as exc:
        if any(word in str(exc).lower() for word in ('owner required','owner protected','member not found','concurrent','aborted')):
            raise HTTPException(409, 'Membership changed or cannot be revoked. Refresh before retrying.') from None
        raise
    return {'revoked':True}


@router.delete('/api/settings/invitations/{invitation_id}')
def revoke_invitation(invitation_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client = owner_client(request, repo, user)
    try:
        repo.query(f'''BEGIN TRANSACTION;
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        ASSERT EXISTS(SELECT 1 FROM `{repo.table('client_memberships')}` WHERE client_id=@cid AND user_id=@actor AND access_role='owner' AND is_active=TRUE) AS 'Owner required';
        UPDATE `{repo.table('workspace_invitations')}` SET revoked_at=CURRENT_TIMESTAMP()
        WHERE id=@id AND client_id=@cid AND accepted_at IS NULL AND revoked_at IS NULL;
        ASSERT @@row_count=1 AS 'Invitation changed';
        INSERT INTO `{repo.table('profile_audit')}` VALUES (GENERATE_UUID(),@cid,@actor,'invitation_revoked',JSON_OBJECT('invitation_id',@id),NULL,CURRENT_TIMESTAMP());
        COMMIT TRANSACTION;''',
        [param('id',invitation_id),param('cid',str(client.id)),param('actor',str(user.id))])
    except (BadRequest, Conflict) as exc:
        if any(word in str(exc).lower() for word in ('owner required','invitation changed','concurrent','aborted')):
            raise HTTPException(409, 'Invitation or access changed. Refresh before retrying.') from None
        raise
    return {'revoked':True}
