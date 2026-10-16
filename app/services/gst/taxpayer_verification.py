"""Client-registration evidence only; never ownership, KYC, ITC or filing approval."""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, Conflict

from .medallion import param
from .profiles import validate_gstin
from .taxpayer_provider import ProviderRecord, ProviderFailure

FRESHNESS = timedelta(hours=24)


def fingerprint(profile):
    fields = ['gstin', 'legal_name', 'trade_name', 'principal_address', 'registration_type', 'state_code']
    payload = {key: str(profile.get(key) or '').strip() for key in fields}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def comparable(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).casefold()


def assess(profile, record):
    record = ProviderRecord.model_validate(record.model_dump() if isinstance(record, ProviderRecord) else record)
    expected = validate_gstin(profile.get('gstin'))
    if not expected['valid'] or record.gstin != expected['gstin']:
        raise ProviderFailure('invalid_response')
    if not record.found and (record.registration_status != 'unknown' or record.legal_name or record.trade_name or record.address):
        raise ProviderFailure('invalid_response')
    if record.found and not record.legal_name.strip():
        raise ProviderFailure('invalid_response')
    name_match = comparable(record.legal_name) == comparable(profile.get('legal_name')) if record.found and profile.get('legal_name') else None
    comparisons = {'legal_name': name_match}
    for saved, remote in [('trade_name','trade_name'), ('principal_address','address'), ('registration_type','registration_type')]:
        comparisons[saved] = (comparable(profile[saved]) == comparable(getattr(record, remote))) if profile.get(saved) and getattr(record, remote) else None
    if not record.found:
        outcome = 'not_found'
    elif record.registration_status in {'cancelled','suspended','inactive'}:
        outcome = 'inactive'
    elif record.registration_status == 'unknown':
        outcome = 'failed'
    elif any(value is False for value in comparisons.values()) or name_match is None:
        outcome = 'mismatch'
    else:
        outcome = 'verified'
    return {'state': outcome, 'checksum_valid': True, 'taxpayer_found': record.found,
            'registration_status': record.registration_status, 'business_name_match': name_match,
            'comparisons': comparisons, 'record': record.model_dump(),
            'ownership_verified': False, 'kyc_verified': False}


class EvidenceStore:
    def __init__(self, repo, client_id):
        self.repo, self.client_id = repo, str(client_id)
        self.table = repo.table('gst_taxpayer_verification')

    def latest(self):
        rows = list(self.repo.query(f"""SELECT attempt_id,profile_hash,created_at,result
            FROM `{self.table}` WHERE client_id=@client
            AND created_at>=TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 366 DAY)
            ORDER BY created_at DESC,terminal DESC LIMIT 1""", [param('client',self.client_id)]))
        if not rows:
            return None
        row = dict(rows[0]);row['result'] = json.loads(row['result']) if isinstance(row['result'],str) else row['result']
        return row

    def begin(self, profile, actor, provider):
        attempt = str(uuid4())
        try:
            self.repo.query(f"""BEGIN TRANSACTION;
                ASSERT (SELECT COUNT(*) FROM `{self.repo.table('gst_verification_guard')}` WHERE id='lookup')=1 AS 'Verification guard missing';
                UPDATE `{self.repo.table('gst_verification_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='lookup';
                ASSERT (SELECT COUNT(*) FROM `{self.table}` WHERE client_id=@client AND terminal=FALSE
                    AND created_at>TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 60 SECOND))=0 AS 'Verification cooldown';
                ASSERT (SELECT COUNT(*) FROM `{self.table}` WHERE client_id=@client AND terminal=FALSE
                    AND created_at>TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 1 HOUR))<5 AS 'Verification rate limit';
                INSERT INTO `{self.table}` (attempt_id,client_id,profile_hash,actor_id,provider,terminal,created_at,result)
                VALUES (@attempt,@client,@hash,@actor,@provider,FALSE,CURRENT_TIMESTAMP(),@result);
                COMMIT TRANSACTION;""", [param('attempt',attempt),param('client',self.client_id),
                param('hash',fingerprint(profile)),param('actor',str(actor)),param('provider',provider),
                param('result',json.dumps({'state':'pending','source':provider}))])
        except (BadRequest, Conflict) as exc:
            if any(term in str(exc).lower() for term in ['cooldown','rate limit','concurrent','aborted']):
                raise HTTPException(429,'A verification was recently requested. Please retry later.') from None
            raise HTTPException(503,'Verification storage is unavailable.') from None
        return attempt

    def finish(self, attempt, profile, actor, provider, result):
        self.repo.query(f"""INSERT INTO `{self.table}`
            (attempt_id,client_id,profile_hash,actor_id,provider,terminal,created_at,result)
            VALUES (@attempt,@client,@hash,@actor,@provider,TRUE,CURRENT_TIMESTAMP(),@result)""",
            [param('attempt',attempt),param('client',self.client_id),param('hash',fingerprint(profile)),
             param('actor',str(actor)),param('provider',provider),param('result',json.dumps(result))])


def presentation(profile, evidence, configured, mode, now=None):
    now = now or datetime.now(timezone.utc)
    base = {'state':'not_checked' if configured else 'not_configured','automatic_available':configured,
            'mode':mode,'checksum_valid':validate_gstin(profile.get('gstin'))['valid'],
            'ownership_verified':False,'kyc_verified':False}
    if not evidence:
        return base
    result = {**base, **evidence['result']}
    result['automatic_available'] = configured
    result['checksum_valid'] = base['checksum_valid']
    created = evidence['created_at']
    if isinstance(created,str):
        created = datetime.fromisoformat(created.replace('Z','+00:00'))
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    result['checked_at'] = created.isoformat()
    result['expires_at'] = (created+FRESHNESS).isoformat()
    result['fresh'] = evidence['profile_hash'] == fingerprint(profile) and created <= now < created+FRESHNESS
    if not result['fresh']:
        result['previous_state'] = result['state'];result['state'] = 'stale'
    elif result['state'] == 'pending' and now-created > timedelta(minutes=2):
        result.update(state='failed',error_code='interrupted')
    return result


def verify(store, profile, actor, provider_name, provider):
    validation = validate_gstin(profile.get('gstin'))
    if not validation['valid']:
        raise HTTPException(422,validation['message'])
    existing = store.latest()
    status = presentation(profile,existing,True,'gsp')
    if status.get('fresh') and status['state'] in {'verified','mismatch','inactive','not_found'}:
        return {**status,'cached':True}
    attempt = store.begin(profile,actor,provider_name)
    try:
        result = assess(profile,provider.lookup(validation['gstin'],timeout_seconds=10))
    except (TimeoutError, ProviderFailure) as exc:
        result = {'state':'failed','error_code':exc.code if isinstance(exc,ProviderFailure) else 'timeout'}
    except Exception:
        result = {'state':'failed','error_code':'invalid_response'}
    result.update(source=provider_name,checked_at=datetime.now(timezone.utc).isoformat())
    store.finish(attempt,profile,actor,provider_name,result)
    return presentation(profile,{'profile_hash':fingerprint(profile),'created_at':result['checked_at'],'result':result},True,'gsp')
