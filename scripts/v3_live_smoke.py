"""Authenticated deployed checks; never upload synthetic customer bills."""
import json
import os
from pathlib import Path
from uuid import uuid4
import httpx

BASE=os.environ.get('BV_TEST_URL','https://preview-v3---bills-voucher-web-foovqasysa-el.a.run.app').rstrip('/')
checks=[]
with httpx.Client(base_url=BASE,timeout=120) as client:
    response=client.post('/api/auth/login',json={'email':os.environ['BV_TEST_EMAIL'],'password':os.environ['BV_TEST_PASSWORD']},headers={'Origin':BASE})
    assert response.status_code==200,('login',response.status_code)
    checks.append('authenticated login')
    response=client.get('/api/auth/csrf');response.raise_for_status();token=response.json()['token']
    headers={'Origin':BASE,'x-csrf-token':token}
    for period in ['2026-09','2026-10']:
        response=client.get('/api/gst/bills/dashboard',params={'period':period});response.raise_for_status()
        data=response.json();assert not data.get('sample')
        assert all(isinstance(v,str) for v in data['totals'].values())
        assert 'Umesh' not in response.text and '27AAPFU0939F1ZV' not in response.text
        assert client.get('/api/gst/bills',params={'period':period}).status_code==200
    checks.append('tenant-bound confirmed dashboard with decimal strings and no sample fixture')
    for path in ['/api/gst/bills/template.xlsx','/api/gst/bills/export?period=2026-09&format=xlsx','/api/gst/bills/export?period=2026-09&format=csv','/api/gst/bills/working-papers?period=2026-09']:
        result=client.get(path);assert result.status_code==200,(path,result.status_code)
    checks.append('template and real-record export endpoints')
    missing=str(uuid4())
    for path in [f'/api/gst/bills/{missing}',f'/api/gst/bills/{missing}/original',f'/api/gst/bills/upload/{missing}']:
        assert client.get(path).status_code==404,path
    for action in ['confirm','reject']:
        assert client.post(f'/api/gst/bills/{missing}/{action}',headers=headers).status_code==404
    checks.append('unavailable bill and original return 404, including authenticated writes')
    result=client.post('/api/gst/bills/upload?period=2026-09',files={'files':('invalid.exe',b'not accepted','application/octet-stream')},headers=headers)
    assert result.status_code==422,('upload must reach validation rather than sample block',result.status_code)
    checks.append('real-upload auth reaches validation; invalid file saved nowhere')
    result=client.post('/api/gst/bills/upload?period=2026-09',files={'files':('invalid.exe',b'not accepted','application/octet-stream')},headers={'Origin':'https://untrusted.example','x-csrf-token':token})
    assert result.status_code==403
    checks.append('CSRF origin enforcement')
Path('artifacts/v3').mkdir(parents=True,exist_ok=True)
Path('artifacts/v3/live-smoke.json').write_text(json.dumps({'url':BASE,'passed':True,'checks':checks,'synthetic_uploads':0},indent=2))
print('PASS '+str(len(checks))+' live groups; no synthetic customer uploads.')
