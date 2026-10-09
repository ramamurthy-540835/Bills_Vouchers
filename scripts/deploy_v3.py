"""Deploy tested immutable images to v3 tags, asserting all existing traffic stays fixed."""
import argparse
import json
import os
import subprocess
from pathlib import Path

PROJECT='aidirac-503309'
REGION='asia-south1'
SDK=Path(os.environ['LOCALAPPDATA'])/'Google/Cloud SDK/google-cloud-sdk'
ENV={k:v for k,v in os.environ.items() if k.upper()!='PYTHONPATH'}
WEB='https://preview-v3---bills-voucher-web-foovqasysa-el.a.run.app'
API='https://api-preview-v3---bills-voucher-foovqasysa-el.a.run.app'


def gcloud(*args):
    return subprocess.check_output([str(SDK/'platform/bundledpython/python.exe'),str(SDK/'lib/gcloud.py'),*args],env=ENV,text=True)


def state(service):
    return json.loads(gcloud('run','services','describe',service,'--project',PROJECT,'--region',REGION,'--format=json(status.traffic)'))['status']['traffic']


def unchanged(before,after,new_tag):
    original={(r.get('tag','production'),r['revisionName'],r.get('percent',0)) for r in before if r.get('tag')!=new_tag}
    current={(r.get('tag','production'),r['revisionName'],r.get('percent',0)) for r in after if r.get('tag')!=new_tag}
    assert original==current, 'Existing traffic changed: inspect Cloud Run before any further action.'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--api-build',required=True);parser.add_argument('--web-build',required=True)
    args=parser.parse_args()
    images={}
    for build_id in {args.api_build,args.web_build}:
        build=json.loads(gcloud('builds','describe',build_id,'--project',PROJECT,'--format=json(status,results.images)'))
        assert build['status']=='SUCCESS', f'Build {build_id} is not successful.'
        for result in build['results']['images']:
            base=result['name'].rsplit(':',1)[0]
            if ('bills-voucher-web' in base and build_id==args.web_build) or (base.endswith('/bills-voucher') and build_id==args.api_build):
                images['web' if 'bills-voucher-web' in base else 'api']=base+'@'+result['digest']
    api_before,web_before=state('bills-voucher'),state('bills-voucher-web')
    path=Path('artifacts/v3');path.mkdir(parents=True,exist_ok=True)
    (path/'traffic-before.json').write_text(json.dumps({'api':api_before,'web':web_before},indent=2))
    common=['--project',PROJECT,'--region',REGION,'--no-traffic','--quiet']
    values={'GST_BILLS_ENABLED':'true','DEMO_FALLBACK':'false','MEDALLION_ENABLED':'true','APP_ENV':'production',
        'GCP_PROJECT_ID':PROJECT,'GCP_REGION':REGION,'BIGQUERY_DATASET':'finance_analytics',
        'GCS_BUCKET_NAME':'aidirac-503309-bills-voucher-documents','GEMINI_ENABLED':'true','GEMINI_MODEL':'gemini-2.5-flash',
        'ALLOWED_ORIGINS':WEB,'REQUIRE_OTP':'false','BOOTSTRAP_ADMIN_PASSWORD':''}
    values.update(GST_BILLS_QUEUE=f'projects/{PROJECT}/locations/{REGION}/queues/bills-v3',
        GST_BILLS_WORKER_URL=API,GST_BILLS_WORKER_AUDIENCE='https://bills-voucher-foovqasysa-el.a.run.app',
        GST_BILLS_WORKER_ACCOUNT='624683933018-compute@developer.gserviceaccount.com')
    settings='^~^'+'~'.join(k+'='+v for k,v in values.items())
    print(gcloud('run','deploy','bills-voucher','--image',images['api'],'--tag','api-preview-v3',
        '--update-env-vars',settings,'--remove-secrets','RED_TAXI_CLIENT_BOOTSTRAP','--timeout','1800','--memory','1Gi','--concurrency','4',*common),flush=True)
    unchanged(api_before,state('bills-voucher'),'api-preview-v3')
    print(gcloud('run','deploy','bills-voucher-web','--image',images['web'],'--tag','preview-v3',
        '--update-env-vars','BACKEND_URL='+API,'--remove-secrets','RED_TAXI_CLIENT_BOOTSTRAP','--timeout','1800',*common),flush=True)
    api_after,web_after=state('bills-voucher'),state('bills-voucher-web')
    unchanged(api_before,api_after,'api-preview-v3');unchanged(web_before,web_after,'preview-v3')
    (path/'deployment.json').write_text(json.dumps({'url':WEB,'api_url':API,'images':images,'api':api_after,'web':web_after,'existing_traffic_unchanged':True},indent=2))
    print(WEB,flush=True)


if __name__=='__main__':main()
