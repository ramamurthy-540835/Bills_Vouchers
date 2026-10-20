from fastapi import APIRouter, Depends, HTTPException, Query, Request

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
    raise HTTPException(403, {'code':'sample_data_blocked','message':'Sample packs cannot be exported.'})


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
    from app.config import get_settings
    if get_settings().gst_bills_enabled:
        from app.gst.store import BillStore
        from app.gst.evidence import documents, confirmed_summary, reconciliation_context
        from app.gst.report import calculate
        from app.services.auth_identity import throttle
        from app.routes import active_client
        throttle(repo,'assistant:'+str(user.id))
        bills=BillStore(repo,store.client_id)
        invoices=bills.list(store.period)
        profile=store.profile() or {}
        statements=bills.matching_rows(store.period)
        report=calculate(invoices,profile,statements)
        dashboard={'period':store.period,'profile':profile,'source':'canonical','summary':{**report,**confirmed_summary(invoices)},
                   'totals':report['totals'],'validated_invoices':report['confirmed_count'],
                   'sample':getattr(active_client(request,repo,user),'is_test',False),
                   'reconciliation':reconciliation_context(invoices,statements,bool(statements) or bool(bills.statement_history(store.period)))}
        context=grounded_context(dashboard,documents(invoices[:500],store.period),payload.question)
        context['client_id']=store.client_id
        return generate_answer(payload,context)
    workspace = store.workspace()
    from ...fixtures.red_taxi_sample import use_sample, sample_dashboard
    dashboard = sample_dashboard(store) if use_sample(store) else customer_dashboard(store)
    context = grounded_context(dashboard, workspace['documents'], payload.question, ledger=workspace['ledger'])
    context['client_id']=store.client_id
    return generate_answer(payload, context)
