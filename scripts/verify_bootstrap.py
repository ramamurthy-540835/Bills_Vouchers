"""Verify the authorised bootstrap without printing or persisting secret values."""
import json
import os
import subprocess

from google.cloud import bigquery
from google.oauth2.credentials import Credentials

os.environ.update(GCP_PROJECT_ID="aidirac-503309", BIGQUERY_DATASET="finance_analytics", DEMO_FALLBACK="false")
from app.config import get_settings
from app.db import BigQueryRepository
from app.services.gst.bootstrap import bootstrap
from app.services.gst.medallion import param

token = subprocess.check_output(['gcloud.cmd', 'auth', 'print-access-token'], text=True).strip()
raw = subprocess.check_output(['gcloud.cmd', 'secrets', 'versions', 'access', 'latest', '--secret=red-taxi-client-bootstrap', '--project=aidirac-503309'], text=True)
settings = get_settings()
settings.red_taxi_client_bootstrap = raw
repo = object.__new__(BigQueryRepository)
repo.settings, repo.dataset = settings, 'aidirac-503309.finance_analytics'
repo.client = bigquery.Client(project='aidirac-503309', credentials=Credentials(token))
bootstrap(repo)
bootstrap(repo)
email = json.loads(raw)['email'].lower()
rows = repo.query(f"SELECT role,client_id FROM `{repo.table('client_user_role')}` WHERE email=@email AND is_current=TRUE", [param('email',email)])
assert any(row.role=='client' for row in rows)
for row in rows:
    profiles=repo.query(f"SELECT gstin,legal_name,business_nature FROM `{repo.table('gst_client_profile')}` WHERE client_id=@client_id AND is_current=TRUE", [param('client_id',row.client_id)])
    assert profiles and all(not p.gstin or p.gstin.startswith('33') for p in profiles)
print('PASS idempotent Red Taxi bootstrap, current client role, no invented GSTIN')
from app.repository import FinanceRepository
from app.security import verify_password
user = FinanceRepository(repo).user_by_email(email)
print('ACCOUNT_ACTIVE=' + str(bool(user and user.is_active)))
print('BOOTSTRAP_PASSWORD_MATCHES_EXISTING_ACCOUNT=' + str(bool(user and verify_password(json.loads(raw)['password'], user.password_hash))))
print('PASSWORD_CHANGE_REQUIRED=' + str(bool(user and getattr(user, 'must_change_password', False))))
