"""Canonical preparation snapshots; no government-format or filing claims."""
import json
from uuid import uuid4

from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, Conflict

from app.services.gst.medallion import param


def fingerprint_sql(store, include_reviews=True):
    base = f'''(SELECT TO_HEX(SHA256(TO_JSON_STRING(STRUCT(
        ARRAY(SELECT AS STRUCT invoice_id,version FROM {store.table('gold','gst_invoice')}
              WHERE client_id=@client_id AND period=@period ORDER BY invoice_id) AS invoices,
        ARRAY(SELECT TO_JSON_STRING(payload) FROM {store.table('silver','gst_bills_gstr2b')}
              WHERE client_id=@client_id AND period=@period ORDER BY TO_JSON_STRING(payload)) AS statements,
        ARRAY(SELECT CAST(profile_id AS STRING) FROM `{store.repo.table('gst_client_profile')}`
              WHERE client_id=@client_id AND is_current=TRUE ORDER BY profile_id) AS profiles
    )))))'''
    if not include_reviews:
        return base
    # Preserve pre-migration snapshot hashes where no review has been recorded.
    reviews = f"FROM {store.table('ops','gst_reconciliation_review')} WHERE client_id=@client_id AND period=@period"
    return f'''IF(EXISTS(SELECT 1 {reviews}),
        TO_HEX(SHA256(CONCAT({base},TO_JSON_STRING(ARRAY(SELECT AS STRUCT case_id,version {reviews} ORDER BY case_id,version))))),{base})'''


def fingerprint(store,period,include_reviews=True):
    return store.query(f'SELECT {fingerprint_sql(store,include_reviews)} AS source_digest',[param('period',period)])[0]['source_digest']


def current(store,period):
    rows=store.query(f'''SELECT * FROM {store.table('ops','gst_return_current')}
        WHERE client_id=@client_id AND period=@period''',[param('period',period)])
    if len(rows)>1:
        raise HTTPException(409,'Conflicting return records require review.')
    return dict(rows[0]) if rows else {'state':'draft','version':0,'period':period}


def authorize_transition(state,action,actor,reason):
    if action=='review':
        if state['state']!='prepared' or state.get('maker_id')!=str(actor.id):
            raise HTTPException(409,'Only the preparer can submit this prepared snapshot for review.')
        return 'under_review'
    if action not in {'approve','reject','reopen'}:
        raise HTTPException(422,'Unsupported return action.')
    if actor.role not in {'admin','tax_admin'}:
        raise HTTPException(403,'A tax administrator must review or reopen this return.')
    if not isinstance(reason,str) or not 3<=len(reason.strip())<=1000:
        raise HTTPException(422,'Record a review reason between 3 and 1000 characters.')
    if action in {'approve','reject'}:
        if state['state']!='under_review':
            raise HTTPException(409,'Submit the snapshot for review first.')
        if state.get('maker_id')==str(actor.id):
            raise HTTPException(403,'The preparer cannot approve or reject their own snapshot.')
        return 'approved' if action=='approve' else 'draft'
    if state['state'] not in {'under_review','approved','exported'}:
        raise HTTPException(409,'This return is not locked for review or approval.')
    return 'reopened'


def change(store,period,actor,action,expected,source_hash='',payload=None,reason=''):
    state=current(store,period)
    if expected!=state['version']:
        raise HTTPException(409,'Return changed. Refresh before retrying.')
    snapshot_id=state.get('snapshot_id')
    maker=state.get('maker_id')
    if action=='prepare':
        if state['state'] not in {'draft','prepared','reopened'}:
            raise HTTPException(409,'Reopen this return before preparing a new snapshot.')
        target='prepared';snapshot_id=str(uuid4());maker=str(actor.id)
    else:
        target=authorize_transition(state,action,actor,reason)
        source_hash=state.get('source_hash','')
    params=[param('period',period),param('expected',expected,'INT64'),param('state',state['state']),
            param('target',target),param('snapshot',snapshot_id),param('hash',source_hash),
            param('actor',str(actor.id)),param('maker',maker),param('action',action),
            param('reason',reason.strip()),param('payload',json.dumps(payload,default=str,sort_keys=True))]
    try:
        store.query(f'''BEGIN TRANSACTION;
        UPDATE {store.table('ops','gst_bill_lock')} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
        ASSERT @@row_count=1 AS 'Storage guard missing';
        ASSERT COALESCE((SELECT version FROM {store.table('ops','gst_return_current')} WHERE client_id=@client_id AND period=@period),0)=@expected AS 'Return changed';
        ASSERT @action IN ('reopen','reject') OR {fingerprint_sql(store)}=@hash AS 'Source changed';
        ASSERT NOT EXISTS(SELECT 1 FROM `{store.repo.table('gst_filing_status')}` WHERE client_id=@client_id AND period=@period AND is_current=TRUE AND state NOT IN ('draft','reopened')) AS 'Legacy filing period frozen';
        IF @action='prepare' THEN
          INSERT INTO {store.table('ops','gst_return_snapshot')} VALUES (@client_id,@period,@snapshot,@hash,PARSE_JSON(@payload),@maker,CURRENT_TIMESTAMP());
        END IF;
        DELETE FROM {store.table('ops','gst_return_current')} WHERE client_id=@client_id AND period=@period;
        INSERT INTO {store.table('ops','gst_return_current')} VALUES (@client_id,@period,@target,@expected+1,@snapshot,@hash,@maker,IF(@action='approve',@actor,NULL),CURRENT_TIMESTAMP());
        INSERT INTO {store.table('ops','gst_return_audit')} VALUES (@client_id,@period,@snapshot,@actor,@action,@reason,@state,@target,CURRENT_TIMESTAMP());
        COMMIT TRANSACTION;''',params)
    except (BadRequest,Conflict) as exc:
        if any(word in str(exc).lower() for word in ('source changed','return changed','concurrent','aborted','filing period frozen')):
            raise HTTPException(409,'Source data or return state changed, or the period is frozen. Refresh and prepare again if needed.') from None
        raise
    return current(store,period)


def snapshot(store,period,state):
    if not state.get('snapshot_id'):
        raise HTTPException(404,'No prepared snapshot.')
    rows=store.query(f'''SELECT payload FROM {store.table('ops','gst_return_snapshot')}
        WHERE client_id=@client_id AND period=@period AND snapshot_id=@id''',
        [param('period',period),param('id',state['snapshot_id'])])
    if len(rows)!=1:
        raise HTTPException(409,'Snapshot evidence is unavailable.')
    payload=rows[0]['payload']
    return json.loads(payload) if isinstance(payload,str) else payload
