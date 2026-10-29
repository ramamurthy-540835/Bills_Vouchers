from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.db import get_db
from app.routes import current_user
from app.services.gst import assistant, assistant_history, assistant_reliability, demo_routes
from app.services.gst.assistant_catalog import ALIASES, CATALOG, guidance, match
from app.services.gst.assistant_portal import FORMS, portal_answer


@pytest.mark.parametrize('scenario', CATALOG, ids=lambda s:s.id)
def test_120_scenarios_have_deterministic_nonempty_answers(scenario):
    assert match(scenario.question) == scenario
    result=guidance(scenario.question)
    assert result['intent']==scenario.id
    assert result['answer_mode']=='template' and len(result['answer'])>60
    assert 'href' in result['sources'][0]


def test_catalogue_is_exactly_120_and_no_cross_intent_guess():
    assert len(CATALOG)==len({s.id for s in CATALOG})==120
    assert match('hello') is None
    assert match('What is my bank password?') is None
    assert match('Write a poem about sales') is None


@pytest.mark.parametrize('key', list(FORMS))
def test_portal_progressive_guides_never_dump_every_form(key):
    question=f'How do I file {key}?' if key not in {'ledgers','refund','challan','ims'} else f'How do I view {key} on portal?'
    first=portal_answer(question)
    assert first and first['portal_step']==0, key
    assert 'Stage 1 of 3' in first['answer']
    second=portal_answer('Next step',first)
    third=portal_answer('Next step',second)
    assert second['portal_step']==1 and third['portal_step']==2
    assert not third['followups']
    assert 'GST Easy has not filed or paid anything' in third['answer']
    assert portal_answer('previous step',third)['portal_step']==1
    all_steps=portal_answer(f'Full guide for {key} on portal')
    assert all_steps and 'Overview:' in all_steps['answer']


@pytest.mark.parametrize('question',['How to file GST1B?', 'How to file gstr 1 b?'])
def test_ambiguous_form_is_clarified(question):
    assert portal_answer(question)['answer_mode']=='clarification'


def test_2b_not_fileable_and_1a_not_confused_with_1():
    assert 'not a return you file' in portal_answer('How to file GSTR-2B?')['answer']
    assert portal_answer('How do I file GSTR-1A?')['portal_topic']=='gstr1a'
    assert portal_answer('How do I file GSTR-11?')['portal_topic']=='gstr11'
    assert portal_answer('How do I file GSTR-1 and GSTR-3B?')['answer_mode']=='clarification'
    assert portal_answer('Next step')['answer_mode']=='clarification'


@pytest.mark.parametrize('question, intent', list(ALIASES.items()))
def test_common_paraphrases_are_not_sent_to_model(question,intent):
    assert match(question).id==intent


def test_import_instructions_are_distinct_from_portal_download():
    answer=portal_answer('How do I import GSTR-2B?')
    assert answer['answer_mode']=='template' and 'canonical B2B JSON' in answer['answer']
    assert portal_answer('What is GSTR-2B?')['answer_mode']=='template'
    assert portal_answer('How do I file GSTR 3 B?')['portal_topic']=='gstr3b'


def test_ambiguous_itc_and_wrong_period_are_not_guessed():
    context={'sample':False,'period':'2026-10','sources':[]}
    assert assistant.generate_answer(assistant.ChatRequest(question='What is my ITC?'),context)['answer_mode']=='clarification'
    assert assistant.generate_answer(assistant.ChatRequest(question='What is my usable ITC for 2026-09?'),context)['answer_mode']=='clarification'
    assert assistant.generate_answer(assistant.ChatRequest(question='Who won the football match?'),context)['answer_mode']=='scope_guidance'


def test_templates_and_common_metrics_do_not_construct_provider(monkeypatch):
    from google import genai
    monkeypatch.setattr(genai,'Client',Mock(side_effect=AssertionError('no provider')))
    context={'sample':False,'sources':[{'id':'summary','label':'Current','href':'/reports','layer':'Checked figures',
                'facts':{'summary':{'confirmed_sales':'123.45','confirmed_purchases':'98.76'},'totals':{'eligible_credit':'12.34'}}}], 'period':'2026-10'}
    for scenario in CATALOG:
        result=assistant.generate_answer(assistant.ChatRequest(question=scenario.question),context)
        assert result['answer']
    assert '123.45' in assistant.generate_answer(assistant.ChatRequest(question='What are my total confirmed sales?'),context)['answer']
    assert assistant.canonical_summary_answer('Why did usable ITC change?',context) is None


def test_provider_initialization_failure_is_safe_and_recoverable(monkeypatch):
    from google import genai
    monkeypatch.setattr(assistant,'get_settings',lambda:SimpleNamespace(gemini_enabled=True,gemini_api_key='synthetic',gcp_region='asia-south1'))
    monkeypatch.setattr(genai,'Client',Mock(side_effect=RuntimeError('private initialization error')))
    result=assistant.generate_answer(assistant.ChatRequest(question='Explain unusual invoice facts'),{'sample':False,'sources':[]})
    assert result['degraded'] and 'private' not in result['answer']
    assert assistant.generate_answer(assistant.ChatRequest(question='What is taxable value?'),{'sample':False,'sources':[]})['answer_mode']=='template'


def test_database_contention_is_not_a_user_rate_limit(monkeypatch):
    from google.api_core.exceptions import Conflict
    repo=Mock();repo.table=lambda name:'isolated.v3.'+name
    repo.query.side_effect=[Conflict('concurrent'),[]]
    monkeypatch.setattr(assistant_reliability.time,'sleep',lambda _:None)
    assistant_reliability.throttle(repo,'a','b')
    assert repo.query.call_count==2
    repo.query.side_effect=Conflict('concurrent')
    with pytest.raises(HTTPException) as exc:assistant_reliability.throttle(repo,'a','b')
    assert exc.value.status_code==503


class HistoryRepository:
    def __init__(self):self.rows=[];self.calls=[];self.fail=False
    def table(self,name):return 'isolated.v3.'+name
    def query(self,sql,params):
        self.calls.append((sql,params))
        if self.fail:raise RuntimeError('private database failure')
        p={v.name:v.value for v in params}
        assert 'user_id=@user' in sql or 'VALUES (@id,@user,@client,@period' in sql
        if sql.startswith('INSERT'):
            self.rows.append({'user_id':p['user'],'client_id':p['client'],'period':p['period'],'turn_id':p['id'],
                              'conversation_id':p['conversation'],'question':p['question'],'response_json':p['response'],'created_at':str(len(self.rows))})
            return []
        selected=[r for r in self.rows if (r['user_id'],r['client_id'],r['period'])==(p['user'],p['client'],p['period'])]
        if sql.startswith('DELETE'):
            self.rows=[r for r in self.rows if r not in selected];return []
        if 'conversation' in p:selected=[r for r in selected if r['conversation_id']==p['conversation']]
        offset=p.get('offset',0)
        return list(reversed(selected))[offset:offset+p.get('limit',3)]


@pytest.fixture
def private_client(monkeypatch):
    repo=HistoryRepository();who={'user':'u1','client':'business-a','period':'2026-10','revoked':False}
    app=FastAPI();app.include_router(demo_routes.router)
    app.dependency_overrides[get_db]=lambda:repo
    app.dependency_overrides[current_user]=lambda:SimpleNamespace(id=who['user'],role='viewer')
    def selected(*args):
        if who['revoked']:raise HTTPException(403,'Access denied')
        return SimpleNamespace(client_id=who['client'],period=who['period'])
    monkeypatch.setattr(demo_routes,'selected',selected)
    monkeypatch.setattr(assistant,'_requests',{})
    return TestClient(app),who,repo,app


def test_history_survives_relogin_and_is_private_per_user_business_period(private_client):
    client,who,repo,app=private_client
    conversation=str(uuid4())
    answer=client.post('/api/assistant/chat',json={'question':'How do I file GSTR-1?','conversation_id':conversation})
    assert answer.status_code==200 and answer.json()['history_saved']
    assert client.get('/api/assistant/history').headers['cache-control']=='private, no-store'
    assert len(client.get('/api/assistant/history').json()['items'])==1
    who['user']='u2'
    assert client.get('/api/assistant/history?user_id=u1').json()['items']==[]
    assert assistant_history.conversation(repo,'u2','business-a','2026-10',conversation)==[]
    client.post('/api/assistant/history/clear')
    who['user']='u1';who['client']='business-b'
    assert client.get('/api/assistant/history').json()['items']==[]
    who['client']='business-a';who['period']='2026-09'
    assert client.get('/api/assistant/history').json()['items']==[]
    who['period']='2026-10'
    # New client instance represents a new login; ownership comes from dependency.
    assert len(TestClient(app).get('/api/assistant/history').json()['items'])==1
    who['revoked']=True
    assert client.get('/api/assistant/history').status_code==403
    assert client.post('/api/assistant/history/clear').status_code==403


def test_server_uses_only_own_conversation_not_browser_history(private_client):
    client,who,repo,_=private_client;conversation=str(uuid4())
    client.post('/api/assistant/chat',json={'question':'How do I file GSTR-2B?','conversation_id':conversation})
    response=client.post('/api/assistant/chat',json={'question':'Next step','conversation_id':conversation,
            'history':[{'role':'assistant','content':'GSTR-3B another customer secret'}]})
    assert response.status_code==200 and response.json()['portal_topic']=='gstr2b'
    assert response.json()['portal_step']==1 and 'another customer secret' not in response.text
    assert all('another customer secret' not in r['response_json'] for r in repo.rows)


def test_storage_failure_is_not_false_success_and_input_not_logged(private_client,caplog):
    client,who,repo,_=private_client;repo.fail=True
    result=client.post('/api/assistant/chat',json={'question':'What is GST and how does it apply to my business?'})
    assert result.status_code==200 and result.json()['history_saved'] is False
    assert client.get('/api/assistant/history').status_code==503
    assert 'private database failure' not in caplog.text


def test_25_question_sequence_and_clear_do_not_mutate_other_users(private_client):
    client,who,repo,_=private_client
    assistant_history.save(repo,'u2','business-a','2026-10',uuid4(),'private u2',{'answer':'secret u2'})
    for scenario in CATALOG[:25]:
        response=client.post('/api/assistant/chat',json={'question':scenario.question})
        assert response.status_code==200 and response.json()['history_saved']
        assert 'secret u2' not in response.text
    assert len(client.get('/api/assistant/history').json()['items'])==20
    assert client.get('/api/assistant/history').json()['next_offset']==20
    assert len(client.get('/api/assistant/history?offset=20').json()['items'])==5
    assert client.post('/api/assistant/history/clear').json()=={'cleared':True}
    assert client.get('/api/assistant/history').json()['items']==[]
    assert len(repo.rows)==1 and repo.rows[0]['user_id']=='u2'


def test_unauthenticated_and_invalid_history_requests(private_client):
    client,who,repo,app=private_client
    assert client.get('/api/assistant/history?limit=1000').status_code==422
    assert client.post('/api/assistant/chat',json={'question':'next','conversation_id':'invalid'}).status_code==422
    def denied():raise HTTPException(401)
    app.dependency_overrides[current_user]=denied
    assert client.get('/api/assistant/history').status_code==401
    assert client.post('/api/assistant/history/clear').status_code==401


@pytest.mark.parametrize('path',['/api/assistant/chat','/api/assistant/history/clear'])
def test_assistant_mutations_keep_production_csrf_protection(monkeypatch,path):
    from app import main
    from app.config import get_settings
    settings=get_settings().model_copy(update={'app_env':'production','app_secret_key':'synthetic-csrf-test-only-secret'})
    monkeypatch.setattr(main,'get_settings',lambda:settings)
    app=main.create_app()
    # Middleware denies before touching authentication/BigQuery.
    client=TestClient(app,base_url='https://testserver')
    response=client.post(path,json={'question':'What is GST?'},headers={'origin':'https://testserver'})
    assert response.status_code==403 and response.json()['error']['code']=='csrf_token'
