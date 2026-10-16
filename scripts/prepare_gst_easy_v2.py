"""Create ONLY new V2 resources. Copy table schemas, never existing rows."""
import argparse
import json
import os
import secrets
import subprocess
from pathlib import Path
from google.cloud import bigquery
from google.oauth2.credentials import Credentials

PROJECT='aidirac-503309'
REGION='asia-south1'
PREFIX='gst_easy_v2_'
ART=Path('artifacts/gst_easy_v2')
ENV={k:v for k,v in os.environ.items() if k.upper()!='PYTHONPATH'}


def cloud(*args, input=None):
    result=subprocess.run(['gcloud.cmd',*args],env=ENV,input=input,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('gcloud '+ ' '.join(args[:3])+' failed: '+result.stderr)
    return result.stdout.strip()


def exists(*args):
    return subprocess.run(['gcloud.cmd',*args],env=ENV,capture_output=True).returncode==0


def account(kind):return f'gst-easy-v2-{kind}@{PROJECT}.iam.gserviceaccount.com'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true',required=True);parser.parse_args()
    ART.mkdir(parents=True,exist_ok=True)
    before=json.loads(cloud('run','services','list','--project',PROJECT,'--platform','managed','--format=json'))
    if any(s['metadata']['name'] in {'gst-easy-v2-api','gst-easy-v2-web'} for s in before):
        raise RuntimeError('V2 services already exist; inspect before provisioning')
    path=ART/'services-before.json'
    if not path.exists():path.write_text(json.dumps(before,indent=2),encoding='utf-8')
    policies={}
    for s in ([] if (ART/'service-iam-before.json').exists() else before):
        name=s['metadata']['name'];region=s['metadata']['labels']['cloud.googleapis.com/location']
        policies[name]=json.loads(cloud('run','services','get-iam-policy',name,'--project',PROJECT,'--region',region,'--format=json'))
    if policies:(ART/'service-iam-before.json').write_text(json.dumps(policies,indent=2),encoding='utf-8')
    for kind in ['api','web','build']:
        if not exists('iam','service-accounts','describe',account(kind),'--project',PROJECT):
            cloud('iam','service-accounts','create','gst-easy-v2-'+kind,'--project',PROJECT,'--display-name','GST Easy V2 '+kind)
    for role in ['roles/bigquery.jobUser','roles/aiplatform.user']:
        cloud('projects','add-iam-policy-binding',PROJECT,'--member=serviceAccount:'+account('api'),'--role='+role,'--condition=None','--quiet')
    cloud('projects','add-iam-policy-binding',PROJECT,'--member=serviceAccount:'+account('build'),'--role=roles/logging.logWriter','--condition=None','--quiet')
    client=bigquery.Client(project=PROJECT,credentials=Credentials(cloud('auth','print-access-token')))
    tables=[]
    for source in ['finance_analytics','gold','silver','ops']:
        target=PREFIX+source
        dataset=bigquery.Dataset(PROJECT+'.'+target);dataset.location=REGION;dataset.labels={'application':'gst-easy-v2','purpose':'synthetic-demo'}
        dataset=client.create_dataset(dataset,exists_ok=True)
        if dataset.labels.get('application')!='gst-easy-v2':raise RuntimeError('Refusing unowned dataset '+target)
        grants=list(dataset.access_entries)
        entry=bigquery.AccessEntry('WRITER','userByEmail',account('api'))
        if entry not in grants:dataset.access_entries=grants+[entry];client.update_dataset(dataset,['access_entries'])
        existing={t.table_id for t in client.list_tables(PROJECT+'.'+target)}
        print('Preparing isolated dataset',target,flush=True)
        for item in client.list_tables(PROJECT+'.'+source):
            if item.table_type!='TABLE':continue
            if item.table_id in existing:
                tables.append(item.table_id)
                continue
            original=client.get_table(item.reference)
            table=bigquery.Table(PROJECT+'.'+target+'.'+item.table_id,schema=original.schema)
            table.time_partitioning=original.time_partitioning;table.range_partitioning=original.range_partitioning
            table.clustering_fields=original.clustering_fields;table.labels={'application':'gst-easy-v2'}
            client.create_table(table,exists_ok=True);tables.append(table.full_table_id or table.table_id)
    # Only serialization guards, never customer or financial rows.
    for dataset,table,key,value in [('finance_analytics','auth_guard','id','identity'),('ops','gst_bill_lock','client_id','__guard__')]:
        client.query(f"INSERT INTO `{PROJECT}.{PREFIX}{dataset}.{table}` ({key},touched_at) SELECT '{value}',CURRENT_TIMESTAMP() FROM (SELECT 1) WHERE NOT EXISTS(SELECT 1 FROM `{PROJECT}.{PREFIX}{dataset}.{table}` WHERE {key}='{value}')",location=REGION).result()
    for suffix in ['documents','builds']:
        bucket=f'gs://{PROJECT}-gst-easy-v2-{suffix}'
        if not exists('storage','buckets','describe',bucket):
            cloud('storage','buckets','create',bucket,'--project',PROJECT,'--location',REGION,'--uniform-bucket-level-access','--public-access-prevention')
        kind='api' if suffix=='documents' else 'build';role='roles/storage.objectAdmin' if suffix=='documents' else 'roles/storage.objectViewer'
        cloud('storage','buckets','add-iam-policy-binding',bucket,'--member=serviceAccount:'+account(kind),'--role='+role)
    if not exists('artifacts','repositories','describe','gst-easy-v2','--project',PROJECT,'--location',REGION):
        cloud('artifacts','repositories','create','gst-easy-v2','--project',PROJECT,'--location',REGION,'--repository-format=docker','--description=Isolated GST Easy V2 images')
    cloud('artifacts','repositories','add-iam-policy-binding','gst-easy-v2','--project',PROJECT,'--location',REGION,'--member=serviceAccount:'+account('build'),'--role=roles/artifactregistry.writer')
    if not exists('tasks','queues','describe','gst-easy-v2-bills','--project',PROJECT,'--location',REGION):
        cloud('tasks','queues','create','gst-easy-v2-bills','--project',PROJECT,'--location',REGION,'--max-concurrent-dispatches=1','--max-dispatches-per-second=1','--max-attempts=5')
    cloud('tasks','queues','add-iam-policy-binding','gst-easy-v2-bills','--project',PROJECT,'--location',REGION,'--member=serviceAccount:'+account('api'),'--role=roles/cloudtasks.enqueuer')
    cloud('iam','service-accounts','add-iam-policy-binding',account('api'),'--project',PROJECT,'--member=serviceAccount:'+account('api'),'--role=roles/iam.serviceAccountUser')
    for name in ['gst-easy-v2-session','gst-easy-v2-demo-password']:
        if not exists('secrets','describe',name,'--project',PROJECT):
            cloud('secrets','create',name,'--project',PROJECT,'--replication-policy=automatic','--labels=application=gst-easy-v2')
        if name.endswith('session'):
            versions=json.loads(cloud('secrets','versions','list',name,'--project',PROJECT,'--format=json'))
            if not versions:cloud('secrets','versions','add',name,'--project',PROJECT,'--data-file=-',input=secrets.token_urlsafe(48))
            cloud('secrets','add-iam-policy-binding',name,'--project',PROJECT,'--member=serviceAccount:'+account('api'),'--role=roles/secretmanager.secretAccessor')
    (ART/'resources.json').write_text(json.dumps({'project':PROJECT,'prefix':PREFIX,'schema_tables':len(tables),'financial_rows_seeded':0,'demo_password':'awaiting user-supplied secret version'},indent=2),encoding='utf-8')
    print('V2 resources prepared; copied table schemas only:',len(tables))


if __name__=='__main__':main()
