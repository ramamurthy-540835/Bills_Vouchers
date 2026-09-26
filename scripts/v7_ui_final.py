"""Targeted browser verification of the final frontend-only polish."""
import json
import os
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

BASE=os.environ.get('BV_TEST_URL','https://preview-v2---bills-voucher-web-foovqasysa-el.a.run.app').rstrip('/')
with httpx.Client(base_url=BASE,timeout=120) as client:
    response=client.post('/api/auth/login',json={'email':os.environ['BV_TEST_EMAIL'],'password':os.environ['BV_TEST_PASSWORD']})
    response.raise_for_status()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000})
        context.add_cookies([{'name':c.name,'value':c.value,'domain':httpx.URL(BASE).host,'path':'/','secure':True} for c in client.cookies.jar])
        page=context.new_page()
        page.goto(BASE+'/gst/workspace?period=2026-09',timeout=90000)
        assert page.locator('.profile-notice').count()==0
        assert 'GSTIN' not in page.locator('.bv-header').inner_text()
        assert 'Complete and verify this client' not in page.locator('.gst-checks').inner_text()
        assert page.get_by_role('button',name='Download working papers',exact=True).is_disabled()
        page.screenshot(path='artifacts/v7/gst-workspace.png',full_page=True)
        page.get_by_role('button',name='Purchases',exact=True).click()
        assert page.get_by_role('cell',name='Checked',exact=True).count()==20
        page.goto(BASE+'/documents?period=2026-09',timeout=90000)
        assert page.get_by_role('button',name='Upload bill',exact=True).is_disabled()
        assert page.get_by_role('cell',name='Checked',exact=True).count()==120
        page.goto(BASE+'/settings/account',timeout=90000)
        assert page.locator('.section-heading').get_by_role('button',name='Save your details',exact=True).is_visible()
        page.get_by_label('Open account menu').click()
        assert page.locator('.account-contact small').count()==2
        page.screenshot(path='artifacts/v7/account.png',full_page=True)
        page.goto(BASE+'/gst/workspace?period=2026-09',timeout=90000)
        page.set_viewport_size({'width':390,'height':844})
        assert page.locator('.mobile-tabs').is_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path='artifacts/v7/mobile.png',full_page=True)
        browser.close()
Path('artifacts/v7/final-ui-gates.json').write_text(json.dumps({'passed':True,'checks':['single GSTIN notice','Checked status labels','sample upload and export disabled','account primary action','account menu contact fields','mobile bottom tabs and overflow']},indent=2))
print('PASS final frontend gates and screenshots',flush=True)
