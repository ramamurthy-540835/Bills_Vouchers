import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.db import get_db
from app.routes import current_user
from app.gst import returns
from app.gst.report import calculate
from app.services.gst.medallion import clean, period_value
from app.services.gst.profiles import validate_gstin
from .gst_bills import scope, profile_for

router=APIRouter(prefix='/api/gst/returns',tags=['Return preparation'])


@router.get('')
def get_return(request: Request,period: str,repo=Depends(get_db),user=Depends(current_user)):
    client,store=scope(request,repo,user)
    period=period_value(period)
    state=returns.current(store,period)
    return clean({**state,'snapshot':returns.snapshot(store,period,state) if state.get('snapshot_id') else None,
                  'can_review':user.role in {'admin','tax_admin'},'user_id':str(user.id),
                  'source_changed':bool(state.get('source_hash') and state['source_hash']!=returns.fingerprint(store,period)),
                  'portal_export_supported':False,'is_test':getattr(client,'is_test',False)})


@router.post('/{action}')
async def change_return(action: str,request: Request,period: str,repo=Depends(get_db),user=Depends(current_user)):
    client,store=scope(request,repo,user,'bills:write')
    period=period_value(period)
    if getattr(client,'is_test',False):
        raise HTTPException(403,'Synthetic workspaces cannot approve or prepare real returns.')
    body=await request.json()
    if not isinstance(body,dict) or type(body.get('version')) is not int or body['version']<0:
        raise HTTPException(422,'Provide the current return version.')
    if not isinstance(body.get('reason',''),str) or len(body.get('reason',''))>1000:
        raise HTTPException(422,'Enter a review reason of at most 1000 characters.')
    payload=None;source_hash=''
    if action=='prepare':
        source_hash=returns.fingerprint(store,period)
        invoices=store.list(period)
        profile=profile_for(repo,client.id,period)
        statement=store.matching_rows(period)
        if not validate_gstin(profile.get('gstin',''))['valid']:
            raise HTTPException(409,'Complete a valid GST business profile before preparing a return.')
        if not invoices or any(inv.sample or inv.status not in {'confirmed','rejected'} for inv in invoices):
            raise HTTPException(409,'Review all invoices and confirm the applicable records before preparation.')
        confirmed=[inv for inv in invoices if inv.status=='confirmed']
        if not confirmed:
            raise HTTPException(409,'No confirmed invoices. Nil-return preparation is not supported yet.')
        payload={'draft':True,'portal_upload_ready':False,'format':'gst-easy-working-paper-v1',
                 'period':period,'gstin':profile['gstin'],'prepared_at':datetime.now(timezone.utc).isoformat(),
                 'invoices':[inv.model_dump(mode='json') for inv in confirmed],
                 'profile':clean(profile),'statement':clean(statement),'summary':clean(calculate(confirmed,profile,statement))}
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
