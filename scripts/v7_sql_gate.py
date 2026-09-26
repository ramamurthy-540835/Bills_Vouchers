"""Compile the account mutation SQL in BigQuery dry-run mode; no DML executes."""
import asyncio
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from app.services.gst import account


async def main():
    token=subprocess.check_output(['gcloud.cmd','auth','print-access-token'],text=True).strip()
    bq=bigquery.Client(project='aidirac-503309',credentials=Credentials(token))
    captured=[]
    class Repo:
        def table(self,name):return 'aidirac-503309.finance_analytics.'+name
        def query(self,sql,params):captured.append((sql,params))
    class Request:
        async def json(self):return {'client_id':'lint-client','legal_name':'SQL compile only','contact_phone':'+919876543210','contact_email':'compile@example.test','principal_address':'No write'}
    account.active_client=lambda *args:SimpleNamespace(id='lint-client')
    account.can=lambda *args:True
    account.Medallion.profile=lambda self:{'profile_id':'lint-profile','legal_name':'SQL compile only'}
    await account.save_profile(Request(),Repo(),SimpleNamespace(id='lint-user',role='client'))
    for sql,params in captured:
        assert 'client_id=@client_id' in sql
        job=bq.query(sql,job_config=bigquery.QueryJobConfig(dry_run=True,use_query_cache=False,query_parameters=params))
        print('PASS BigQuery account transaction dry-run; bytes='+str(job.total_bytes_processed),flush=True)


asyncio.run(main())
