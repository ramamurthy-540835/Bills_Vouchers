"""Self-service registration creates exactly one isolated client membership."""
import re
from uuid import uuid4

from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, Conflict

from app.security import hash_password, password_is_strong
from app.services.gst.medallion import param
from app.services.gst.profiles import validate_gstin
from app.services.identity_validation import registration_mobile


def register(repo, body):
    email = str(body.get('email', '')).strip().lower()
    name = str(body.get('full_name', '')).strip()
    business = str(body.get('business_name', '')).strip()
    password = str(body.get('password', ''))
    mobile = registration_mobile(body)
    gstin = str(body.get('gstin', '')).strip()
    gst = validate_gstin(gstin) if gstin else dict(valid=True, gstin='', pan='', state_code='', entity_code='')
    if len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise HTTPException(422, 'Enter a valid email address.')
    if not name or len(name) > 120 or not business or len(business) > 200:
        raise HTTPException(422, 'Enter your name and business name.')
    if not password_is_strong(password):
        raise HTTPException(422, 'Use at least 12 characters and at most 72 UTF-8 bytes, including uppercase, lowercase and a number.')
    if password != body.get('confirm'):
        raise HTTPException(422, 'Passwords do not match.')
    if not gst['valid']:
        raise HTTPException(422, gst['message'])
    uid, cid, mail_id = str(uuid4()), str(uuid4()), str(uuid4())
    params = [param(k, v) for k, v in dict(email=email, name=name, business=business,
        uid=uid, cid=cid, mid=str(uuid4()), pid=str(uuid4()), mail_id=mail_id, password=hash_password(password), mobile=mobile,
        gstin=gst['gstin'], pan=gst['pan'], state=gst['state_code'], entity=gst['entity_code']).items()]
    try:
        repo.query(f'''BEGIN TRANSACTION;
        ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_guard')}` WHERE id='identity')=1 AS 'Storage guard missing';
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        ASSERT NOT EXISTS(SELECT 1 FROM `{repo.table('users')}` WHERE LOWER(email)=@email) AS 'Account already exists';
        INSERT INTO `{repo.table('users')}` (id,email,password_hash,full_name,role,is_active,created_at,must_change_password,session_version,mobile_number,mobile_verified,email_verified)
        VALUES (@uid,@email,@password,@name,'client',TRUE,CURRENT_TIMESTAMP(),FALSE,0,@mobile,FALSE,FALSE);
        INSERT INTO `{repo.table('clients')}` (id,code,name,gstin,address,is_active,created_at,storage_slug,is_test)
        VALUES (@cid,@cid,@business,@gstin,'',TRUE,CURRENT_TIMESTAMP(),@cid,FALSE);
        INSERT INTO `{repo.table('client_memberships')}` (id,client_id,user_id,access_role,is_active,created_at)
        VALUES (@mid,@cid,@uid,'client',TRUE,CURRENT_TIMESTAMP());
        INSERT INTO `{repo.table('client_user_role')}` (email,client_id,role,effective_from,effective_to,is_current)
        VALUES (@email,@cid,'client',CURRENT_TIMESTAMP(),NULL,TRUE);
        INSERT INTO `{repo.table('gst_client_profile')}` (profile_id,client_id,gstin,pan,state_code,entity_code,legal_name,trade_name,contact_email,contact_person,status,filing_frequency,gstin_verified,effective_from,is_current,source,created_by,created_at)
        VALUES (@pid,@cid,@gstin,@pan,@state,@entity,@business,@business,@email,@name,'ACTIVE','monthly',FALSE,CURRENT_TIMESTAMP(),TRUE,'SELF_REGISTRATION',@uid,CURRENT_TIMESTAMP());
        INSERT INTO `{repo.table('auth_events')}` VALUES (GENERATE_UUID(),@uid,'registration_pending_verification',CURRENT_TIMESTAMP());
        INSERT INTO `{repo.table('auth_outbox')}` VALUES (@mail_id,@email,'verify','pending',CURRENT_TIMESTAMP(),NULL,NULL);
        COMMIT TRANSACTION;''', params)
    except (BadRequest, Conflict) as exc:
        if 'account already exists' in str(exc).lower():
            raise HTTPException(409, 'An account already exists for this email. Sign in instead.') from None
        if any(s in str(exc).lower() for s in ('concurrent', 'aborted')):
            raise HTTPException(409, 'Registration is busy. Please try again.') from None
        raise
    return {'id': uid, 'client_id': cid, 'email': email, 'mail_id': mail_id}
