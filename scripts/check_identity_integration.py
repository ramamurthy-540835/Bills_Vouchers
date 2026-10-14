"""Real BigQuery identity tests in a new expiring dataset; no customer row reads.

Requires explicit --run. Copies schema metadata only, never source data.
All test tables expire after 24 hours. The empty dataset can be removed later.
"""
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from fastapi import HTTPException
from google.cloud import bigquery
from google.oauth2.credentials import Credentials

from app.services import auth_identity
from app.services.registration import register
from app.services.gst.medallion import param
from deploy_v3 import gcloud


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', required=True)
    parser.add_argument('--resume-latest', action='store_true')
    parser.add_argument('--workspace', action='store_true')
    args = parser.parse_args()
    project = 'aidirac-503309'
    client = bigquery.Client(project=project, credentials=Credentials(gcloud('auth', 'print-access-token').strip()))
    source = client.get_dataset(project + '.finance_analytics')
    dataset_id = project + '.gst_easy_identity_test_' + uuid4().hex[:12]
    if args.resume_latest:
        candidates = [client.get_dataset(item.reference) for item in client.list_datasets()
                      if item.dataset_id.startswith('gst_easy_identity_test_')]
        candidates = [item for item in candidates if item.labels.get('purpose') == 'gst-easy-identity-integration']
        if not candidates:
            raise RuntimeError('No prior isolated test dataset found')
        dataset_id = max(candidates, key=lambda item: item.created).full_dataset_id.replace(':', '.')
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = source.location
    dataset.default_table_expiration_ms = 24 * 60 * 60 * 1000
    dataset.labels = {'purpose': 'gst-easy-identity-integration', 'synthetic': 'true'}
    client.create_dataset(dataset, exists_ok=args.resume_latest)
    print('Isolated test dataset: ' + dataset_id, flush=True)
    for name in ('users', 'clients', 'client_memberships', 'client_user_role', 'gst_client_profile'):
        original = client.get_table(project + '.finance_analytics.' + name)
        client.create_table(bigquery.Table(dataset_id + '.' + name, schema=original.schema), exists_ok=args.resume_latest)

    class Repo:
        settings = SimpleNamespace(gcp_project_id=project)

        def table(self, name):
            return dataset_id + '.' + name

        def query(self, sql, params=()):
            job = client.query(sql, location=source.location, job_config=bigquery.QueryJobConfig(
                query_parameters=list(params), maximum_bytes_billed=100_000_000,
                labels={'purpose': 'gst-easy-identity-test'}))
            return list(job.result(timeout=90))

        def one(self, sql, params=()):
            rows = self.query(sql, params)
            return rows[0] if rows else None

    repo = Repo()
    migration = Path('migrations/010_identity_verification.sql').read_text().replace(project + '.finance_analytics', dataset_id)
    repo.query(migration)
    if args.workspace:
        repo.query(Path('migrations/012_workspace_onboarding.sql').read_text().replace(project + '.finance_analytics', dataset_id))
    run_id = uuid4().hex
    concurrent_email = 'concurrent-' + run_id + '@example.invalid'
    body = dict(email='synthetic-' + run_id + '@example.invalid', full_name='Synthetic Identity', business_name='Synthetic Business',
                password='SyntheticTestOnly123', confirm='SyntheticTestOnly123', country_code='+91', mobile_number='9876543210')
    user = register(repo, body)
    row = repo.query(f"SELECT email_verified,mobile_verified,role FROM `{repo.table('users')}` WHERE id=@id", [param('id', user['id'])])[0]
    assert row['email_verified'] is False and row['mobile_verified'] is False and row['role'] == 'client'
    assert len(repo.query(f"SELECT * FROM `{repo.table('client_memberships')}` WHERE user_id=@id", [param('id', user['id'])])) == 1

    def concurrent_register(_):
        try:
            register(repo, {**body, 'email': concurrent_email})
            return 201
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(concurrent_register, range(2)))
    assert sorted(outcomes) == [201, 409], outcomes
    assert len(repo.query(f"SELECT id FROM `{repo.table('users')}` WHERE email=@email", [param('email', concurrent_email)])) == 1

    def token(value, purpose, expired=False, target=None):
        repo.query(f'''INSERT INTO `{repo.table('auth_tokens')}` VALUES
        (@hash,@uid,@purpose,CURRENT_TIMESTAMP(),TIMESTAMP_ADD(CURRENT_TIMESTAMP(),INTERVAL @minutes MINUTE),NULL)''',
        [param('hash', auth_identity.digest(value)), param('uid', target or user['id']), param('purpose', purpose), param('minutes', -1 if expired else 30, 'INT64')])

    verify = 'synthetic-verify-' + uuid4().hex
    token(verify, 'verify')
    auth_identity.consume(repo, verify, 'verify')
    assert repo.query(f"SELECT email_verified FROM `{repo.table('users')}` WHERE id=@id", [param('id', user['id'])])[0]['email_verified'] is True
    try:
        auth_identity.consume(repo, verify, 'verify')
        raise AssertionError('Replayed token accepted')
    except HTTPException as exc:
        assert exc.status_code == 422
    expired = 'synthetic-expired-' + uuid4().hex
    token(expired, 'reset', expired=True)
    try:
        auth_identity.consume(repo, expired, 'reset', 'ChangedPassword123', 'ChangedPassword123')
        raise AssertionError('Expired token accepted')
    except HTTPException as exc:
        assert exc.status_code == 422
    reset = 'synthetic-reset-' + uuid4().hex
    token(reset, 'reset')
    auth_identity.consume(repo, reset, 'reset', 'ChangedPassword123', 'ChangedPassword123')
    assert repo.query(f"SELECT session_version FROM `{repo.table('users')}` WHERE id=@id", [param('id', user['id'])])[0]['session_version'] == 1
    for _ in range(5):
        auth_identity.throttle(repo, 'synthetic-rate-test-' + run_id)
    try:
        auth_identity.throttle(repo, 'synthetic-rate-test-' + run_id)
        raise AssertionError('Rate limit not enforced')
    except HTTPException as exc:
        assert exc.status_code == 429
    workspace_checks = []
    if args.workspace:
        from app.services.gst import account, workspace_members
        from app.services import auth_mail

        class Request:
            def __init__(self, body=None, client_id=None):
                self.body = body or {}
                self.session = {'client_id': client_id or user['client_id']}
            async def json(self):
                return self.body

        owner = SimpleNamespace(id=user['id'], email=body['email'], role='client', email_verified=True)
        profile_body = {'client_id':user['client_id'], 'legal_name':'Synthetic Business', 'constitution':'Proprietorship',
                        'registration_type':'Unregistered','gstin':'','state_code':'33','principal_address':'Synthetic address',
                        'contact_person':'Synthetic Owner','contact_email':body['email'],'contact_phone':'+919876543210',
                        'filing_frequency':'monthly','complete_onboarding':True}
        asyncio.run(account.save_profile(Request(profile_body), repo, owner))
        current = repo.query(f"SELECT onboarding_completed FROM `{repo.table('gst_client_profile')}` WHERE client_id=@cid AND is_current=TRUE", [param('cid',user['client_id'])])
        assert len(current) == 1 and current[0]['onboarding_completed'] is True
        target = repo.query(f"SELECT id FROM `{repo.table('users')}` WHERE email=@email", [param('email',concurrent_email)])[0]['id']
        verification = 'workspace-verify-' + uuid4().hex
        token(verification, 'verify', target=target)
        auth_identity.consume(repo, verification, 'verify')
        invited_user = SimpleNamespace(id=target, email=concurrent_email, role='client', email_verified=True)
        with patch.object(auth_mail, 'ready', return_value=None), patch.object(auth_mail, 'schedule'), patch.object(workspace_members, 'get_settings', return_value=SimpleNamespace(app_secret_key='synthetic-integration-key-not-for-deployment')):
            asyncio.run(workspace_members.invite(Request({'email':concurrent_email,'role':'viewer'}),repo,owner))
            invitation = repo.query(f"SELECT id FROM `{repo.table('workspace_invitations')}` WHERE client_id=@cid AND email=@email AND revoked_at IS NULL", [param('cid',user['client_id']),param('email',concurrent_email)])[0]
            acceptance = Request({'token':workspace_members.invite_token(invitation['id'])})
            assert asyncio.run(workspace_members.accept(acceptance, repo, invited_user)) == {'accepted':True}
            assert acceptance.session['client_id'] == user['client_id']
            try:
                asyncio.run(workspace_members.accept(acceptance, repo, invited_user))
                raise AssertionError('Invitation replay accepted')
            except HTTPException as exc:
                assert exc.status_code == 409
            try:
                asyncio.run(workspace_members.invite(Request({'email':'blocked@example.invalid','role':'admin'}),repo,invited_user))
                raise AssertionError('Non-owner could invite')
            except HTTPException as exc:
                assert exc.status_code == 403
            assert workspace_members.revoke_member(target, Request(), repo, owner) == {'revoked':True}
            assert not repo.query(f"SELECT 1 FROM `{repo.table('client_memberships')}` WHERE client_id=@cid AND user_id=@uid AND is_active=TRUE", [param('cid',user['client_id']),param('uid',target)])
        workspace_checks = ['onboarding_profile_version','email_bound_invitation','invitation_replay_rejection','non_owner_rejection','membership_revocation']
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'dataset': dataset_id,
              'location': source.location, 'table_expiry_hours': 24,
              'checks': ['registration', 'isolated_membership', 'concurrent_duplicate', 'email_verification',
                         'replay_rejection', 'expiry_rejection', 'session_revocation', 'distributed_rate_limit'],
              'concurrent_registration_statuses': outcomes, 'workspace_checks': workspace_checks, 'result': 'passed'}
    output = Path('artifacts/gst_easy/identity-integration.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
