"""Provision synthetic customers using actual BQ transactions and private GCS markers."""
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from google.cloud import bigquery, storage
from google.oauth2.credentials import Credentials

from app.services import customer_workspace as service
from deploy_v3 import gcloud, PROJECT, REGION


def main():
    credentials = Credentials(gcloud('auth', 'print-access-token').strip())
    client = bigquery.Client(project=PROJECT, credentials=credentials)
    gcs = storage.Client(project=PROJECT, credentials=credentials)
    dataset_id = PROJECT + '.gst_easy_customer_test_' + uuid4().hex[:12]
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = REGION
    dataset.default_table_expiration_ms = 86400000
    dataset.labels = {'synthetic': 'true', 'purpose': 'customer-setup-test'}
    client.create_dataset(dataset)
    for name in ('auth_guard','clients','client_memberships','client_user_role','gst_client_profile','profile_audit'):
        schema = client.get_table(f'{PROJECT}.finance_analytics.{name}').schema
        client.create_table(bigquery.Table(dataset_id + '.' + name, schema=schema))
    class Repo:
        def table(self, name): return dataset_id + '.' + name
        def query(self, sql, params=()):
            return list(client.query(sql, location=REGION, job_config=bigquery.QueryJobConfig(
                query_parameters=list(params), maximum_bytes_billed=100000000)).result(timeout=90))
    repo = Repo()
    repo.query(f"INSERT INTO `{dataset_id}.auth_guard` (id,touched_at) VALUES ('identity',CURRENT_TIMESTAMP())")
    user = SimpleNamespace(id='synthetic-owner',role='client',email='synthetic@example.invalid',full_name='Synthetic Owner')
    body = {'request_id':str(uuid4()),'legal_name':'Synthetic customer integration','website_url':'https://example.com'}
    bucket_name = 'aidirac-503309-bills-voucher-documents'
    with patch('google.cloud.storage.Client',return_value=gcs), patch.object(service,'get_settings',return_value=SimpleNamespace(gcp_project_id=PROJECT,gcs_bucket_name=bucket_name)):
        first = service.create_customer(repo,user,body)
        assert service.create_customer(repo,user,body) == first
    for name in ('clients','client_memberships','client_user_role','gst_client_profile','profile_audit'):
        assert repo.query(f'SELECT COUNT(*) AS n FROM `{dataset_id}.{name}`')[0]['n'] == 1, name
    profile = repo.query(f'SELECT * FROM `{dataset_id}.gst_client_profile`')[0]
    assert profile['gstin_verified'] is False and profile['website_url']=='https://example.com'
    blob = gcs.bucket(bucket_name).blob(first['client_id']+'/profile/workspace.json')
    assert json.loads(blob.download_as_bytes())['client_id']==first['client_id']
    blob.metadata={'synthetic':'true','purpose':'customer-setup-test'}
    blob.patch()
    result={'utc':datetime.now(timezone.utc).isoformat(),'result':'passed','dataset':dataset_id,
            'synthetic_storage_object':f'gs://{bucket_name}/{blob.name}', 'table_expiry_hours':24,
            'checks':['actual transaction','retry creates one profile and membership','creation audit','private GCS marker','GST not falsely verified'],
            'genuine_customer_created':False,'authenticated_uat':False}
    Path('artifacts/gst_easy/customer-setup-integration.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
