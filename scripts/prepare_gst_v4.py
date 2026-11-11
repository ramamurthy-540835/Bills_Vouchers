"""Provision only reviewed, isolated V4 resources. Shared IAM needs explicit approval."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess

from audit_gst_v4 import ART, cloud


def secret_input(*args, value):
    sdk = Path(os.environ['LOCALAPPDATA']) / 'Google/Cloud SDK/google-cloud-sdk'
    result = subprocess.run([str(sdk/'platform/bundledpython/python.exe'), str(sdk/'lib/gcloud.py'), *args],
        input=value.encode() if isinstance(value,str) else value, capture_output=True,
        env={k:v for k,v in os.environ.items() if k.upper()!='PYTHONPATH'})
    if result.returncode:
        raise RuntimeError('Secure secret provisioning failed; inspect Cloud audit logs')


def exists(*args):
    try:
        cloud(*args)
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', required=True)
    p.add_argument('--approve-project-iam', action='store_true', required=True)
    args=p.parse_args()
    if not args.apply or not args.approve_project_iam:
        raise RuntimeError('Explicit isolated provisioning and shared-IAM approval required')
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GSTv4':
        raise RuntimeError('Run only on GSTv4')
    baseline=json.loads((ART/'protected-before.json').read_text())
    project,region=baseline['project'],baseline['region']
    prefix='gst_easy_v4_'
    account=lambda kind:f'gst-easy-v4-{kind}@{project}.iam.gserviceaccount.com'
    created_file=ART/'created-resources.json'
    created=json.loads(created_file.read_text()) if created_file.exists() else []
    def remember(name):
        if name not in created:
            created.append(name);created_file.write_text(json.dumps(created,indent=2))
    def create(name, describe, command):
        if exists(*describe):
            if name not in created:
                raise RuntimeError('Pre-existing V4 resource requires review: '+name)
        else:
            cloud(*command);remember(name)
    policy=ART/'project-iam-before.json'
    if not policy.exists():
        policy.write_text(cloud('projects','get-iam-policy',project,'--format=json'))
    for kind in ('api','web','build'):
        create(account(kind), ['iam','service-accounts','describe',account(kind),'--project',project],
            ['iam','service-accounts','create','gst-easy-v4-'+kind,'--project',project,'--display-name','GST Easy V4 '+kind])
    role='gstEasyV4Predictor'
    create(role,['iam','roles','describe',role,'--project',project],
        ['iam','roles','create',role,'--project',project,'--title=GST Easy V4 model invocation',
         '--permissions=aiplatform.endpoints.predict','--stage=GA'])
    for kind,role_name in [('api','roles/bigquery.jobUser'),('api',f'projects/{project}/roles/{role}'),('build','roles/logging.logWriter')]:
        cloud('projects','add-iam-policy-binding',project,'--member=serviceAccount:'+account(kind),
              '--role='+role_name,'--condition=None','--quiet','--format=none')
    from google.cloud import bigquery
    from google.oauth2.credentials import Credentials
    bq=bigquery.Client(project=project,credentials=Credentials(cloud('auth','print-access-token')),location=region)
    tables=[]
    for source in ('finance_analytics','gold','silver','ops'):
        name=project+'.'+prefix+source
        try:
            dataset=bq.get_dataset(name)
            if name not in created or dataset.labels.get('application')!='gst-easy-v4':
                raise RuntimeError('Pre-existing dataset requires review: '+name)
        except __import__('google.api_core.exceptions',fromlist=['NotFound']).NotFound:
            dataset=bigquery.Dataset(name);dataset.location=region
            dataset.labels={'application':'gst-easy-v4','purpose':'isolated-release'}
            dataset=bq.create_dataset(dataset);remember(name)
        grants=list(dataset.access_entries)
        grant=bigquery.AccessEntry('WRITER','userByEmail',account('api'))
        if grant not in grants:
            dataset.access_entries=grants+[grant];bq.update_dataset(dataset,['access_entries'])
        for original in bq.list_tables(project+'.gst_easy_v3_'+source):
            if original.table_type!='TABLE':
                raise RuntimeError('Non-table schema requires separate isolation review: '+original.table_id)
            original=bq.get_table(original.reference)
            target=bigquery.Table(name+'.'+original.table_id,schema=original.schema)
            target.time_partitioning=original.time_partitioning
            target.range_partitioning=original.range_partitioning
            target.clustering_fields=original.clustering_fields
            target.labels={'application':'gst-easy-v4'}
            bq.create_table(target,exists_ok=True)
            tables.append(target.table_id)
        print('Prepared V4 schema dataset',prefix+source,flush=True)
    for dataset,table,key,value in [('finance_analytics','auth_guard','id','identity'),('ops','gst_bill_lock','client_id','__guard__')]:
        target=f'{project}.{prefix}{dataset}.{table}'
        bq.query(f'INSERT INTO `{target}` ({key},touched_at) SELECT @value,CURRENT_TIMESTAMP() FROM (SELECT 1) WHERE NOT EXISTS(SELECT 1 FROM `{target}` WHERE {key}=@value)',
            job_config=bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('value','STRING',value)])).result()
    for suffix in ('documents','builds'):
        bucket=f'gs://{project}-gst-easy-v4-{suffix}'
        create(bucket,['storage','buckets','describe',bucket],['storage','buckets','create',bucket,
            '--project',project,'--location',region,'--uniform-bucket-level-access','--public-access-prevention'])
        kind,access=('api','roles/storage.objectAdmin') if suffix=='documents' else ('build','roles/storage.objectViewer')
        cloud('storage','buckets','add-iam-policy-binding',bucket,'--member=serviceAccount:'+account(kind),'--role='+access,'--format=none')
    create('gst-easy-v4-registry',['artifacts','repositories','describe','gst-easy-v4','--project',project,'--location',region],
        ['artifacts','repositories','create','gst-easy-v4','--project',project,'--location',region,'--repository-format=docker'])
    cloud('artifacts','repositories','add-iam-policy-binding','gst-easy-v4','--project',project,'--location',region,
        '--member=serviceAccount:'+account('build'),'--role=roles/artifactregistry.writer','--format=none')
    for kind in ('bills','auth'):
        queue='gst-easy-v4-'+kind
        create(queue,['tasks','queues','describe',queue,'--project',project,'--location',region],
            ['tasks','queues','create',queue,'--project',project,'--location',region,
             '--max-concurrent-dispatches=2' if kind=='bills' else '--max-concurrent-dispatches=1',
             '--max-dispatches-per-second=1','--max-attempts=5','--min-backoff=30s','--max-backoff=300s'])
        cloud('tasks','queues','add-iam-policy-binding',queue,'--project',project,'--location',region,
            '--member=serviceAccount:'+account('api'),'--role=roles/cloudtasks.enqueuer','--format=none')
    cloud('iam','service-accounts','add-iam-policy-binding',account('api'),'--project',project,
        '--member=serviceAccount:'+account('api'),'--role=roles/iam.serviceAccountUser','--format=none')
    source_env={v['name']:v for v in baseline['services']['gst-easy-v3-api']['spec']['template']['spec']['containers'][0]['env']}
    smtp=source_env['SMTP_PASSWORD']['valueFrom']['secretKeyRef']
    if not smtp['name'].startswith('gst-easy-v3-'):
        raise RuntimeError('Unreviewed SMTP secret source')
    for name in ('gst-easy-v4-session','gst-easy-v4-smtp-password'):
        create(name,['secrets','describe',name,'--project',project],
            ['secrets','create',name,'--project',project,'--replication-policy=automatic','--labels=application=gst-easy-v4'])
        versions=json.loads(cloud('secrets','versions','list',name,'--project',project,'--format=json'))
        if not versions:
            value=secrets.token_urlsafe(48) if name.endswith('session') else cloud('secrets','versions','access',smtp['key'],
                '--secret',smtp['name'],'--project',project)
            secret_input('secrets','versions','add',name,'--project',project,'--data-file=-',value=value)
            del value
        cloud('secrets','add-iam-policy-binding',name,'--project',project,'--member=serviceAccount:'+account('api'),
            '--role=roles/secretmanager.secretAccessor','--format=none')
    report={'project':project,'region':region,'dataset_prefix':prefix,'schemas_copied':len(tables),
        'customer_rows_copied':0,'financial_rows_copied':0,'serialization_guards_initialized':2}
    (ART/'resources.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=='__main__':
    main()
