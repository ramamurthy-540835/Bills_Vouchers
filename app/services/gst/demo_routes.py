from fastapi import APIRouter, Depends, HTTPException, Query, Request
import logging
from fastapi.responses import JSONResponse

from ...db import get_db
from ...routes import current_user
from .assistant import ChatRequest, check_rate, generate_answer, grounded_context
from .dashboard import customer_dashboard
from .evidence_search import search_evidence
from .mock_data import SCENARIOS, generate_mock_data
from .workbench import selected

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('/api/assistant/history')
def assistant_history(request: Request, limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0, le=10000), repo=Depends(get_db), user=Depends(current_user)):
    from .assistant_history import recent, read_response
    store = selected(request, repo, user)
    try:
        rows = recent(repo, user.id, store.client_id, store.period, limit, offset)
        items = [{'question': row['question'], 'response': read_response(row),
                  'conversation_id': row['conversation_id'], 'created_at': str(row['created_at'])} for row in rows]
    except Exception:
        logger.warning('assistant_history_unavailable')
        raise HTTPException(503, 'Recently asked could not be loaded. Please retry. Saved history requires the V3 assistant migration.') from None
    return JSONResponse({'items': items, 'next_offset': offset+len(items) if len(items)==limit else None, 'period': store.period, 'retention_days': 90},
                        headers={'Cache-Control': 'private, no-store'})


@router.post('/api/assistant/history/clear')
def clear_assistant_history(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    from .assistant_history import clear
    store = selected(request, repo, user)
    try:
        clear(repo, user.id, store.client_id, store.period)
    except Exception:
        logger.warning('assistant_history_clear_failed')
        raise HTTPException(503, 'History could not be cleared. Please retry.') from None
    return JSONResponse({'cleared': True}, headers={'Cache-Control': 'private, no-store'})


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
    from .assistant_history import conversation, read_response, save
    from .assistant import Turn
    from .assistant_portal import portal_answer
    from .assistant_catalog import guidance
    previous = None
    # Never accept browser-supplied conversation text as another user's context.
    payload.history = []
    try:
        for row in conversation(repo, user.id, store.client_id, store.period, payload.conversation_id):
            previous = read_response(row)
            payload.history.extend([Turn(role='user', content=row['question']),
                                    Turn(role='assistant', content=previous['answer'][:4000])])
    except Exception:
        logger.warning('assistant_conversation_unavailable')

    def finish(answer):
        answer['conversation_id'] = str(payload.conversation_id)
        try:
            save(repo, user.id, store.client_id, store.period, payload.conversation_id, payload.question, answer)
            answer['history_saved'] = True
        except Exception:
            logger.warning('assistant_history_save_failed')
            answer['history_saved'] = False
        return JSONResponse(answer, headers={'Cache-Control': 'private, no-store'})

    # Public instructions need no financial query and disclose no business facts.
    direct = portal_answer(payload.question, previous)
    if direct is None:
        from .assistant_catalog import match
        matched = match(payload.question)
        if matched and matched.id[0] in 'ABCGHJK':
            direct = guidance(payload.question)
    if direct is not None:
        return finish(direct)
    from app.config import get_settings
    if get_settings().gst_bills_enabled:
        from app.gst.store import BillStore
        from app.gst.evidence import documents, confirmed_summary, reconciliation_context
        from app.gst.report import calculate
        from .assistant_reliability import throttle
        from app.routes import active_client
        bills=BillStore(repo,store.client_id)
        invoices=bills.list(store.period)
        profile=store.profile() or {}
        statements=bills.matching_rows(store.period)
        report=calculate(invoices,profile,statements)
        dashboard={'period':store.period,'profile':profile,'source':'canonical','summary':{**report,**confirmed_summary(invoices)},
                   'totals':report['totals'],'heads':report['heads'],'validated_invoices':report['confirmed_count'],
                   'sample':getattr(active_client(request,repo,user),'is_test',False),
                   'reconciliation':reconciliation_context(invoices,statements,bool(statements) or bool(bills.statement_history(store.period)))}
        context=grounded_context(dashboard,documents(invoices[:500],store.period),payload.question)
        context['client_id']=store.client_id
        context['previous_response'] = previous
        return finish(generate_answer(payload,context, before_model=lambda: throttle(repo,str(user.id),store.client_id)))
    workspace = store.workspace()
    from ...fixtures.red_taxi_sample import use_sample, sample_dashboard
    dashboard = sample_dashboard(store) if use_sample(store) else customer_dashboard(store)
    context = grounded_context(dashboard, workspace['documents'], payload.question, ledger=workspace['ledger'])
    context['client_id']=store.client_id
    context['previous_response'] = previous
    from .assistant_reliability import throttle
    return finish(generate_answer(payload, context, before_model=lambda: throttle(repo,str(user.id),store.client_id)))
