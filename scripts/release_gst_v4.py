"""Build exact GSTv4 source; deploy only independently owned V4 services."""
import argparse
import json
from pathlib import Path
import subprocess

from audit_gst_v4 import ART, cloud


def write(name,value):
    (ART/name).write_text(json.dumps(value,indent=2),encoding='utf-8')


def branch():
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GSTv4':
        raise RuntimeError('Only GSTv4 is authorized')


def source():
    branch()
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/GSTv4'],text=True).split()
    if not remote or remote[0]!=sha:
        raise RuntimeError('GSTv4 remote does not match the reviewed local commit')
    if subprocess.check_output(['git','status','--porcelain'],text=True).strip():
        raise RuntimeError('Review and commit all V4 work before building')
    return sha


def service(name,project,region):
    if name not in {'gst-easy-v4-api','gst-easy-v4-web'}:
        raise RuntimeError('Protected service target')
    return json.loads(cloud('run','services','describe',name,'--project',project,'--region',region,'--format=json'))


def environment(baseline,sha):
    project,region=baseline['project'],baseline['region']
    old={v['name']:v.get('value','') for v in baseline['services']['gst-easy-v3-api']['spec']['template']['spec']['containers'][0]['env']}
    demo_ids=[]
    for name in ('naturelabs','naturelabs1'):
        path=ART/(name+'-provisioning.json')
        if path.exists():
            demo=json.loads(path.read_text())
            if demo.get('provenance')!='SYNTHETIC_TEST_ONLY' or not all(b['is_test'] and not b['gstin_verified'] for b in demo['businesses']):
                raise RuntimeError('Unreviewed demo identity metadata')
            demo_ids.extend(b['client_id'] for b in demo['businesses'])
    return {'APP_ENV':'production','DEPLOYMENT_GENERATION':'v4','GCP_PROJECT_ID':project,'GCP_REGION':region,
        'BIGQUERY_DATASET':'gst_easy_v4_finance_analytics','GST_DATASET_PREFIX':'gst_easy_v4_',
        'GCS_BUCKET_NAME':project+'-gst-easy-v4-documents','MEDALLION_ENABLED':'true','GST_BILLS_ENABLED':'true',
        'GST_BILLS_QUEUE':f'projects/{project}/locations/{region}/queues/gst-easy-v4-bills',
        'AUTH_MAIL_QUEUE':f'projects/{project}/locations/{region}/queues/gst-easy-v4-auth',
        'GST_BILLS_WORKER_ACCOUNT':f'gst-easy-v4-api@{project}.iam.gserviceaccount.com',
        'AUTH_WORKER_ACCOUNT':f'gst-easy-v4-api@{project}.iam.gserviceaccount.com',
        'GEMINI_ENABLED':'true','GEMINI_MODEL':old['GEMINI_MODEL'],'GEMINI_LOCATION':old['GEMINI_LOCATION'],
        'GEMINI_CUSTOMER_EXTRACTION_GLOBAL_ENABLED':'true','GEMINI_ALLOWED_CLIENT_IDS':','.join(demo_ids),
        'DEMO_OPERATOR_IDENTITY_ENABLED':'true' if demo_ids else 'false','DEMO_FALLBACK':'false','PLATFORM_ADMIN_EMAILS':'',
        'REQUIRE_OTP':'false','BOOTSTRAP_ADMIN_EMAIL':'','BOOTSTRAP_ADMIN_PASSWORD':'','RED_TAXI_CLIENT_BOOTSTRAP':'',
        'SMTP_HOST':old['SMTP_HOST'],'SMTP_PORT':old['SMTP_PORT'],
        'SMTP_USERNAME':old['SMTP_USERNAME'],'SMTP_SENDER':old['SMTP_SENDER'],
        'PERFORMANCE_METRICS_ENABLED':'true','RELEASE_REVISION':sha}


def gate():
    import xml.etree.ElementTree as ET
    suites=ET.parse(ART/'backend-final.xml').getroot()
    if any(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites.iter('testsuite')):
        raise RuntimeError('Backend regressions are unresolved')
    ui=json.loads((ART/'frontend-tests.json').read_text())
    if ui['stats']['unexpected'] or ui['stats']['expected']<100:
        raise RuntimeError('Full browser acceptance has not passed')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['build','deploy','pair','publish'])
    p.add_argument('--build')
    p.add_argument('--kind',choices=['api','web'])
    args=p.parse_args();branch()
    baseline=json.loads((ART/'protected-before.json').read_text())
    project,region=baseline['project'],baseline['region']
    if args.action=='build':
        sha=source();gate()
        archive=ART/'v4-source.tar.gz'
        subprocess.check_call(['git','archive','--format=tar.gz','--output',str(archive),sha])
        result=json.loads(cloud('builds','submit',str(archive),'--project',project,'--config','cloudbuild-gst-easy-v4.yaml',
            '--substitutions',f'_REVISION={sha},_REGION={region}','--gcs-source-staging-dir',f'gs://{project}-gst-easy-v4-builds/source',
            '--async','--quiet','--format=json'))
        write('build-request.json',{'commit':sha,'build_id':result['id']})
        print(json.dumps({'commit':sha,'build_id':result['id'],'status':result.get('status')}));return
    if args.action=='deploy':
        sha=source();gate()
        build=json.loads(cloud('builds','describe',args.build,'--project',project,'--format=json'))
        if build['status']!='SUCCESS' or build['substitutions']['_REVISION']!=sha:
            raise RuntimeError('Build/source verification failed')
        kind=args.kind
        if kind not in {'api','web'}:raise RuntimeError('Choose a V4 service')
        name='gst-easy-v4-'+kind
        inventory=json.loads(cloud('run','services','list','--project',project,'--format=json'))
        if any(s['metadata']['name']==name for s in inventory):
            raise RuntimeError('V4 service already exists; inspect rather than overwriting')
        image=f'{region}-docker.pkg.dev/{project}/gst-easy-v4/{kind}'
        match=next(i for i in build['results']['images'] if i['name']==image+':'+sha)
        image+='@'+match['digest']
        if kind=='api':env=environment(baseline,sha)
        else:
            api=json.loads((ART/'api-service.json').read_text())['url']
            env={'BACKEND_URL':api,'BACKEND_ID_TOKEN_AUDIENCE':api,'RELEASE_REVISION':sha}
        flags=ART/(kind+'-deploy-flags.json')
        flags.write_text(json.dumps({'--set-env-vars':env}))
        common=['--project',project,'--region',region,'--service-account',f'{name}@{project}.iam.gserviceaccount.com',
            '--image',image,'--no-allow-unauthenticated','--labels=application=gst-easy-v4',
            '--min-instances=0','--max-instances=3','--timeout=1800','--cpu=1','--quiet','--flags-file',str(flags)]
        if kind=='api':common.extend(['--port=8000','--memory=1Gi','--concurrency=8',
            '--set-secrets=APP_SECRET_KEY=gst-easy-v4-session:1,SMTP_PASSWORD=gst-easy-v4-smtp-password:1'])
        else:common.extend(['--port=3000','--memory=512Mi','--concurrency=20'])
        cloud('run','deploy',name,*common)
        result=service(name,project,region)
        record={'commit':sha,'build_id':args.build,'uid':result['metadata']['uid'],'url':result['status']['url'],
            'revision':result['status']['latestReadyRevisionName'],'image':image}
        write(kind+'-service.json',record)
        if kind=='api':
            for identity in ('api','web'):
                cloud('run','services','add-iam-policy-binding',name,'--project',project,'--region',region,
                    '--member=serviceAccount:'+f'gst-easy-v4-{identity}@{project}.iam.gserviceaccount.com',
                    '--role=roles/run.invoker','--format=none')
        print(json.dumps(record));return
    api=json.loads((ART/'api-service.json').read_text());web=json.loads((ART/'web-service.json').read_text())
    for kind,record in [('api',api),('web',web)]:
        current=service('gst-easy-v4-'+kind,project,region)
        if current['metadata']['uid']!=record['uid'] or current['metadata'].get('labels',{}).get('application')!='gst-easy-v4':
            raise RuntimeError('V4 service ownership changed')
    if args.action=='pair':
        values=environment(baseline,api['commit'])
        values.update(GST_BILLS_WORKER_URL=api['url'],GST_BILLS_WORKER_AUDIENCE=api['url'],
            AUTH_WORKER_URL=api['url'],AUTH_WORKER_AUDIENCE=api['url'],AUTH_PUBLIC_URL=web['url'],ALLOWED_ORIGINS=web['url'])
        path=ART/'api-paired-env.json';path.write_text(json.dumps(values))
        cloud('run','services','update','gst-easy-v4-api','--project',project,'--region',region,'--env-vars-file',str(path),'--quiet')
        api['revision']=service('gst-easy-v4-api',project,region)['status']['latestReadyRevisionName']
        write('api-service.json',api);print(json.dumps({'paired':True,'api':api['url'],'web':web['url']}))
    else:
        gate()
        # Only the new frontend becomes a public login surface; API stays private.
        cloud('run','services','add-iam-policy-binding','gst-easy-v4-web','--project',project,'--region',region,
            '--member=allUsers','--role=roles/run.invoker','--format=none')
        write('access-policy.json',{'public_frontend_login':True,'api_iam_protected':True,'application_authentication_required':True})
        print(json.dumps({'url':web['url'],'public_login':True,'api_private':True}))


if __name__=='__main__':main()
