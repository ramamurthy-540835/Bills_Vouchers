"""Bounded provider work and evidence-only fallback; never invented answers."""
import logging
import time
from uuid import uuid4

logger=logging.getLogger(__name__)


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
