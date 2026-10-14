"""Exercise canonical bill transactions with synthetic rows in expiring tables."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from google.cloud import bigquery
from google.oauth2.credentials import Credentials

from app.gst.store import BillStore
from app.gst.schemas.invoice import GstInvoice
from deploy_v3 import gcloud


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true',required=True)
    parser.parse_args()
    project='aidirac-503309'
    client=bigquery.Client(project=project,credentials=Credentials(gcloud('auth','print-access-token').strip()))
    dataset_id=project+'.gst_easy_bills_test_'+uuid4().hex[:12]
    dataset=bigquery.Dataset(dataset_id)
    dataset.location='asia-south1'
    dataset.default_table_expiration_ms=86400000
    dataset.labels={'purpose':'gst-easy-bills-integration','synthetic':'true'}
    client.create_dataset(dataset)
    print('Isolated synthetic dataset: '+dataset_id,flush=True)
    for source,name in [('gold','gst_invoice'),('silver','gst_invoice_line'),('silver','gst_bills_gstr2b'),('ops','gst_bill_audit'),('ops','gst_bill_lock'),('ops','gst_bill_job'),('finance_analytics','gst_filing_status')]:
        original=client.get_table(f'{project}.{source}.{name}')
        client.create_table(bigquery.Table(dataset_id+'.'+name,schema=original.schema))

    class Repo:
        settings=SimpleNamespace(gcp_project_id=project)

        def table(self,name):
            return dataset_id+'.'+name

        def query(self,sql,params=()):
            return list(client.query(sql,location='asia-south1',job_config=bigquery.QueryJobConfig(
                query_parameters=list(params),maximum_bytes_billed=100000000,
                labels={'purpose':'gst-easy-bills-test'})).result(timeout=90))

    class Store(BillStore):
        def table(self,dataset,name):
            return f'`{dataset_id}.{name}`'

    repo=Repo()
    repo.query(f"INSERT INTO `{dataset_id}.gst_bill_lock` VALUES ('__guard__',CURRENT_TIMESTAMP())")
    store=Store(repo,'synthetic-a')
    invoice=GstInvoice(client_id='synthetic-a',source_doc_id='synthetic-document',selected_period='2026-09',invoice_number='SYNTHETIC-1',invoice_date='2026-09-01')
    store.save(invoice,'synthetic-actor','upload')
    assert store.get(invoice.invoice_id).version==1
    assert Store(repo,'synthetic-b').list()==[]
    store.delete(invoice,'synthetic-actor')
    assert store.list()==[] and len(store.deleted('2026-09'))==1
    try:
        store.save(invoice,'synthetic-actor','upload')
        raise AssertionError('Deleted evidence silently recreated')
    except HTTPException as exc:
        assert exc.status_code==409
    source={'sha256':'a'*64,'period':'2026-09','raw_ref':'synthetic-only-no-gcs-object','record_count':0,'parser_version':'b2b-2'}
    store.save_matching('2026-09',[],'synthetic-actor',source)
    assert store.statement_history('2026-09')[0]['sha256']==source['sha256']
    assert Store(repo,'synthetic-b').statement_history('2026-09')==[]
    try:
        store.save_matching('2026-09',[],'synthetic-actor',source)
        raise AssertionError('Duplicate statement accepted')
    except HTTPException as exc:
        assert exc.status_code==409
    restored=store.deleted_invoice(invoice.invoice_id)
    restored.version+=1
    restored.status='needs_review'

    def restore(_):
        try:
            store.save(restored,'synthetic-actor','restore')
            return 200
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(restore,range(2)))
    assert sorted(outcomes)==[200,409],outcomes
    assert store.deleted('2026-09')==[]
    assert store.get(invoice.invoice_id).status=='needs_review'
    assert len(store.list())==1
    store.job('synthetic-job',{'job_id':'synthetic-job','period':'2026-09','status':'completed','files':[]})
    assert len(store.job_history('2026-09'))==1
    assert Store(repo,'synthetic-b').job_history('2026-09')==[]
    store.job('retry-job',{'job_id':'retry-job','period':'2026-09','status':'needs_attention','files':[{'status':'needs_attention','invoice_ids':[],'reason':'Dispatch failed'}]})
    retry=store.retry_job('retry-job')
    assert retry['status']=='queued' and retry['files'][0]['status']=='reading'
    try:
        store.retry_job('retry-job')
        raise AssertionError('Duplicate retry accepted')
    except HTTPException as exc:
        assert exc.status_code==409
    repo.query(f"INSERT INTO `{dataset_id}.gst_filing_status` (client_id,period,state,is_current) VALUES ('synthetic-a','2026-09','locked',TRUE)")
    moved=restored.model_copy(deep=True)
    moved.invoice_date=moved.invoice_date.replace(month=10)
    moved.version+=1
    for action in (lambda:store.assert_writable('2026-09'),lambda:store.delete(restored,'synthetic-actor'),
                   lambda:store.save(moved,'synthetic-actor','edit',restored),lambda:store.save_matching('2026-09',[],'synthetic-actor')):
        try:
            action()
            raise AssertionError('Frozen period changed')
        except HTTPException as exc:
            assert exc.status_code==409
    assert store.get(invoice.invoice_id).version==restored.version
    report={'utc':datetime.now(timezone.utc).isoformat(),'dataset':dataset_id,'result':'passed',
            'checks':['canonical_save','tenant_isolation','audited_delete','deleted_reupload_blocked','concurrent_restore','restore_needs_review','durable_job_history','single_retry_claim','statement_history_duplicate_and_tenant_checks','frozen_period_delete_import_and_date_move_blocked'],
            'concurrent_restore_statuses':outcomes,'table_expiry_hours':24}
    target=Path('artifacts/gst_easy/canonical-integration.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
