"""Provider-backed OTP checks. A local flag never substitutes for approval."""
import re
from uuid import uuid4

import httpx
from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, Conflict

from app.config import get_settings
from app.services.auth_identity import throttle
from app.services.gst.medallion import param


def configured():
    """Configuration presence only; never implies provider delivery or verification."""
    settings = get_settings()
    return bool(re.fullmatch(r'VA[0-9a-fA-F]{32}', settings.twilio_verify_service_sid)
                and settings.twilio_api_key and settings.twilio_api_secret)


def provider_request(resource, data):
    settings = get_settings()
    if not configured():
        raise HTTPException(503, 'Mobile verification is not configured. Please contact support.')
    url = 'https://verify.twilio.com/v2/Services/' + settings.twilio_verify_service_sid + '/' + resource
    try:
        response = httpx.post(url, data=data, auth=(settings.twilio_api_key, settings.twilio_api_secret), timeout=15)
        if response.status_code in {400, 404}:
            raise HTTPException(422, 'The code is invalid, expired or already used. Request a new code.')
        if response.status_code == 429:
            raise HTTPException(429, 'Too many verification attempts. Please try later.')
        if response.status_code not in {200, 201}:
            raise HTTPException(503, 'Mobile verification is temporarily unavailable.')
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError('Invalid provider response')
        return payload
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, 'Mobile verification is temporarily unavailable.') from None


def start(repo, user):
    mobile = str(getattr(user, 'mobile_number', '') or '')
    if not re.fullmatch(r'\+[1-9][0-9]{7,14}', mobile):
        raise HTTPException(422, 'Save a valid mobile number before requesting a code.')
    if getattr(user, 'mobile_verified', False):
        raise HTTPException(409, 'This mobile number is already verified.')
    throttle(repo, 'mobile-send:' + str(user.id))
    throttle(repo, 'mobile-number:' + mobile)
    payload = provider_request('Verifications', {'To': mobile, 'Channel': 'sms'})
    sid = str(payload.get('sid', ''))
    if payload.get('status') != 'pending' or payload.get('to') != mobile or not re.fullmatch(r'VE[0-9a-fA-F]{32}', sid):
        raise HTTPException(503, 'The provider did not start mobile verification.')
    challenge = str(uuid4())
    repo.query(f'''INSERT INTO `{repo.table('mobile_challenges')}`
        VALUES (@id,@uid,@mobile,@sid,CURRENT_TIMESTAMP(),TIMESTAMP_ADD(CURRENT_TIMESTAMP(),INTERVAL 10 MINUTE),NULL)''',
        [param('id', challenge), param('uid', str(user.id)), param('mobile', mobile), param('sid', sid)])
    return {'challenge_id': challenge, 'expires_in': 600}


def check(repo, user, challenge, code):
    if not re.fullmatch(r'[0-9]{4,10}', str(code)) or not re.fullmatch(r'[0-9a-f-]{36}', str(challenge)):
        raise HTTPException(422, 'Enter the code from your verification message.')
    throttle(repo, 'mobile-check:' + str(user.id))
    params = [param('id', challenge), param('uid', str(user.id)), param('mobile', str(getattr(user, 'mobile_number', '') or ''))]
    rows = repo.query(f'''SELECT provider_sid FROM `{repo.table('mobile_challenges')}`
        WHERE id=@id AND user_id=@uid AND mobile_number=@mobile AND consumed_at IS NULL AND expires_at>CURRENT_TIMESTAMP()''', params)
    if len(rows) != 1:
        raise HTTPException(422, 'This verification has expired or was already used.')
    sid = rows[0]['provider_sid']
    payload = provider_request('VerificationCheck', {'VerificationSid': sid, 'Code': code})
    if payload.get('status') != 'approved' or payload.get('sid') != sid or payload.get('to') != getattr(user, 'mobile_number', ''):
        raise HTTPException(422, 'The verification code was not approved.')
    try:
        repo.query(f'''BEGIN TRANSACTION;
        ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_guard')}` WHERE id='identity')=1 AS 'Storage guard missing';
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        ASSERT (SELECT COUNT(*) FROM `{repo.table('mobile_challenges')}` WHERE id=@id AND user_id=@uid AND mobile_number=@mobile AND consumed_at IS NULL AND expires_at>CURRENT_TIMESTAMP())=1 AS 'Mobile challenge changed';
        UPDATE `{repo.table('users')}` SET mobile_verified=TRUE WHERE id=@uid AND mobile_number=@mobile AND is_active=TRUE;
        ASSERT @@row_count=1 AS 'Mobile challenge changed';
        INSERT INTO `{repo.table('auth_events')}` VALUES (GENERATE_UUID(),@uid,'mobile_verified',CURRENT_TIMESTAMP());
        UPDATE `{repo.table('mobile_challenges')}` SET consumed_at=CURRENT_TIMESTAMP() WHERE user_id=@uid AND mobile_number=@mobile AND consumed_at IS NULL;
        COMMIT TRANSACTION;''', params)
    except (BadRequest, Conflict) as exc:
        if any(word in str(exc).lower() for word in ('mobile challenge changed', 'concurrent', 'aborted')):
            raise HTTPException(409, 'Your mobile details changed. Request a new code.') from None
        raise
    return {'mobile_verified': True}
