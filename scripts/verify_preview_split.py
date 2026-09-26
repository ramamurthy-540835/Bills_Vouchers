"""Verify the old preview and v7 preview-v2 remain separate and functional."""
import json
import os
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

targets=[('old','https://preview---bills-voucher-web-foovqasysa-el.a.run.app',22),
         ('preview-v2','https://preview-v2---bills-voucher-web-foovqasysa-el.a.run.app',120)]
results=[]
for name,base,count in targets:
    with httpx.Client(base_url=base,timeout=120) as client:
        r=client.post('/api/auth/login',json={'email':os.environ['BV_TEST_EMAIL'],'password':os.environ['BV_TEST_PASSWORD']},headers={'Origin':base})
        assert r.status_code==200,(name,'login',r.status_code)
        r=client.get('/api/auth/csrf');r.raise_for_status()
        csrf=r.json()['token']
        r=client.post('/api/workspace/period',json={'period':'2026-09'},headers={'Origin':base,'x-csrf-token':csrf})
        assert r.status_code==200,(name,'origin/CSRF',r.status_code)
        r=client.get('/api/dashboard?period=2026-09');r.raise_for_status()
        data=r.json()
        assert data['validated_invoices']==count,(name,data['validated_invoices'])
        assert bool(data.get('sample'))==(name=='preview-v2')
        if name=='preview-v2':
            r=client.get('/api/gst/workspace/download?period=2026-09')
            assert r.status_code==403 and r.json()['error']['code']=='sample_data_blocked'
            r=client.post('/api/workspace/period',json={'period':'2026-09'},headers={'Origin':'https://untrusted.example','x-csrf-token':csrf})
            assert r.status_code==403 and r.json()['error']['code']=='csrf_origin'
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1000})
            context.add_cookies([{'name':c.name,'value':c.value,'domain':httpx.URL(base).host,'path':'/','secure':True} for c in client.cookies.jar])
            page=context.new_page()
            page.goto(base+'/gst/workspace?period=2026-09',timeout=90000)
            page.locator('.bv-header').wait_for(timeout=30000)
            assert page.locator('.client-identity').count()==(1 if name=='old' else 0)
            assert page.locator('.sample-banner').count()==0
            if name=='preview-v2':
                assert page.get_by_role('img',name='Red Taxi',exact=True).is_visible()
            browser.close()
        results.append({'name':name,'url':base,'validated_invoices':count,'login_origin_csrf_browser':'passed'})
        print('PASS '+name+' login, origin, CSRF, dashboard and restored/separate UI',flush=True)
output=Path('artifacts/v7/preview-split.json');output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(results,indent=2))
