"""Post-deployment checks; normal login only, no account or financial writes."""
import json
import os
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

BASE=os.environ.get('BV_TEST_URL','https://preview-v2---bills-voucher-web-foovqasysa-el.a.run.app').rstrip('/')


def main():
    output=Path('artifacts/v7');output.mkdir(parents=True,exist_ok=True)
    checks=[]
    def passed(text):
        checks.append(text);print('PASS '+text,flush=True)
    with httpx.Client(base_url=BASE,timeout=120) as client:
        response=client.post('/api/auth/login',json={'email':os.environ['BV_TEST_EMAIL'],'password':os.environ['BV_TEST_PASSWORD']})
        assert response.status_code==200, f'Login: {response.status_code}'
        csrf=client.get('/api/auth/csrf').json()['token']
        headers={'x-csrf-token':csrf}
        response=client.post('/api/workspace/client',json={'client_id':'02f66f3a-0981-4db9-8bd3-1870855c4c09'},headers=headers)
        response.raise_for_status()
        for period in ['2026-09','2026-08']:
            for endpoint in ['dashboard','workspace','gst/workspace']:
                response=client.get(f'/api/{endpoint}?period={period}')
                response.raise_for_status()
                result=response.json()
                assert result['client_id']=='02f66f3a-0981-4db9-8bd3-1870855c4c09'
                assert result['sample'] and result['summary']
                assert 'Umesh' not in response.text and '27AAPFU0939F1ZV' not in response.text
                if endpoint=='workspace':assert len(result['documents'])==120
                if endpoint=='gst/workspace':assert len(result['ledger'])==120 and len(result['outward'])==13
                passed(endpoint+' populated, labelled and tenant-bound '+period)
        for path in ['/api/gst/workspace/download?period=2026-09','/api/demo/redtaxi-pack?period=2026-09',
                     '/api/pipeline/documents/sample-redtaxi-2026-09-001/file?period=2026-09']:
            response=client.get(path)
            assert response.status_code==403 and response.json()['error']['code']=='sample_data_blocked', (path,response.status_code)
            passed('sample export blocked '+path)
        for path,body in [('/api/gst/filing/generate/gstr3b',{}),('/api/gst/filing/transition',{'state':'validated'}),('/api/gst/filing/recompute',{})]:
            response=client.post(path+'?period=2026-09',json=body,headers=headers)
            assert response.status_code==403 and response.json()['error']['code']=='sample_data_blocked',(path,response.status_code)
            passed('sample mutation blocked '+path)
        response=client.post('/api/workspace/client',json={'client_id':'v7-unauthorised-client'},headers=headers)
        assert response.status_code==403
        response=client.get('/api/gst/workspace?period=2026-09&client_id=v7-unauthorised-client')
        assert response.json()['client_id']=='02f66f3a-0981-4db9-8bd3-1870855c4c09'
        passed('cross-client selector denied and query override ignored')
        account=client.get('/api/settings/account');account.raise_for_status()
        assert account.json()['user']['last_sign_in']
        passed('account profile and last sign-in available')
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1000})
            context.add_cookies([{'name':c.name,'value':c.value,'domain':httpx.URL(BASE).host,'path':'/','secure':True} for c in client.cookies.jar])
            page=context.new_page()
            for path in ['/?period=2026-09','/gst/workspace?period=2026-09','/documents?period=2026-09','/gst/filing?period=2026-09','/settings/account','/settings/profile']:
                page.goto(BASE+path,timeout=90000)
                page.locator('.bv-header').wait_for(timeout=30000)
                text=page.locator('body').inner_text()
                assert 'Umesh' not in text and '27AAPFU0939F1ZV' not in text
                assert page.locator('.client-identity').count()==0
                assert page.locator('.sidebar-note').count()==0
                assert 'GSTIN pending' not in page.locator('.bv-header').inner_text()
                assert 'client' not in page.locator('.bv-header').inner_text().split()
                assert page.locator('.account-menu summary .avatar').inner_text()
                page.get_by_label('Open account menu').click()
                menu=page.locator('.account-popover')
                assert menu.get_by_role('link',name='Account settings',exact=True).is_visible()
                assert menu.get_by_role('link',name='Client profile',exact=True).is_visible()
                assert menu.locator('.account-contact small').count()==2
                page.get_by_label('Open account menu').click()
                assert 'Sample data for illustration' not in text
                assert 'Illustrative rate: rides at 12%' not in text
                if path.startswith('/gst/workspace'):
                    assert 'Sample — 1 of 1 months' in text
                    assert 'Open Red Taxi sample walkthrough' not in text
                    assert page.get_by_role('button',name='Download working papers',exact=True).is_disabled()
                    page.screenshot(path=str(output/'gst-workspace.png'),full_page=True)
                    page.get_by_role('button',name='ITC decisions',exact=True).click()
                    assert '49A/49B' in page.locator('body').inner_text()
                if path.startswith('/?'):
                    page.screenshot(path=str(output/'overview.png'),full_page=True)
                if path=='/settings/account':
                    assert page.get_by_text('Access level',exact=True).is_visible()
                    assert page.get_by_label('Login email',exact=True).get_attribute('readonly') is not None
                passed('browser chrome and content '+path)
            page.goto(BASE+'/gst/workspace?period=2026-09',timeout=90000)
            page.set_viewport_size({'width':390,'height':844})
            assert page.locator('.mobile-tabs').is_visible()
            assert not page.locator('.bv-sidebar').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output/'mobile.png'),full_page=True)
            passed('mobile bottom tabs and no horizontal overflow')
            browser.close()
    (output/'live-gates.json').write_text(json.dumps({'url':BASE,'checks':checks},indent=2))


if __name__=='__main__':main()
