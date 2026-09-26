"""Account edits are authenticated and bound to the selected client membership."""
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from ...config import get_settings
from ...db import get_db
from ...repository import FinanceRepository
from ...routes import current_user, active_client
from .medallion import Medallion, clean, clear_cache, param
from .profiles import validate_gstin

router = APIRouter()


def can(user, action, client_id, repo):
    roles = {'admin', 'tax_admin', 'client', 'viewer'} if action == 'bills:read' else {'client', 'tax_admin', 'admin'}
    return (action in {'edit_profile', 'bills:write', 'bills:read'} and user.role in roles
            and FinanceRepository(repo).can_access_client(user.id,client_id))


def phone(value):
    value = str(value or '').strip()
    if value and not re.fullmatch(r'\+[1-9]\d{7,14}',value):
        raise HTTPException(422,'Use an E.164 phone number, for example +919876543210.')
    return value


@router.get('/api/settings/account')
def account(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client = active_client(request,repo,user)
    profile = Medallion(repo,client.id,'2026-09').profile()
    return clean({'client_id':client.id,'profile':profile,'user':{
        'full_name':user.full_name,'email':user.email,'role':user.role,
        'mobile_number':getattr(user,'mobile_number','') or '',
        'mobile_verified':bool(getattr(user,'mobile_verified',False)),
        'last_sign_in':getattr(user,'last_sign_in',None)},
        'clients':[{'id':c.id,'name':c.name} for c in FinanceRepository(repo).clients(user.id)],
        'can_edit_profile':can(user,'edit_profile',client.id,repo),'require_otp':get_settings().require_otp})


@router.post('/api/settings/account')
async def save_account(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    body = await request.json()
    name = str(body.get('full_name','')).strip()
    mobile = phone(body.get('mobile_number'))
    if not name or len(name)>120:
        raise HTTPException(422,'Enter a display name of 1–120 characters.')
    if get_settings().require_otp and mobile != (getattr(user,'mobile_number','') or ''):
        raise HTTPException(409,{'code':'otp_verification_required','message':'Phone verification is required; OTP delivery is not configured.'})
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
    fields = ['legal_name','trade_name','contact_email','contact_phone','contact_person','principal_address']
    changes = {k:str(body[k]).strip() for k in fields if k in body}
    if 'legal_name' in changes and not changes['legal_name']:
        raise HTTPException(422,'Legal name is required.')
    if any(len(v)>2000 for v in changes.values()):
        raise HTTPException(422,'A profile field is too long.')
    if changes.get('contact_email') and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',changes['contact_email']):
        raise HTTPException(422,'Enter a valid contact email.')
    if 'contact_phone' in changes:
        changes['contact_phone'] = phone(changes['contact_phone'])
    if 'gstin' in body:
        if user.role not in {'tax_admin','admin'}:
            raise HTTPException(403,'A tax administrator must change the GSTIN.')
        result = validate_gstin(body['gstin'])
        if not result['valid']:
            raise HTTPException(422,result)
        if str(previous.get('legal_name','')).lower()=='red taxi' and result['state_code']!='33':
            raise HTTPException(422,'Red Taxi requires a Tamil Nadu registration.')
        changes.update({k:result[k] for k in ('gstin','pan','state_code','entity_code')})
    if not changes:
        return {'saved':False}
    params = [param('client_id',str(client.id)),param('previous',previous['profile_id']),param('new_id',str(uuid4())),param('actor',str(user.id))]
    params += [param(k,v) for k,v in changes.items()]
    replacements = [f'@{k} AS {k}' for k in changes]
    replacements += ['@new_id AS profile_id','CURRENT_TIMESTAMP() AS effective_from',
        'CURRENT_TIMESTAMP() AS created_at','@actor AS created_by',"'ACCOUNT_SETTINGS' AS source"]
    if 'gstin' in changes:
        replacements.append('FALSE AS gstin_verified')
    repo.query(f"""BEGIN TRANSACTION;
      ASSERT (SELECT COUNT(*) FROM `{repo.table('gst_client_profile')}` WHERE client_id=@client_id AND profile_id=@previous AND is_current=TRUE)=1 AS 'Profile changed; reload';
      INSERT INTO `{repo.table('gst_client_profile')}` SELECT * REPLACE ({','.join(replacements)}) FROM `{repo.table('gst_client_profile')}` WHERE client_id=@client_id AND profile_id=@previous AND is_current=TRUE;
      UPDATE `{repo.table('gst_client_profile')}` SET is_current=FALSE,effective_to=CURRENT_TIMESTAMP() WHERE client_id=@client_id AND profile_id=@previous AND is_current=TRUE;
      COMMIT TRANSACTION;""",params)
    clear_cache(str(client.id))
    return {'saved':True,'gstin_verified':False if 'gstin' in changes else previous.get('gstin_verified')}
