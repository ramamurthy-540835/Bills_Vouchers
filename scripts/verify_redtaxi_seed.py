"""Read-only authenticated verification of the populated preview dashboard."""
import json
import os
import subprocess
from pathlib import Path
import httpx

BASE = 'https://preview---bills-voucher-web-foovqasysa-el.a.run.app'


def main():
    manifest = json.loads(Path('artifacts/redtaxi-bigquery-seed/manifest.json').read_text())
    secret = ({'email':os.environ['BV_TEST_EMAIL'], 'password':os.environ['BV_TEST_PASSWORD']}
        if os.environ.get('BV_TEST_EMAIL') else json.loads(subprocess.check_output(
        ['gcloud.cmd', 'secrets', 'versions', 'access', 'latest',
         '--secret=red-taxi-client-bootstrap', '--project=aidirac-503309'], text=True)))
    with httpx.Client(base_url=BASE, timeout=120) as client:
        response = client.post('/api/auth/login', json={'email':secret['email'], 'password':secret['password']})
        assert response.status_code == 200, f'Login returned {response.status_code}'
        def get(path):
            response = client.get(path)
            response.raise_for_status()
            return response
        csrf = get('/api/auth/csrf').json()['token']
        selected = client.post('/api/workspace/client', json={'client_id':manifest['client_id']},
            headers={'x-csrf-token':csrf})
        selected.raise_for_status()
        dashboard = get('/api/dashboard?period=2026-09').json()
        assert dashboard['client_id'] == manifest['client_id']
        assert dashboard['mode'] == 'live' and dashboard['source'] == 'gold'
        assert dashboard['validated_invoices'] == 22
        assert dashboard['totals'] == manifest['dashboard_totals']
        workspace = get('/api/workspace?period=2026-09').json()
        assert workspace['counts'] == {'documents':26, 'review':2, 'posted':22, 'failed':2}
        assert workspace['outward_count'] == 6
        for path in ['/?period=2026-09','/documents?period=2026-09','/gst/filing?period=2026-09','/gst/workspace?period=2026-09']:
            html = get(path).text
            assert 'Your workspace could not be loaded' not in html
            assert 'Red Taxi' in html
            print('PASS rendered '+path, flush=True)
        result = {'url':BASE+'/?period=2026-09','counts':workspace['counts'], 'totals':dashboard['totals']}
        Path('artifacts/redtaxi-bigquery-seed/live-verification.json').write_text(json.dumps(result,indent=2))
        print('PASS authenticated BigQuery dashboard '+json.dumps(result), flush=True)
        # Browser receives only this legitimate login session; credentials stay in memory.
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
            context = browser.new_context(viewport={'width':1440,'height':1000})
            context.add_cookies([{'name':c.name,'value':c.value,'domain':httpx.URL(BASE).host,'path':'/','secure':True} for c in client.cookies.jar])
            page = context.new_page()
            page.goto(BASE+'/?period=2026-09', timeout=90000)
            page.get_by_text('Eligible input credit',exact=True).wait_for(timeout=30000)
            assert '20,547.35' in page.locator('body').inner_text()
            page.screenshot(path='artifacts/redtaxi-bigquery-seed/dashboard.png',full_page=True)
            browser.close()
        print('PASS browser dashboard; screenshot saved', flush=True)


if __name__=='__main__':
    main()
