"""Only the current authorized business; no supplier or arbitrary GSTIN input."""
from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, Depends, HTTPException, Request
from app.config import get_settings
from app.db import get_db
from app.routes import current_user, active_client
from .medallion import Medallion
from .taxpayer_provider import integration
from .taxpayer_verification import EvidenceStore, presentation, verify

router = APIRouter()


def scope(request, repo, user, write=False):
    from .account import can
    client = active_client(request,repo,user)
    if not can(user,'edit_profile' if write else 'bills:read',client.id,repo):
        raise HTTPException(403,'You do not have permission to verify this business.')
    return client, Medallion(repo,client.id,'2026-09').profile()


@router.get('/api/businesses/current/gstin-verification')
def status(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client, profile = scope(request,repo,user)
    settings = get_settings()
    provider, mode = integration(settings)
    try:
        evidence = EvidenceStore(repo,client.id).latest() if settings.gst_verification_storage_enabled else None
    except Exception:
        raise HTTPException(503,'Verification history could not be loaded. Please retry.') from None
    result = presentation(profile,evidence,provider is not None,mode)
    from .account import can
    result['can_verify'] = provider is not None and not getattr(client,'is_test',False) and can(user,'edit_profile',client.id,repo)
    return result


@router.post('/api/businesses/current/verify-gstin')
async def lookup(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client, profile = scope(request,repo,user,True)
    if request.query_params or await request.body():
        raise HTTPException(422,'This action verifies only the saved current business. Do not supply a GSTIN or client ID.')
    settings = get_settings()
    provider, _ = integration(settings)
    if provider is None:
        raise HTTPException(503,'Automatic verification not configured.')
    if getattr(client,'is_test',False):
        raise HTTPException(403,'Live verification is disabled for synthetic businesses.')
    try:
        result = await run_in_threadpool(verify,EvidenceStore(repo,client.id),profile,user.id,settings.gst_verification_provider,provider)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503,'Verification evidence could not be recorded. Please retry later.') from None
    # Do not let an in-flight profile change make an old result look current.
    from .medallion import clear_cache
    clear_cache(str(client.id))
    from .taxpayer_verification import fingerprint
    if fingerprint(Medallion(repo,client.id,'2026-09').profile()) != fingerprint(profile):
        result.update(state='stale',fresh=False)
    result['can_verify'] = True
    return result
