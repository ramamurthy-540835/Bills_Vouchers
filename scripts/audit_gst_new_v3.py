"""Read-only preservation baseline. Never writes to cloud resources."""
import hashlib
import json
import subprocess
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path('artifacts/gst_new_v3')
PROJECT = 'aidirac-503309'


def cloud(*args):
    result = subprocess.run(['gcloud.cmd', *args, '--project', PROJECT, '--format=json'],
                            env={k:v for k,v in os.environ.items() if k.upper()!='PYTHONPATH'},
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def assert_preserved():
    baseline=json.loads((ROOT/'preservation-before.json').read_text())
    current={s['metadata']['name']:s for s in cloud('run','services','list','--platform=managed')}
    for record in baseline['services']:
        name=record['name']
        if name not in current or fingerprint(current[name])!=record['configuration_sha256']:
            raise RuntimeError('Existing service configuration changed: '+name)
        policy=cloud('run','services','get-iam-policy',name,'--region',record['region'])
        if fingerprint(policy)!=record['iam_sha256']:
            raise RuntimeError('Existing service IAM changed: '+name)
    (ROOT/'preservation-after.json').write_text(json.dumps({
        'observed_at':datetime.now(timezone.utc).isoformat(),
        'unchanged_services':[r['name'] for r in baseline['services']]},indent=2))
    return True


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT/'preservation-before.json'
    if path.exists():
        raise RuntimeError('Baseline already exists; never overwrite it.')
    services = cloud('run', 'services', 'list', '--platform=managed')
    if any(s['metadata']['name'] in {'gst-easy-v3-api', 'gst-easy-v3-web'} for s in services):
        raise RuntimeError('Requested V3 services already exist. Inspect before any deployment.')
    rows = []
    safe = {'GCP_PROJECT_ID','GCP_REGION','BIGQUERY_DATASET','GST_DATASET_PREFIX',
            'GCS_BUCKET_NAME','BACKEND_URL','AUTH_PUBLIC_URL','GST_BILLS_QUEUE',
            'AUTH_MAIL_QUEUE','GST_BILLS_ENABLED','DEMO_FALLBACK_ENABLED'}
    for service in services:
        name = service['metadata']['name']
        region = service['metadata']['labels']['cloud.googleapis.com/location']
        policy = cloud('run','services','get-iam-policy',name,'--region',region)
        container = service['spec']['template']['spec']['containers'][0]
        env = [{**{'name':e['name']},
                **({'value':e['value']} if e['name'] in safe and 'value' in e else {}),
                **({'secret_reference':e['valueFrom']} if 'valueFrom' in e else {})}
               for e in container.get('env',[])]
        rows.append({'name':name,'region':region,'url':service['status'].get('url'),
                     'revision':service['status'].get('latestReadyRevisionName'),
                     'image':container['image'],'traffic':service['status'].get('traffic'),
                     'service_account':service['spec']['template']['spec'].get('serviceAccountName'),
                     'environment':env,'configuration_sha256':fingerprint(service),
                     'iam_sha256':fingerprint(policy)})
    path.write_text(json.dumps({'observed_at':datetime.now(timezone.utc).isoformat(),
                                'services':rows},indent=2))
    print(f'Captured sanitized preservation baseline for {len(rows)} services; no cloud mutations.')


if __name__ == '__main__':
    main()
