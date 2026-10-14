"""Non-mutating/public-boundary smoke checks for the deployed preview."""
import json
from datetime import datetime,timezone
from pathlib import Path

import httpx

from deploy_gst_easy import WEB,API


def main():
    results=[]
    with httpx.Client(timeout=60,follow_redirects=False) as client:
        for path in ('/login','/register','/forgot-password','/reset-password'):
            response=client.get(WEB+path)
            assert response.status_code==200,(path,response.status_code)
            results.append({'path':path,'status':response.status_code})
        response=client.get(API+'/health')
        assert response.status_code==200,('health',response.status_code)
        results.append({'path':'health','status':response.status_code})
        response=client.get(API+'/readyz')
        assert response.status_code==200,('readiness',response.status_code)
        results.append({'path':'readyz','status':response.status_code})
        for path in ('/api/gst/bills?period=2026-09','/api/gst/returns?period=2026-09','/api/settings/members'):
            response=client.get(API+path)
            assert response.status_code in (401,403),(path,response.status_code)
            results.append({'path':path,'status':response.status_code,'unauthenticated_denied':True})
        response=client.post(API+'/api/gst/bills/internal/process',json={'client_id':'not-authorized','job_id':'not-authorized'})
        assert response.status_code in (401,403),('worker',response.status_code)
        results.append({'path':'internal/process','status':response.status_code,'unauthenticated_denied':True})
    result={'utc':datetime.now(timezone.utc).isoformat(),'url':WEB,'result':'passed','checks':results,
            'authenticated_customer_uat':False}
    Path('artifacts/gst_easy/preview-smoke.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
