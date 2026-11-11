"""Owner-authorized V3-only upload/auth release; protected services stay unchanged."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import release_assistant_v3 as common

ART=Path('artifacts/v3-upload-release-2026-11-10')
ART.mkdir(parents=True,exist_ok=True)
common.ART=ART
TAG='uploads-nov10'
PROJECT=common.PROJECT
REGION=common.REGION

def write(name,value):
    (ART/name).write_text(json.dumps(value,indent=2),encoding='utf-8')

def cloud(*args):
    return common.cloud(*args)

def build(commit):
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GST_NEW_V3':
        raise RuntimeError('Wrong release branch')
    if subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()!=commit:
        raise RuntimeError('Source revision mismatch')
    if subprocess.check_output(['git','diff','HEAD','--','app','frontend','scripts'],text=True).strip():
        raise RuntimeError('Application source has uncommitted changes')
    archive=ART/'source.tar.gz'
    subprocess.check_call(['git','archive','--format=tar.gz','--output',str(archive),commit])
    result=json.loads(cloud('builds','submit',str(archive),'--project',PROJECT,'--config','cloudbuild-gst-easy-v3.yaml',
        '--substitutions','_REVISION='+commit,'--gcs-source-staging-dir',f'gs://{PROJECT}-gst-easy-v3-builds/uploads-nov10/',
        '--async','--format=json','--quiet'))
    write('build-request.json',{'commit':commit,'build_id':result['id'],'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()})
    print(json.dumps({'commit':commit,'build_id':result['id'],'status':result.get('status')}))

def deploy(kind,commit,build_id,canonical=False):
    if kind not in {'api','web'}:
        raise RuntimeError('Invalid V3 target')
    build=json.loads(cloud('builds','describe',build_id,'--project',PROJECT,'--format=json'))
    if build['status']!='SUCCESS' or build.get('substitutions',{}).get('_REVISION')!=commit:
        raise RuntimeError('Build not verified')
    write('build.json',{'id':build_id,'status':build['status'],'commit':commit,'images':build['results']['images']})
    service='gst-easy-v3-'+kind
    image_name=f'{REGION}-docker.pkg.dev/{PROJECT}/gst-easy-v3/{kind}'
    image=next(v for v in build['results']['images'] if v['name']==image_name+':'+commit)
    immutable=image_name+'@'+image['digest']
    before=common.service(service)
    values={v['name']:v.get('value','') for v in before['spec']['template']['spec']['containers'][0].get('env',[])}
    updates={'RELEASE_REVISION':commit}
    if kind=='api':
        if values.get('BIGQUERY_DATASET')!='gst_easy_v3_finance_analytics' or values.get('GST_DATASET_PREFIX')!='gst_easy_v3_':
            raise RuntimeError('Unisolated V3 API configuration')
        updates['GEMINI_CUSTOMER_EXTRACTION_GLOBAL_ENABLED']='true'
        updates['GST_BILLS_WORKER_URL']=('https://gst-easy-v3-api-foovqasysa-el.a.run.app' if canonical
            else f'https://{TAG}---gst-easy-v3-api-foovqasysa-el.a.run.app')
        updates['GST_BILLS_WORKER_AUDIENCE']='https://gst-easy-v3-api-foovqasysa-el.a.run.app'
        updates['ALLOWED_ORIGINS']=','.join(dict.fromkeys([*values.get('ALLOWED_ORIGINS','').split(','),
            f'https://{TAG}---gst-easy-v3-web-foovqasysa-el.a.run.app',
            f'https://{TAG}-main---gst-easy-v3-web-foovqasysa-el.a.run.app']))
    else:
        updates['BACKEND_URL']=('https://gst-easy-v3-api-foovqasysa-el.a.run.app' if canonical else f'https://{TAG}---gst-easy-v3-api-foovqasysa-el.a.run.app')
        updates['BACKEND_ID_TOKEN_AUDIENCE']='https://gst-easy-v3-api-foovqasysa-el.a.run.app'
    tag=TAG+'-main' if canonical else TAG
    flags=ART/(kind+('-main' if canonical else '-candidate')+'-flags.json')
    flags.write_text(json.dumps({'--update-env-vars':updates}),encoding='utf-8')
    cloud('run','deploy',service,'--image',immutable,'--no-traffic','--tag',tag,'--flags-file',str(flags),
        '--project',PROJECT,'--region',REGION,'--quiet')
    after=common.service(service)
    def traffic(resource):return {v['revisionName']:v.get('percent',0) for v in resource['status']['traffic'] if v.get('percent')}
    if traffic(after)!=traffic(before):raise RuntimeError('Unexpected live traffic change')
    revision=next(v for v in after['status']['traffic'] if v.get('tag')==tag)
    result={'commit':commit,'build_id':build_id,'service':service,'image':immutable,'candidate':revision}
    write(kind+('-main.json' if canonical else '-candidate.json'),result)
    print(json.dumps(result))

def promote(kind):
    if kind not in {'api','web'}:raise RuntimeError('Wrong V3 service')
    gate=json.loads((ART/'acceptance-candidate.json').read_text())
    if not gate.get('passed'):raise RuntimeError('Candidate acceptance not passed')
    release=json.loads((ART/('api-main.json' if kind=='api' else 'web-main.json')).read_text())
    if release['commit']!=gate['commit']:raise RuntimeError('Acceptance/source mismatch')
    regression=json.loads((ART/'diagnostics-candidate.json').read_text())
    if not regression.get('passed') or regression['commit']!=release['commit']:
        raise RuntimeError('Candidate regression acceptance/source mismatch')
    if kind=='web':
        canonical=json.loads((ART/'acceptance-canonical.json').read_text())
        api=json.loads((ART/'api-main.json').read_text())
        if not canonical.get('passed') or canonical['commit']!=release['commit']:
            raise RuntimeError('Canonical frontend acceptance/source mismatch')
        if api['commit']!=release['commit'] or not any(
            v.get('percent')==100 and v['revisionName']==api['candidate']['revisionName']
            for v in common.service('gst-easy-v3-api')['status']['traffic']):
            raise RuntimeError('Tested API must be live before frontend promotion')
    service=release['service']
    cloud('run','services','update-traffic',service,'--to-revisions',release['candidate']['revisionName']+'=100',
        '--project',PROJECT,'--region',REGION,'--quiet')
    state=common.service(service)
    if not any(t.get('percent')==100 and t['revisionName']==release['candidate']['revisionName'] for t in state['status']['traffic']):
        raise RuntimeError('Promotion verification failed')
    write(kind+'-promotion.json',{'commit':release['commit'],'traffic':state['status']['traffic']})
    print(json.dumps({'service':service,'revision':release['candidate']['revisionName'],'percent':100}))

p=argparse.ArgumentParser()
p.add_argument('action',choices=['snapshot','build','deploy','promote','verify'])
p.add_argument('--kind',choices=['api','web'])
p.add_argument('--commit')
p.add_argument('--build')
p.add_argument('--canonical',action='store_true')
args=p.parse_args()
if args.action=='snapshot':common.inspect()
elif args.action=='build':build(args.commit)
elif args.action=='deploy':deploy(args.kind,args.commit,args.build,args.canonical)
elif args.action=='promote':promote(args.kind)
else:common.verify()
