"""Real V3 BQ/GCS synthetic service integration, not browser-login acceptance."""
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from google.cloud import bigquery, storage
from google.oauth2.credentials import Credentials
from prepare_gst_new_v3 import PROJECT, REGION, PREFIX, ART, cloud

sys.path.insert(0,str(Path('.').resolve()))


def main():
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GST_NEW_V3':
        raise RuntimeError('Wrong branch')
    client_id=str(UUID((ART/'acceptance-client.txt').read_text().strip()))
    credentials=Credentials(cloud('auth','print-access-token'))
    bq=bigquery.Client(project=PROJECT,credentials=credentials,location=REGION)
    class Repo:
        settings=SimpleNamespace(gcp_project_id=PROJECT,gst_dataset_prefix=PREFIX)
        def table(self,name):return f'{PROJECT}.{PREFIX}finance_analytics.{name}'
        def query(self,sql,params=()):
            return list(bq.query(sql,job_config=bigquery.QueryJobConfig(
                query_parameters=list(params),maximum_bytes_billed=100000000)).result())
    repo=Repo()
    from app.services.gst.medallion import param
    authorized=repo.query(f"""SELECT c.id FROM `{repo.table('clients')}` c
        JOIN `{repo.table('gst_client_profile')}` p ON p.client_id=c.id
        WHERE c.id=@id AND c.is_test=TRUE AND p.source='SYNTHETIC_TEST_ONLY'
        AND c.name='GST Easy V3 Synthetic Acceptance Workspace'""",[param('id',client_id)])
    if len(authorized)!=1:raise RuntimeError('Wrong synthetic test workspace')
    os.environ['GCS_BUCKET_NAME']=PROJECT+'-gst-easy-v3-documents'
    from app.config import get_settings
    get_settings.cache_clear()
    from app.gst.store import BillStore
    import app.gst.store as store_module
    original_factory=storage.Client
    store_module.storage.Client=lambda **kwargs:original_factory(credentials=credentials,**kwargs)
    from app.routers.gst_intake import stage_batch,reconcile_staged
    store=BillStore(repo,client_id)
    def count():
        return store.query(f"SELECT COUNT(*) AS n FROM {store.table('gold','gst_invoice')} WHERE client_id=@client_id")[0]['n']
    before=count()
    vendor=[{'source_record_id':'V3-SYNTHETIC-VENDOR-001','event_type':'invoice',
             'source_version':'1','invoice_number':'SYNTHETIC-NOT-FOR-FILING-001',
             'invoice_date':'2026-10-01','supplier_gstin':'33AAAAA0000A1Z0','customer_gstin':'33BBBBB0000B1Z0',
             'trip_id':'V3-SYNTHETIC-TRIP-001','taxable_amount':'100.00','cgst':'9.00','sgst':'9.00',
             'igst':'0.00','cess':'0.00','invoice_total':'118.00'}]
    driver=[{'source_record_id':'V3-SYNTHETIC-DRIVER-001','event_type':'trip','source_version':'1',
             'trip_id':'V3-SYNTHETIC-TRIP-001','payment_amount':'118.00'}]
    content=json.dumps(vendor).encode()
    batch=stage_batch(store,'v3-authorized-integration-test','vendor','{}',content,'SYNTHETIC-TEST-ONLY-vendor.json')
    replay=stage_batch(store,'v3-authorized-integration-test','vendor','{}',content,'SYNTHETIC-TEST-ONLY-vendor.json')
    assert replay['replayed'] is True and replay['batch_id']==batch['batch_id']
    original=store.query(f"SELECT payload FROM {store.table('ops','bulk_import_batches')} WHERE client_id=@client_id AND batch_id=@batch",
                         [param('batch',batch['batch_id'])])[0]['payload']
    original=json.loads(original) if isinstance(original,str) else original
    assert store.download_object(original['original_ref'])==content
    from fastapi import HTTPException
    try:
        store.download_object(original['original_ref'].replace('/'+client_id+'/', '/unrelated-client/'))
    except HTTPException as exc:
        assert exc.status_code==404
    else:
        raise AssertionError('Foreign source path was not rejected')
    trip=stage_batch(store,'v3-authorized-integration-test','driver','{}',json.dumps(driver).encode(),'SYNTHETIC-TEST-ONLY-driver.json')
    first=reconcile_staged(store,batch['batch_id'],'2026-10','v3-authorized-integration-test')
    again=reconcile_staged(store,batch['batch_id'],'2026-10','v3-authorized-integration-test')
    event=reconcile_staged(store,trip['batch_id'],'2026-10','v3-authorized-integration-test')
    assert first['run_id']==again['run_id']
    assert first['counts']=={'source_only':1}
    assert event['counts']=={'ambiguous_reference':1}
    assert count()==before
    report={'integration':'actual V3 BigQuery and private GCS, authorized operator service calls',
            'browser_login_test':False,'batch_replay_idempotent':True,'snapshot_replay_idempotent':True,
            'invoice_reconciliation':first['counts'],'driver_reconciliation':event['counts'],
            'financial_rows_before':before,'financial_rows_after':count(),
            'originals_retained':True,'original_bytes_verified':True,'foreign_source_path_denied':True,'synthetic_only':True,
            'batch_ids':[batch['batch_id'],trip['batch_id']],'run_ids':[first['run_id'],event['run_id']]}
    (ART/'source-storage-integration.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=='__main__':
    main()
