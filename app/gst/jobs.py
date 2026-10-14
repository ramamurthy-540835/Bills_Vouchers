"""Durable bill jobs. Stable invoice IDs make retrying partial work safe."""
import json
import logging
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from app.config import get_settings
from .extract import extract
from .schemas.invoice import GstInvoice, Extraction
from .validate_invoice import validate_invoice
from .naming import bill_filename
from fastapi import HTTPException

logger=logging.getLogger(__name__)


def public_job(job):
    return {'job_id':job['job_id'],'status':job['status'],'files':[
        {k:v for k,v in entry.items() if k in {'filename','status','invoice_ids','reason'}} for entry in job['files']]}


def enqueue(client_id,job_id):
    from google.cloud.tasks_v2 import CloudTasksClient, HttpMethod
    settings=get_settings()
    if not settings.gst_bills_worker_url or not settings.gst_bills_worker_account:
        raise RuntimeError('Bill worker is not configured')
    CloudTasksClient().create_task(request={'parent':settings.gst_bills_queue,'task':{
        'name':settings.gst_bills_queue+'/tasks/bill-'+job_id,
        'dispatch_deadline':{'seconds':1800},
        'http_request':{'http_method':HttpMethod.POST,
            'url':settings.gst_bills_worker_url+'/api/gst/bills/internal/process',
            'headers':{'Content-Type':'application/json'},
            'oidc_token':{'service_account_email':settings.gst_bills_worker_account,'audience':settings.gst_bills_worker_audience or settings.gst_bills_worker_url},
            'body':json.dumps({'client_id':client_id,'job_id':job_id}).encode()}}})


def process_job(store,profile,actor,job):
    if job['status']=='completed':
        return job
    job['status']='reading';store.job(job['job_id'],job)
    existing=store.list()
    existing_ids={i.invoice_id for i in existing}
    for entry in job['files']:
        if entry['status'] in {'ready','needs_attention'}:
            continue
        if entry.get('extracted_ref'):
            invoices=[GstInvoice.model_validate(i) for i in json.loads(store.download_object(entry['extracted_ref'],layer='silver'))]
        else:
            content=store.download_object(entry['raw_ref'])
            try:
                invoices=extract(content,entry['filename'],store.client_id,entry['doc_id'],profile,entry['raw_ref'],
                    lambda a,b:store.usage(entry['doc_id'],a,b))
            except Exception:
                logger.exception('Bill extraction requires manual review',extra={'client_id':store.client_id,'source_doc_id':entry['doc_id']})
                invoices=[GstInvoice(client_id=store.client_id,source_doc_id=entry['doc_id'],
                    extraction=Extraction(raw_ref=entry['raw_ref'],confidence=Decimal('0')))]
                entry['reason']='We could not read all the details. Open the original bill and complete the highlighted fields.'
            if not invoices:
                entry.update(status='needs_attention',reason='The file contains no bill rows. Check the template and upload again.')
                store.job(job['job_id'],job);continue
            for index,invoice in enumerate(invoices):
                invoice.invoice_id=str(uuid5(NAMESPACE_URL,f'{store.client_id}/{entry["doc_id"]}/{index}'))
                invoice.selected_period=job['period']
            entry['extracted_ref']=store.upload_object(json.dumps([i.model_dump(mode='json') for i in invoices]).encode(),entry['doc_id'],'invoice.json','silver','application/json')
            store.job(job['job_id'],job)
        needs_attention=False
        for invoice in invoices:
            if invoice.invoice_id in existing_ids:
                saved=next(i for i in existing if i.invoice_id==invoice.invoice_id)
            else:
                saved=validate_invoice(invoice,profile,existing)
                if 'duplicate_invoice' in saved.review_reasons:
                    entry['reason']='This bill already exists. No duplicate was added.'
                    needs_attention=True
                    continue
                try:
                    store.save(saved,actor,'upload',selected_period=job['period'])
                except HTTPException as exc:
                    if exc.status_code != 409:
                        raise
                    entry['reason']='This bill was already saved or changed in another upload. Refresh your bills.'
                    needs_attention=True
                    continue
                existing.append(saved);existing_ids.add(saved.invoice_id)
            if len(invoices)==1:
                entry['filename']=bill_filename(saved)
            if saved.invoice_id not in entry['invoice_ids']:
                entry['invoice_ids'].append(saved.invoice_id)
            needs_attention=needs_attention or saved.status in {'needs_review','rejected'}
        entry['status']='needs_attention' if needs_attention else 'ready'
        store.job(job['job_id'],job)
    job['status']='completed';store.job(job['job_id'],job)
    return job
