"""Apply only the reviewed additive reconciliation table; never replay seed migrations."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from deploy_v3 import gcloud, PROJECT

parser = argparse.ArgumentParser()
parser.add_argument('--apply', action='store_true', required=True)
parser.parse_args()
source = Path('migrations/015_reconciliation_reviews.sql').read_bytes()
client = bigquery.Client(project=PROJECT, credentials=Credentials(gcloud('auth','print-access-token').strip()))
job = client.query(source.decode('utf-8-sig'), location='asia-south1',
                   job_config=bigquery.QueryJobConfig(maximum_bytes_billed=100000000,
                                                      labels={'purpose':'gst-easy-additive-migration'}))
job.result(timeout=90)
result = {'file':'015_reconciliation_reviews.sql','sha256':hashlib.sha256(source).hexdigest(),
          'job_id':job.job_id,'utc':datetime.now(timezone.utc).isoformat(),'status':'applied'}
Path('artifacts/gst_easy/migration-015.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
