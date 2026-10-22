"""Durable, bounded repair reservations; no delivery-success assertion."""
import hashlib
import json
import logging

from fastapi import HTTPException
from google.api_core.exceptions import AlreadyExists, BadRequest, Conflict, NotFound

from app.services.gst.medallion import param

logger = logging.getLogger(__name__)
MAX_REPAIRS = 3
COOLDOWN_MINUTES = 10


def reserve(repo, terminal):
    """Serialize budget allocation and reuse pending reservations after crashes."""
    outbox = f"`{repo.table('auth_outbox')}`"
    repairs = f"`{repo.table('auth_mail_repairs')}`"
    sql = f'''BEGIN TRANSACTION;
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        ASSERT @@row_count=1 AS 'Storage guard missing';
        INSERT INTO {repairs} (mail_id,attempt,state,created_at,queued_at)
        SELECT m.id,COALESCE(r.attempts,0)+1,'pending',CURRENT_TIMESTAMP(),NULL
        FROM {outbox} m LEFT JOIN (
            SELECT mail_id,COUNT(*) AS attempts,COUNTIF(state='pending') AS pending,
                MAX(COALESCE(queued_at,created_at)) AS last_attempt FROM {repairs} GROUP BY mail_id
        ) r ON r.mail_id=m.id
        WHERE m.status NOT IN ({terminal})
          AND m.created_at>TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 1 DAY)
          AND m.created_at<TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL {COOLDOWN_MINUTES} MINUTE)
          AND (m.lease_until IS NULL OR m.lease_until<CURRENT_TIMESTAMP())
          AND COALESCE(r.attempts,0)<{MAX_REPAIRS} AND COALESCE(r.pending,0)=0
          AND (r.last_attempt IS NULL OR r.last_attempt<TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL {COOLDOWN_MINUTES} MINUTE))
        ORDER BY m.created_at,m.id LIMIT 50;
        COMMIT TRANSACTION;
        SELECT r.mail_id,r.attempt FROM {repairs} r JOIN {outbox} m ON m.id=r.mail_id
        WHERE r.state='pending' AND m.status NOT IN ({terminal})
          AND m.created_at>TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 1 DAY)
          AND (m.lease_until IS NULL OR m.lease_until<CURRENT_TIMESTAMP())
        ORDER BY r.created_at,r.mail_id LIMIT 50;'''
    try:
        return repo.query(sql)
    except NotFound:
        raise HTTPException(503, 'Email repair storage is unavailable. Contact support.') from None
    except (BadRequest, Conflict):
        raise HTTPException(503, 'Email repair could not reserve its retry budget. Retry later.') from None


def repair(repo, settings, terminal):
    from google.cloud.tasks_v2 import CloudTasksClient, HttpMethod
    rows = reserve(repo, terminal)
    if not rows:
        return 0
    client = CloudTasksClient()
    scheduled = 0
    for row in rows:
        mail_id, attempt = row['mail_id'], row['attempt']
        # Stable across concurrent repair calls and unknown enqueue outcomes.
        identity = hashlib.sha256(f'{mail_id}:{attempt}'.encode()).hexdigest()
        task = {
            'name': settings.auth_mail_queue+'/tasks/'+identity+'-mail-repair',
            'http_request': {
                'http_method': HttpMethod.POST,
                'url': settings.auth_worker_url.rstrip('/')+'/internal/auth/mail',
                'headers': {'Content-Type': 'application/json'},
                'oidc_token': {'service_account_email': settings.auth_worker_account,
                              'audience': settings.auth_worker_audience or settings.auth_worker_url},
                'body': json.dumps({'mail_id': mail_id}).encode(),
            },
        }
        try:
            client.create_task(request={'parent': settings.auth_mail_queue, 'task': task})
        except AlreadyExists:
            pass  # The same reservation was already accepted; never mint a new ID.
        except Exception:
            logger.error('auth_mail_repair_enqueue_unknown', extra={'mail_id': mail_id, 'attempt': attempt})
            continue  # Keep pending; no false queued/provider/delivery success.
        repo.query(f'''UPDATE `{repo.table('auth_mail_repairs')}`
            SET state='queued',queued_at=CURRENT_TIMESTAMP()
            WHERE mail_id=@id AND attempt=@attempt AND state='pending' ''',
            [param('id', mail_id), param('attempt', attempt, 'INT64')])
        scheduled += 1
    return scheduled
