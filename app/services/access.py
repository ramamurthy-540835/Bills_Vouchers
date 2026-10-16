"""Platform administration is separately provisioned and explicitly signed in."""
import logging
from fastapi import HTTPException
from app.config import get_settings
from app.services.demo_identity import isolated_v2_demo
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


def navigation_permissions(user, owner=False, client=None):
    """UI capabilities derived from the selected, authorized workspace identity."""
    result = ['view_workspace', 'manage_own_account']
    if not getattr(client, 'is_test', False) or isolated_v2_demo():
        result.append('view_reports')
    if user.role in {'client', 'tax_admin', 'admin'}:
        result += ['edit_profile', 'create_customer']
    if owner:
        result.append('manage_members')
    if owner or user.role in {'tax_admin', 'admin'}:
        result.append('edit_gstin')
    if getattr(user, 'is_platform_admin', False):
        result.append('platform_admin')
    return result


def require_platform_admin(user, action):
    if not getattr(user, 'is_platform_admin', False):
        logging.getLogger('bills_voucher.security').warning(
            'platform_access_denied', extra={'actor_id':str(user.id), 'action':action})
        raise HTTPException(403, 'Platform administrator access is required.')
