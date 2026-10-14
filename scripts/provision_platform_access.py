"""Apply explicitly approved client/admin assignments; preserve credentials and evidence."""
import argparse
import json
from pathlib import Path

from google.cloud import bigquery
from google.oauth2.credentials import Credentials

from deploy_v3 import gcloud, PROJECT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--admin-email', required=True)
    parser.add_argument('--client-email', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    admin, customer = args.admin_email.strip().lower(), args.client_email.strip().lower()
    if admin == customer:
        raise ValueError('Use separate administrator and client identities.')
    client = bigquery.Client(project=PROJECT, credentials=Credentials(gcloud('auth', 'print-access-token').strip()))
    params = [bigquery.ScalarQueryParameter('admin', 'STRING', admin),
              bigquery.ScalarQueryParameter('customer', 'STRING', customer)]
    config = bigquery.QueryJobConfig(query_parameters=params, maximum_bytes_billed=500000000)
    dataset = PROJECT + '.finance_analytics'
    rows = list(client.query(f'''SELECT id,email,role,email_verified FROM `{dataset}.users`
        WHERE LOWER(email) IN (@admin,@customer) AND is_active=TRUE''',
        location='asia-south1', job_config=config).result(timeout=60))
    if len(rows) != 2 or {row['email'].lower() for row in rows} != {admin, customer}:
        raise RuntimeError('Exactly two existing active identities are required; no automatic account creation.')
    if not args.apply:
        print(json.dumps({'proposed_admin_grant': admin, 'proposed_client_role': customer,
                          'passwords_unchanged': True, 'verification_unchanged': True,
                          'admin_email_verified': next(row['email_verified'] for row in rows if row['email'].lower() == admin)}))
        return
    migration = client.query(Path('migrations/014_platform_admin_grants.sql').read_text(), location='asia-south1')
    migration.result(timeout=60)
    sql = f'''BEGIN TRANSACTION;
    UPDATE `{dataset}.auth_guard` SET touched_at=CURRENT_TIMESTAMP() WHERE id='identity';
    ASSERT @@row_count=1 AS 'Identity guard missing';
    ASSERT (SELECT COUNT(*) FROM `{dataset}.users` WHERE LOWER(email)=@admin AND is_active=TRUE)=1 AS 'Admin identity changed';
    ASSERT (SELECT COUNT(*) FROM `{dataset}.users` WHERE LOWER(email)=@customer AND is_active=TRUE)=1 AS 'Client identity changed';
    IF NOT EXISTS(SELECT 1 FROM `{dataset}.platform_admin_grants` WHERE email=@admin AND is_active=TRUE) THEN
      INSERT INTO `{dataset}.platform_admin_grants`
        SELECT id,LOWER(email),TRUE,CURRENT_TIMESTAMP() FROM `{dataset}.users` WHERE LOWER(email)=@admin AND is_active=TRUE;
      UPDATE `{dataset}.users` SET session_version=COALESCE(session_version,0)+1 WHERE LOWER(email)=@admin;
      INSERT INTO `{dataset}.auth_events` SELECT GENERATE_UUID(),id,'operator_provisioned_platform_admin',CURRENT_TIMESTAMP() FROM `{dataset}.users` WHERE LOWER(email)=@admin;
    END IF;
    IF EXISTS(SELECT 1 FROM `{dataset}.users` WHERE LOWER(email)=@customer AND role!='client') THEN
      UPDATE `{dataset}.users` SET role='client',session_version=COALESCE(session_version,0)+1 WHERE LOWER(email)=@customer;
      INSERT INTO `{dataset}.auth_events` SELECT GENERATE_UUID(),id,'operator_changed_identity_to_client',CURRENT_TIMESTAMP() FROM `{dataset}.users` WHERE LOWER(email)=@customer;
    END IF;
    UPDATE `{dataset}.platform_admin_grants` SET is_active=FALSE WHERE email=@customer;
    COMMIT TRANSACTION;'''
    job = client.query(sql, location='asia-south1', job_config=config)
    job.result(timeout=90)
    result = {'migration_job': migration.job_id, 'assignment_job': job.job_id,
              'admin': admin, 'client': customer, 'passwords_changed': False,
              'verification_changed': False, 'memberships_changed': False,
              'admin_verification_required': next(row['email_verified'] for row in rows if row['email'].lower() == admin) is not True}
    Path('artifacts/gst_easy/platform-access.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
