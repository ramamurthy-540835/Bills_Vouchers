"""Synthetic snapshot/restore drill. Never deletes or overwrites source evidence."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from uuid import uuid4

from google.cloud import bigquery, storage
from google.oauth2.credentials import Credentials

from deploy_v3 import gcloud, PROJECT, REGION


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true',required=True)
    parser.parse_args()
    started=monotonic()
    source=json.loads(Path('artifacts/gst_easy/canonical-integration.json').read_text())['dataset']
    if not re.fullmatch(re.escape(PROJECT)+r'\.gst_easy_bills_test_[a-f0-9]{12}',source):
        raise RuntimeError('Only the recorded synthetic integration dataset is allowed.')
    credentials=Credentials(gcloud('auth','print-access-token').strip())
    client=bigquery.Client(project=PROJECT,credentials=credentials)
    original=client.get_dataset(source)
    if original.labels.get('synthetic')!='true' or original.location!=REGION:
        raise RuntimeError('Source must be labelled synthetic in the expected region.')
    run=uuid4().hex[:12]
    target=PROJECT+'.gst_easy_restore_test_'+run
    dataset=bigquery.Dataset(target)
    dataset.location=REGION
    dataset.default_table_expiration_ms=86400000
    dataset.labels={'synthetic':'true','purpose':'gst-easy-restore-drill'}
    client.create_dataset(dataset)
    print('Isolated restore dataset: '+target,flush=True)
    def query(sql,params=()):
        return list(client.query(sql,location=REGION,job_config=bigquery.QueryJobConfig(
            query_parameters=list(params),maximum_bytes_billed=200000000,
            labels={'purpose':'gst-easy-restore-test'})).result(timeout=90))
    snapshot_time=query('SELECT CURRENT_TIMESTAMP() AS stamp')[0]['stamp']
    stamp=[bigquery.ScalarQueryParameter('stamp','TIMESTAMP',snapshot_time)]
    def fingerprint(table, historical=False):
        suffix=' FOR SYSTEM_TIME AS OF @stamp' if historical else ''
        row=query(f'''SELECT COUNT(*) AS count,TO_HEX(SHA256(COALESCE(
            STRING_AGG(TO_JSON_STRING(t),'\\n' ORDER BY TO_JSON_STRING(t)),''))) AS digest
            FROM `{table}` AS t{suffix}''',stamp if historical else [])[0]
        return {'count':row['count'],'sha256':row['digest']}
    checks=[]
    for table in sorted(client.list_tables(source),key=lambda row:row.table_id):
        name=table.table_id
        if not re.fullmatch(r'[a-z_][a-z_0-9]*',name) or table.table_type!='TABLE':
            raise RuntimeError('Unexpected synthetic source table.')
        full=client.get_table(source+'.'+name)
        if (full.num_rows or 0)>10000 or (full.num_bytes or 0)>50000000:
            raise RuntimeError('Synthetic drill size limit exceeded.')
        snapshot=target+'.snapshot_'+name
        restored=target+'.restored_'+name
        query(f'''CREATE SNAPSHOT TABLE `{snapshot}` CLONE `{source}.{name}`
            FOR SYSTEM_TIME AS OF @stamp
            OPTIONS(expiration_timestamp=TIMESTAMP_ADD(CURRENT_TIMESTAMP(),INTERVAL 1 DAY))''',stamp)
        query(f'''CREATE TABLE `{restored}` CLONE `{snapshot}`
            OPTIONS(expiration_timestamp=TIMESTAMP_ADD(CURRENT_TIMESTAMP(),INTERVAL 1 DAY))''')
        before=fingerprint(source+'.'+name,True)
        assert fingerprint(restored)==before, 'Restored contents differ: '+name
        assert client.get_table(restored).schema==full.schema, 'Restored schema differs: '+name
        checks.append({'table':name,**before})
        print('Restored and verified: '+name,flush=True)
    bucket_name=PROJECT+'-bills-voucher-documents'
    bucket=storage.Client(project=PROJECT,credentials=credentials).bucket(bucket_name)
    prefix='__gst_easy_restore_probe__/'+run+'/'
    content=b'GST Easy synthetic object restoration probe. No customer evidence.\n'
    raw=bucket.blob(prefix+'original.txt')
    raw.metadata={'synthetic':'true','purpose':'restore-drill'}
    raw.upload_from_string(content,content_type='text/plain',if_generation_match=0)
    backup=bucket.copy_blob(raw,bucket,prefix+'backup.txt',source_generation=raw.generation,if_generation_match=0)
    restored=bucket.copy_blob(backup,bucket,prefix+'restored.txt',source_generation=backup.generation,if_generation_match=0)
    assert restored.download_as_bytes(if_generation_match=restored.generation)==content
    assert raw.download_as_bytes(if_generation_match=raw.generation)==content
    result={'utc':datetime.now(timezone.utc).isoformat(),'result':'passed','source_dataset':source,
            'snapshot_time':snapshot_time.isoformat(),'restore_dataset':target,'tables':checks,
            'gcs':{'bucket':bucket_name,'prefix':prefix,'sha256':hashlib.sha256(content).hexdigest(),
                   'original_generation':str(raw.generation),'backup_generation':str(backup.generation),
                   'restored_generation':str(restored.generation),'objects_retained':3},
            'elapsed_seconds':round(monotonic()-started,2),'table_expiry_hours':24,
            'customer_data_used':False,'source_deletes_or_overwrites':False,'production_recovery_certified':False}
    Path('artifacts/gst_easy/restore-drill.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
