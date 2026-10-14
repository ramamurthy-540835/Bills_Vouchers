"""Durable email outbox. Public requests never look up account existence."""
import hashlib
import hmac
import json
import logging
from uuid import uuid4

from fastapi import HTTPException
from google.api_core.exceptions import AlreadyExists, BadRequest, Conflict

from app.services.gst.medallion import param
from app.services import auth_identity

logger = logging.getLogger(__name__)


def ready():
    settings = auth_identity.delivery_ready()
    if not (settings.auth_mail_queue and settings.auth_worker_url and settings.auth_worker_account
            and len(settings.app_secret_key) >= 32):
        raise HTTPException(503, 'Account email processing is not configured. Please contact support.')
    return settings


def schedule(mail_id):
    from google.cloud.tasks_v2 import CloudTasksClient, HttpMethod
    settings = ready()
    task = {'name': settings.auth_mail_queue + '/tasks/auth-mail-' + mail_id,
            'http_request': {'http_method': HttpMethod.POST,
                'url': settings.auth_worker_url.rstrip('/') + '/internal/auth/mail',
                'oidc_token': {'service_account_email': settings.auth_worker_account,
                              'audience': settings.auth_worker_audience or settings.auth_worker_url},
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'mail_id': mail_id}).encode()}}
    try:
        CloudTasksClient().create_task(request={'parent': settings.auth_mail_queue, 'task': task})
    except AlreadyExists:
        pass
    except Exception:
        # Durable pending row remains available to the authenticated repair worker.
        logger.error('auth_mail_enqueue_failed', extra={'mail_id': mail_id})


def request_link(repo, email, purpose):
    ready()
    mail_id = str(uuid4())
    repo.query(f'''INSERT INTO `{repo.table('auth_outbox')}`
        VALUES (@id,@email,@purpose,'pending',CURRENT_TIMESTAMP(),NULL,NULL)''',
        [param('id', mail_id), param('email', email), param('purpose', purpose)])
    schedule(mail_id)


def process(repo, mail_id):
    settings = ready()
    rows = repo.query(f"SELECT * FROM `{repo.table('auth_outbox')}` WHERE id=@id", [param('id', mail_id)])
    if len(rows) != 1:
        raise HTTPException(404, 'Email request not found.')
    mail = rows[0]
    if mail['status'] in {'sent', 'ignored'}:
        return
    try:
        repo.query(f'''BEGIN TRANSACTION;
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_outbox')}` WHERE id=@id AND status NOT IN ('sent','ignored') AND (lease_until IS NULL OR lease_until<CURRENT_TIMESTAMP()))=1 AS 'Mail lease busy';
        UPDATE `{repo.table('auth_outbox')}` SET status='processing',lease_until=TIMESTAMP_ADD(CURRENT_TIMESTAMP(),INTERVAL 2 MINUTE) WHERE id=@id;
        COMMIT TRANSACTION;''', [param('id', mail_id)])
    except (BadRequest, Conflict):
        raise HTTPException(503, 'Email request is being processed.') from None
    users = repo.query(f"SELECT id,email_verified FROM `{repo.table('users')}` WHERE LOWER(email)=@email AND is_active=TRUE", [param('email', mail['email'])])
    if len(users) != 1 or (mail['purpose'] == 'verify' and users[0]['email_verified'] is not False):
        repo.query(f"UPDATE `{repo.table('auth_outbox')}` SET status='ignored',lease_until=NULL WHERE id=@id", [param('id', mail_id)])
        return
    if mail['purpose'] == 'password_changed':
        auth_identity.send_email(mail['email'], 'Your GST Easy password changed',
            'Your password was changed and previous sessions were revoked. If you did not make this change, use account recovery and contact your business administrator immediately.')
        repo.query(f"UPDATE `{repo.table('auth_outbox')}` SET status='sent',sent_at=CURRENT_TIMESTAMP(),lease_until=NULL WHERE id=@id", [param('id', mail_id)])
        return
    if mail['purpose'] not in {'reset', 'verify'}:
        raise HTTPException(422, 'Unsupported email request.')
    token = hmac.new(settings.app_secret_key.encode(), ('gst-easy-mail-link:' + mail_id).encode(), hashlib.sha256).hexdigest()
    token_hash = auth_identity.digest(token)
    repo.query(f'''INSERT INTO `{repo.table('auth_tokens')}`
        SELECT @hash,@uid,@purpose,CURRENT_TIMESTAMP(),TIMESTAMP_ADD(CURRENT_TIMESTAMP(),INTERVAL 30 MINUTE),NULL
        FROM UNNEST([1]) WHERE NOT EXISTS(SELECT 1 FROM `{repo.table('auth_tokens')}` WHERE token_hash=@hash)''',
        [param('hash', token_hash), param('uid', users[0]['id']), param('purpose', mail['purpose'])])
    usable = repo.query(f"SELECT 1 FROM `{repo.table('auth_tokens')}` WHERE token_hash=@hash AND consumed_at IS NULL AND expires_at>CURRENT_TIMESTAMP()", [param('hash', token_hash)])
    if usable:
        auth_identity.send_link(mail['email'], token, mail['purpose'])
    repo.query(f"UPDATE `{repo.table('auth_outbox')}` SET status='sent',sent_at=CURRENT_TIMESTAMP(),lease_until=NULL WHERE id=@id", [param('id', mail_id)])


def repair(repo):
    rows = repo.query(f'''SELECT id FROM `{repo.table('auth_outbox')}` WHERE status NOT IN ('sent','ignored')
        AND created_at>TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 1 DAY)
        AND (lease_until IS NULL OR lease_until<CURRENT_TIMESTAMP()) ORDER BY created_at LIMIT 50''')
    for row in rows:
        # Repair uses a new task name; SMTP retries reuse the same link/token.
        from google.cloud.tasks_v2 import CloudTasksClient, HttpMethod
        settings = ready()
        CloudTasksClient().create_task(request={'parent': settings.auth_mail_queue, 'task': {
            'http_request': {'http_method': HttpMethod.POST, 'url': settings.auth_worker_url.rstrip('/') + '/internal/auth/mail',
                'headers': {'Content-Type': 'application/json'},
                'oidc_token': {'service_account_email': settings.auth_worker_account,
                              'audience': settings.auth_worker_audience or settings.auth_worker_url},
                'body': json.dumps({'mail_id': row['id']}).encode()}}})
    return len(rows)
