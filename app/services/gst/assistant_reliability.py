"""Bounded provider work and evidence-only fallback; never invented answers."""
import logging
import time
from uuid import uuid4

logger=logging.getLogger(__name__)


def throttle(repo, user_id, client_id):
    """Persistent assistant budget, separate from five-per-15-minute auth limits."""
    from hashlib import sha256
    from fastapi import HTTPException
    from google.api_core.exceptions import BadRequest, Conflict
    from .medallion import param
    key=sha256(f'assistant-minute:{client_id}:{user_id}'.encode()).hexdigest()
    try:
        repo.query(f'''BEGIN TRANSACTION;
            ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_guard')}` WHERE id='identity')=1 AS 'Storage guard missing';
            UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
            ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_attempts')}`
                WHERE key_hash=@key AND created_at>TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 60 SECOND))<8 AS 'Assistant rate limit';
            INSERT INTO `{repo.table('auth_attempts')}` (key_hash,created_at) VALUES (@key,CURRENT_TIMESTAMP());
            COMMIT TRANSACTION;''',[param('key',key)])
    except (BadRequest,Conflict) as exc:
        if any(word in str(exc).lower() for word in ('assistant rate limit','concurrent','aborted')):
            raise HTTPException(429,'Question limit reached. Please wait one minute, then retry.',headers={'Retry-After':'60'}) from None
        raise


def category(exc):
    code=getattr(exc,'code',None) or getattr(exc,'status_code',None)
    if code==429:
        return 'provider_rate_limit'
    if code in {401,403}:
        return 'provider_access'
    if code==404:
        return 'model_unavailable'
    if isinstance(exc,TimeoutError) or 'timeout' in type(exc).__name__.lower():
        return 'provider_timeout'
    if isinstance(exc,(ValueError,TypeError,KeyError)):
        return 'invalid_provider_response'
    return 'provider_unavailable'


def generate(client, **kwargs):
    for attempt in range(2):
        try:
            return client.models.generate_content(**kwargs)
        except Exception as exc:
            if attempt or category(exc) not in {'provider_rate_limit','provider_timeout','provider_unavailable'}:
                raise
            time.sleep(0.5)
    raise RuntimeError('Provider retry exhausted')


def fallback(context, reason):
    reference=uuid4().hex
    logger.warning('assistant_fallback',extra={'request_id':reference,'failure_category':reason})
    return {'answer':'AI interpretation is temporarily unavailable. Your records have not changed. Open the authorized financial summary or source evidence below, or retry your question.',
            'sources':[{k:s[k] for k in ('id','label','href','layer')} for s in context['sources'][:9]],
            'sample':context['sample'],'followups':[],'degraded':True,'failure_category':reason,'request_id':reference}
