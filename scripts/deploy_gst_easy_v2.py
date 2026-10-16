"""Deploy immutable V2 build results; never target a pre-existing service."""
import argparse
import json
import subprocess
from pathlib import Path
from prepare_gst_easy_v2 import cloud, PROJECT, REGION, PREFIX, ART, account


def snapshot_unchanged():
    before=json.loads((ART/'services-before.json').read_text(encoding='utf-8'))
    after=json.loads(cloud('run','services','list','--project',PROJECT,'--platform=managed','--format=json'))
    lookup={s['metadata']['name']:s for s in after}
    for original in before:
        name=original['metadata']['name']
        if lookup.get(name)!=original:raise RuntimeError('Existing service differs from baseline: '+name)
    policies=json.loads((ART/'service-iam-before.json').read_text(encoding='utf-8'))
    for original in before:
        name=original['metadata']['name'];region=original['metadata']['labels']['cloud.googleapis.com/location']
        current=json.loads(cloud('run','services','get-iam-policy',name,'--project',PROJECT,'--region',region,'--format=json'))
        if current!=policies[name]:raise RuntimeError('Existing service IAM changed: '+name)
    (ART/'services-after.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
    return True


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--api-build',required=True);parser.add_argument('--web-build',required=True);args=parser.parse_args()
    source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GST-EASY-V2':raise RuntimeError('Wrong release branch')
    services=json.loads(cloud('run','services','list','--project',PROJECT,'--platform=managed','--format=json'))
    if any(s['metadata']['name'] in {'gst-easy-v2-api','gst-easy-v2-web'} for s in services):raise RuntimeError('V2 already exists; inspect rather than overwriting')
    images={}
    for kind,build_id in [('api',args.api_build),('web',args.web_build)]:
        build=json.loads(cloud('builds','describe',build_id,'--project',PROJECT,'--format=json'))
        if build['status']!='SUCCESS' or build.get('substitutions',{}).get('_REVISION')!=source:raise RuntimeError('Build is unsuccessful or not current reviewed source')
        expected=f'{REGION}-docker.pkg.dev/{PROJECT}/gst-easy-v2/{kind}'
        matches=[i for i in build['results']['images'] if i['name']==expected+':'+source]
        if len(matches)!=1:raise RuntimeError('Unexpected V2 image')
        images[kind]=expected+'@'+matches[0]['digest']
    snapshot_unchanged()
    common=['--project',PROJECT,'--region',REGION,'--platform=managed','--quiet','--max-instances=2','--min-instances=0']
    values={'APP_ENV':'production','GCP_PROJECT_ID':PROJECT,'GCP_REGION':REGION,'BIGQUERY_DATASET':PREFIX+'finance_analytics',
            'GST_DATASET_PREFIX':PREFIX,'GCS_BUCKET_NAME':PROJECT+'-gst-easy-v2-documents','GST_BILLS_ENABLED':'true',
            'MEDALLION_ENABLED':'true','DEMO_FALLBACK':'false','DEMO_OPERATOR_IDENTITY_ENABLED':'true',
            'GEMINI_ENABLED':'true','GEMINI_MODEL':'gemini-2.5-flash','PLATFORM_ADMIN_EMAILS':'','REQUIRE_OTP':'false',
            'GST_BILLS_QUEUE':f'projects/{PROJECT}/locations/{REGION}/queues/gst-easy-v2-bills','GST_BILLS_WORKER_ACCOUNT':account('api'),
            'RELEASE_REVISION':source}
    cloud('run','deploy','gst-easy-v2-api','--image',images['api'],'--service-account',account('api'),'--no-allow-unauthenticated',
          '--port=8000','--memory=1Gi','--cpu=1','--concurrency=4','--timeout=1800',
          '--set-env-vars','^~^'+'~'.join(k+'='+v for k,v in values.items()),'--set-secrets=APP_SECRET_KEY=gst-easy-v2-session:1',*common)
    api=cloud('run','services','describe','gst-easy-v2-api','--project',PROJECT,'--region',REGION,'--format=value(status.url)')
    for kind in ['api','web']:
        cloud('run','services','add-iam-policy-binding','gst-easy-v2-api','--project',PROJECT,'--region',REGION,'--member=serviceAccount:'+account(kind),'--role=roles/run.invoker')
    cloud('run','deploy','gst-easy-v2-web','--image',images['web'],'--service-account',account('web'),'--allow-unauthenticated',
          '--port=3000','--memory=512Mi','--cpu=1','--concurrency=20','--timeout=1800',
          '--set-env-vars','^~^BACKEND_URL='+api+'~BACKEND_ID_TOKEN_AUDIENCE='+api+'~RELEASE_REVISION='+source,*common)
    web=cloud('run','services','describe','gst-easy-v2-web','--project',PROJECT,'--region',REGION,'--format=value(status.url)')
    cloud('run','services','update','gst-easy-v2-api','--project',PROJECT,'--region',REGION,'--update-env-vars',
          '^~^GST_BILLS_WORKER_URL='+api+'~GST_BILLS_WORKER_AUDIENCE='+api+'~ALLOWED_ORIGINS='+web+'~AUTH_PUBLIC_URL='+web,'--quiet')
    report={'source_commit':source,'api_build':args.api_build,'web_build':args.web_build,'images':images,'frontend_url':web,'backend_url':api,
            'existing_services_unchanged':snapshot_unchanged(),'public_access_policy':'public frontend login; private API IAM; application authentication and worker OIDC retained','financial_rows_seeded':0}
    (ART/'deployment.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
