"""Durable bill jobs. Stable invoice IDs make retrying partial work safe."""
import json
import logging
from uuid import NAMESPACE_URL, uuid5

from app.config import get_settings
from .extract import extract
from .schemas.invoice import GstInvoice, AutoReview
from .validate_invoice import validate_invoice
from .naming import bill_filename
from .job_state import retryable
from .extraction_issues import issue_for
from fastapi import HTTPException
from app.services.performance import measure

logger=logging.getLogger(__name__)


def public_job(job):
    return {'job_id':job['job_id'],'status':job['status'],'retryable':retryable(job),
        'reason':job.get('reason'),'result':job.get('result'),'files':[
        {**{k:v for k,v in entry.items() if k in {'filename','original_filename','status','invoice_ids','reason','period_notice','invoice_periods','extraction_issue','auto_review_status','auto_review_reasons'}},
         'original_url':f"/api/gst/bills/upload/{job['job_id']}/original/{index}" if entry.get('raw_ref') else None}
        for index,entry in enumerate(job['files'])]}


def enqueue(client_id,job_id,attempt=None):
    from google.cloud.tasks_v2 import CloudTasksClient, HttpMethod
    settings=get_settings()
    if not settings.gst_bills_worker_url or not settings.gst_bills_worker_account:
        raise RuntimeError('Bill worker is not configured')
    CloudTasksClient().create_task(request={'parent':settings.gst_bills_queue,'task':{
        'name':settings.gst_bills_queue+'/tasks/bill-'+job_id+('-'+attempt if attempt else ''),
        'dispatch_deadline':{'seconds':1800},
        'http_request':{'http_method':HttpMethod.POST,
            'url':settings.gst_bills_worker_url+'/api/gst/bills/internal/process',
            'headers':{'Content-Type':'application/json'},
            'oidc_token':{'service_account_email':settings.gst_bills_worker_account,'audience':settings.gst_bills_worker_audience or settings.gst_bills_worker_url},
            'body':json.dumps({'client_id':client_id,'job_id':job_id}).encode()}}})


def run_job(store, profile, actor, job):
    claimed = store.claim_job(job['job_id'], actor)
    if claimed['status'] == 'completed':
        return claimed
    try:
        return process_job(store, profile, actor, claimed)
    except Exception:
        claimed['status'] = 'needs_attention'
        claimed['reason'] = 'Processing stopped. Your originals and saved progress are retained. Retry from upload history.'
        try:
            store.job(claimed['job_id'], claimed)
        except Exception:
            logger.exception('Worker could not record failure; its claim may have expired')
        raise


def process_job(store,profile,actor,job):
    if job['status']=='completed':
        return job
    if job['status'] != 'reading':
        job['status']='reading';store.job(job['job_id'],job)
    if job.get('kind') == 'auto_review':
        from .auto_review import process_review_job
        return process_review_job(store, profile, actor, job)
    if job.get('kind') == 'intelligence_batch':
        from .intelligence import process_batch
        return process_batch(store, profile, actor, job)
    existing=store.list()
    existing_ids={i.invoice_id for i in existing}
    for entry_index, entry in enumerate(job['files']):
        entry.setdefault('original_filename',entry['filename'])
        if entry['status'] in {'ready','needs_attention'}:
            continue
        if entry.get('extracted_ref'):
            try:
                invoices=[GstInvoice.model_validate(i) for i in json.loads(store.download_object(entry['extracted_ref'],layer='silver'))]
            except Exception:
                entry.update(status='needs_attention',reason='Saved extraction data could not be restored. The original is retained; retry extraction.',
                    extraction_issue={'code':'extraction_cache_unavailable','message':'Saved extraction data could not be restored. Retry to re-read the retained original.', 'retryable':True})
                store.job(job['job_id'],job)
                continue
        else:
            try:
                with measure('original_download', job['job_id']):
                    content=store.download_object(entry['raw_ref'])
            except Exception as exc:
                entry.update(status='needs_attention',extraction_issue=issue_for(exc,'evidence'))
                entry['reason']=entry['extraction_issue']['message']
                store.job(job['job_id'],job)
                continue
            try:
                with measure('invoice_extraction', job['job_id']):
                    invoices=extract(content,entry['filename'],store.client_id,entry['doc_id'],profile,entry['raw_ref'],
                        lambda a,b:store.usage(entry['doc_id'],a,b))
            except Exception as exc:
                problem=issue_for(exc)
                logger.warning('Bill extraction stopped: %s',problem['code'])
                entry.update(status='needs_attention',reason=problem['message'],extraction_issue=problem)
                # Retain original evidence and failure metadata, not a fabricated
                # blank financial invoice or a cached failed extraction.
                store.job(job['job_id'],job)
                continue
            if not invoices:
                entry.update(status='needs_attention',reason='The file contains no bill rows. Check the template and upload again.')
                store.job(job['job_id'],job);continue
            if entry.get('replace_invoice_id') and len(invoices)!=1:
                entry.update(status='needs_attention',reason='This source contains multiple invoice records. Its saved bill was not replaced.',
                    extraction_issue={'code':'multiple_source_records','message':'Re-reading a saved bill requires a single-invoice original. Review this source manually.', 'retryable':False})
                store.job(job['job_id'],job)
                continue
            for index,invoice in enumerate(invoices):
                invoice.invoice_id=entry.get('replace_invoice_id') or str(uuid5(NAMESPACE_URL,f'{store.client_id}/{entry["doc_id"]}/{index}'))
                invoice.selected_period=job['period']
            entry.pop('extraction_issue',None)
            entry.pop('reason',None)
            entry['extracted_ref']=store.upload_object(json.dumps([i.model_dump(mode='json') for i in invoices]).encode(),entry['doc_id'],f"invoice-{job.get('worker_token','local')}.json",'silver','application/json')
            store.job(job['job_id'],job)
        needs_attention=False
        for invoice in invoices:
            if entry.get('replace_invoice_id'):
                previous=store.get(entry['replace_invoice_id'])
                if (previous.version != entry['expected_version'] or previous.status not in {'extracted','needs_review'}
                        or previous.source_doc_id != entry['doc_id'] or previous.auto_review.status == 'running'):
                    entry.update(status='needs_attention',reason='This bill changed or was confirmed after extraction was requested. Its current fields have been preserved.',
                        extraction_issue={'code':'extraction_version_changed','message':'Current bill fields were preserved. Open the bill and review its latest version.', 'retryable':False})
                    needs_attention=True
                    break
                with measure('financial_and_gst_validation', job['job_id']):
                    saved=validate_invoice(invoice,profile,[i for i in existing if i.invoice_id!=previous.invoice_id])
                saved.version=previous.version+1
                saved.auto_review=AutoReview()
                try:
                    store.save(saved,actor,'extraction_retry',previous,job['period'])
                except HTTPException as exc:
                    if exc.status_code not in {403,409}:
                        raise
                    entry.update(status='needs_attention',reason='The bill, permissions or filing lock changed. Current fields are preserved.',
                        extraction_issue={'code':'extraction_version_changed','message':'Current fields are preserved. Refresh and review the latest bill.', 'retryable':False})
                    needs_attention=True
                    break
                existing[:]=[i for i in existing if i.invoice_id!=saved.invoice_id]+[saved]
            elif invoice.invoice_id in existing_ids:
                saved=next(i for i in existing if i.invoice_id==invoice.invoice_id)
            else:
                with measure('financial_and_gst_validation', job['job_id']):
                    saved=validate_invoice(invoice,profile,existing)
                saved.auto_review = AutoReview()  # Document content cannot opt in.
                enabled = job.get('auto_review_enabled', False)
                if job.get('business_policy_version') is not None:
                    from .intelligence import policy
                    selected = policy(store)
                    enabled = enabled and selected.enabled and selected.version == job['business_policy_version']
                if enabled or (job.get('auto_review_explicit') and job.get('auto_review_enabled') is False):
                    from .auto_review import now
                    saved.auto_review.enabled = bool(enabled)
                    saved.auto_review.requested_by = actor
                    saved.auto_review.requested_at = now()
                    saved.auto_review.job_id = job['job_id']
                if 'duplicate_invoice' in saved.review_reasons:
                    entry['reason']='This bill already exists. No duplicate was added.'
                    needs_attention=True
                    continue
                try:
                    with measure('canonical_invoice_save', job['job_id']):
                        store.save(saved,actor,'upload',selected_period=job['period'])
                except HTTPException as exc:
                    if exc.status_code != 409 or not isinstance(exc.detail, dict) or exc.detail.get('code') != 'bill_conflict':
                        raise
                    entry['reason']='This bill was already saved or changed in another upload. Refresh your bills.'
                    needs_attention=True
                    continue
                existing.append(saved);existing_ids.add(saved.invoice_id)
            if saved.auto_review.enabled and saved.auto_review.job_id == job['job_id'] and saved.auto_review.status == 'not_started':
                from .auto_review import review_invoice
                store.intelligence_version = job.get('business_policy_version')
                try:
                    saved = review_invoice(store, profile, actor, saved.invoice_id, saved.version)
                except HTTPException as exc:
                    if exc.status_code != 409:
                        raise
                    saved = store.get(saved.invoice_id)
                    entry['reason'] = 'Settings, invoice version or filing lock changed. Review manually.'
                finally:
                    store.intelligence_version = None
            if len(invoices)==1:
                entry['filename']=bill_filename(saved)
            if saved.invoice_id not in entry['invoice_ids']:
                entry['invoice_ids'].append(saved.invoice_id)
            if saved.invoice_date:
                actual_period=saved.invoice_date.strftime('%Y-%m')
                entry['invoice_periods']=sorted(set([*entry.get('invoice_periods',[]),actual_period]))
                if actual_period!=job['period']:
                    entry['period_notice']=f"This file contains a bill dated {actual_period}. It is recorded in that invoice period, not {job['period']}. Open the bill to check the date or select its actual period."
            if saved.auto_review.enabled:
                entry['auto_review_status'] = saved.auto_review.status
                entry['auto_review_reasons'] = saved.auto_review.reasons
                entry['reason'] = ('Auto Confirmed: all required checks passed.' if saved.auto_review.status == 'auto_confirmed'
                                   else 'Manual Review Required: ' + '; '.join(saved.auto_review.reasons))
            needs_attention=needs_attention or saved.status in {'needs_review','rejected'}
        entry['status']='needs_attention' if needs_attention else 'ready'
        # The final fenced completion saves the last entry in the same update.
        if entry_index < len(job['files']) - 1:
            store.job(job['job_id'],job)
    job['status']='completed';store.job(job['job_id'],job)
    return job
