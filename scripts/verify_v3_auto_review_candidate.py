"""Live candidate acceptance using only the existing authorized synthetic demo."""
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from prepare_gst_new_v3 import cloud, PROJECT

ART = Path('artifacts/auto-review-v3')


def main():
    release = json.loads((ART / 'deployment.json').read_text())
    base = release['candidates']['web']['url']
    assert base.startswith('https://auto-review---gst-easy-v3-web-')
    results = {'url': base, 'checks': {}, 'limitations': ['Live automatic confirmation is gated by unconfigured approved GST policies.']}

    def record(name, value=True):
        results['checks'][name] = value
        (ART / 'candidate-live-results.json').write_text(json.dumps(results, indent=2))
        print(name, value, flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        page = context.new_page()
        page.set_default_timeout(180000)
        page.goto(base + '/login')
        page.get_by_label('Email', exact=True).fill('naturelabs1@demo.com')
        password = cloud('secrets', 'versions', 'access', '1', '--secret=gst-easy-v3-naturelabs1-password', '--project', PROJECT)
        page.locator('input[type=password]').fill(password)
        del password
        with page.expect_response(lambda response: response.url.endswith('/api/auth/login')) as login:
            page.get_by_role('button', name='Sign in', exact=True).click()
        assert login.value.status == 200, ('Sign-in HTTP status', login.value.status)
        page.wait_for_url('**/gst/workspace')
        record('real_login')
        csrf = context.request.get(base + '/api/auth/csrf').json()['token']

        def req(method, path, **kwargs):
            response = context.request.fetch(base + path, method=method, headers={'Origin': base, 'x-csrf-token': csrf}, timeout=180000, **kwargs)
            assert response.ok, (method, path, response.status)
            return response

        account = req('GET', '/api/settings/account').json()
        assert account['user']['email'] == 'naturelabs1@demo.com'
        assert account['profile']['legal_name'] == 'Nature Labs Synthetic Manufacturing Pvt Ltd'
        before = req('GET', '/api/gst/bills?period=2026-10').json()
        pending = [i for i in before['invoices'] if i['status'] == 'needs_review' and i['invoice_number'].startswith('NL1-')]
        assert pending, 'No eligible existing synthetic pending invoice; do not mutate unrelated records.'
        detail = None
        for invoice in pending:
            response = req('GET', '/api/gst/bills/' + invoice['invoice_id']).json()
            candidate = response.get('invoice', response)
            if not candidate.get('auto_review_locked') and not candidate.get('auto_review', {}).get('enabled'):
                detail = candidate
                break
        assert detail, 'No unlocked synthetic invoice available.'
        identifier = detail['invoice_id']
        page.goto(base + '/bills?period=2026-10&invoice=' + identifier)
        toggle = page.get_by_role('switch', name='Auto Review', exact=True)
        toggle.wait_for()
        assert toggle.get_attribute('aria-checked') == 'false'
        record('default_off')
        assert not toggle.is_disabled(), 'Synthetic invoice is not editable.'
        toggle.click()
        page.get_by_role('button', name='Run Auto Review', exact=True).wait_for()
        page.reload()
        page.get_by_role('button', name='Run Auto Review', exact=True).wait_for()
        assert toggle.get_attribute('aria-checked') == 'true'
        record('policy_persists_across_refresh')
        page.get_by_role('button', name='Run Auto Review', exact=True).click()
        deadline = time.monotonic() + 240
        current = None
        while time.monotonic() < deadline:
            response = req('GET', '/api/gst/bills/' + identifier).json()
            current = response.get('invoice', response)
            if current['auto_review']['status'] in {'manual_required', 'failed', 'auto_confirmed'}:
                break
            page.wait_for_timeout(2500)
        assert current['auto_review']['status'] == 'manual_required', current['auto_review']['status']
        assert current['status'] == 'needs_review'
        assert any('policy' in r.lower() for r in current['auto_review']['reasons'])
        record('cloud_tasks_review_completed_with_manual_exception')
        page.reload()
        page.get_by_text('Manual Review Required', exact=True).wait_for()
        for width, name in [(1440, 'desktop'), (390, 'mobile')]:
            page.set_viewport_size({'width': width, 'height': 1000})
            page.screenshot(path=str(ART / f'candidate-{name}.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        record('desktop_mobile_no_overflow')
        original = page.get_by_role('link', name='View Original Bill', exact=True).get_attribute('href')
        assert req('GET', original).status == 200
        record('authorized_original_retained')
        toggle.click()
        page.wait_for_function("document.querySelector('[role=switch][aria-label=\"Auto Review\"]')?.getAttribute('aria-checked')==='false'")
        after = req('GET', '/api/gst/bills?period=2026-10').json()
        assert {i['invoice_id']: i['status'] for i in before['invoices']} == {i['invoice_id']: i['status'] for i in after['invoices']}
        record('existing_invoice_statuses_unchanged_and_policy_reset_off')
        unauthorized = p.request.new_context()
        response = unauthorized.get(base + '/api/gst/bills/' + identifier, max_redirects=0)
        assert response.status in {401, 403, 307}
        record('anonymous_invoice_access_denied')
        unauthorized.dispose()
        browser.close()


if __name__ == '__main__':
    main()
