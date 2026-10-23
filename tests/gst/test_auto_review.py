from copy import deepcopy
from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.gst import auto_review
from app.gst.jobs import process_job
from app.gst.schemas.invoice import AutoReview
from app.routers import gst_bills


@pytest.fixture
def store(invoice):
    invoice.extraction.raw_ref = 'original'
    invoice.supplier_address = 'Synthetic supplier address'
    invoice.recipient_address = 'Synthetic recipient address'
    invoice.recipient_legal_name = 'Synthetic recipient'
    invoice.auto_review = AutoReview(enabled=True, requested_by='owner')
    state = SimpleNamespace(current=invoice, audit=[], locked=False)
    result = Mock(client_id=invoice.client_id)
    result.get.side_effect = lambda _: state.current.model_copy(deep=True)
    result.list.side_effect = lambda: [state.current]
    result.download_object.return_value = b'synthetic original'
    result.query.return_value = [{'policy':{
        'policy_id':'synthetic-reviewed-fixture', 'approved_by':'fixture-reviewer',
        'official_source':'https://cbic-gst.gov.in/gst-invoice-rules.html',
        'legal_basis':'CGST Rules, 2017, rule 46', 'source_version':'synthetic-fixture-v1',
        'source_checked_at':'2026-10-23', 'identity_evidence':'synthetic-identities',
        'review_status':'approved','supplier_gstin':invoice.supplier_gstin,
        'recipient_gstin':invoice.recipient_gstin, 'hsn_sac':'8703','direction':'purchase',
        'supply_type':'intra','place_of_supply':'33','invoice_type':'tax_invoice','rate':'18',
        'effective_from':'2026-09-01','effective_to':'2026-09-30','review_expires_at':'2099-01-01T00:00:00+00:00',
    }}]
    def writable(_):
        if state.locked: raise HTTPException(409, 'Filing period frozen')
    def save(value, actor, action, previous=None, selected_period=None):
        writable(selected_period)
        if previous and previous.version != state.current.version: raise HTTPException(409, 'stale')
        state.current = value.model_copy(deep=True)
        state.audit.append((actor, action))
    result.save.side_effect = save
    result.assert_writable = Mock(side_effect=writable)
    result.state = state
    return result


def test_off_is_default_and_never_confirms(store, profile):
    store.state.current.auto_review = AutoReview()
    result = auto_review.review_invoice(store, profile, 'owner', 'invoice', 1)
    assert result.status != 'confirmed'
    store.save.assert_not_called()


def test_eligible_opt_in_confirms_once_with_audit_and_original(store, profile):
    result = auto_review.review_invoice(store, profile, 'owner', 'invoice', 1)
    assert result.status == 'confirmed' and result.auto_review.status == 'auto_confirmed'
    assert all(result.auto_review.checks.values())
    assert result.extraction.raw_ref == 'original' and result.auto_review.rule_ids
    auto_review.review_invoice(store, profile, 'owner', 'invoice', 1)
    assert store.save.call_count == 1
    assert store.state.audit == [('owner','auto_review_decision')]


def test_v3_resubmitted_invoice_still_requires_manual_approval(store, profile):
    store.state.current.correction_state = 'resubmitted'
    result = auto_review.review_invoice(store, profile, 'owner', 'invoice', 1)
    assert result.status == 'needs_review'
    assert result.correction_state == 'resubmitted'
    assert result.auto_review.status == 'manual_required'
    assert any('correction workflow' in reason for reason in result.auto_review.reasons)


@pytest.mark.parametrize('fault', ['tax','total','gstin','confidence','original','policy','expired','note','duplicate','head','address','untrusted_source','missing_legal_basis'])
def test_hard_gate_failure_never_confirms(store, profile, fault):
    invoice = store.state.current
    if fault == 'tax': invoice.line_items[0].cgst = Decimal('89.99')
    if fault == 'address': invoice.supplier_address = ''
    if fault == 'total': invoice.totals.invoice_total = Decimal('1179.99')
    if fault == 'gstin': invoice.supplier_gstin = ''
    if fault == 'confidence': invoice.extraction.confidence = Decimal('0.1')
    if fault == 'original': store.download_object.side_effect = HTTPException(404)
    if fault == 'policy': store.query.return_value = []
    if fault == 'expired': store.query.return_value[0]['policy']['review_expires_at'] = '2000-01-01'
    if fault == 'untrusted_source': store.query.return_value[0]['policy']['official_source'] = 'https://example.test/rule'
    if fault == 'missing_legal_basis': store.query.return_value[0]['policy']['legal_basis'] = ''
    if fault == 'note': invoice.invoice_type = 'credit_note'
    if fault == 'head': invoice.line_items[0].igst = Decimal('180')
    if fault == 'duplicate':
        other = invoice.model_copy(deep=True); other.invoice_id='another'
        store.list.side_effect = lambda: [invoice, other]
    result = auto_review.review_invoice(store, profile, 'owner', 'invoice', 1)
    assert result.status == 'needs_review'
    assert result.auto_review.status == 'manual_required' and result.auto_review.reasons


def test_lock_and_stale_decision_cannot_write(store, profile):
    store.state.locked = True
    with pytest.raises(HTTPException): auto_review.review_invoice(store, profile, 'owner','id',1)
    store.save.assert_not_called()
    store.state.locked = False
    store.state.current.version = 2
    auto_review.review_invoice(store, profile, 'owner','id',1)
    store.save.assert_not_called()


def test_cancellation_between_check_and_commit_wins(store, profile):
    original = store.download_object.side_effect
    def concurrent_cancel(_):
        store.state.current.version += 1
        store.state.current.auto_review.enabled = False
        return b'evidence'
    store.download_object.side_effect = concurrent_cancel
    with pytest.raises(HTTPException): auto_review.review_invoice(store, profile, 'owner','id',1)
    assert store.state.current.status != 'confirmed'
    assert not store.state.current.auto_review.enabled
    store.download_object.side_effect = original


@pytest.fixture
def api(store, profile, monkeypatch):
    user = SimpleNamespace(id='owner',role='client')
    app = FastAPI();app.include_router(gst_bills.router)
    app.dependency_overrides[gst_bills.current_user] = lambda:user
    app.dependency_overrides[gst_bills.get_db] = lambda:None
    monkeypatch.setattr(gst_bills,'get_settings',lambda:SimpleNamespace(gst_bills_enabled=True,gst_bills_queue=''))
    monkeypatch.setattr(gst_bills,'active_client',lambda *args:SimpleNamespace(id='a',is_test=False))
    monkeypatch.setattr(gst_bills,'BillStore',lambda *args:store)
    monkeypatch.setattr(gst_bills,'can',lambda u,action,*args:action=='bills:read' or u.role!='viewer')
    monkeypatch.setattr(gst_bills,'profile_for',lambda *args:profile)
    jobs = {}
    def job(id,payload=None):
        if payload is not None:jobs[id]=deepcopy(payload)
        return jobs[id]
    store.job.side_effect = job
    store.claim_job.side_effect = lambda id,actor:jobs[id]
    return TestClient(app),user


def test_api_toggle_persists_runs_and_off_does_not_unconfirm(api, store):
    client,_=api
    store.state.current.auto_review=AutoReview()
    path='/api/gst/bills/id'
    response=client.patch(path+'/auto-review',json={'enabled':True},headers={'if-match':'1'})
    assert response.status_code==200
    assert client.get(path).json()['auto_review']['enabled'] is True
    version=response.json()['version']
    response=client.post(path+'/auto-review/run',headers={'if-match':str(version)})
    assert response.status_code==200 and response.json()['status']=='confirmed'
    response=client.patch(path+'/auto-review',json={'enabled':False},headers={'if-match':str(response.json()['version'])})
    assert response.status_code==200 and response.json()['status']=='confirmed'
    assert response.json()['auto_review']['enabled'] is False


def test_api_denies_viewer_stale_missing_version_and_protected_edit(api, store):
    client,user=api;path='/api/gst/bills/id'
    assert client.patch(path+'/auto-review',json={'enabled':True}).status_code==428
    assert client.patch(path+'/auto-review',json={'enabled':True},headers={'if-match':'0'}).status_code==409
    assert client.patch(path,json={'auto_review':{'enabled':True}},headers={'if-match':'1'}).status_code==422
    user.role='viewer'
    assert client.patch(path+'/auto-review',json={'enabled':True},headers={'if-match':'1'}).status_code==403
    assert client.post(path+'/auto-review/run',headers={'if-match':'1'}).status_code==403


@pytest.mark.parametrize('action',['confirm','reject'])
def test_manual_decision_ends_pending_auto_review(api, store, action):
    client,_=api
    store.state.current.auto_review.status='running'
    response=client.post('/api/gst/bills/id/'+action,json={'reason':'Manual decision'},headers={'if-match':'1'})
    assert response.status_code==200
    assert response.json()['auto_review']['status']=='cancelled'


def test_locked_or_rejected_toggle_denied(api, store):
    client,_=api
    store.state.locked=True
    assert client.patch('/api/gst/bills/id/auto-review',json={'enabled':True},headers={'if-match':'1'}).status_code==409
    store.state.locked=False
    store.state.current.status='rejected'
    assert client.patch('/api/gst/bills/id/auto-review',json={'enabled':True},headers={'if-match':'1'}).status_code==409


def test_failed_job_can_retry_but_active_job_cannot(api, store):
    client,_=api
    store.state.current.auto_review.status='running'
    store.state.current.auto_review.job_id='old-job'
    job={'job_id':'old-job','status':'queued','files':[]}
    store.job('old-job',job)
    assert client.post('/api/gst/bills/id/auto-review/run',headers={'if-match':'1'}).status_code==409
    job['status']='needs_attention';store.job('old-job',job)
    response=client.post('/api/gst/bills/id/auto-review/run',headers={'if-match':'1'})
    assert response.status_code==200 and response.json()['auto_review']['status']=='auto_confirmed'


@pytest.mark.parametrize('enabled',[False,True])
def test_batch_policy_not_document_content_controls_auto_review(store,profile,monkeypatch,enabled):
    invoice=store.state.current.model_copy(deep=True)
    store.list.side_effect=lambda:[]
    monkeypatch.setattr('app.gst.jobs.extract',lambda *args:[invoice])
    store.upload_object.return_value='silver'
    job={'job_id':'batch','status':'queued','period':'2026-09','auto_review_enabled':enabled,
         'files':[{'filename':'bill.pdf','doc_id':'doc','raw_ref':'original','status':'reading','invoice_ids':[]}]}
    process_job(store,profile,'owner',job)
    assert store.state.current.auto_review.enabled is enabled
    assert (store.state.current.status=='confirmed') is enabled


def test_mixed_batch_confirms_only_valid_invoice_and_retains_both_originals(store, profile, monkeypatch):
    good=store.state.current.model_copy(deep=True)
    bad=good.model_copy(deep=True);bad.invoice_number='INV-2';bad.totals.invoice_total=Decimal('1181')
    saved={}
    store.list.side_effect=lambda:list(saved.values())
    store.get.side_effect=lambda id:saved[id].model_copy(deep=True)
    def save(value, actor, action, previous=None, selected_period=None):
        if previous and saved[value.invoice_id].version != previous.version: raise HTTPException(409)
        saved[value.invoice_id]=value.model_copy(deep=True)
    store.save.side_effect=save
    store.upload_object.return_value='silver'
    monkeypatch.setattr('app.gst.jobs.extract',lambda *args:[good,bad])
    job={'job_id':'mixed','status':'queued','period':'2026-09','auto_review_enabled':True,
         'files':[{'filename':'two.csv','doc_id':'doc','raw_ref':'original','status':'reading','invoice_ids':[]}]}
    process_job(store,profile,'owner',job)
    assert len(saved)==2
    assert sorted(inv.status for inv in saved.values())==['confirmed','needs_review']
    assert all(inv.extraction.raw_ref=='original' for inv in saved.values())
    assert sum((inv.totals.invoice_total for inv in saved.values() if inv.status=='confirmed'),Decimal(0))==Decimal('1180')
