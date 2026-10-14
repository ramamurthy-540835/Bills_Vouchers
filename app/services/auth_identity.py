"""Single-use ownership/recovery tokens; only hashes are persisted."""
import hashlib
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, Conflict

from app.config import get_settings
from app.security import hash_password, password_is_strong
from app.services.gst.medallion import param


def delivery_ready():
    settings = get_settings()
    url = urlsplit(settings.auth_public_url)
    if not (settings.smtp_host and settings.smtp_sender and url.scheme == 'https' and url.netloc and not url.query and not url.fragment):
        raise HTTPException(503, 'Account email delivery is not configured. Please contact support.')
    return settings


def send_link(email, token, purpose):
    settings = delivery_ready()
    path = 'verify-email' if purpose == 'verify' else 'reset-password'
    subject = 'Verify your GST Easy email' if purpose == 'verify' else 'Reset your GST Easy password'
    body = f"Open this single-use link within 30 minutes:\n{settings.auth_public_url.rstrip('/')}/{path}#token={token}\n\nIf you did not request this, ignore this email."
    send_email(email, subject, body)


def send_email(email, subject, body):
    settings = delivery_ready()
    message = EmailMessage()
    message['From'] = settings.smtp_sender
    message['To'] = email
    message['Subject'] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        raise HTTPException(503, 'Email delivery is temporarily unavailable. Please request a new link shortly.') from None


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def issue(repo, user_id, email, purpose):
    delivery_ready()
    token = secrets.token_urlsafe(32)
    repo.query(f'''INSERT INTO `{repo.table('auth_tokens')}`
        (token_hash,user_id,purpose,created_at,expires_at,consumed_at)
        VALUES (@hash,@uid,@purpose,CURRENT_TIMESTAMP(),TIMESTAMP_ADD(CURRENT_TIMESTAMP(),INTERVAL 30 MINUTE),NULL)''',
        [param('hash', digest(token)), param('uid', user_id), param('purpose', purpose)])
    send_link(email, token, purpose)


def throttle(repo, key):
    """Transaction guard serializes first writes across Cloud Run instances."""
    try:
        repo.query(f'''BEGIN TRANSACTION;
        ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_guard')}` WHERE id='identity')=1 AS 'Storage guard missing';
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_attempts')}` WHERE key_hash=@key AND created_at>TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL 15 MINUTE))<5 AS 'Auth rate limit';
        INSERT INTO `{repo.table('auth_attempts')}` (key_hash,created_at) VALUES (@key,CURRENT_TIMESTAMP());
        COMMIT TRANSACTION;''', [param('key', digest(key))])
    except (BadRequest, Conflict) as exc:
        if any(value in str(exc).lower() for value in ('auth rate limit', 'concurrent', 'aborted')):
            raise HTTPException(429, 'Too many attempts. Please try again later.') from None
        raise


def consume(repo, token, purpose, password='', confirm=''):
    if purpose not in {'verify', 'reset'}:
        raise HTTPException(422, 'Invalid token purpose.')
    if not isinstance(token, str) or len(token) < 32 or len(token) > 128:
        raise HTTPException(422, 'This link is invalid or expired. Request a new link.')
    if purpose == 'reset' and (not password_is_strong(password) or password != confirm):
        raise HTTPException(422, 'Use matching passwords with 12 or more characters, uppercase, lowercase and a number, up to 72 UTF-8 bytes.')
    assignment = 'email_verified=TRUE' if purpose == 'verify' else 'password_hash=@password,must_change_password=FALSE,session_version=COALESCE(session_version,0)+1'
    mail_id = str(uuid4())
    params = [param('hash', digest(token)), param('purpose', purpose), param('mail_id', mail_id)]
    if purpose == 'reset':
        params.append(param('password', hash_password(password)))
    try:
        repo.query(f'''DECLARE target_user STRING;
        BEGIN TRANSACTION;
        ASSERT (SELECT COUNT(*) FROM `{repo.table('auth_guard')}` WHERE id='identity')=1 AS 'Storage guard missing';
        UPDATE `{repo.table('auth_guard')}` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
        SET target_user=(SELECT user_id FROM `{repo.table('auth_tokens')}` WHERE token_hash=@hash AND purpose=@purpose AND consumed_at IS NULL AND expires_at>CURRENT_TIMESTAMP());
        ASSERT target_user IS NOT NULL AS 'Invalid auth token';
        UPDATE `{repo.table('users')}` SET {assignment}
        WHERE id=target_user AND is_active=TRUE;
        ASSERT @@row_count=1 AS 'Invalid auth token';
        INSERT INTO `{repo.table('auth_events')}`
        VALUES (GENERATE_UUID(),target_user,IF(@purpose='verify','email_verified','password_reset'),CURRENT_TIMESTAMP());
        IF @purpose='reset' THEN
        INSERT INTO `{repo.table('auth_outbox')}`
        SELECT @mail_id,email,'password_changed','pending',CURRENT_TIMESTAMP(),NULL,NULL
        FROM `{repo.table('users')}` WHERE id=target_user;
        END IF;
        UPDATE `{repo.table('auth_tokens')}` SET consumed_at=CURRENT_TIMESTAMP()
        WHERE user_id=target_user AND purpose=@purpose AND consumed_at IS NULL;
        COMMIT TRANSACTION;''', params)
    except (BadRequest, Conflict) as exc:
        if any(value in str(exc).lower() for value in ('invalid auth token', 'concurrent', 'aborted')):
            raise HTTPException(422, 'This link is invalid, expired or already used. Request a new link.') from None
        raise
    return mail_id if purpose == 'reset' else None
