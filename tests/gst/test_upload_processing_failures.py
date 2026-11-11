"""Synthetic jobs/routes: failed reading retains evidence, never invents bills."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.db import get_db
from app.gst import jobs
from app.gst.auto_review import evaluate
from app.gst.extract import ExtractionResponseError
from app.gst.extraction_issues import clear_reviewed_fields, issue_for
from app.gst.job_state import JobState, retryable
from app.gst.validate_invoice import validate_invoice
from app.routes import current_user
from app.services.model_access import ModelAccessDenied


def batch():
    return {'job_id':'batch','status':'queued','period':'2026-09','files':[
        {'filename':'bad-original.png','doc_id':'bad-doc','raw_ref':'private-bad-original','status':'reading','invoice_ids':[]},
        {'filename':'good-original.pdf','doc_id':'doc','raw_ref':'private-good-original','status':'reading','invoice_ids':[]}]}


def processing_store(invoice):
    saved = []
    blobs = {'private-bad-original':b'original-one','private-good-original':b'original-two'}
    store = Mock(client_id=invoice.client_id)
    store.list.side_effect = lambda: saved.copy()
    store.download_object.side_effect = lambda ref, **kwargs: blobs[ref]
    def upload(content, doc_id, *args):
        ref = 'silver-'+doc_id
        blobs[ref] = content
        return ref
    store.upload_object.side_effect = upload
    store.save.side_effect = lambda value, *args, **kwargs: saved.append(value.model_copy(deep=True))
    return store, saved, blobs


@pytest.mark.parametrize('error,code', [
    (ModelAccessDenied('private business identifier and credential'), 'reading_not_authorized'),
    (TimeoutError('private raw source and credential'), 'reading_timeout'),
    (ExtractionResponseError('private malformed model payload'), 'invalid_extraction_response'),
])
def test_failed_reading_does_not_fabricate_invoice_or_stop_valid_second_file(invoice, profile, monkeypatch, caplog, error, code):
    store, saved, blobs = processing_store(invoice)
    original_bytes = {key:value for key,value in blobs.items()}
    extractor = Mock(side_effect=[error, [invoice.model_copy(deep=True)]])
    monkeypatch.setattr(jobs, 'extract', extractor)
    job = batch()
    result = jobs.process_job(store, profile, 'actor', job)
    assert result['status'] == 'completed'
    assert len(saved) == 1
    assert saved[0].invoice_number == invoice.invoice_number
    assert job['files'][0]['invoice_ids'] == []
    assert 'extracted_ref' not in job['files'][0]
    assert job['files'][0]['original_filename'] == 'bad-original.png'
    assert job['files'][0]['extraction_issue']['code'] == code
    assert job['files'][1]['invoice_ids'] == [saved[0].invoice_id]
    assert all(blobs[key] == value for key,value in original_bytes.items())
    public = jobs.public_job(result)
    assert public['files'][0]['original_url'].endswith('/batch/original/0')
    assert 'raw_ref' not in public['files'][0]
    assert 'private malformed' not in str(public) + caplog.text
    assert 'credential' not in str(public) + caplog.text


def test_unavailable_original_is_individual_failure_and_other_file_continues(invoice, profile, monkeypatch):
    store, saved, blobs = processing_store(invoice)
    del blobs['private-bad-original']
    monkeypatch.setattr(jobs, 'extract', lambda *args:[invoice.model_copy(deep=True)])
    job = jobs.process_job(store, profile, 'actor', batch())
    assert job['files'][0]['extraction_issue']['code'] == 'original_unavailable'
    assert job['files'][0]['invoice_ids'] == []
    assert len(saved) == 1
    assert blobs['private-good-original'] == b'original-two'


@pytest.mark.parametrize('cache', [b'not json', b'[{"unknown":"invalid stored invoice"}]', None])
def test_corrupt_or_unavailable_extraction_cache_is_isolated_and_explicit_retry_rereads_original(invoice,profile,monkeypatch,cache):
    store,saved,blobs=processing_store(invoice)
    if cache is not None:
        blobs['corrupt-silver']=cache
    calls=[]
    def read(content,filename,client_id,doc_id,*args):
        calls.append(doc_id)
        return [invoice.model_copy(deep=True,update={'source_doc_id':doc_id,'invoice_number':'READ-'+doc_id})]
    monkeypatch.setattr(jobs,'extract',read)
    source=batch()
    source['files'][0]['extracted_ref']='corrupt-silver'
    result=jobs.process_job(store,profile,'actor',source)
    assert len(saved)==1 and calls==['doc']
    assert result['files'][0]['extraction_issue']['code']=='extraction_cache_unavailable'
    assert result['files'][0]['raw_ref']=='private-bad-original'
    assert result['files'][0]['invoice_ids']==[]
    assert result['files'][0]['extracted_ref']=='corrupt-silver'
    good_file=deepcopy(result['files'][1])
    assert retryable(result)
    store.job.return_value=deepcopy(result)
    store.transition_job.side_effect=lambda value,*args:value
    retry=JobState.retry_job(store,'batch','actor')
    assert 'extracted_ref' not in retry['files'][0]
    assert retry['files'][1]==good_file
    jobs.process_job(store,profile,'actor',retry)
    assert len(saved)==2 and calls==['doc','bad-doc']
    assert retry['files'][1]==good_file
    assert blobs['private-bad-original']==b'original-one'


@pytest.mark.parametrize('status',[403,409])
def test_reextract_write_race_is_per_file_and_later_valid_invoice_still_saves(invoice,profile,monkeypatch,status):
    store,saved,_=processing_store(invoice)
    previous=invoice.model_copy(deep=True)
    before=previous.model_dump(mode='json')
    store.get.return_value=previous
    store.list.side_effect=lambda:[previous,*saved]
    original_save=store.save.side_effect
    def save(value,*args,**kwargs):
        if args[1]=='extraction_retry':
            raise HTTPException(status,{'code':'bill_conflict','message':'private concurrent mutation details'})
        original_save(value,*args,**kwargs)
    store.save.side_effect=save
    first=invoice.model_copy(deep=True)
    second=invoice.model_copy(deep=True,update={'source_doc_id':'second-doc','invoice_number':'SECOND-2'})
    monkeypatch.setattr(jobs,'extract',Mock(side_effect=[[first],[second]]))
    source=batch()
    source['files'][0].update(doc_id=invoice.source_doc_id,replace_invoice_id=invoice.invoice_id,expected_version=invoice.version)
    source['files'][1]['doc_id']='second-doc'
    result=jobs.process_job(store,profile,'actor',source)
    assert result['files'][0]['extraction_issue']['code']=='extraction_version_changed'
    assert result['files'][0]['invoice_ids']==[]
    assert previous.model_dump(mode='json')==before
    assert len(saved)==1 and saved[0].invoice_number=='SECOND-2'
    assert 'private concurrent' not in str(jobs.public_job(result))


def test_completed_batch_with_transient_failure_can_retry_only_failed_file():
    previous = batch()
    previous['status'] = 'completed'
    previous['files'][0].update(status='needs_attention', extraction_issue=issue_for(TimeoutError('provider failed')))
    previous['files'][1].update(status='ready',invoice_ids=['saved-valid'],extracted_ref='saved-silver')
    assert retryable(previous)
    store = Mock()
    store.job.return_value = deepcopy(previous)
    store.transition_job.side_effect = lambda job,*args:job
    retried = JobState.retry_job(store, 'batch', 'actor')
    assert retried['status'] == 'queued'
    assert retried['files'][0]['status'] == 'reading'
    assert retried['files'][0]['raw_ref'] == 'private-bad-original'
    assert 'extraction_issue' not in retried['files'][0]
    assert retried['files'][1] == previous['files'][1]
    assert store.transition_job.call_args.args[3] == 'job_retry'


def test_completed_policy_failure_does_not_claim_retry_will_fix_authorization():
    previous = batch()
    previous['status'] = 'completed'
    previous['files'] = previous['files'][:1]
    previous['files'][0].update(status='needs_attention', extraction_issue=issue_for(ModelAccessDenied('not allowed')))
    assert not retryable(previous)


@pytest.mark.parametrize('change', ['version','confirmed','rejected','source','auto_review'])
def test_queued_reextract_does_not_overwrite_a_changed_or_protected_invoice(invoice, profile, monkeypatch, change):
    current = invoice.model_copy(deep=True)
    if change == 'version':
        current.version += 1
    elif change in {'confirmed','rejected'}:
        current.status = change
    elif change == 'source':
        current.source_doc_id = 'other-source'
    else:
        current.auto_review.status = 'running'
    before = current.model_dump(mode='json')
    store, saved, _ = processing_store(invoice)
    store.list.return_value = [current]
    store.list.side_effect = None
    store.get.return_value = current
    monkeypatch.setattr(jobs, 'extract', lambda *args:[invoice.model_copy(deep=True)])
    job = batch()
    job['files'] = [job['files'][1]]
    job['files'][0].update(replace_invoice_id=current.invoice_id,expected_version=invoice.version)
    result = jobs.process_job(store, profile, 'actor', job)
    assert saved == []
    assert current.model_dump(mode='json') == before
    assert result['files'][0]['extraction_issue']['code'] == 'extraction_version_changed'


@pytest.mark.parametrize('human_review', [False,True])
def test_unresolved_source_field_is_a_hard_gate_even_with_high_confidence(invoice, profile, human_review):
    invoice.extraction.document_flags = ['field_issue:invalid:totals.invoice_total']
    validated = validate_invoice(invoice, profile, human_review=human_review)
    assert 'extraction_fields_unresolved' in validated.review_reasons
    assert validated.status == 'needs_review'


def test_auto_review_cannot_override_unresolved_source_field(invoice, profile):
    invoice.extraction.document_flags = ['field_issue:missing:totals.cgst']
    store = Mock()
    store.list.return_value = []
    store.query.return_value = []
    store.download_object.return_value = b'private evidence'
    _, reasons, checks, _ = evaluate(store, invoice, profile)
    assert 'extraction_fields_unresolved' in reasons
    assert not checks['required_fields']


def test_review_acknowledgement_requires_exact_submitted_nonempty_field():
    flags = ['field_issue:missing:totals.cgst','field_issue:invalid:invoice_date','duplicate_pdf_page']
    assert clear_reviewed_fields(flags, {'totals':{'cgst':'0'}}, ['totals.cgst']) == flags[1:]
    for body, reviewed in [({},['totals.cgst']), ({'totals':{'sgst':'0'}},['totals.cgst']),
                            ({'totals':{'cgst':None}},['totals.cgst']), ({'totals':{'cgst':''}},['totals.cgst']),
                            ({'invoice_date':'2026-09-01'},['extraction.confidence']),
                            ({'invoice_date':'   '},['invoice_date'])]:
        with pytest.raises(HTTPException) as caught:
            clear_reviewed_fields(flags, body, reviewed)
        assert caught.value.status_code == 422


@pytest.fixture
def upload_api(monkeypatch, invoice, profile):
    from app.routers import gst_bills
    user = SimpleNamespace(id='u',role='client')
    repo = object()
    records = {invoice.invoice_id:invoice.model_copy(deep=True)}
    uploads = {}
    store = Mock(client_id=invoice.client_id)
    store.assert_writable = Mock(return_value=None)
    def get(id):
        if id not in records:
            raise HTTPException(404,'Bill not found.')
        return records[id]
    def job(id, body=None):
        if body is not None:
            uploads[id] = deepcopy(body)
        if id not in uploads:
            raise HTTPException(404,'Upload not found.')
        return uploads[id]
    def save(value,*args,**kwargs):
        records[value.invoice_id] = value
    store.get.side_effect = get
    store.job.side_effect = job
    store.job_history.side_effect = lambda period:list(uploads.values())
    store.list.side_effect = lambda *args:list(records.values())
    store.save.side_effect = save
    store.download_object.return_value = b'original invoice bytes'
    monkeypatch.setattr(gst_bills,'get_settings',lambda:SimpleNamespace(gst_bills_enabled=True,gst_bills_queue='synthetic-queue'))
    monkeypatch.setattr(gst_bills,'BillStore',lambda *args:store)
    monkeypatch.setattr(gst_bills,'active_client',lambda *args:SimpleNamespace(id=invoice.client_id,is_test=False))
    monkeypatch.setattr(gst_bills,'can',lambda actor,action,*args:action=='bills:read' or actor.role=='client')
    monkeypatch.setattr(gst_bills,'profile_for',lambda *args:profile)
    monkeypatch.setattr(gst_bills,'enqueue',Mock())
    app = FastAPI()
    app.include_router(gst_bills.router)
    app.dependency_overrides[get_db] = lambda:repo
    app.dependency_overrides[current_user] = lambda:user
    return TestClient(app), records, uploads, store, user


def test_explicit_reextract_requires_current_version_and_keeps_original(upload_api, invoice):
    client, records, uploads, _, _ = upload_api
    records[invoice.invoice_id].extraction.raw_ref = 'private/retained-source.png'
    url=f'/api/gst/bills/{invoice.invoice_id}/reextract'
    assert client.post(url).status_code == 428
    assert client.post(url,headers={'if-match':'999'}).status_code == 409
    assert uploads == {}
    response = client.post(url,headers={'if-match':str(invoice.version)})
    assert response.status_code == 200
    assert len(uploads) == 1
    entry = next(iter(uploads.values()))['files'][0]
    assert entry['raw_ref'] == 'private/retained-source.png'
    assert entry['replace_invoice_id'] == invoice.invoice_id
    assert entry['expected_version'] == invoice.version
    assert records[invoice.invoice_id].version == invoice.version


@pytest.mark.parametrize('state',['confirmed','rejected','running','locked'])
def test_reextract_protects_confirmed_rejected_running_and_locked_work(upload_api,invoice,state):
    client,records,uploads,store,_=upload_api
    saved=records[invoice.invoice_id]
    saved.extraction.raw_ref='private/original.pdf'
    if state in {'confirmed','rejected'}:
        saved.status=state
    elif state=='running':
        saved.auto_review.status='running'
    else:
        store.assert_writable.side_effect=HTTPException(409,'Period locked')
    before=saved.model_dump(mode='json')
    result=client.post(f'/api/gst/bills/{invoice.invoice_id}/reextract',headers={'if-match':'1'})
    assert result.status_code==409
    assert uploads=={}
    assert records[invoice.invoice_id].model_dump(mode='json')==before


def test_failed_upload_original_is_authenticated_tenant_scoped_and_private(upload_api):
    client, _, uploads, _, user = upload_api
    uploads['failed-upload'] = batch()
    url='/api/gst/bills/upload/failed-upload/original/0'
    response=client.get(url)
    assert response.status_code==200
    assert response.content==b'original invoice bytes'
    assert response.headers['cache-control']=='private, no-store'
    assert 'bad-original.png' in response.headers['content-disposition']
    assert client.get('/api/gst/bills/upload/foreign-job/original/0').status_code==404
    assert client.get('/api/gst/bills/upload/failed-upload/original/99').status_code==404
    user.role='viewer'
    assert client.post('/api/gst/bills/foreign/reextract',headers={'if-match':'1'}).status_code==403


def test_patch_only_clears_explicitly_supplied_reviewed_paths_and_confirmation_stays_blocked(upload_api, invoice):
    client, records, _, _, _=upload_api
    records[invoice.invoice_id].extraction.document_flags=['field_issue:missing:totals.cgst','field_issue:invalid:invoice_date']
    url=f'/api/gst/bills/{invoice.invoice_id}'
    assert client.post(url+'/confirm',headers={'if-match':'1'}).status_code==409
    bad=client.patch(url,headers={'if-match':'1'},json={'reviewed_extraction_fields':['totals.cgst']})
    assert bad.status_code==422
    result=client.patch(url,headers={'if-match':'1'},json={'totals':invoice.totals.model_dump(mode='json'),'reviewed_extraction_fields':['totals.cgst']})
    assert result.status_code==200
    assert result.json()['extraction']['document_flags']==['field_issue:invalid:invoice_date']
    assert client.post(url+'/confirm',headers={'if-match':'2'}).status_code==409
    result=client.patch(url,headers={'if-match':'2'},json={'invoice_date':'2026-09-01','reviewed_extraction_fields':['invoice_date']})
    assert result.status_code==200
    assert result.json()['extraction']['document_flags']==[]
    assert client.post(url+'/confirm',headers={'if-match':'3'}).status_code==200


@pytest.mark.parametrize('body',[None,[],42,'not a bill'])
def test_malformed_patch_body_fails_validation_instead_of_crashing(upload_api,invoice,body):
    client,*_=upload_api
    result=client.patch(f'/api/gst/bills/{invoice.invoice_id}',headers={'if-match':'1'},json=body)
    assert result.status_code==422


def test_original_invoice_period_is_preserved_and_explained(invoice,profile,monkeypatch):
    from unittest.mock import Mock
    from app.gst.jobs import process_job, public_job
    monkeypatch.setattr('app.gst.jobs.extract',lambda *args:[invoice.model_copy(deep=True)])
    store=Mock(client_id=invoice.client_id)
    store.list.return_value=[]
    store.download_object.return_value=b'synthetic original'
    store.upload_object.return_value='synthetic-cache'
    job={'job_id':'different-period','status':'queued','period':'2026-10','files':[{'filename':'september-original.png','doc_id':'doc','raw_ref':'original','status':'reading','invoice_ids':[]}]}
    process_job(store,profile,'reviewer',job)
    saved=store.save.call_args.args[0]
    assert str(saved.invoice_date)=='2026-09-01'
    assert saved.selected_period=='2026-10'
    assert job['files'][0]['invoice_periods']==['2026-09']
    assert '2026-09' in public_job(job)['files'][0]['period_notice']


def test_explicit_replacement_lines_resolve_removed_row_without_dummy_rows(upload_api,invoice):
    from app.gst.schemas.invoice import LineItem
    client,records,_,_,_=upload_api
    previous=records[invoice.invoice_id]
    previous.line_items.append(LineItem(quantity='0'))
    previous.extraction.document_flags=['field_issue:invalid:line_items',
        'field_issue:missing:line_items.1.quantity','field_issue:missing:line_items.1.hsn_sac']
    url=f'/api/gst/bills/{invoice.invoice_id}'
    replacement=[invoice.line_items[0].model_dump(mode='json')]
    # Removing the bad row alone is not proof of source review.
    result=client.patch(url,headers={'if-match':'1'},json={'line_items':replacement})
    assert result.status_code==200
    assert 'extraction_fields_unresolved' in result.json()['review_reasons']
    assert client.post(url+'/confirm',headers={'if-match':'2'}).status_code==409
    # A reviewer can explicitly attest the new collection; obsolete row indices
    # must no longer require creating fake replacement data.
    result=client.patch(url,headers={'if-match':'2'},json={'line_items':replacement,'reviewed_extraction_fields':['line_items']})
    assert result.status_code==200
    assert result.json()['extraction']['document_flags']==[]
    assert len(result.json()['line_items'])==1
    assert client.post(url+'/confirm',headers={'if-match':'3'}).status_code==200


def test_replacement_acknowledgement_preserves_other_unreviewed_field_issues(invoice):
    flags=['field_issue:missing:line_items.1.quantity','field_issue:missing:totals.invoice_total','duplicate_pdf_page']
    replacement=[invoice.line_items[0].model_dump(mode='json')]
    assert clear_reviewed_fields(flags,{'line_items':replacement},['line_items'])==flags[1:]
    with pytest.raises(HTTPException):
        clear_reviewed_fields(flags,{'line_items':[]},['line_items'])


def test_reviewed_replacement_cannot_bypass_wrong_gst_arithmetic(upload_api,invoice):
    client,records,_,_,_=upload_api
    records[invoice.invoice_id].extraction.document_flags=['field_issue:missing:line_items.0.cgst']
    replacement=[invoice.line_items[0].model_dump(mode='json')]
    replacement[0]['cgst']='0'
    url=f'/api/gst/bills/{invoice.invoice_id}'
    result=client.patch(url,headers={'if-match':'1'},json={'line_items':replacement,'reviewed_extraction_fields':['line_items']})
    assert result.status_code==200
    assert result.json()['extraction']['document_flags']==[]
    assert 'tax_arithmetic' in result.json()['review_reasons']
    assert client.post(url+'/confirm',headers={'if-match':'2'}).status_code==409
