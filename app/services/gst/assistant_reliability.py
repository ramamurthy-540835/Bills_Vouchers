"""Bounded provider work and evidence-only fallback; never invented answers."""
import logging
import json
import time
from threading import Lock
from uuid import uuid4

logger=logging.getLogger(__name__)
_circuits: dict[str, float] = {}
_circuit_lock = Lock()


class ProviderCircuitOpen(RuntimeError):
    """Avoid repeatedly waiting on a provider known to be unavailable."""


def circuit_state(model: str) -> dict[str, float | bool]:
    """Small process-local circuit state; no tenant data is retained."""
    with _circuit_lock:
        until = _circuits.get(model, 0.0)
    return {'open': until > time.monotonic(), 'retry_after_seconds': max(0.0, until-time.monotonic())}


def _open_circuit(model: str, reason: str) -> None:
    # A rate-limit response normally asks callers to slow down for longer.
    cooldown = 60.0 if reason == 'provider_rate_limit' else 30.0
    with _circuit_lock:
        _circuits[model] = time.monotonic() + cooldown


def _close_circuit(model: str) -> None:
    with _circuit_lock:
        _circuits.pop(model, None)


def throttle(repo, user_id, client_id):
    """Persistent assistant budget, separate from five-per-15-minute auth limits."""
    from hashlib import sha256
    from fastapi import HTTPException
    from google.api_core.exceptions import BadRequest, Conflict
    from .medallion import param
    key=sha256(f'assistant-minute:{client_id}:{user_id}'.encode()).hexdigest()
    for attempt in range(3):
      try:
        repo.query(f'''BEGIN TRANSACTION;
            ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_guard')}` WHERE id='identity')=1 AS 'Storage guard missing';
            UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
            ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_attempts')}`
                WHERE key_hash=@key AND created_at>TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 60 SECOND))<8 AS 'Assistant rate limit';
            INSERT INTO `{repo.table('auth_attempts')}` (key_hash,created_at) VALUES (@key,CURRENT_TIMESTAMP());
            COMMIT TRANSACTION;''',[param('key',key)])
        return
      except (BadRequest,Conflict) as exc:
        if 'assistant rate limit' in str(exc).lower():
            raise HTTPException(429,'Question limit reached. Please wait one minute, then retry.',headers={'Retry-After':'60'}) from None
        if isinstance(exc, Conflict) or any(word in str(exc).lower() for word in ('concurrent','aborted')):
            if attempt < 2:
                time.sleep(.1 * (attempt + 1))
                continue
            raise HTTPException(503,'Assistant is busy. Please retry shortly.',headers={'Retry-After':'2'}) from None
        raise


def category(exc):
    if isinstance(exc, ProviderCircuitOpen):
        return 'provider_circuit_open'
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
    model = str(kwargs.get('model') or 'default')
    if circuit_state(model)['open']:
        raise ProviderCircuitOpen('Provider circuit is temporarily open')
    for attempt in range(2):
        try:
            response = client.models.generate_content(**kwargs)
            _close_circuit(model)
            return response
        except Exception as exc:
            reason = category(exc)
            if attempt or reason not in {'provider_rate_limit','provider_timeout','provider_unavailable'}:
                if reason in {'provider_rate_limit','provider_timeout','provider_unavailable'}:
                    _open_circuit(model, reason)
                raise
            time.sleep(0.5)
    raise RuntimeError('Provider retry exhausted')


def fallback(context, reason):
    reference=uuid4().hex
    logger.warning(json.dumps({'event':'assistant_fallback','request_id':reference,'failure_category':reason}))
    return {'answer':'AI interpretation is temporarily unavailable. Your records have not changed. Open the authorized financial summary or source evidence below, or retry your question.',
            'sources':[{k:s[k] for k in ('id','label','href','layer')} for s in context['sources'][:9]],
            'sample':context['sample'],'followups':[],'degraded':True,'failure_category':reason,'request_id':reference}
