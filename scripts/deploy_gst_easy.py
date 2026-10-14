"""Deploy successful immutable images to new tags without changing existing traffic."""
import argparse
import json
import subprocess
from pathlib import Path

from deploy_v3 import gcloud,PROJECT,REGION,state,unchanged

TAG='gst-easy'
WEB='https://gst-easy---bills-voucher-web-foovqasysa-el.a.run.app'
API='https://gst-easy---bills-voucher-foovqasysa-el.a.run.app'
AUDIENCE='https://bills-voucher-foovqasysa-el.a.run.app'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--api-build',required=True);parser.add_argument('--web-build',required=True)
    args=parser.parse_args()
    images={}
    for kind,build_id in [('api',args.api_build),('web',args.web_build)]:
        build=json.loads(gcloud('builds','describe',build_id,'--project',PROJECT,'--format=json(status,results.images)'))
        if build['status']!='SUCCESS':raise RuntimeError('Build is not successful: '+build_id)
        expected='/bills-voucher-web' if kind=='web' else '/bills-voucher'
        matches=[item for item in build['results']['images'] if item['name'].rsplit(':',1)[0].endswith(expected)]
        if len(matches)!=1:raise RuntimeError('Unexpected build image result')
        images[kind]=matches[0]['name'].rsplit(':',1)[0]+'@'+matches[0]['digest']
    api_before,web_before=state('bills-voucher'),state('bills-voucher-web')
    path=Path('artifacts/gst_easy');path.mkdir(parents=True,exist_ok=True)
    (path/'traffic-before.json').write_text(json.dumps({'api':api_before,'web':web_before},indent=2))
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    runtime=json.loads(gcloud('run','services','describe','bills-voucher','--project',PROJECT,'--region',REGION,
                             '--format=json(spec.template.spec.serviceAccountName,spec.template.spec.containers)'))
    account=runtime['spec']['template']['spec']['serviceAccountName']
    env=runtime['spec']['template']['spec']['containers'][0].get('env',[])
    readiness={key:any(item['name']==key and (item.get('value') or item.get('valueFrom')) for item in env)
               for key in ('SMTP_HOST','SMTP_USERNAME','SMTP_PASSWORD','SMTP_SENDER','TWILIO_VERIFY_SERVICE_SID','TWILIO_API_KEY','TWILIO_API_SECRET')}
    for queue in ('gst-easy-bills','gst-easy-auth'):
        existing=json.loads(gcloud('tasks','queues','list','--project',PROJECT,'--location',REGION,'--format=json(name)'))
        if not any(row['name'].endswith('/'+queue) for row in existing):
            gcloud('tasks','queues','create',queue,'--project',PROJECT,'--location',REGION,
                   '--max-concurrent-dispatches','2','--max-dispatches-per-second','2','--max-attempts','10','--quiet')
    values={'GST_BILLS_ENABLED':'true','DEMO_FALLBACK':'false','MEDALLION_ENABLED':'true','APP_ENV':'production',
            'GCP_PROJECT_ID':PROJECT,'GCP_REGION':REGION,'BIGQUERY_DATASET':'finance_analytics',
            'GCS_BUCKET_NAME':'aidirac-503309-bills-voucher-documents','GEMINI_ENABLED':'true','GEMINI_MODEL':'gemini-2.5-flash',
            'ALLOWED_ORIGINS':WEB,'BOOTSTRAP_ADMIN_PASSWORD':'','AUTH_PUBLIC_URL':WEB,
            'GST_BILLS_QUEUE':f'projects/{PROJECT}/locations/{REGION}/queues/gst-easy-bills',
            'GST_BILLS_WORKER_URL':API,'GST_BILLS_WORKER_AUDIENCE':AUDIENCE,'GST_BILLS_WORKER_ACCOUNT':account,
            'AUTH_MAIL_QUEUE':f'projects/{PROJECT}/locations/{REGION}/queues/gst-easy-auth',
            'AUTH_WORKER_URL':API,'AUTH_WORKER_AUDIENCE':AUDIENCE,'AUTH_WORKER_ACCOUNT':account,'RELEASE_REVISION':revision}
    common=['--project',PROJECT,'--region',REGION,'--no-traffic','--tag',TAG,'--quiet']
    gcloud('run','deploy','bills-voucher','--image',images['api'],'--update-env-vars','^~^'+'~'.join(k+'='+v for k,v in values.items()),
           '--remove-secrets','RED_TAXI_CLIENT_BOOTSTRAP','--timeout','1800','--memory','1Gi','--concurrency','4',*common)
    unchanged(api_before,state('bills-voucher'),TAG)
    gcloud('run','deploy','bills-voucher-web','--image',images['web'],'--update-env-vars','BACKEND_URL='+API,
           '--remove-secrets','RED_TAXI_CLIENT_BOOTSTRAP','--timeout','1800',*common)
    api_after,web_after=state('bills-voucher'),state('bills-voucher-web')
    unchanged(api_before,api_after,TAG);unchanged(web_before,web_after,TAG)
    report={'source_revision':revision,'url':WEB,'api_url':API,'images':images,'api':api_after,'web':web_after,
            'existing_traffic_unchanged':True,'provider_configuration_present':readiness,'service_account':account}
    (path/'deployment.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
