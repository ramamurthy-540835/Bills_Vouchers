"""Opt-in stage timings. Never record evidence, amounts, credentials or tokens."""
from contextlib import contextmanager
import json
import logging
from time import perf_counter
from app.config import get_settings

logger = logging.getLogger('uvicorn.error.performance')


@contextmanager
def measure(operation, job_id=None):
    started = perf_counter()
    outcome = 'ok'
    try:
        yield
    except Exception:
        outcome = 'failed'
        raise
    finally:
        if getattr(get_settings(), 'performance_metrics_enabled', False):
            record = {'event': 'stage_timing', 'operation': operation,
                'duration_ms': round((perf_counter() - started) * 1000, 3), 'outcome': outcome}
            if job_id:
                record['job_id'] = str(job_id)
            logger.info(json.dumps(record))
