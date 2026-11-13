import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.db import get_db
from app.routes import current_user
from app.gst import returns, reconciliation_reviews
from app.gst.report import calculate
from app.services.gst.medallion import clean, param, period_value
from app.services.gst.account import can
from app.services.documents import validate_upload
from app.services.gst.method_a import assess, build_package
from .gst_bills import scope, profile_for

router=APIRouter(prefix='/api/gst/returns',tags=['Return preparation'])


def _history(store, period, snapshot_id):
    rows=store.query(f'''SELECT actor_id,action,reason,from_state,to_state,created_at
        FROM {store.table('ops','gst_return_audit')}
        WHERE client_id=@client_id AND period=@period AND snapshot_id=@snapshot
          AND action IN ('method_a_package_downloaded','portal_evidence_uploaded','customer_filing_evidence_recorded')
        ORDER BY created_at DESC LIMIT 100''',
        [param('period',period),param('snapshot',snapshot_id or '')])
    result=[]
    for row in rows:
        raw=row.get('reason') or '{}'
        try:
            details=json.loads(raw) if isinstance(raw,str) else raw
        except (TypeError, ValueError):
            details={'message':'Audit detail is unavailable.'}
        if isinstance(details,dict):
            details={key:value for key,value in details.items() if key!='gcs_uri'}
        result.append({'actor_id':str(row.get('actor_id') or ''),'action':row.get('action'),
            'details':details,'from_state':row.get('from_state'),'to_state':row.get('to_state'),
            'created_at':str(row.get('created_at'))})
    return result


def _approved_snapshot(store, period, client, user, repo):
    if getattr(client,'is_test',False):
        raise HTTPException(403,'Synthetic workspaces cannot generate filing packages or record statutory filing evidence.')
    state=returns.current(store,period)
    if state.get('state')!='approved' or not state.get('snapshot_id'):
        raise HTTPException(409,'A maker-checker approved snapshot is required first.')
    if state.get('source_hash')!=returns.fingerprint(store,period):
        raise HTTPException(409,'The approved snapshot is stale. Reopen, resolve changes and obtain approval again.')
    snapshot=returns.snapshot(store,period,state)
    profile=profile_for(repo,client.id,period)
    invoices=store.list(period)
    assessment=assess(invoices,profile,store.matching_rows(period),period)
    if not assessment.get('valid'):
        raise HTTPException(409,{'code':'return_validation_failed','message':'Resolve the return preparation blockers before continuing.','blockers':assessment['blockers']})
    return state,snapshot,assessment


def _audit(store, period, snapshot_id, user, action, details):
    store.query(f'''INSERT INTO {store.table('ops','gst_return_audit')}
        (client_id,period,snapshot_id,actor_id,action,reason,from_state,to_state,created_at)
        VALUES (@client_id,@period,@snapshot,@actor,@action,@reason,'approved','approved',CURRENT_TIMESTAMP())''',
        [param('period',period),param('snapshot',snapshot_id),param('actor',str(user.id)),
         param('action',action),param('reason',json.dumps(details,sort_keys=True))])


@router.get('')
def get_return(request: Request,period: str,repo=Depends(get_db),user=Depends(current_user)):
    client,store=scope(request,repo,user)
    period=period_value(period)
    state=returns.current(store,period)
    return clean({**state,'snapshot':returns.snapshot(store,period,state) if state.get('snapshot_id') else None,
                  'can_review':user.role in {'admin','tax_admin'},'user_id':str(user.id),
                  'can_write':can(user,'bills:write',client.id,repo),
                  'filing_history':_history(store,period,state.get('snapshot_id')) if state.get('snapshot_id') else [],
                  'source_changed':bool(state.get('source_hash') and state['source_hash']!=returns.fingerprint(store,period)),
                  'portal_export_supported':False,'is_test':getattr(client,'is_test',False)})


@router.post('/validate')
async def validate_return(request: Request,period: str,repo=Depends(get_db),user=Depends(current_user)):
    client,store=scope(request,repo,user)
    period=period_value(period)
    body=await request.json()
    if not isinstance(body,dict):
        raise HTTPException(422,'Return validation request must be a JSON object.')
    state=returns.current(store,period)
    if type(body.get('version')) is not int or body['version']!=state.get('version',0):
        raise HTTPException(409,'Return changed. Refresh before validating again.')
    profile=profile_for(repo,client.id,period)
    invoices=store.list(period)
    result=assess(invoices,profile,store.matching_rows(period),period)
    return clean({**result,'is_test':getattr(client,'is_test',False),
        'notice':'Validation is an internal preparation check, not GST Portal acceptance or a legal opinion.'})


@router.post('/{action}')
async def change_return(action: str,request: Request,period: str,repo=Depends(get_db),user=Depends(current_user)):
    client,store=scope(request,repo,user,'bills:write')
    period=period_value(period)
    if getattr(client,'is_test',False):
        raise HTTPException(403,'Synthetic workspaces cannot approve or prepare real returns.')
    body=await request.json()
    if not isinstance(body,dict):
        raise HTTPException(422,'Return update must be a JSON object.')
    if type(body.get('version')) is not int or body['version']<0:
        raise HTTPException(422,'Provide the current return version.')
    if not isinstance(body.get('reason',''),str) or len(body.get('reason',''))>1000:
        raise HTTPException(422,'Enter a review reason of at most 1000 characters.')
    payload=None;source_hash=''
    if action=='prepare':
        source_hash=returns.fingerprint(store,period)
        invoices=store.list(period)
        profile=profile_for(repo,client.id,period)
        statement=store.matching_rows(period)
        assessment=assess(invoices,profile,statement,period)
        if not assessment['valid']:
            raise HTTPException(409,{'code':'return_validation_failed','message':'Resolve the return preparation blockers before preparing a snapshot.','blockers':assessment['blockers']})
        if any(inv.sample for inv in invoices):
            raise HTTPException(403,'Sample records cannot be prepared for filing.')
        confirmed=[inv for inv in invoices if inv.status=='confirmed']
        payload={'draft':True,'portal_upload_ready':False,'format':'gst-easy-working-paper-v1',
                 'period':period,'gstin':profile['gstin'],'prepared_at':datetime.now(timezone.utc).isoformat(),
                 'invoices':[inv.model_dump(mode='json') for inv in confirmed],
                 'reconciliation_reviews':clean(reconciliation_reviews.latest(store,period)),
                 'profile':clean(profile),'statement':clean(statement),'summary':clean(calculate(confirmed,profile,statement)),
                 'validation':clean({'warnings':assessment['warnings'],'portal_upload_ready':False})}
    return clean(returns.change(store,period,user,action,body['version'],source_hash,payload,body.get('reason','')))


@router.get('/working-paper')
def working_paper(request: Request,period: str,repo=Depends(get_db),user=Depends(current_user)):
    client,store=scope(request,repo,user)
    if getattr(client,'is_test',False):
        raise HTTPException(403,'Synthetic workspaces cannot export financial return evidence.')
    period=period_value(period)
    state=returns.current(store,period)
    if state['state']!='approved' or state['source_hash']!=returns.fingerprint(store,period):
        raise HTTPException(409,'An approved, current snapshot is required.')
    return Response(json.dumps(returns.snapshot(store,period,state),sort_keys=True,separators=(',',':')),
        media_type='application/json',headers={'Cache-Control':'private, no-store',
        'Content-Disposition':f'attachment; filename="GST-Easy-{period}-approved-working-paper-DRAFT.json"'})


@router.get('/filing-package')
def filing_package(request: Request,period: str,repo=Depends(get_db),user=Depends(current_user)):
    client,store=scope(request,repo,user)
    period=period_value(period)
    state,snapshot,assessment=_approved_snapshot(store,period,client,user,repo)
    content=build_package(snapshot,assessment,state['snapshot_id'],state['source_hash'])
    digest=hashlib.sha256(content).hexdigest()
    filename=f'GST-Easy-Method-A-Guided-Package-{period}.zip'
    reference=str(uuid5(NAMESPACE_URL,f'{client.id}/{period}/{state["snapshot_id"]}/{digest}'))
    uri=store.upload_object(content,reference,filename,'filing-packages','application/zip')
    _audit(store,period,state['snapshot_id'],user,'method_a_package_downloaded',
           {'sha256':digest,'gcs_uri':uri,'portal_upload_file':False,'snapshot_hash':state['source_hash']})
    return Response(content,media_type='application/zip',headers={
        'Content-Disposition':f'attachment; filename="{filename}"','Cache-Control':'private, no-store',
        'X-GST-Easy-Package-SHA256':digest})


@router.post('/filing-evidence/upload')
async def upload_filing_evidence(request: Request,period: str,file: UploadFile=File(...),repo=Depends(get_db),user=Depends(current_user)):
    client,store=scope(request,repo,user,'bills:write')
    period=period_value(period)
    state,_,_=_approved_snapshot(store,period,client,user,repo)
    content,filename,mime=await validate_upload(file)
    digest=hashlib.sha256(content).hexdigest()
    safe_name=Path(filename).name
    reference=str(uuid5(NAMESPACE_URL,f'{client.id}/{period}/{state["snapshot_id"]}/filing-evidence/{digest}'))
    uri=store.upload_object(content,reference,safe_name,'filing-evidence',mime)
    _audit(store,period,state['snapshot_id'],user,'portal_evidence_uploaded',
           {'evidence_id':digest,'filename':safe_name,'mime_type':mime,'gcs_uri':uri,'sha256':digest,
            'customer_uploaded':True,'officially_verified':False})
    return {'evidence_id':digest,'filename':safe_name,'officially_verified':False,
            'message':'Evidence stored privately. GST Easy has not verified it with the GST Portal.'}


@router.post('/filing-evidence')
async def record_filing_evidence(request: Request,period: str,repo=Depends(get_db),user=Depends(current_user)):
    client,store=scope(request,repo,user,'bills:write')
    period=period_value(period)
    state,_,_=_approved_snapshot(store,period,client,user,repo)
    body=await request.json()
    if not isinstance(body,dict):
        raise HTTPException(422,'Filing acknowledgement must be a JSON object.')
    reference=str(body.get('acknowledgement_reference') or '').strip()
    filed_at=str(body.get('filed_at') or '').strip()
    evidence_ids=body.get('evidence_ids') or []
    if not isinstance(evidence_ids,list) or not reference or len(reference)>64 or not filed_at or len(evidence_ids)>10:
        raise HTTPException(422,'Provide an acknowledgement reference, filing date, and at most ten uploaded evidence IDs.')
    try:
        filing_date=datetime.strptime(filed_at,'%Y-%m-%d').date()
        if filing_date>datetime.now(timezone.utc).date():
            raise ValueError()
    except ValueError:
        raise HTTPException(422,'Enter a valid non-future filing date.') from None
    if any(not isinstance(item,str) or len(item)!=64 or any(c not in '0123456789abcdef' for c in item.lower()) for item in evidence_ids):
        raise HTTPException(422,'Evidence IDs must refer to uploaded evidence records.')
    rows=store.query(f'''SELECT reason FROM {store.table('ops','gst_return_audit')}
        WHERE client_id=@client_id AND period=@period AND snapshot_id=@snapshot AND action='portal_evidence_uploaded' ''',
        [param('period',period),param('snapshot',state['snapshot_id'])])
    known=set()
    for row in rows:
        details=row.get('reason') or '{}'
        details=json.loads(details) if isinstance(details,str) else details
        if details.get('evidence_id'):
            known.add(details['evidence_id'])
    if not set(evidence_ids)<=known:
        raise HTTPException(422,'One or more evidence files do not belong to this approved return snapshot.')
    _audit(store,period,state['snapshot_id'],user,'customer_filing_evidence_recorded',
        {'status':'customer_reported_unverified','acknowledgement_reference':reference,
         'filed_at':filing_date.isoformat(),'evidence_ids':evidence_ids,'customer_attested':True,
         'officially_verified':False})
    return {'status':'customer_reported_unverified','officially_verified':False,
            'message':'Filing evidence recorded as customer-reported. GST Easy has not verified the status with the GST Portal.'}
