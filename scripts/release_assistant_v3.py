"""Guarded V3 assistant release operations. Never deploy to V2/older services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

PROJECT='aidirac-503309'
REGION='asia-south1'
ART=Path('artifacts/assistant-release-2026-10-29')
ART.mkdir(parents=True,exist_ok=True)
SDK=Path(os.environ['LOCALAPPDATA'])/'Google/Cloud SDK/google-cloud-sdk'
ENV={k:v for k,v in os.environ.items() if k.upper()!='PYTHONPATH'}
PROTECTED=['bills-voucher','bills-voucher-web','gst-easy-v2-api','gst-easy-v2-web']
V3=['gst-easy-v3-api','gst-easy-v3-web']


def cloud(*args):
    return subprocess.check_output([str(SDK/'platform/bundledpython/python.exe'),str(SDK/'lib/gcloud.py'),*args],env=ENV,text=True).strip()


def service(name):
    if name not in PROTECTED+V3:
        raise ValueError('Unexpected service')
    return json.loads(cloud('run','services','describe',name,'--project',PROJECT,'--region',REGION,'--format=json'))


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def sanitize(resource):
    resource=json.loads(json.dumps(resource))
    for container in resource.get('spec',{}).get('template',{}).get('spec',{}).get('containers',[]):
        for item in container.get('env',[]):
            if 'value' in item and any(word in item['name'] for word in ('PASSWORD','SECRET','API_KEY','TOKEN','CREDENTIAL')):
                item['value']='SHA256:'+digest(item['value'])
    return resource


def snapshot():
    resources={name:service(name) for name in PROTECTED+V3}
    policies={name:json.loads(cloud('run','services','get-iam-policy',name,'--project',PROJECT,'--region',REGION,'--format=json')) for name in PROTECTED+V3}
    return {'services':{k:sanitize(v) for k,v in resources.items()},'iam':policies}


def verify():
    before=json.loads((ART/'before.json').read_text())
    after=snapshot()
    checks={}
    for name in PROTECTED:
        checks[name]=all(before['services'][name].get(key)==after['services'][name].get(key) for key in ('spec',)) and before['services'][name]['status']['traffic']==after['services'][name]['status']['traffic'] and before['iam'][name]==after['iam'][name]
    for name in V3:
        checks[name+'-iam']=before['iam'][name]==after['iam'][name]
    (ART/'after.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
    (ART/'preservation.json').write_text(json.dumps(checks,indent=2))
    if not all(checks.values()):raise RuntimeError('Preservation mismatch: inspect saved evidence before proceeding')
    print(json.dumps(checks))


def inspect():
    if (ART/'before.json').exists():
        raise RuntimeError('Snapshot already exists; preserve it')
    state=snapshot()
    (ART/'before.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    for name in V3:
        value=state['services'][name]
        container=value['spec']['template']['spec']['containers'][0]
        safe={item['name']:item.get('value','Secret Manager reference') for item in container.get('env',[]) if item['name'] in {'GCP_PROJECT_ID','BIGQUERY_DATASET','GST_DATASET_PREFIX','BACKEND_URL','BACKEND_ID_TOKEN_AUDIENCE','RELEASE_REVISION','GEMINI_MODEL','GEMINI_LOCATION','GEMINI_ENABLED','GCS_BUCKET_NAME'}}
        print(json.dumps({'name':name,'url':value['status']['url'],'traffic':value['status']['traffic'],'settings':safe}))


def migrate():
    from google.cloud import bigquery
    from google.oauth2.credentials import Credentials
    state=service('gst-easy-v3-api')
    env={v['name']:v.get('value','') for v in state['spec']['template']['spec']['containers'][0]['env']}
    if env.get('GCP_PROJECT_ID')!=PROJECT or env.get('BIGQUERY_DATASET')!='gst_easy_v3_finance_analytics':
        raise RuntimeError('Unexpected V3 database target')
    # Use the already authorized gcloud identity; do not persist a key or ADC file.
    client=bigquery.Client(project=PROJECT,credentials=Credentials(token=cloud('auth','print-access-token')))
    dataset=client.get_dataset(PROJECT+'.'+env['BIGQUERY_DATASET'])
    if dataset.location.lower()!='asia-south1':raise RuntimeError('Unexpected dataset location')
    table=PROJECT+'.'+env['BIGQUERY_DATASET']+'.assistant_history'
    sql=Path('migrations/034_private_assistant_history.sql').read_text().replace('PROJECT_ID.DATASET',PROJECT+'.'+env['BIGQUERY_DATASET'])
    job=client.query(sql,location=dataset.location);job.result(timeout=120)
    created=client.get_table(table)
    expected=['turn_id','user_id','client_id','period','conversation_id','question','response_json','created_at']
    if [f.name for f in created.schema]!=expected or created.time_partitioning.expiration_ms!=90*86400000:
        raise RuntimeError('Unexpected history schema/retention')
    report={'table':table,'location':dataset.location,'job_id':job.job_id,'schema':[{'name':f.name,'type':f.field_type,'mode':f.mode} for f in created.schema],
            'retention_days':90,'rows_seeded':0,'additive':True}
    (ART/'migration.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


def deploy(kind,build_id,commit,tag):
    if kind not in {'api','web'}:raise ValueError('Wrong V3 target')
    name='gst-easy-v3-'+kind
    before=json.loads((ART/'before.json').read_text())['services'][name]
    build=json.loads(cloud('builds','describe',build_id,'--project',PROJECT,'--format=json'))
    if build['status']!='SUCCESS' or build.get('substitutions',{}).get('_REVISION')!=commit:raise RuntimeError('Unverified build source/status')
    image=f'{REGION}-docker.pkg.dev/{PROJECT}/gst-easy-v3/{kind}'
    matches=[v for v in build['results']['images'] if v['name']==image+':'+commit]
    if len(matches)!=1:raise RuntimeError('Unexpected image')
    immutable=image+'@'+matches[0]['digest']
    updates={'RELEASE_REVISION':commit}
    if kind=='api':
        current={v['name']:v.get('value','') for v in before['spec']['template']['spec']['containers'][0]['env']}
        origin=current.get('ALLOWED_ORIGINS','')
        candidate=f'https://{tag}---gst-easy-v3-web-foovqasysa-el.a.run.app'
        updates['ALLOWED_ORIGINS']=','.join(dict.fromkeys([*origin.split(','),candidate]))
    else:
        updates['BACKEND_URL']=f'https://{tag}---gst-easy-v3-api-foovqasysa-el.a.run.app'
        updates['BACKEND_ID_TOKEN_AUDIENCE']='https://gst-easy-v3-api-foovqasysa-el.a.run.app'
    flags=ART/(kind+'-candidate-flags.json')
    flags.write_text(json.dumps({'--update-env-vars':updates}))
    cloud('run','deploy',name,'--image',immutable,'--no-traffic','--tag',tag,'--flags-file',str(flags),
          '--project',PROJECT,'--region',REGION,'--quiet')
    result=service(name)
    # Existing percentages must stay pinned while adding only a candidate tag.
    expected={v['revisionName']:v.get('percent',0) for v in before['status']['traffic'] if v.get('percent',0)>0}
    actual={v['revisionName']:v.get('percent',0) for v in result['status']['traffic'] if v.get('percent',0)>0}
    if actual!=expected:raise RuntimeError('Live traffic unexpectedly changed')
    candidate=next(t for t in result['status']['traffic'] if t.get('tag')==tag)
    report={'commit':commit,'build_id':build_id,'service':name,'image':immutable,'candidate':candidate,'traffic_changed':False}
    (ART/(kind+'-candidate.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


def canonical_web():
    report=json.loads((ART/'web-candidate.json').read_text())
    flags=ART/'web-main-flags.json'
    flags.write_text(json.dumps({'--update-env-vars':{
        'BACKEND_URL':'https://gst-easy-v3-api-foovqasysa-el.a.run.app',
        'BACKEND_ID_TOKEN_AUDIENCE':'https://gst-easy-v3-api-foovqasysa-el.a.run.app',
        'RELEASE_REVISION':report['commit']}}))
    cloud('run','deploy','gst-easy-v3-web','--image',report['image'],'--no-traffic','--tag','assistant-main-oct29',
          '--flags-file',str(flags),'--project',PROJECT,'--region',REGION,'--quiet')
    candidate=next(t for t in service('gst-easy-v3-web')['status']['traffic'] if t.get('tag')=='assistant-main-oct29')
    report['candidate']=candidate
    (ART/'web-main.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


def promote(kind):
    if kind not in {'api','web'}:raise ValueError('Wrong promotion target')
    smoke=json.loads((ART/'diagnostics-candidate.json').read_text())
    if not smoke.get('passed'):raise RuntimeError('Candidate acceptance has not passed')
    report=json.loads((ART/('api-candidate.json' if kind=='api' else 'web-main.json')).read_text())
    if report['commit']!=smoke['commit']:raise RuntimeError('Candidate source mismatch')
    name='gst-easy-v3-'+kind
    cloud('run','services','update-traffic',name,'--to-revisions',report['candidate']['revisionName']+'=100',
          '--project',PROJECT,'--region',REGION,'--quiet')
    result=service(name)
    if not any(t.get('percent')==100 and t['revisionName']==report['candidate']['revisionName'] for t in result['status']['traffic']):
        raise RuntimeError('Traffic verification failed')
    (ART/(kind+'-promotion.json')).write_text(json.dumps({'commit':report['commit'],'traffic':result['status']['traffic']},indent=2))
    print(json.dumps({'service':name,'revision':report['candidate']['revisionName'],'percent':100}))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['inspect','migrate','verify','deploy','canonical-web','promote'])
    parser.add_argument('--kind',choices=['api','web']);parser.add_argument('--build');parser.add_argument('--commit');parser.add_argument('--tag',default='assistant-oct29')
    args=parser.parse_args()
    if args.action=='inspect':inspect()
    elif args.action=='migrate':migrate()
    elif args.action=='verify':verify()
    elif args.action=='canonical-web':canonical_web()
    elif args.action=='promote':promote(args.kind)
    else:deploy(args.kind,args.build,args.commit,args.tag)


if __name__=='__main__':main()
