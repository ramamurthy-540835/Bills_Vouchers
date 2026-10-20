"""Deploy immutable V3 build results; never target a pre-existing service."""
import argparse
import json
import subprocess
from prepare_gst_new_v3 import cloud, PROJECT, REGION, PREFIX, ART, account


def environment_file(name, values):
    # JSON is valid YAML. Files avoid Windows cmd.exe consuming gcloud's ^ delimiter.
    path = ART / (name + '-environment.json')
    path.write_text(json.dumps(values, indent=2), encoding='utf-8')
    return str(path)


def api_environment(source):
    return {'APP_ENV':'production','GCP_PROJECT_ID':PROJECT,'GCP_REGION':REGION,'BIGQUERY_DATASET':PREFIX+'finance_analytics',
            'GST_DATASET_PREFIX':PREFIX,'GCS_BUCKET_NAME':PROJECT+'-gst-easy-v3-documents','GST_BILLS_ENABLED':'true',
            'MEDALLION_ENABLED':'true','DEMO_FALLBACK':'false','DEMO_OPERATOR_IDENTITY_ENABLED':'false',
            'GEMINI_ENABLED':'true','GEMINI_MODEL':'gemini-2.5-flash','PLATFORM_ADMIN_EMAILS':'','REQUIRE_OTP':'false',
            'GST_BILLS_QUEUE':f'projects/{PROJECT}/locations/{REGION}/queues/gst-easy-v3-bills','GST_BILLS_WORKER_ACCOUNT':account('api'),
            'RELEASE_REVISION':source,
            'AUTH_MAIL_QUEUE':f'projects/{PROJECT}/locations/{REGION}/queues/gst-easy-v3-auth',
            'AUTH_WORKER_ACCOUNT':account('api'),
            'SMTP_HOST':'smtppro.zoho.in','SMTP_PORT':'587',
            'SMTP_USERNAME':'ai@aidirac.com','SMTP_SENDER':'ai@aidirac.com'}


def snapshot_unchanged():
    from audit_gst_new_v3 import assert_preserved
    return assert_preserved()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--api-build',required=True);parser.add_argument('--web-build',required=True);args=parser.parse_args()
    source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],text=True).strip():raise RuntimeError('Review and commit source before deployment')
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/GST_NEW_V3'],text=True).split()
    if not remote or remote[0]!=source:raise RuntimeError('Remote V3 branch does not match the build source')
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GST_NEW_V3':raise RuntimeError('Wrong release branch')
    services=json.loads(cloud('run','services','list','--project',PROJECT,'--platform=managed','--format=json'))
    if any(s['metadata']['name'] in {'gst-easy-v3-api','gst-easy-v3-web'} for s in services):raise RuntimeError('V3 already exists; inspect rather than overwriting')
    images={}
    for kind,build_id in [('api',args.api_build),('web',args.web_build)]:
        build=json.loads(cloud('builds','describe',build_id,'--project',PROJECT,'--format=json'))
        if build['status']!='SUCCESS' or build.get('substitutions',{}).get('_REVISION')!=source:raise RuntimeError('Build is unsuccessful or not current reviewed source')
        expected=f'{REGION}-docker.pkg.dev/{PROJECT}/gst-easy-v3/{kind}'
        matches=[i for i in build['results']['images'] if i['name']==expected+':'+source]
        if len(matches)!=1:raise RuntimeError('Unexpected V3 image')
        images[kind]=expected+'@'+matches[0]['digest']
    snapshot_unchanged()
    common=['--project',PROJECT,'--region',REGION,'--platform=managed','--quiet','--max-instances=2','--min-instances=0']
    values=api_environment(source)
    cloud('run','deploy','gst-easy-v3-api','--image',images['api'],'--service-account',account('api'),'--no-allow-unauthenticated',
          '--port=8000','--memory=1Gi','--cpu=1','--concurrency=4','--timeout=1800',
          '--env-vars-file',environment_file('api',values),'--set-secrets=APP_SECRET_KEY=gst-easy-v3-session:1,SMTP_PASSWORD=gst-easy-v3-smtp-password:1',*common)
    api=cloud('run','services','describe','gst-easy-v3-api','--project',PROJECT,'--region',REGION,'--format=value(status.url)')
    for kind in ['api','web']:
        cloud('run','services','add-iam-policy-binding','gst-easy-v3-api','--project',PROJECT,'--region',REGION,'--member=serviceAccount:'+account(kind),'--role=roles/run.invoker')
    cloud('run','deploy','gst-easy-v3-web','--image',images['web'],'--service-account',account('web'),'--allow-unauthenticated',
          '--port=3000','--memory=512Mi','--cpu=1','--concurrency=20','--timeout=1800',
          '--env-vars-file',environment_file('web',{'BACKEND_URL':api,'BACKEND_ID_TOKEN_AUDIENCE':api,'RELEASE_REVISION':source}),*common)
    web=cloud('run','services','describe','gst-easy-v3-web','--project',PROJECT,'--region',REGION,'--format=value(status.url)')
    values.update(GST_BILLS_WORKER_URL=api,GST_BILLS_WORKER_AUDIENCE=api,ALLOWED_ORIGINS=web,AUTH_PUBLIC_URL=web,AUTH_WORKER_URL=api,AUTH_WORKER_AUDIENCE=api)
    cloud('run','services','update','gst-easy-v3-api','--project',PROJECT,'--region',REGION,
          '--env-vars-file',environment_file('api',values),'--quiet')
    report={'source_commit':source,'api_build':args.api_build,'web_build':args.web_build,'images':images,'frontend_url':web,'backend_url':api,
            'existing_services_unchanged':snapshot_unchanged(),'public_access_policy':'public frontend login; private API IAM; application authentication and worker OIDC retained','financial_rows_seeded':0}
    (ART/'deployment.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
