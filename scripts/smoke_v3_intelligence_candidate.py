"""Read-only synthetic smoke check for a tagged V3 Intelligence candidate."""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from prepare_gst_new_v3 import PROJECT, cloud


def main():
    candidate = json.loads(Path('artifacts/intelligence-v3/deployment.json').read_text())
    live = len(sys.argv) == 2 and sys.argv[1] == '--live'
    assert len(sys.argv) == 1 or live
    base = ('https://gst-easy-v3-web-foovqasysa-el.a.run.app'
            if live else candidate['candidates']['web']['url'])
    assert base.startswith('https://gst-easy-v3-web-' if live else
                           'https://intelligence---gst-easy-v3-web-')
    password = cloud('secrets', 'versions', 'access', '1',
                     '--secret=gst-easy-v3-naturelabs1-password', '--project', PROJECT)
    checks = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(180000)
        page.goto(base + '/login')
        page.get_by_label('Email', exact=True).fill('naturelabs1@demo.com')
        page.locator('input[type=password]').fill(password)
        del password
        page.get_by_role('button', name='Sign in', exact=True).click()
        page.wait_for_url('**/gst/workspace')
        checks['login'] = True
        page.goto(base + '/bills?period=2026-10')
        page.get_by_role('region', name='Invoice Intelligence', exact=True).wait_for()
        checks['intelligence_ui'] = True
        csrf = context.request.get(base + '/api/auth/csrf').json()['token']
        headers = {'x-csrf-token': csrf, 'origin': base}
        overview = context.request.get(base + '/api/gst/bills/intelligence?period=2026-10')
        assert overview.status == 200 and overview.json()['policy']['enabled'] is False
        checks['business_policy_off'] = True
        for question in ['What is our usable ITC?',
                         'What is the estimated GST cash requirement?',
                         'What is our GST liability on sales?',
                         'What blocked ITC do we have?']:
            response = context.request.post(base + '/api/assistant/chat?period=2026-10',
                                            headers=headers, data={'question': question, 'history': []},
                                            timeout=180000)
            assert response.status == 200, response.status
            answer = response.json()
            assert answer.get('sources') and answer['sources'][0]['id'] == 'gold-summary'
            assert not answer.get('degraded') and '₹' in answer['answer']
        checks['four_canonical_assistant_answers'] = True
        browser.close()
    report = {'commit': candidate['commit'], 'url': base, 'checks': checks}
    output = 'smoke-live.json' if live else 'smoke-current.json'
    Path('artifacts/intelligence-v3', output).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
