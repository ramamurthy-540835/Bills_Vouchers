"""Read-only canonical dashboard range checks against recorded synthetic tables."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

from google.cloud import bigquery
from google.oauth2.credentials import Credentials

from app.gst import dashboard
from app.gst.store import BillStore
from deploy_v3 import gcloud, PROJECT, REGION


def main():
    dataset=json.loads(Path('artifacts/gst_easy/canonical-integration.json').read_text())['dataset']
    if not re.fullmatch(re.escape(PROJECT)+r'\.gst_easy_bills_test_[a-f0-9]{12}',dataset):
        raise RuntimeError('Only the recorded synthetic integration dataset is allowed.')
    client=bigquery.Client(project=PROJECT,credentials=Credentials(gcloud('auth','print-access-token').strip()))
    if client.get_dataset(dataset).labels.get('synthetic')!='true':
        raise RuntimeError('Synthetic dataset label required.')
    measurements=[]
    class Repo:
        settings=SimpleNamespace(gcp_project_id=PROJECT)
        def table(self,name):return dataset+'.'+name
        def query(self,sql,params=()):
            started=monotonic()
            job=client.query(sql,location=REGION,job_config=bigquery.QueryJobConfig(
                query_parameters=list(params),maximum_bytes_billed=500000000,
                labels={'purpose':'gst-easy-dashboard-test'}))
            rows=list(job.result(timeout=90))
            measurements.append({'job_id':job.job_id,'seconds':round(monotonic()-started,3),
                                 'bytes_processed':job.total_bytes_processed,'bytes_billed':job.total_bytes_billed,
                                 'cache_hit':job.cache_hit})
            return rows
    class Store(BillStore):
        def table(self,layer,name):return f'`{dataset}.{name}`'
    store=Store(Repo(),'synthetic-a')
    checks=[]
    monthly=None
    for scope in ('month','quarter','financial_year'):
        before=len(measurements);started=monotonic()
        result=dashboard.build(store,'2026-09',scope,lambda _: {})
        if scope=='month':monthly=result
        assert result['bill_count']==monthly['bill_count']
        assert result['totals']==monthly['totals']
        assert result['scenarios']==monthly['scenarios']
        assert len(measurements)-before==2
        assert len(result['monthly'])=={'month':1,'quarter':3,'financial_year':12}[scope]
        checks.append({'scope':scope,'seconds':round(monotonic()-started,3),'queries':2,
                       'bill_count':result['bill_count'],'periods':result['periods']})
        print('Verified '+scope+' dashboard',flush=True)
    other=dashboard.build(Store(Repo(),'synthetic-b'),'2026-09','financial_year',lambda _: {})
    assert other['bill_count']==0 and other['confirmed_purchases']==0 and other['confirmed_sales']==0
    result={'utc':datetime.now(timezone.utc).isoformat(),'dataset':dataset,'result':'passed','checks':checks,
            'queries':measurements,'cross_tenant_empty':True,'customer_data_used':False,'database_mutations':False,
            'production_load_benchmark':False}
    Path('artifacts/gst_easy/dashboard-integration.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
