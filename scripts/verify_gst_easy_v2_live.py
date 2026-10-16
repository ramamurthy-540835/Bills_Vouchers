"""Read-only live acceptance: no invoice uploads or financial seeding."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from prepare_gst_easy_v2 import cloud, ART


def main():
    deployment = json.loads((ART / 'deployment.json').read_text())
    base = deployment['frontend_url']
    assert base.startswith('https://gst-easy-v2-web-')
    password = cloud('secrets', 'versions', 'access', '1',
                     '--secret=gst-easy-v2-demo-password', '--project=aidirac-503309')
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.set_default_timeout(90000)
        page.goto(base + '/login', timeout=120000)
        page.get_by_label('Email', exact=True).fill('naturelabs@demo.com')
        page.locator('input[type=password]').fill(password)
        del password
        with page.expect_response(lambda r: r.url.endswith('/api/auth/login')) as login_response:
            page.get_by_role('button', name='Sign in', exact=True).click()
        assert login_response.value.status == 200, ('Login HTTP status', login_response.value.status)
        page.wait_for_url('**/gst/workspace', timeout=120000)
        results.append('Real V2 demo login succeeded')
        print(results[-1], flush=True)

        def api(path):
            result = page.evaluate("""async path => {
                const r = await fetch(path, {cache:'no-store'});
                return {status:r.status, body:await r.json()};
            }""", path)
            assert result['status'] == 200, (path, result['status'])
            return result['body']

        account = api('/api/settings/account')
        assert len(account['clients']) == 3
        for client in account['clients']:
            page.get_by_label('Account menu', exact=True).click()
            page.get_by_label('Switch business', exact=True).select_option(client['id'])
            page.wait_for_load_state('networkidle')
            page.wait_for_function("""async id => {
                const r=await fetch('/api/settings/account',{cache:'no-store'});
                return r.ok && (await r.json()).client_id===id;
            }""", arg=client['id'])
            selected = api('/api/settings/account')
            assert selected['client_id'] == client['id']
            page.goto(base + '/settings/profile', timeout=120000)
            page.get_by_role('heading', name='Business Profile', exact=True).wait_for()
            assert client['name'] in page.locator('body').inner_text()
            logo = page.request.get(base + '/api/settings/profile/logo')
            assert logo.status == 200 and logo.headers.get('content-type', '').startswith('image/')
            page.reload(timeout=120000)
            assert api('/api/settings/account')['client_id'] == client['id']
            results.append('Profile, private logo, switch and refresh: ' + client['name'])
            print(results[-1], flush=True)

        reports = ['usable-itc','gst-liability','cash-requirement','purchases-without-itc',
                   'pending-reviews','reconciliation-mismatches','unmatched-invoices',
                   'sales-register','purchase-register']
        for slug in reports:
            page.goto(base + '/reports/' + slug + '?period=2026-10', timeout=120000)
            page.get_by_role('link', name='Back to Reports', exact=False).wait_for()
            page.get_by_role('heading', name='Report Information', exact=True).wait_for()
            if slug != 'cash-requirement':
                page.get_by_role('heading', name='No records found', exact=True).wait_for()
            else:
                # Cash reports retain four calculated tax-head scenarios, not invoice rows.
                page.get_by_text('0 source invoices', exact=False).wait_for()
            results.append('Empty live report: ' + slug)
            print(results[-1], flush=True)
        for route in ['/gst/workspace', '/bills', '/gst/filing', '/reports', '/settings/profile', '/settings', '/help']:
            page.goto(base + route, timeout=120000)
            assert '/login' not in page.url
            results.append('Authenticated route: ' + route)
        for width in [1440, 768, 390]:
            page.set_viewport_size({'width': width, 'height': 1000})
            page.goto(base + '/settings/profile', timeout=120000)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(ART / f'live-profile-{width}.png'), full_page=True)
        page.get_by_label('Account menu', exact=True).click()
        page.get_by_role('button', name='Logout', exact=True).click()
        page.wait_for_url('**/login')
        results.append('Logout succeeded')
        browser.close()
    (ART / 'live-results.json').write_text(json.dumps({'passed':results,
        'financial_uploads_performed':0,
        'limitation':'Financial live acceptance deferred to user uploads; local fixture tests recorded separately.'}, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
