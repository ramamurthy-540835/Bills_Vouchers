"""Read-only reporting checks against the last expiring synthetic integration dataset."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from google.cloud import bigquery
from google.oauth2.credentials import Credentials

from app.gst import reports
from app.gst.store import BillStore
from deploy_v3 import gcloud, PROJECT


def main():
    previous=json.loads(Path('artifacts/gst_easy/canonical-integration.json').read_text())
    dataset=previous['dataset']
    if not re.fullmatch(re.escape(PROJECT)+r'\.gst_easy_bills_test_[a-f0-9]{12}',dataset):
        raise RuntimeError('Only the recorded synthetic integration dataset is allowed.')
    client=bigquery.Client(project=PROJECT,credentials=Credentials(gcloud('auth','print-access-token').strip()))
    checks=[]
    class Repo:
        settings=SimpleNamespace(gcp_project_id=PROJECT)
        def table(self,name):return dataset+'.'+name
        def query(self,sql,params=()):
            return list(client.query(sql,location='asia-south1',job_config=bigquery.QueryJobConfig(
                query_parameters=list(params),maximum_bytes_billed=500000000,
                labels={'purpose':'gst-easy-report-test'})).result(timeout=90))
    class Store(BillStore):
        def table(self,layer,name):return f'`{dataset}.{name}`'
    store=Store(Repo(),'synthetic-a')
    for kind in reports.TITLES:
        report=reports.build(store,'2026-09','month',kind,lambda _: {})
        assert report['client_id']=='synthetic-a'
        for format in ('csv','xlsx'):
            content,mime=reports.render(report,format)
            assert content and mime
        if kind=='audit':
            assert any(row[1]=='reconciliation' for row in report['rows'])
            assert any(row[1]=='return' for row in report['rows'])
            assert any(row[4]=='job_retry' for row in report['rows'])
        if kind=='tax':
            content,_=reports.render(report,'pdf')
            Path('artifacts/gst_easy/synthetic-tax-summary.pdf').write_bytes(content)
        checks.append({'kind':kind,'rows':report['row_count'],'hash':report['report_hash']})
        print('Verified report: '+kind,flush=True)
    other=reports.build(Store(Repo(),'synthetic-b'),'2026-09','month','audit',lambda _: {})
    assert other['rows']==[] and other['source_invoices']==[]
    result={'utc':datetime.now(timezone.utc).isoformat(),'dataset':dataset,'result':'passed',
            'checks':checks,'cross_tenant_empty':True,'customer_data_used':False,'database_mutations':False}
    Path('artifacts/gst_easy/reports-integration.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
