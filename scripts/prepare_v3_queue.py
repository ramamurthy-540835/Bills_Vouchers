"""Create an isolated durable worker queue and minimum missing enqueue permissions."""
import json
from deploy_v3 import gcloud, PROJECT, REGION

ACCOUNT='624683933018-compute@developer.gserviceaccount.com'
queues=json.loads(gcloud('tasks','queues','list','--project',PROJECT,'--location',REGION,'--format=json(name)'))
if not any(q['name'].endswith('/bills-v3') for q in queues):
    print(gcloud('tasks','queues','create','bills-v3','--project',PROJECT,'--location',REGION,
        '--max-concurrent-dispatches','1','--max-dispatches-per-second','1','--max-attempts','10',
        '--min-backoff','10s','--max-backoff','300s'),flush=True)
print(gcloud('projects','add-iam-policy-binding',PROJECT,'--member','serviceAccount:'+ACCOUNT,
    '--role','roles/cloudtasks.enqueuer','--condition=None','--format=value(etag)'),flush=True)
print(gcloud('iam','service-accounts','add-iam-policy-binding',ACCOUNT,'--project',PROJECT,
    '--member','serviceAccount:'+ACCOUNT,'--role','roles/iam.serviceAccountUser','--format=value(etag)'),flush=True)
print('V3 queue ready; existing traffic and queues unchanged.')
