"""Release only the V2 frontend by verified digest, preserving API and old services."""
import argparse
import json
import subprocess

import httpx
from deploy_gst_easy_v2 import snapshot_unchanged
from prepare_gst_easy_v2 import ART, PROJECT, REGION, cloud


def service(name):
    return json.loads(cloud('run','services','describe',name,'--project',PROJECT,'--region',REGION,'--format=json'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build-id',required=True);args=parser.parse_args()
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='GST-EASY-V2'
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    build=json.loads(cloud('builds','describe',args.build_id,'--project',PROJECT,'--format=json'))
    assert build['status']=='SUCCESS' and build['substitutions']['_REVISION']==sha
    image=build['results']['images'][0]
    assert image['name']==f'{REGION}-docker.pkg.dev/{PROJECT}/gst-easy-v2/web:{sha}'
    digest=image['name'].rsplit(':',1)[0]+'@'+image['digest']
    before=service('gst-easy-v2-web');api_before=service('gst-easy-v2-api')
    env={v['name']:v.get('value','') for v in before['spec']['template']['spec']['containers'][0]['env']}
    assert env['BACKEND_URL']==api_before['status']['url']==env['BACKEND_ID_TOKEN_AUDIENCE']
    assert not any(t.get('tag')=='bill-review' for t in before['status']['traffic'])
    (ART/'review-web-before.json').write_text(json.dumps(before,indent=2))
    snapshot_unchanged()
    cloud('run','services','update','gst-easy-v2-web','--project',PROJECT,'--region',REGION,
          '--image',digest,'--update-env-vars=RELEASE_REVISION='+sha,'--no-traffic','--tag=bill-review','--quiet')
    staged=service('gst-easy-v2-web')
    tag=next(t for t in staged['status']['traffic'] if t.get('tag')=='bill-review')
    for path in ['/login','/pdfjs/pdf.worker.min.mjs']:
        response=httpx.get(tag['url']+path,timeout=120);assert response.status_code==200,(path,response.status_code)
    cloud('run','services','update-traffic','gst-easy-v2-web','--project',PROJECT,'--region',REGION,
          '--to-revisions='+tag['revisionName']+'=100','--quiet')
    assert service('gst-easy-v2-api')==api_before
    assert snapshot_unchanged()
    report=dict(source_commit=sha,build_id=args.build_id,image=digest,frontend_url=before['status']['url'],
                revision=tag['revisionName'],staged_url=tag['url'],api_unchanged=True,previous_services_unchanged=True,
                rollback_traffic=before['status']['traffic'])
    (ART/'review-deployment.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
