"""Idempotent customer provisioning; shared private storage, isolated tenant rows."""
import json
from uuid import UUID, uuid5, NAMESPACE_URL

from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, Conflict, PreconditionFailed, GoogleAPICallError

from app.config import get_settings
from app.services.gst.medallion import param
from app.services.gst.profiles import validate_gstin, website_url


def provision_storage(client_id):
    from google.cloud.storage import Client
    settings = get_settings()
    blob = Client(project=settings.gcp_project_id).bucket(settings.gcs_bucket_name).blob(
        f'{client_id}/profile/workspace.json')
    content = json.dumps({'client_id': client_id, 'version': 1}, sort_keys=True)
    try:
        blob.upload_from_string(content, content_type='application/json', if_generation_match=0)
    except PreconditionFailed:
        if blob.download_as_bytes() != content.encode():
            raise HTTPException(409, 'Customer storage configuration conflicts. Contact support.') from None


def create_customer(repo, user, body):
    if user.role not in {'client', 'admin', 'tax_admin'}:
        raise HTTPException(403, 'You cannot create a customer workspace.')
    try:
        request_id = str(UUID(str(body.get('request_id', ''))))
        website = website_url(body.get('website_url', ''))
    except ValueError as exc:
        raise HTTPException(422, 'Enter a valid request identifier and company website.') from exc
    name = str(body.get('legal_name', '')).strip()
    if not name or len(name) > 200:
        raise HTTPException(422, 'Enter a business legal name of 1–200 characters.')
    raw_gstin = str(body.get('gstin', '')).strip()
    gst = validate_gstin(raw_gstin) if raw_gstin else dict(valid=True, gstin='', pan='', state_code='', entity_code='')
    if not gst['valid']:
        raise HTTPException(422, gst['message'])
    cid = str(uuid5(NAMESPACE_URL, f'gst-easy/customer/{user.id}/{request_id}'))
    values = dict(cid=cid, uid=str(user.id), email=user.email.lower(), person=user.full_name,
                  name=name, website=website, gstin=gst['gstin'], pan=gst['pan'],
                  state=gst['state_code'], entity=gst['entity_code'])
    # Create-only marker contains no personal information. If SQL fails, retry reuses it.
    try:
        provision_storage(cid)
        repo.query(f'''BEGIN TRANSACTION;
        ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_guard')}` WHERE id='identity')=1 AS 'Storage guard missing';
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        IF NOT EXISTS(SELECT 1 FROM `{repo.table('clients')}` WHERE id=@cid) THEN
          INSERT INTO `{repo.table('clients')}` (id,code,name,gstin,address,is_active,created_at,storage_slug,is_test)
          VALUES (@cid,@cid,@name,@gstin,'',TRUE,CURRENT_TIMESTAMP(),@cid,FALSE);
          INSERT INTO `{repo.table('client_memberships')}` (id,client_id,user_id,access_role,is_active,created_at)
          VALUES (GENERATE_UUID(),@cid,@uid,'owner',TRUE,CURRENT_TIMESTAMP());
          INSERT INTO `{repo.table('client_user_role')}` (email,client_id,role,effective_from,effective_to,is_current)
          VALUES (@email,@cid,'client',CURRENT_TIMESTAMP(),NULL,TRUE);
          INSERT INTO `{repo.table('gst_client_profile')}`
          (profile_id,client_id,gstin,pan,state_code,entity_code,legal_name,trade_name,website_url,contact_email,contact_person,status,filing_frequency,gstin_verified,effective_from,is_current,source,created_by,created_at)
          VALUES (GENERATE_UUID(),@cid,@gstin,@pan,@state,@entity,@name,@name,@website,@email,@person,'ACTIVE','monthly',FALSE,CURRENT_TIMESTAMP(),TRUE,'CUSTOMER_SETUP',@uid,CURRENT_TIMESTAMP());
          INSERT INTO `{repo.table('profile_audit')}` (id,client_id,actor_id,action,before_value,after_value,created_at)
          VALUES (GENERATE_UUID(),@cid,@uid,'customer_created',NULL,JSON_OBJECT('legal_name',@name),CURRENT_TIMESTAMP());
        END IF;
        ASSERT EXISTS(SELECT 1 FROM `{repo.table('client_memberships')}` WHERE client_id=@cid AND user_id=@uid AND access_role='owner' AND is_active=TRUE) AS 'Customer ownership changed';
        COMMIT TRANSACTION;''', [param(k, v) for k, v in values.items()])
    except (BadRequest, Conflict) as exc:
        raise HTTPException(409, 'Customer setup could not finish. Retry or contact support if access changed.') from exc
    except GoogleAPICallError as exc:
        raise HTTPException(503, 'Customer setup is temporarily unavailable. Retry with the same form.') from exc
    return {'client_id': cid, 'saved': True, 'storage_ready': True}
