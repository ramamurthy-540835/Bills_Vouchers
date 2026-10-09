from copy import deepcopy
from unittest.mock import Mock
from app.gst.jobs import process_job, public_job


def test_retry_after_partial_save_does_not_duplicate(invoice,profile,monkeypatch):
    import app.gst.jobs as jobs
    inv=invoice.model_copy(deep=True)
    monkeypatch.setattr(jobs,'extract',lambda *a:[inv])
    saved=[];blobs={'raw':b'content'}
    def upload(content,*args):blobs['silver']=content;return 'silver'
    store=Mock(client_id='a')
    store.list.side_effect=lambda:saved.copy()
    store.download_object.side_effect=lambda ref,**kwargs:blobs[ref]
    store.upload_object.side_effect=upload
    store.save.side_effect=lambda value,*args,**kwargs:saved.append(value)
    job={'job_id':'j','status':'queued','period':'2026-09','actor_id':'u','files':[{'filename':'bill.png','doc_id':'d','raw_ref':'raw','status':'reading','invoice_ids':[]}]}
    process_job(store,profile,'u',job)
    assert len(saved)==1 and job['status']=='completed'
    retry=deepcopy(job);retry['status']='reading';retry['files'][0]['status']='reading';retry['files'][0]['invoice_ids']=[]
    process_job(store,profile,'u',retry)
    assert len(saved)==1 and retry['files'][0]['invoice_ids']==[saved[0].invoice_id]
    assert 'raw_ref' not in public_job(retry)['files'][0] and 'actor_id' not in public_job(retry)


def test_worker_rejects_unauthenticated_requests(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.gst_bills import router
    from app.db import get_db
    app=FastAPI();app.include_router(router);app.dependency_overrides[get_db]=lambda:object()
    response=TestClient(app).post('/api/gst/bills/internal/process',json={'client_id':'other','job_id':'x'})
    assert response.status_code==403
