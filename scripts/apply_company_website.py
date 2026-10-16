"""Apply only the additive website column. No historical migration or data replay."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from deploy_v3 import gcloud, PROJECT, REGION


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true',required=True)
    parser.parse_args()
    source=Path('migrations/016_company_website.sql').read_bytes()
    client=bigquery.Client(project=PROJECT,credentials=Credentials(gcloud('auth','print-access-token').strip()))
    job=client.query(source.decode('utf-8-sig'),location=REGION,job_config=bigquery.QueryJobConfig(
        maximum_bytes_billed=100000000,labels={'purpose':'gst-easy-additive-migration'}))
    job.result(timeout=90)
    field=next(item for item in client.get_table(PROJECT+'.finance_analytics.gst_client_profile').schema if item.name=='website_url')
    assert field.field_type=='STRING' and field.mode=='NULLABLE'
    result={'file':'016_company_website.sql','sha256':hashlib.sha256(source).hexdigest(),'job_id':job.job_id,
            'utc':datetime.now(timezone.utc).isoformat(),'status':'applied','customer_rows_updated':False}
    Path('artifacts/gst_easy/migration-016.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
