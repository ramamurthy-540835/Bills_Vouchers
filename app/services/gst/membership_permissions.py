"""Workspace ownership is an explicit active membership, never a GSTIN match."""
from app.services.gst.medallion import param


def is_owner(repo, user, client_id):
    rows = repo.query(f'''SELECT access_role FROM `{repo.table('client_memberships')}`
        WHERE user_id=@uid AND client_id=@cid AND is_active=TRUE''',
        [param('uid', str(user.id)), param('cid', str(client_id))])
    return any(row['access_role'] == 'owner' for row in rows)
