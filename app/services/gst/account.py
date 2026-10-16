"""Account edits are authenticated and bound to the selected client membership."""
import re
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import Response
from ...config import get_settings
from ...db import get_db
from ...repository import FinanceRepository
from ...routes import current_user, active_client
from .medallion import Medallion, clean, clear_cache, param
from .profiles import validate_gstin, website_url, company_checks
from .membership_permissions import is_owner
from .validation import VALID_STATE_CODES

router = APIRouter()


@router.post('/api/settings/customers')
async def create_customer(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    from app.services.customer_workspace import create_customer as provision
    result = provision(repo, user, await request.json())
    request.session['client_id'] = result['client_id']
    return result


@router.post('/api/auth/mobile/start')
def start_mobile(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    from app.services.mobile_verification import start
    return start(repo, user)


@router.post('/api/auth/mobile/check')
async def check_mobile(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    from app.services.mobile_verification import check
    body = await request.json()
    return check(repo, user, str(body.get('challenge_id', '')), str(body.get('code', '')))


def logo_blob(client_id):
    from google.cloud.storage import Client
    settings = get_settings()
    return Client(project=settings.gcp_project_id).bucket(settings.gcs_bucket_name).blob(f'{client_id}/profile/logo.png')


def archive_logo(blob, client_id):
    from google.api_core.exceptions import NotFound
    try:
        blob.reload()
    except NotFound:
        return 0, None
    generation = int(blob.generation)
    key = f'{client_id}/profile/history/{uuid4()}.png'
    blob.bucket.copy_blob(blob, blob.bucket, key, if_source_generation_match=generation)
    return generation, key


def audit_logo(repo, client_id, actor, action, before, after):
    repo.query(f'''INSERT INTO `{repo.table('profile_audit')}`
        (id,client_id,actor_id,action,before_value,after_value,created_at)
        VALUES (GENERATE_UUID(),@client_id,@actor,@action,PARSE_JSON(@before),PARSE_JSON(@after),CURRENT_TIMESTAMP())''',
        [param('client_id',str(client_id)),param('actor',str(actor)),param('action',action),
         param('before',json.dumps(before)),param('after',json.dumps(after))])


@router.delete('/api/settings/profile/logo')
def remove_logo(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    from google.api_core.exceptions import PreconditionFailed
    client = active_client(request, repo, user)
    if not can(user, 'edit_profile', client.id, repo):
        raise HTTPException(403, 'You cannot edit this client profile.')
    blob = logo_blob(client.id)
    try:
        generation, archive = archive_logo(blob, client.id)
        if not generation:
            return {'removed':False}
        audit_logo(repo, client.id, user.id, 'logo_remove_requested', {'archive':archive,'generation':generation}, None)
        blob.delete(if_generation_match=generation)
    except PreconditionFailed:
        raise HTTPException(409, 'The logo changed. Reload before removing it.') from None
    audit_logo(repo, client.id, user.id, 'logo_removed', {'archive':archive,'generation':generation}, None)
    return {'removed':True}


@router.get('/api/settings/profile/logo')
def get_logo(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    from google.api_core.exceptions import NotFound
    client = active_client(request, repo, user)
    try:
        content = logo_blob(client.id).download_as_bytes()
    except NotFound:
        raise HTTPException(404, 'No logo uploaded.') from None
    return Response(content, media_type='image/png', headers={'Cache-Control': 'private, no-store'})


@router.post('/api/settings/profile/logo')
def upload_logo(request: Request, file: UploadFile = File(...), repo=Depends(get_db), user=Depends(current_user)):
    from io import BytesIO
    from PIL import Image, ImageOps, UnidentifiedImageError
    client = active_client(request, repo, user)
    if not can(user, 'edit_profile', client.id, repo):
        raise HTTPException(403, 'You cannot edit this client profile.')
    content = file.file.read(2 * 1024 * 1024 + 1)
    if not content or len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, 'Choose a logo up to 2 MB.')
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format not in {'PNG', 'JPEG', 'WEBP'} or image.width * image.height > 16000000:
                raise ValueError('Invalid logo')
            normalized = ImageOps.exif_transpose(image).convert('RGBA')
            normalized.thumbnail((1024, 1024))
            output = BytesIO()
            normalized.save(output, format='PNG')
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, 'Choose a valid PNG, JPEG or WebP logo under 16 megapixels.') from None
    from google.api_core.exceptions import PreconditionFailed
    blob = logo_blob(client.id)
    try:
        generation, archive = archive_logo(blob, client.id)
        audit_logo(repo, client.id, user.id, 'logo_upload_requested', {'archive':archive,'generation':generation}, {'file':'logo.png'})
        blob.upload_from_string(output.getvalue(), content_type='image/png', if_generation_match=generation)
    except PreconditionFailed:
        raise HTTPException(409, 'The logo changed. Reload before replacing it.') from None
    audit_logo(repo, client.id, user.id, 'logo_uploaded', {'archive':archive,'generation':generation}, {'file':'logo.png'})
    return {'saved': True}


def can(user, action, client_id, repo):
    roles = {'admin', 'tax_admin', 'client', 'viewer'} if action == 'bills:read' else {'client', 'tax_admin', 'admin'}
    return (action in {'edit_profile', 'bills:write', 'bills:read'} and user.role in roles
            and FinanceRepository(repo).can_access_client(user.id,client_id))


def phone(value):
    value = str(value or '').strip()
    if value and not re.fullmatch(r'\+[1-9]\d{7,14}',value):
        raise HTTPException(422,'Use an E.164 phone number, for example +919876543210.')
    if value.startswith('+91') and not re.fullmatch(r'\+91[6-9][0-9]{9}', value):
        raise HTTPException(422, 'Enter a valid Indian mobile number with country code +91.')
    return value


@router.get('/api/settings/account')
def account(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    from app.services.mobile_verification import configured
    client = active_client(request,repo,user)
    profile = Medallion(repo,client.id,'2026-09').profile()
    return clean({'client_id':client.id,'profile':profile,'user':{
        'full_name':user.full_name,'email':user.email,'role':user.role,
        'mobile_number':getattr(user,'mobile_number','') or '',
        'mobile_verified':bool(getattr(user,'mobile_verified',False)),
        'last_sign_in':getattr(user,'last_sign_in',None)},
        'clients':[{'id':c.id,'name':c.name} for c in FinanceRepository(repo).clients(user.id)],
        'can_edit_profile':can(user,'edit_profile',client.id,repo),
        'is_owner':is_owner(repo,user,client.id),'require_otp':get_settings().require_otp,
        'mobile_verification_available':configured(), 'company_checks':company_checks(profile)})


@router.post('/api/settings/account')
async def save_account(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    body = await request.json()
    name = str(body.get('full_name','')).strip()
    mobile = phone(body.get('mobile_number'))
    if not name or len(name)>120:
        raise HTTPException(422,'Enter a display name of 1–120 characters.')
    if get_settings().require_otp and not mobile:
        raise HTTPException(422, 'A mobile number is required.')
    repo.query(f"UPDATE `{repo.table('users')}` SET full_name=@name, mobile_verified=IF(COALESCE(mobile_number,'')=@mobile,mobile_verified,FALSE),mobile_number=@mobile WHERE id=@id",
        [param('name',name),param('mobile',mobile),param('id',str(user.id))])
    return {'saved':True}


@router.post('/api/settings/profile')
async def save_profile(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client = active_client(request,repo,user)
    body = await request.json()
    if str(body.get('client_id','')) != str(client.id) or not can(user,'edit_profile',client.id,repo):
        raise HTTPException(403,'You cannot edit this client profile.')
    store = Medallion(repo,client.id,'2026-09')
    previous = store.profile()
    if not previous:
        raise HTTPException(409,'A client profile must be created by the administrator first.')
    if body.get('profile_id') and str(body['profile_id']) != str(previous['profile_id']):
        raise HTTPException(409, 'The business profile changed. Reload before saving.')
    fields = ['legal_name','trade_name','contact_email','contact_phone','contact_person','principal_address',
              'constitution','registration_type','filing_frequency','state_code','pan','website_url']
    changes = {k:str(body[k]).strip() for k in fields if k in body}
    if 'website_url' in body:
        try:
            changes['website_url'] = website_url(body['website_url'])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
    if 'legal_name' in changes and not changes['legal_name']:
        raise HTTPException(422,'Legal name is required.')
    if any(len(v)>2000 for v in changes.values()):
        raise HTTPException(422,'A profile field is too long.')
    if changes.get('contact_email') and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',changes['contact_email']):
        raise HTTPException(422,'Enter a valid contact email.')
    if 'contact_phone' in changes:
        changes['contact_phone'] = phone(changes['contact_phone'])
    allowed = {'constitution': {'Proprietorship','Partnership','LLP','Company','Trust','Other'},
               'registration_type': {'Regular','Composition','Unregistered'},
               'filing_frequency': {'monthly','quarterly'}, 'state_code': VALID_STATE_CODES}
    for field, values in allowed.items():
        if field in changes and changes[field] and changes[field] not in values:
            raise HTTPException(422, f'Choose a valid {field.replace("_", " ")}.')
    if changes.get('pan') and not re.fullmatch(r'[A-Z]{5}[0-9]{4}[A-Z]', changes['pan']):
        raise HTTPException(422, 'Enter a valid PAN.')
    if 'gstin' in body:
        if user.role not in {'tax_admin','admin'} and not is_owner(repo,user,client.id):
            raise HTTPException(403,'A business owner or tax administrator must change the GSTIN.')
        supplied = str(body['gstin']).strip()
        unregistered = changes.get('registration_type', previous.get('registration_type')) == 'Unregistered'
        result = validate_gstin(supplied) if supplied else {'valid':unregistered,'message':'A GSTIN is required for a registered business.',
            'gstin':'','pan':changes.get('pan',previous.get('pan') or ''),'state_code':changes.get('state_code',previous.get('state_code') or ''),'entity_code':''}
        if not result['valid']:
            raise HTTPException(422,result)
        if str(previous.get('legal_name','')).lower()=='red taxi' and result['state_code']!='33':
            raise HTTPException(422,'Red Taxi requires a Tamil Nadu registration.')
        changes.update({k:result[k] for k in ('gstin','pan','state_code','entity_code')})
    effective = {**previous, **changes}
    if effective.get('gstin'):
        identity = validate_gstin(effective['gstin'])
        if identity['valid'] and (effective.get('pan') != identity['pan'] or effective.get('state_code') != identity['state_code']):
            raise HTTPException(422, 'PAN and registration state must match the GSTIN.')
    required = ('legal_name','constitution','registration_type','state_code','principal_address','contact_person','contact_email','contact_phone','filing_frequency')
    complete = all(effective.get(field) for field in required) and (effective.get('registration_type') == 'Unregistered' or bool(effective.get('gstin')))
    if body.get('complete_onboarding') and not complete:
        raise HTTPException(422, 'Complete the required business, registration, address and contact fields.')
    if not changes:
        return {'saved':False}
    params = [param('client_id',str(client.id)),param('previous',previous['profile_id']),param('new_id',str(uuid4())),param('actor',str(user.id))]
    params += [param(k,v) for k,v in changes.items()]
    params += [param('onboarding', complete, 'BOOL'), param('before_profile',json.dumps(previous,default=str)), param('after_profile',json.dumps(effective,default=str))]
    replacements = [f'@{k} AS {k}' for k in changes]
    replacements += ['@new_id AS profile_id','CURRENT_TIMESTAMP() AS effective_from',
        'CURRENT_TIMESTAMP() AS created_at','@actor AS created_by',"'ACCOUNT_SETTINGS' AS source", '@onboarding AS onboarding_completed']
    if 'gstin' in changes:
        replacements.append('FALSE AS gstin_verified')
    from google.api_core.exceptions import BadRequest, Conflict
    canonical_guard = ''
    if get_settings().gst_bills_enabled:
        from app.gst.store import BillStore
        guard = BillStore(repo,client.id).table('ops','gst_bill_lock')
        canonical_guard = f"UPDATE {guard} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__'; ASSERT @@row_count=1 AS 'Storage guard missing';"
    try:
        repo.query(f"""BEGIN TRANSACTION;
          {canonical_guard}
          ASSERT (SELECT COUNT(*) FROM `{repo.table('gst_client_profile')}` WHERE client_id=@client_id AND profile_id=@previous AND is_current=TRUE)=1 AS 'Profile changed; reload';
          INSERT INTO `{repo.table('gst_client_profile')}` SELECT * REPLACE ({','.join(replacements)}) FROM `{repo.table('gst_client_profile')}` WHERE client_id=@client_id AND profile_id=@previous AND is_current=TRUE;
          UPDATE `{repo.table('gst_client_profile')}` SET is_current=FALSE,effective_to=CURRENT_TIMESTAMP() WHERE client_id=@client_id AND profile_id=@previous AND is_current=TRUE;
          INSERT INTO `{repo.table('profile_audit')}` VALUES (GENERATE_UUID(),@client_id,@actor,'profile_update',PARSE_JSON(@before_profile),PARSE_JSON(@after_profile),CURRENT_TIMESTAMP());
          COMMIT TRANSACTION;""",params)
    except (BadRequest, Conflict) as exc:
        if any(value in str(exc).lower() for value in ('profile changed','concurrent','aborted')):
            raise HTTPException(409, 'The profile changed. Reload before saving.') from None
        raise
    clear_cache(str(client.id))
    return {'saved':True,'gstin_verified':False if 'gstin' in changes else previous.get('gstin_verified')}
