"""Platform administration is separately provisioned and explicitly signed in."""
from app.config import get_settings
from app.services.gst.medallion import param


def is_provisioned_admin(user, repo):
    allowed = {value.strip().lower() for value in get_settings().platform_admin_emails.split(',') if value.strip()}
    email = str(getattr(user, 'email', '')).lower()
    if email not in allowed or not getattr(user, 'is_active', True) or getattr(user, 'email_verified', None) is not True:
        return False
    return bool(repo.one(f'''SELECT user_id FROM `{repo.table('platform_admin_grants')}`
        WHERE user_id=@uid AND email=@email AND is_active=TRUE LIMIT 1''',
        [param('uid', str(user.id)), param('email', email)]))


def workspace_role(value):
    # Legacy workspace 'admin' is business access, never platform administration.
    return {'owner': 'client', 'admin': 'client', 'client': 'client',
            'accountant': 'tax_admin', 'tax_admin': 'tax_admin', 'viewer': 'viewer'}.get(str(value).lower(), 'viewer')
