from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from ...db import get_db
from ...routes import current_user
from .assistant import ChatRequest, check_rate, generate_answer, grounded_context
from .dashboard import customer_dashboard
from .evidence_search import search_evidence
from .mock_data import SCENARIOS, generate_mock_data
from .workbench import selected

router = APIRouter()


@router.get('/api/demo/redtaxi-pack')
def redtaxi_pack(period: str = '2026-09', user=Depends(current_user)):
    import hashlib
    import io
    import json
    from pathlib import Path
    from zipfile import ZIP_DEFLATED, ZipFile
    from .filing_workspace import csv_bytes
    from .redtaxi_mock import png_prompts
    bundle = generate_mock_data('redtaxi', period)
    files = {'mock-data.json':json.dumps(bundle,indent=2,ensure_ascii=False).encode('utf-8'),
             'PNG-PROMPTS.md':png_prompts(bundle).encode('utf-8'),
             'README-AUDITORS.md':(Path(__file__).resolve().parents[3]/'docs/README-REDTAXI-AUDITORS.md').read_bytes()}
    for name,rows in [('sales',bundle['outward']),('gstr2b',bundle['gstr2b']),('itc-decisions',bundle['ledger'])]:
        files[name+'.csv']=csv_bytes(rows,list(rows[0]) if rows else [])
    files['manifest.json']=json.dumps({'sample':True,'period':period,'seed':42,
        'sha256':{name:hashlib.sha256(body).hexdigest() for name,body in files.items()}},indent=2).encode()
    output=io.BytesIO()
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for name,body in files.items():
            archive.writestr(name,body)
    return Response(output.getvalue(),media_type='application/zip',headers={
        'Content-Disposition':f'attachment; filename="RedTaxi-DEMO-{period}.zip"','Cache-Control':'private, no-store'})


def demo_bundle(scenario: str = 'mixed', period: str = '2026-09', seed: int = Query(42, ge=0, le=1000000)):
    try:
        return generate_mock_data(scenario, period, seed)
    except ValueError:
        raise HTTPException(422, 'Choose a valid demo scenario and period.')


@router.get('/api/demo/scenarios')
def scenarios(user=Depends(current_user)):
    return {'scenarios': [{'id': name, 'label': label} for name, label in SCENARIOS.items()]}


@router.get('/api/demo/data')
def demo_data(bundle=Depends(demo_bundle), user=Depends(current_user)):
    return {**bundle, 'user': {'full_name': user.full_name, 'email': user.email, 'role': user.role},
            'scenario_options': [{'id': name, 'label': label} for name, label in SCENARIOS.items()]}


@router.get('/api/demo/search')
def demo_search(q: str = '', status: str = '', minimum: str | None = None, maximum: str | None = None,
                offset: int = 0, limit: int = 20, bundle=Depends(demo_bundle), user=Depends(current_user)):
    return {**search_evidence(bundle['documents'], q, status, minimum, maximum, offset, limit), 'sample': True}


@router.post('/api/demo/chat')
def demo_chat(payload: ChatRequest, bundle=Depends(demo_bundle), user=Depends(current_user)):
    check_rate(str(user.id))
    context = grounded_context(bundle['dashboard'], bundle['documents'], payload.question, bundle['scenario'], bundle['ledger'])
    return generate_answer(payload, context)


@router.post('/api/assistant/chat')
def live_chat(payload: ChatRequest, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    check_rate(str(user.id))
    store = selected(request, repo, user)
    workspace = store.workspace()
    context = grounded_context(customer_dashboard(store), workspace['documents'], payload.question, ledger=workspace['ledger'])
    return generate_answer(payload, context)
