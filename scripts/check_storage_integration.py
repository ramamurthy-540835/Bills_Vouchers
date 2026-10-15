"""Real GCS round trips under a unique synthetic tenant; no customer objects."""
import hashlib
import json
import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from google.cloud import bigquery, storage
from google.oauth2.credentials import Credentials
from PIL import Image

from app.gst import store as bills
from app.gst.schemas.invoice import GstInvoice
from app.services.gst import account
from deploy_v3 import gcloud, PROJECT, REGION


def main():
    dataset=json.loads(Path('artifacts/gst_easy/canonical-integration.json').read_text())['dataset']
    if not re.fullmatch(re.escape(PROJECT)+r'\.gst_easy_bills_test_[a-f0-9]{12}',dataset):
        raise RuntimeError('Only the recorded synthetic dataset is allowed.')
    credentials=Credentials(gcloud('auth','print-access-token').strip())
    bq=bigquery.Client(project=PROJECT,credentials=credentials)
    if bq.get_dataset(dataset).labels.get('synthetic')!='true':raise RuntimeError('Synthetic label required.')
    storage_client=storage.Client(project=PROJECT,credentials=credentials)
    bucket=storage_client.bucket(PROJECT+'-bills-voucher-documents')
    tenant='__gst_easy_storage_probe__'+uuid4().hex
    class Repo:
        settings=SimpleNamespace(gcp_project_id=PROJECT)
        def table(self,name):
            if name!='profile_audit':raise RuntimeError('Only synthetic profile audit writes allowed.')
            return dataset+'.'+name
        def query(self,sql,params=()):
            return list(bq.query(sql,location=REGION,job_config=bigquery.QueryJobConfig(
                query_parameters=list(params),maximum_bytes_billed=500000000,
                labels={'purpose':'gst-easy-storage-test'})).result(timeout=90))
    repo=Repo()
    repo.query(f'''CREATE TABLE IF NOT EXISTS `{dataset}.profile_audit`
        (id STRING,client_id STRING,actor_id STRING,action STRING,before_value JSON,after_value JSON,created_at TIMESTAMP)
        OPTIONS(expiration_timestamp=TIMESTAMP_ADD(CURRENT_TIMESTAMP(),INTERVAL 1 DAY))''')
    settings=SimpleNamespace(gcs_bucket_name=bucket.name)
    content=BytesIO();Image.new('RGB',(20,20),'blue').save(content,format='PNG');original=content.getvalue()
    store=bills.BillStore(repo,tenant)
    with patch.object(bills,'get_settings',return_value=settings),patch.object(bills.storage,'Client',return_value=storage_client):
        ref=store.upload_object(original,'synthetic-doc','original.png','bronze','image/png')
        assert store.upload_object(original,'synthetic-doc','original.png','bronze','image/png')==ref
        try:store.upload_object(b'different','synthetic-doc','original.png','bronze','image/png')
        except HTTPException as exc:assert exc.status_code==409
        else:raise AssertionError('Different evidence overwrote original')
        inv=GstInvoice(client_id=tenant,source_doc_id='synthetic-doc',supplier_gstin='33ABCDE1234F1Z7',invoice_number='STORAGE/TEST')
        inv.extraction.raw_ref=ref;store.name_original(inv);named=inv.extraction.raw_ref
        assert named!=ref and store.download_object(named)==original and store.download_object(ref)==original
        inv.extraction.raw_ref=ref;store.name_original(inv)
        try:bills.BillStore(repo,tenant+'-other').download_object(named)
        except HTTPException as exc:assert exc.status_code==404
        else:raise AssertionError('Foreign storage access allowed')
    actor=SimpleNamespace(id='synthetic-storage-actor',role='client')
    with patch.object(account,'active_client',return_value=SimpleNamespace(id=tenant)),\
         patch.object(account,'can',return_value=True),\
         patch.object(account,'logo_blob',side_effect=lambda cid:bucket.blob(cid+'/profile/logo.png')):
        account.upload_logo(None,UploadFile(filename='logo.png',file=BytesIO(original)),repo,actor)
        first_logo=account.get_logo(None,repo,actor).body
        assert first_logo.startswith(b'\x89PNG')
        second=BytesIO();Image.new('RGB',(20,20),'green').save(second,format='JPEG')
        account.upload_logo(None,UploadFile(filename='replacement.jpg',file=BytesIO(second.getvalue())),repo,actor)
        assert account.get_logo(None,repo,actor).body!=original
        assert account.remove_logo(None,repo,actor)=={'removed':True}
        try:account.get_logo(None,repo,actor)
        except HTTPException as exc:assert exc.status_code==404
        else:raise AssertionError('Removed active logo still exists')
    objects=list(storage_client.list_blobs(bucket,prefix=tenant+'/'))
    archives=[blob for blob in objects if '/profile/history/' in blob.name]
    assert len(archives)==2
    assert any(blob.download_as_bytes()==first_logo for blob in archives)
    audit=repo.query(f"SELECT action FROM `{dataset}.profile_audit` WHERE client_id=@client_id",
                    [bigquery.ScalarQueryParameter('client_id','STRING',tenant)])
    assert len(audit)==6
    result={'utc':datetime.now(timezone.utc).isoformat(),'result':'passed','synthetic_tenant':tenant,
        'bucket':bucket.name,'dataset':dataset,'objects_retained':len(objects),'logo_archives_retained':2,
        'logo_audit_events':len(audit),'original_sha256':hashlib.sha256(original).hexdigest(),
        'checks':['create-only upload','identical retry','different-byte conflict','canonical copy','original retained',
                  'cross-tenant reference denied','logo upload/normalize/replace/remove','logo archives and audit retained'],
        'customer_data_used':False,'authenticated_preview_uat':False,
        'scope':'Actual GCS and BigQuery; local controlled actor/membership boundary. No identity delivery or live login tested.'}
    Path('artifacts/gst_easy/storage-integration.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
