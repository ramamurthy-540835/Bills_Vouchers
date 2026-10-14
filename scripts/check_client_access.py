"""Inspect one reported identity's roles without passwords, tokens or invoices."""
import json
import argparse
from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from deploy_v3 import gcloud, PROJECT

parser = argparse.ArgumentParser()
parser.add_argument('--email', required=True)
args = parser.parse_args()
client = bigquery.Client(project=PROJECT, credentials=Credentials(gcloud('auth', 'print-access-token').strip()))
query = '''SELECT u.id,u.role AS identity_role,u.email_verified,m.client_id,m.access_role,m.is_active AS membership_active,r.role AS workspace_role
FROM `aidirac-503309.finance_analytics.users` u
LEFT JOIN `aidirac-503309.finance_analytics.client_memberships` m ON m.user_id=u.id
LEFT JOIN `aidirac-503309.finance_analytics.client_user_role` r ON r.client_id=m.client_id AND LOWER(r.email)=LOWER(u.email) AND r.is_current=TRUE
WHERE LOWER(u.email)=@email'''
rows = client.query(query, location='asia-south1', job_config=bigquery.QueryJobConfig(
    query_parameters=[bigquery.ScalarQueryParameter('email', 'STRING', args.email.strip().lower())],
    maximum_bytes_billed=100000000)).result(timeout=60)
print(json.dumps([dict(row) for row in rows], default=str, indent=2))
