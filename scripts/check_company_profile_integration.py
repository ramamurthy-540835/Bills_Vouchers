"""Actual versioned BigQuery website updates in a new expiring synthetic dataset."""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from google.cloud import bigquery
from google.oauth2.credentials import Credentials

from app.gst import store as bill_store
from app.services.gst import account
from app.services.gst.medallion import param
from deploy_v3 import gcloud, PROJECT, REGION


def main():
    client=bigquery.Client(project=PROJECT,credentials=Credentials(gcloud('auth','print-access-token').strip()))
    dataset_id=PROJECT+'.gst_easy_profile_test_'+uuid4().hex[:12]
    dataset=bigquery.Dataset(dataset_id);dataset.location=REGION;dataset.default_table_expiration_ms=86400000
    dataset.labels={'synthetic':'true','purpose':'gst-easy-profile-test'}
    client.create_dataset(dataset)
    for source,name in [('finance_analytics','gst_client_profile'),('finance_analytics','profile_audit'),('ops','gst_bill_lock')]:
        schema=client.get_table(f'{PROJECT}.{source}.{name}').schema
        client.create_table(bigquery.Table(dataset_id+'.'+name,schema=schema))
    class Repo:
        settings=SimpleNamespace(gcp_project_id=PROJECT)
        def table(self,name):return dataset_id+'.'+name
        def query(self,sql,params=()):
            return list(client.query(sql,location=REGION,job_config=bigquery.QueryJobConfig(
                query_parameters=list(params),maximum_bytes_billed=100000000,
                labels={'purpose':'gst-easy-profile-test'})).result(timeout=90))
    class Store(bill_store.BillStore):
        def table(self,layer,name):return f'`{dataset_id}.{name}`'
    class Request:
        def __init__(self,body):self.body=body
        async def json(self):return self.body
    repo=Repo();actor=SimpleNamespace(id='synthetic-owner',role='client')
    repo.query(f"INSERT INTO `{dataset_id}.gst_bill_lock` VALUES ('__guard__',CURRENT_TIMESTAMP())")
    repo.query(f'''INSERT INTO `{dataset_id}.gst_client_profile`
        (profile_id,client_id,legal_name,gstin,registration_type,effective_from,is_current,created_at,created_by,gstin_verified)
        VALUES ('before','synthetic-company','Synthetic company','','Unregistered',CURRENT_TIMESTAMP(),TRUE,CURRENT_TIMESTAMP(),'synthetic-owner',FALSE)''')
    with patch.object(account,'active_client',return_value=SimpleNamespace(id='synthetic-company')),\
         patch.object(account,'can',return_value=True),\
         patch.object(account,'get_settings',return_value=SimpleNamespace(gst_bills_enabled=True)),\
         patch.object(bill_store,'BillStore',Store):
        body={'client_id':'synthetic-company','profile_id':'before','website_url':'Example.com/company','gstin_verified':True}
        assert asyncio.run(account.save_profile(Request(body),repo,actor))['saved']
        rows=repo.query(f"SELECT profile_id,website_url,gstin_verified,is_current FROM `{dataset_id}.gst_client_profile` ORDER BY effective_from")
        assert len(rows)==2 and sum(bool(row['is_current']) for row in rows)==1
        current=next(row for row in rows if row['is_current'])
        assert current['website_url']=='https://example.com/company' and current['gstin_verified'] is False
        try:asyncio.run(account.save_profile(Request(body),repo,actor))
        except HTTPException as exc:assert exc.status_code==409
        else:raise AssertionError('Stale profile accepted')
        try:asyncio.run(account.save_profile(Request({**body,'client_id':'foreign'}),repo,actor))
        except HTTPException as exc:assert exc.status_code==403
        else:raise AssertionError('Foreign profile accepted')
        audit=repo.query(f"SELECT before_value,after_value FROM `{dataset_id}.profile_audit` WHERE client_id=@client_id",[param('client_id','synthetic-company')])
        assert len(audit)==1
        after=audit[0]['after_value'];after=json.loads(after) if isinstance(after,str) else after
        assert after['website_url']==current['website_url'] and after['gstin_verified'] is False
    result={'utc':datetime.now(timezone.utc).isoformat(),'dataset':dataset_id,'result':'passed',
            'checks':['website persisted','prior version retained','one current profile','audit before/after',
                      'stale save denied','foreign client denied','verification cannot be forged'],
            'customer_rows_updated':False,'table_expiry_hours':24,'live_identity_uat':False}
    Path('artifacts/gst_easy/company-profile-integration.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
