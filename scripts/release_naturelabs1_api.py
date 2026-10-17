"""Update only the isolated V2 API image, preserving its configuration and web service."""
import argparse
import json
import subprocess
from prepare_gst_easy_v2 import cloud, ART, PROJECT, REGION
from deploy_gst_easy_v2 import snapshot_unchanged


def service(name):
    return json.loads(cloud('run','services','describe',name,'--project',PROJECT,'--region',REGION,'--format=json'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build-id',required=True)
    parser.add_argument('--tag',default='naturelabs1');args=parser.parse_args()
    assert args.tag in {'naturelabs1','naturelabs1-r2','naturelabs1-r3','naturelabs1-r4'}
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='GST-EASY-V2'
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    build=json.loads(cloud('builds','describe',args.build_id,'--project',PROJECT,'--format=json'))
    assert build['status']=='SUCCESS' and build['substitutions']['_REVISION']==sha
    image=build['results']['images'][0]
    assert image['name']==f'{REGION}-docker.pkg.dev/{PROJECT}/gst-easy-v2/api:{sha}'
    before=service('gst-easy-v2-api');web=service('gst-easy-v2-web')
    env={v['name']:v.get('value','') for v in before['spec']['template']['spec']['containers'][0]['env']}
    assert env['BIGQUERY_DATASET']=='gst_easy_v2_finance_analytics'
    assert env['GST_DATASET_PREFIX']=='gst_easy_v2_' and env['GCS_BUCKET_NAME']==PROJECT+'-gst-easy-v2-documents'
    assert not any(t.get('tag')==args.tag for t in before['status']['traffic'])
    (ART/(args.tag+'-api-before.json')).write_text(json.dumps(before,indent=2))
    snapshot_unchanged()
    digest=image['name'].rsplit(':',1)[0]+'@'+image['digest']
    cloud('run','services','update','gst-easy-v2-api','--project',PROJECT,'--region',REGION,
          '--image',digest,'--update-env-vars=RELEASE_REVISION='+sha,'--no-traffic','--tag='+args.tag,'--quiet')
    staged=service('gst-easy-v2-api');tag=next(t for t in staged['status']['traffic'] if t.get('tag')==args.tag)
    assert staged['status']['conditions'][0]['status']=='True'
    newenv={v['name']:v for v in staged['spec']['template']['spec']['containers'][0]['env']}
    for value in before['spec']['template']['spec']['containers'][0]['env']:
        if value['name']!='RELEASE_REVISION':assert newenv[value['name']]==value
    cloud('run','services','update-traffic','gst-easy-v2-api','--project',PROJECT,'--region',REGION,
          '--to-revisions='+tag['revisionName']+'=100','--quiet')
    assert service('gst-easy-v2-web')==web
    assert snapshot_unchanged()
    (ART/(args.tag+'-deployment.json')).write_text(json.dumps(dict(source_commit=sha,build_id=args.build_id,
        image=digest,revision=tag['revisionName'],url=before['status']['url'],web_unchanged=True,
        prior_services_unchanged=True,rollback=before['status']['traffic']),indent=2))
    print('V2 API released; frontend, existing service configuration and previous services preserved.')


if __name__=='__main__':main()
