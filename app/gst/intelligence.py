"""Tenant policy and durable existing-invoice review; never a financial source."""
import json
from uuid import uuid4

from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, Conflict
from pydantic import BaseModel, ConfigDict, StrictBool
from typing import Literal

from app.services.gst.medallion import param
from .auto_review import now, review_invoice
from .naming import bill_filename


class Policy(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: StrictBool = False
    scope: Literal['existing', 'future', 'both'] = 'both'
    version: int = 0
    actor: str = ''
    changed_at: str = ''


def policy_sql(store):
    return f"SELECT after_payload FROM {store.table('ops','gst_bill_audit')} WHERE client_id=@client_id AND action='intelligence_policy' ORDER BY created_at DESC LIMIT 1"


def policy(store):
    rows = store.query(policy_sql(store))
    value = rows[0]['after_payload'] if rows else {}
    return Policy.model_validate(json.loads(value) if isinstance(value, str) else value)


def update_policy(store, enabled, scope, expected, actor):
    previous = policy(store)
    if previous.version != expected:
        raise HTTPException(409, 'Auto Review settings changed. Refresh before saving.')
    current = Policy(enabled=enabled, scope=scope, version=expected+1, actor=str(actor), changed_at=now())
    try:
        store.query(f'''BEGIN TRANSACTION;
            UPDATE {store.table('ops','gst_bill_lock')} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
            ASSERT @@row_count=1 AS 'Storage guard missing';
            ASSERT COALESCE((SELECT CAST(JSON_VALUE(after_payload,'$.version') AS INT64) FROM ({policy_sql(store)})),0)=@expected AS 'Policy changed';
            INSERT INTO {store.table('ops','gst_bill_audit')} VALUES
            (@client_id,NULL,@actor,'intelligence_policy',PARSE_JSON(@before),PARSE_JSON(@after),CURRENT_TIMESTAMP());
            COMMIT TRANSACTION;''', [param('expected', expected, 'INT64'), param('actor', str(actor)),
                param('before', previous.model_dump_json()), param('after', current.model_dump_json())])
    except (BadRequest, Conflict) as exc:
        if 'policy changed' in str(exc).lower() or isinstance(exc, Conflict):
            raise HTTPException(409, 'Auto Review settings changed. Refresh before saving.') from None
        raise
    return current


def eligible(invoice):
    return (invoice.status in {'extracted','needs_review'} and not invoice.sample
            and invoice.auto_review.status != 'running'
            and not (invoice.auto_review.requested_at and not invoice.auto_review.enabled))


def start_batch(store, period, actor, expected):
    selected = policy(store)
    if not selected.enabled or selected.scope == 'future' or selected.version != expected:
        raise HTTPException(409, 'Enable the existing-bill scope and refresh settings first.')
    store.assert_writable(period)
    candidates = sorted({i.invoice_id:i for i in store.list(period) if eligible(i)}.values(), key=lambda i: (i.auto_review.requested_at,i.invoice_id))
    if not candidates:
        raise HTTPException(409, 'No eligible pending bills remain in this period.')
    # Bound one worker lease; subsequent batches cover the remaining records.
    entries = [{'invoice_id': i.invoice_id, 'version': i.version, 'status': 'queued',
                'filename': bill_filename(i), 'invoice_ids': [i.invoice_id]} for i in candidates[:100]]
    job = {'job_id': str(uuid4()), 'kind': 'intelligence_batch', 'status': 'queued',
           'period': period, 'actor_id': str(actor), 'recovery_version': 1,
           'business_policy_version': selected.version, 'files': entries, 'remaining': max(0,len(candidates)-100)}
    try:
        store.query(f'''BEGIN TRANSACTION;
            UPDATE {store.table('ops','gst_bill_lock')} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
            ASSERT @@row_count=1 AS 'Storage guard missing';
            {store.writable_sql()}
            ASSERT COALESCE((SELECT CAST(JSON_VALUE(after_payload,'$.version') AS INT64) FROM ({policy_sql(store)})),0)=@policy_version AS 'Policy changed';
            ASSERT NOT EXISTS(SELECT 1 FROM {store.table('ops','gst_bill_job')}
                WHERE client_id=@client_id AND JSON_VALUE(payload,'$.period')=@period
                AND JSON_VALUE(payload,'$.kind')='intelligence_batch'
                AND JSON_VALUE(payload,'$.status') IN ('queued','reading','needs_attention')) AS 'Batch active';
            INSERT INTO {store.table('ops','gst_bill_job')} VALUES (@client_id,@id,PARSE_JSON(@payload),CURRENT_TIMESTAMP());
            INSERT INTO {store.table('ops','gst_bill_audit')} VALUES (@client_id,NULL,@actor,'intelligence_batch_requested',NULL,PARSE_JSON(@payload),CURRENT_TIMESTAMP());
            COMMIT TRANSACTION;''', [param('period',period),param('previous_period',period),param('id',job['job_id']),
                param('payload',json.dumps(job)),param('actor',str(actor)),param('policy_version',selected.version,'INT64')])
    except (BadRequest, Conflict) as exc:
        if 'batch active' in str(exc).lower() or 'policy changed' in str(exc).lower() or isinstance(exc, Conflict):
            raise HTTPException(409, 'A batch already exists. Check upload history and retry that batch if needed.') from None
        raise
    return job


def process_batch(store, profile, actor, job):
    for entry in job['files']:
        if entry['status'] != 'queued':
            continue
        selected = policy(store)
        if not selected.enabled or selected.version != job['business_policy_version']:
            entry.update(status='cancelled',reason='Business Auto Review settings changed; no decision was applied.')
        else:
            try:
                previous = store.get(entry['invoice_id'])
                if previous.version != entry['version'] or not eligible(previous):
                    entry.update(status='cancelled',reason='Invoice changed, was excluded or is no longer pending.')
                else:
                    store.intelligence_version = selected.version
                    invoice = previous.model_copy(deep=True)
                    invoice.auto_review.enabled = True
                    invoice.auto_review.requested_by = actor
                    invoice.auto_review.requested_at = now()
                    invoice.auto_review.job_id = job['job_id']
                    invoice.version += 1
                    store.save(invoice, actor, 'auto_review_requested', previous, job['period'])
                    result = review_invoice(store, profile, actor, invoice.invoice_id, invoice.version)
                    entry.update(status='ready' if result.status=='confirmed' else 'needs_attention',
                        auto_review_status=result.auto_review.status, auto_review_reasons=result.auto_review.reasons)
            except HTTPException as exc:
                if exc.status_code not in {403,404,409}:
                    raise
                entry.update(status='cancelled',reason='Invoice access, version or filing lock changed. Refresh and review manually.')
            finally:
                store.intelligence_version = None
        store.job(job['job_id'],job)
    job['status']='completed'
    store.job(job['job_id'],job)
    return job


LABELS = {
    'recipient_gstin_mismatch': ('gstin','Recipient GSTIN does not match this business'),
    'supplier_gstin_mismatch': ('gstin','Supplier GSTIN does not match this business'),
    'supplier_gstin_invalid': ('gstin','Supplier GSTIN is invalid or missing'),
    'recipient_gstin_invalid': ('gstin','Recipient GSTIN is invalid or missing'),
    'tax_arithmetic': ('gst','GST amounts do not match the declared rate'),
    'line_price_incomplete': ('total','Unit price and price basis are incomplete'),
    'line_price_invalid': ('total','Unit price or discount needs correction'),
    'line_valuation_mismatch': ('total','Taxable value does not match the supplied unit price'),
    'tax_head_mismatch': ('gst','CGST, SGST or IGST allocation needs correction'),
    'totals_mismatch': ('total','Line amounts do not match the invoice subtotal'),
    'invoice_total_mismatch': ('total','Invoice total does not match taxable value and tax'),
    'invoice_identity_missing': ('missing','Enter the invoice date and a valid invoice number'),
    'invoice_details_missing': ('missing','Required supplier or line details are missing'),
    'place_of_supply_invalid': ('missing','Verify the place of supply'),
    'client_gstin_missing': ('missing','Complete this business GSTIN profile'),
    'hsn_invalid': ('rate','Verify the HSN or SAC code'),
    'rate_invalid': ('rate','GST rate requires verification'),
    'low_confidence': ('unreadable','Invoice could not be read reliably'),
    'duplicate_pdf_page': ('evidence','A PDF page appears more than once; verify the original'),
    'multiple_invoice_numbers': ('evidence','This PDF appears to contain multiple invoices; upload each separately'),
    'duplicate_invoice': ('duplicate','This invoice may already exist'),
}


def reason_info(code):
    if code in LABELS:
        category,label=LABELS[code]
    elif 'policy' in code.lower() or 'HSN/SAC' in code:
        category,label='rate','GST rate and applicability require verified policy evidence'
    elif 'evidence' in code.lower():
        category,label='evidence','Original evidence needs verification'
    elif 'total' in code.lower():
        category,label='total','Invoice totals need correction'
    elif 'GST amounts' in code:
        category,label='gst','GST amounts need correction'
    else:
        category,label='other',code.replace('_',' ').capitalize()
    return {'code':code,'category':category,'label':label}


def overview(store, period, category='all', offset=0):
    invoices=store.list(period)
    rows=[]
    for inv in invoices:
        if inv.status not in {'extracted','needs_review'} or inv.auto_review.status=='running':
            continue
        reasons=list(dict.fromkeys([*inv.review_reasons,*inv.auto_review.reasons])) or ['Manual confirmation is required']
        details=[reason_info(r) for r in reasons]
        rows.append({'invoice_id':inv.invoice_id,'filename':bill_filename(inv),'party':inv.supplier_legal_name if inv.direction=='purchase' else inv.recipient_legal_name,
            'invoice_date':str(inv.invoice_date) if inv.invoice_date else None,'amount':str(inv.totals.invoice_total),'reasons':details})
    filtered=[row for row in rows if category=='all' or any(r['category']==category for r in row['reasons'])]
    jobs=store.job_history(period)
    active=[j for j in jobs if j['status'] in {'queued','reading'}]
    job_counts=store.intelligence_job_counts(period) if hasattr(type(store),'intelligence_job_counts') else {
        'processing':sum(sum(e['status'] in {'queued','reading'} for e in j['files']) for j in active),
        'failed':sum(j['status']=='needs_attention' for j in jobs),'duplicates':0}
    return {'policy':policy(store).model_dump(),'eligible':sum(eligible(i) for i in invoices),
        'counts':{'auto_confirmed':sum(i.status=='confirmed' and i.auto_review.status=='auto_confirmed' for i in invoices),
                  'attention':len(rows),'processing':job_counts['processing'],
                  'duplicates_failed':sum('duplicate_invoice' in i.review_reasons for i in invoices)+job_counts['failed']+job_counts['duplicates']},
        'exceptions':filtered[offset:offset+20],'total_exceptions':len(filtered),
        'next_offset':offset+20 if len(filtered)>offset+20 else None,
        'jobs':[{'job_id':j['job_id'],'status':j['status'],'done':sum(e['status'] not in {'queued','reading'} for e in j['files']),'total':len(j['files'])} for j in active]}
