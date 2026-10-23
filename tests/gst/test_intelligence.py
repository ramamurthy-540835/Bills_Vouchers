import json
from copy import deepcopy
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.gst import intelligence
from app.gst.schemas.invoice import AutoReview
from tests.gst.test_auto_review import store as store_fixture, api as api_fixture
from tests.gst.test_auto_review_storage import make_store


@pytest.fixture
def store(invoice):
    return store_fixture.__wrapped__(invoice)


@pytest.fixture
def api(store,profile,monkeypatch):
    return api_fixture.__wrapped__(store,profile,monkeypatch)


def test_policy_defaults_and_tenant_version_transaction(invoice):
    db=make_store(invoice)
    assert intelligence.policy(db)==intelligence.Policy()
    result=intelligence.update_policy(db,True,'both',0,'owner')
    assert result.enabled and result.version==1 and result.actor=='owner'
    sql,params=db.repo.query.call_args.args
    assert 'client_id=@client_id' in sql and 'BEGIN TRANSACTION' in sql and 'Policy changed' in sql
    assert {p.name:p.value for p in params}['client_id']==invoice.client_id
    db.repo.query.return_value=[{'after_payload':result.model_dump()}]
    with pytest.raises(HTTPException) as error:intelligence.update_policy(db,False,'both',0,'owner')
    assert error.value.status_code==409


@pytest.mark.parametrize('enabled,scope',[(False,'both'),(True,'future')])
def test_scope_does_not_authorize_existing_batch(store,monkeypatch,enabled,scope):
    monkeypatch.setattr(intelligence,'policy',lambda _:intelligence.Policy(enabled=enabled,scope=scope,version=1))
    with pytest.raises(HTTPException):intelligence.start_batch(store,'2026-09','owner',1)
    store.save.assert_not_called()


def batch(store):
    inv=store.state.current
    return {'job_id':'batch','period':'2026-09','status':'reading','business_policy_version':1,
        'files':[{'invoice_id':inv.invoice_id,'version':inv.version,'status':'queued','invoice_ids':[inv.invoice_id]}]}


@pytest.mark.parametrize('change',['none','off','stale','confirmed','rejected','excluded','locked'])
def test_existing_batch_is_fenced_and_retry_safe(store,profile,monkeypatch,change):
    job=batch(store)
    chosen=intelligence.Policy(enabled=change!='off',version=1)
    monkeypatch.setattr(intelligence,'policy',lambda _:chosen)
    inv=store.state.current
    if change=='stale':inv.version+=1
    if change in {'confirmed','rejected'}:inv.status=change
    if change=='excluded':inv.auto_review=AutoReview(enabled=False,requested_at='2026-10-23')
    if change=='locked':store.state.locked=True
    intelligence.process_batch(store,profile,'owner',job)
    if change=='none':assert store.state.current.status=='confirmed'
    else:assert job['files'][0]['status']=='cancelled'
    calls=store.save.call_count
    intelligence.process_batch(store,profile,'owner',job)
    assert store.save.call_count==calls


def test_save_has_atomic_business_off_and_membership_fences(invoice):
    db=make_store(invoice);db.intelligence_version=7
    previous=invoice.model_copy(deep=True);invoice.version+=1
    db.save(invoice,'owner','auto_review_decision',previous,'2026-09')
    sql,params=db.repo.query.call_args.args
    assert 'business policy cancelled' in sql and 'review membership revoked' in sql
    assert sql.index('business policy cancelled')<sql.index('DELETE FROM')
    assert {p.name:p.value for p in params}['intelligence_version']==7


def test_exceptions_real_counts_filters_and_confirmed_exclusion(store,monkeypatch):
    inv=store.state.current;inv.status='needs_review';inv.review_reasons=['recipient_gstin_mismatch','invoice_total_mismatch']
    confirmed=inv.model_copy(deep=True);confirmed.invoice_id='confirmed';confirmed.status='confirmed';confirmed.auto_review.status='auto_confirmed'
    store.list=Mock(return_value=[inv,confirmed]);store.job_history=Mock(return_value=[])
    monkeypatch.setattr(intelligence,'policy',lambda _:intelligence.Policy())
    result=intelligence.overview(store,'2026-09','gstin')
    assert result['counts']['attention']==1 and result['counts']['auto_confirmed']==1
    assert result['exceptions'][0]['reasons'][0]['label']=='Recipient GSTIN does not match this business'
    assert intelligence.overview(store,'2026-09','unreadable')['exceptions']==[]
    inv.status='confirmed'
    assert intelligence.overview(store,'2026-09')['counts']['attention']==0


def test_policy_api_permissions_input_and_version(api,store,monkeypatch):
    client,user=api
    monkeypatch.setattr(intelligence,'policy',lambda _:intelligence.Policy())
    store.query.return_value=[]
    route='/api/gst/bills/intelligence/policy'
    assert client.patch(route,json={'enabled':True,'scope':'both'}).status_code==428
    assert client.patch(route,json={'enabled':'yes','scope':'both'},headers={'if-match':'0'}).status_code==422
    assert client.patch(route,json={'enabled':True,'scope':[]},headers={'if-match':'0'}).status_code==422
    assert client.patch(route,content='{',headers={'if-match':'0','content-type':'application/json'}).status_code==422
    assert client.patch(route,json={'enabled':True,'scope':'both'},headers={'if-match':'0'}).status_code==200
    user.role='viewer'
    assert client.patch(route,json={'enabled':True,'scope':'both'},headers={'if-match':'0'}).status_code==403


def test_snapshot_batch_deduplicates_limits_and_records_versions(store,monkeypatch):
    monkeypatch.setattr(intelligence,'policy',lambda _:intelligence.Policy(enabled=True,version=1))
    invoices=[]
    for n in range(105):
        inv=store.state.current.model_copy(deep=True);inv.invoice_id=f'{n:03}';invoices.append(inv)
    store.list=Mock(return_value=invoices)
    store.query.return_value=[]
    store.writable_sql.return_value='-- period guard'
    job=intelligence.start_batch(store,'2026-09','owner',1)
    assert len(job['files'])==100 and job['remaining']==5
    assert all(e['version']==1 for e in job['files'])
    sql,params=store.query.call_args.args
    assert 'Batch active' in sql and 'intelligence_batch_requested' in sql
    assert json.loads(next(p.value for p in params if p.name=='payload'))==job


def test_combined_critical_failures_do_not_cancel_each_other(store,profile):
    from app.gst.auto_review import evaluate
    baseline=deepcopy(store.state.current)
    for faults in [('total','gstin'),('head','policy'),('original','duplicate'),('confidence','tax'),('correction','total')]:
        invoice=baseline.model_copy(deep=True);store.state.current=invoice
        store.list=Mock(return_value=[invoice]);store.download_object=Mock(return_value=b'evidence')
        for fault in faults:
            if fault=='total':invoice.totals.invoice_total+=1
            if fault=='gstin':invoice.recipient_gstin='invalid'
            if fault=='head':invoice.line_items[0].igst=1
            if fault=='policy':store.query.return_value=[]
            if fault=='original':store.download_object.return_value=b''
            if fault=='duplicate':
                other=invoice.model_copy(deep=True);other.invoice_id='duplicate';store.list.return_value.append(other)
            if fault=='confidence':invoice.extraction.confidence=0
            if fault=='tax':invoice.line_items[0].cgst=89
            if fault=='correction':invoice.correction_state='resubmitted'
        _,reasons,_,_=evaluate(store,invoice,profile)
        assert len(reasons)>=2


@pytest.mark.parametrize('explicit',[False,True])
def test_uploaded_off_exclusion_is_distinct_from_default_off(store,profile,monkeypatch,explicit):
    from app.gst.jobs import process_job
    invoice=store.state.current.model_copy(deep=True)
    store.list.side_effect=lambda:[]
    monkeypatch.setattr('app.gst.jobs.extract',lambda *args:[invoice])
    store.upload_object.return_value='silver'
    job={'job_id':'batch','status':'queued','period':'2026-09','auto_review_enabled':False,
         'auto_review_explicit':explicit,
         'files':[{'filename':'bill.pdf','doc_id':'doc','raw_ref':'original','status':'reading','invoice_ids':[]}]}
    process_job(store,profile,'owner',job)
    saved=store.state.current
    assert not saved.auto_review.enabled and saved.status!='confirmed'
    assert bool(saved.auto_review.requested_at)==explicit
    assert intelligence.eligible(saved) is not explicit
