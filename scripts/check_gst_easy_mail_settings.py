"""Report configuration presence/length only; never display secret values."""
import json
from deploy_v3 import PROJECT, REGION, gcloud

runtime = json.loads(gcloud('run', 'services', 'describe', 'bills-voucher',
                           '--project', PROJECT, '--region', REGION, '--format=json'))
env = {item['name']: item for item in runtime['spec']['template']['spec']['containers'][0]['env']}
for key in ('AUTH_MAIL_QUEUE', 'AUTH_WORKER_URL', 'AUTH_WORKER_ACCOUNT', 'APP_SECRET_KEY'):
    item = env.get(key, {})
    ref = item.get('valueFrom', {}).get('secretKeyRef')
    if ref:
        value = gcloud('secrets', 'versions', 'access', ref['key'], '--secret', ref['name'], '--project', PROJECT).rstrip('\r\n')
    else:
        value = item.get('value', '')
    print(json.dumps({'key': key, 'present': bool(value), 'length': len(value), 'secret_reference': ref}))
    value = None
