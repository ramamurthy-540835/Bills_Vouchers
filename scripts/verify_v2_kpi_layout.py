"""Check the deployed v2 Overview amounts and requested header cleanup."""
import json
import os
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

BASE = 'https://preview-v2---bills-voucher-web-foovqasysa-el.a.run.app'
results = []
with httpx.Client(base_url=BASE, timeout=120) as client:
    response = client.post('/api/auth/login', json={
        'email': os.environ['BV_TEST_EMAIL'],
        'password': os.environ['BV_TEST_PASSWORD'],
    })
    response.raise_for_status()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            headless=True,
        )
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        context.add_cookies([
            {'name': c.name, 'value': c.value, 'domain': httpx.URL(BASE).host,
             'path': '/', 'secure': True} for c in client.cookies.jar
        ])
        page = context.new_page()
        page.goto(BASE + '/?period=2026-09', timeout=90000)
        page.locator('.overview-kpis').wait_for()
        page.evaluate('document.fonts.ready')
        assert page.locator('.overview-kpis > .metric-card > strong').count() == 4
        assert page.locator('.profile-notice, .overview-intro, .sample-banner').count() == 0
        assert page.locator('.page-heading h1').count() == 0
        logo = page.locator('.bv-header img[alt="Red Taxi"]')
        assert logo.is_visible()
        assert logo.evaluate('(img) => img.complete && img.naturalWidth > 0')
        for width in [1440, 1280, 1200, 1024, 768, 760, 600, 480, 390, 320]:
            page.set_viewport_size({'width': width, 'height': 1000})
            metrics = page.locator('.overview-kpis > .metric-card > strong').evaluate_all('''elements => elements.map(el => {
                const range = document.createRange();
                range.selectNodeContents(el);
                const rects = [...range.getClientRects()];
                const box = el.getBoundingClientRect();
                return {text: el.textContent, lines: rects.length,
                    fits: rects.every(r => r.left >= box.left - 1 && r.right <= box.right + 1),
                    fontSize: getComputedStyle(el).fontSize};
            })''')
            assert all(m['lines'] == 1 and m['fits'] for m in metrics), (width, metrics)
            assert all(m['text'].startswith('₹') for m in metrics), metrics
            results.append({'width': width, 'amounts': metrics,
                            'page_overflow': page.evaluate('document.documentElement.scrollWidth > innerWidth')})
            if width in (1440, 390):
                page.screenshot(path=f'artifacts/v7/overview-kpi-{width}.png', full_page=True)
        browser.close()
Path('artifacts/v7/kpi-layout.json').write_text(json.dumps(results, indent=2))
print('PASS: all four amounts fit on one line at 10 viewport widths; logo and cleanup verified.')
