from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...db import get_db
from ...routes import current_user
from .assistant import ChatRequest, check_rate, generate_answer, grounded_context
from .dashboard import customer_dashboard
from .evidence_search import search_evidence
from .mock_data import SCENARIOS, generate_mock_data
from .workbench import selected

router = APIRouter()


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
