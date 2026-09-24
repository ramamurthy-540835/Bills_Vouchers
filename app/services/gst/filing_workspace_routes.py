from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from ...db import get_db
from ...repository import FinanceRepository
from ...routes import current_user
from .filing_workspace import build_filing_workspace, working_papers
from .workbench import selected

router = APIRouter()


@router.get('/api/gst/workspace')
def gst_workspace(request: Request, scope: str = 'month', repo=Depends(get_db), user=Depends(current_user)):
    store = selected(request, repo, user)
    report = build_filing_workspace(repo, store.client_id, store.period, scope)
    report['user'] = {'full_name':user.full_name, 'email':user.email, 'role':user.role}
    report['clients'] = [{'id':c.id,'name':c.name} for c in FinanceRepository(repo).clients(user.id)]
    return report


@router.get('/api/gst/workspace/download')
def download(request: Request, scope: str = 'month', repo=Depends(get_db), user=Depends(current_user)):
    store = selected(request, repo, user)
    report = build_filing_workspace(repo, store.client_id, store.period, scope)
    return Response(working_papers(report), media_type='application/zip', headers={
        'Content-Disposition':f'attachment; filename="GST-working-papers-{store.period}-{scope}.zip"',
        'Cache-Control':'private, no-store'})
