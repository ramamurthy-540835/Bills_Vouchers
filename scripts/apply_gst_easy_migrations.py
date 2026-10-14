"""Apply the reviewed additive GST_EASY migrations; no historical seeds or deletes."""
import argparse
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from deploy_v3 import gcloud,PROJECT


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true',required=True);parser.parse_args()
    client=bigquery.Client(project=PROJECT,credentials=Credentials(gcloud('auth','print-access-token').strip()))
    files=['010_identity_verification.sql','011_mobile_verification.sql','012_workspace_onboarding.sql','013_canonical_return_workflow.sql']
    count=list(client.query(f'''SELECT COUNT(*) AS affected FROM `{PROJECT}.finance_analytics.client_memberships` m
        WHERE m.is_active=TRUE AND m.access_role='client' AND EXISTS(SELECT 1 FROM `{PROJECT}.finance_analytics.gst_client_profile` p
        WHERE p.client_id=m.client_id AND p.created_by=m.user_id AND p.source='SELF_REGISTRATION')''',location='asia-south1',
        job_config=bigquery.QueryJobConfig(maximum_bytes_billed=100000000)).result(timeout=90))[0]['affected']
    print('Explicit self-registration owner backfill count: '+str(count),flush=True)
    report={'utc':datetime.now(timezone.utc).isoformat(),'owner_backfill_count':count,'migrations':[]}
    path=Path('artifacts/gst_easy/migrations.json');path.parent.mkdir(parents=True,exist_ok=True)
    for name in files:
        raw=Path('migrations',name).read_bytes()
        job=client.query(raw.decode('utf-8-sig'),location='asia-south1',job_config=bigquery.QueryJobConfig(
            maximum_bytes_billed=100000000,labels={'purpose':'gst-easy-additive-migration'}))
        job.result(timeout=180)
        report['migrations'].append({'file':name,'sha256':hashlib.sha256(raw).hexdigest(),'job_id':job.job_id,'status':'applied'})
        path.write_text(json.dumps(report,indent=2))
        print(name+' applied',flush=True)


if __name__=='__main__':main()
