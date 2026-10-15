"""Non-mutating/public-boundary smoke checks for the deployed preview."""
import json
from datetime import datetime,timezone
from pathlib import Path

import httpx

from deploy_gst_easy import WEB,API


def main():
    results=[]
    with httpx.Client(timeout=60,follow_redirects=False) as client:
        for path in ('/login','/admin/login','/register','/forgot-password','/reset-password'):
            response=client.get(WEB+path)
            assert response.status_code==200,(path,response.status_code)
            results.append({'path':path,'status':response.status_code})
        response=client.get(API+'/health')
        assert response.status_code==200,('health',response.status_code)
        results.append({'path':'health','status':response.status_code})
        response=client.get(API+'/readyz')
        assert response.status_code==200,('readiness',response.status_code)
        results.append({'path':'readyz','status':response.status_code})
        response=client.post(WEB+'/api/auth/admin/login',json={'email':'preview-probe@example.invalid','password':'invalid-probe'},headers={'Origin':WEB})
        assert response.status_code==401,('admin/login',response.status_code)
        results.append({'path':'admin/login','status':response.status_code,'invalid_credentials_denied':True})
        for path in ('/api/gst/bills?period=2026-09','/api/gst/bills/reconciliation?period=2026-09','/api/gst/bills/reconciliation/history?period=2026-09&case_id=probe','/api/gst/returns?period=2026-09','/api/settings/members','/api/gst/bills/reports?period=2026-09','/api/gst/bills/dashboard?period=2026-09&scope_name=financial_year'):
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
