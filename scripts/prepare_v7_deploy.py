"""Apply the additive account schema before deploying the v7 API."""
import subprocess
from pathlib import Path
from google.cloud import bigquery
from google.oauth2.credentials import Credentials

token = subprocess.check_output(['gcloud.cmd','auth','print-access-token'],text=True).strip()
bq = bigquery.Client(project='aidirac-503309',credentials=Credentials(token))
job = bq.query(Path('migrations/009_v7_account.sql').read_text())
job.result()
print('Applied additive v7 account migration: '+job.job_id)
