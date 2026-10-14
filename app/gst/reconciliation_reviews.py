"""Append-only, versioned workflow decisions. No ITC or matching overrides."""
import json
import re

from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, Conflict

from app.services.gst.medallion import param
from . import returns
from .reconciliation import compare

DECISIONS = {'needs_correction', 'awaiting_supplier', 'reviewed', 'reopened'}


def latest(store, period):
    return [dict(row) for row in store.query(f'''SELECT * EXCEPT(evidence) FROM {store.table('ops','gst_reconciliation_review')}
        WHERE client_id=@client_id AND period=@period
        QUALIFY ROW_NUMBER() OVER(PARTITION BY case_id ORDER BY version DESC)=1''', [param('period', period)])]


def view(store, period):
    source_hash = returns.fingerprint(store, period, False)
    result = compare(store.list(period), store.matching_rows(period))
    reviews = {row['case_id']: row for row in latest(store, period)}
    for case in result['cases']:
        review = reviews.get(case['id'])
        case['review'] = {**review, 'stale': review['source_hash'] != source_hash} if review else None
    if source_hash != returns.fingerprint(store, period, False):
        raise HTTPException(409, 'Source evidence changed while loading. Refresh reconciliation.')
    return {**result, 'source_hash': source_hash}


def history(store, period, case_id, before_version=None):
    if not isinstance(case_id, str) or not 1 <= len(case_id) <= 200:
        raise HTTPException(422, 'Choose a reconciliation case.')
    params = [param('period', period), param('case', case_id), param('before', before_version, 'INT64')]
    rows = [dict(row) for row in store.query(f'''SELECT * FROM {store.table('ops','gst_reconciliation_review')}
        WHERE client_id=@client_id AND period=@period AND case_id=@case AND (@before IS NULL OR version<@before)
        ORDER BY version DESC LIMIT 51''', params)]
    for row in rows:
        if isinstance(row.get('evidence'), str):
            row['evidence'] = json.loads(row['evidence'])
    return {'history': rows[:50], 'next_before_version': rows[49]['version'] if len(rows) > 50 else None}


def record(store, period, actor, body):
    if actor.role not in {'admin', 'tax_admin'}:
        raise HTTPException(403, 'An authorized accountant or tax administrator must record this review.')
    if not isinstance(body, dict) or type(body.get('version')) is not int or not 0 <= body['version'] < 2**63-1:
        raise HTTPException(422, 'Provide the current review version.')
    decision, reason, case_id, source_hash = (body.get(key) for key in ('decision', 'reason', 'case_id', 'source_hash'))
    if not isinstance(decision, str) or decision not in DECISIONS:
        raise HTTPException(422, 'Choose a supported review decision.')
    if not isinstance(reason, str) or not 3 <= len(reason.strip()) <= 1000:
        raise HTTPException(422, 'Record an evidence-based reason between 3 and 1000 characters.')
    if not isinstance(case_id, str) or not 1 <= len(case_id) <= 200 or not isinstance(source_hash, str) or not re.fullmatch('[0-9A-Fa-f]{64}', source_hash):
        raise HTTPException(422, 'Refresh the case and its source evidence before reviewing.')
    if source_hash != returns.fingerprint(store, period, False):
        raise HTTPException(409, 'Source evidence changed. Refresh before reviewing.')
    case = next((item for item in compare(store.list(period), store.matching_rows(period))['cases'] if item['id'] == case_id), None)
    if case is None:
        raise HTTPException(404, 'Reconciliation case not found in this business and period.')
    params = [param('period', period), param('previous_period', period), param('case', case_id),
              param('expected', body['version'], 'INT64'), param('hash', source_hash),
              param('decision', decision), param('reason', reason.strip()), param('actor', str(actor.id)),
              param('evidence', json.dumps(case, default=str, sort_keys=True))]
    try:
        store.query(f'''BEGIN TRANSACTION;
        UPDATE {store.table('ops','gst_bill_lock')} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
        ASSERT @@row_count=1 AS 'Storage guard missing';
        {store.writable_sql()}
        ASSERT {returns.fingerprint_sql(store,False)}=@hash AS 'Source changed';
        ASSERT COALESCE((SELECT MAX(version) FROM {store.table('ops','gst_reconciliation_review')}
          WHERE client_id=@client_id AND period=@period AND case_id=@case),0)=@expected AS 'Review changed';
        ASSERT @decision!='reopened' OR @expected>0 AS 'Review not started';
        INSERT INTO {store.table('ops','gst_reconciliation_review')}
          VALUES (@client_id,@period,@case,@expected+1,@hash,@decision,@reason,@actor,PARSE_JSON(@evidence),CURRENT_TIMESTAMP());
        COMMIT TRANSACTION;''', params)
    except (BadRequest, Conflict) as exc:
        if any(word in str(exc).lower() for word in ('source changed', 'review changed', 'review not started', 'concurrent', 'aborted', 'filing period frozen')):
            raise HTTPException(409, 'Review or evidence changed, or the period is locked. Refresh before retrying.') from None
        raise
    return {'saved': True, 'version': body['version'] + 1, 'financial_override': False}
