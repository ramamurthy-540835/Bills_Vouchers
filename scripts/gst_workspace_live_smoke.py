"""Read-only preview acceptance checks. Credentials are supplied only via environment."""
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile

from playwright.sync_api import sync_playwright


def main():
    base=os.environ.get('BV_TEST_URL','https://preview---bills-voucher-web-foovqasysa-el.a.run.app').rstrip('/')
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.goto(base+'/gst/workspace',timeout=90000)
        assert page.url.endswith('/login')
        page.locator('input[type=text]').fill(os.environ['BV_TEST_EMAIL'])
        page.locator('input[type=password]').fill(os.environ['BV_TEST_PASSWORD'])
        page.get_by_role('button',name='Sign in',exact=True).click()
        page.wait_for_url(base+'/',timeout=90000)
        before=page.evaluate("async()=>{const r=await fetch('/api/workspace?period=2026-09');if(!r.ok)throw Error(r.status);return (await r.json()).documents.map(d=>[d.doc_id,d.silver?.total])}")
        page.goto(base+'/gst/workspace?period=2026-09',timeout=90000)
        page.get_by_text('Actual customer records',exact=True).wait_for(timeout=30000)
        assert page.get_by_role('navigation',name='Main navigation').get_by_role('link',name='GST Workspace',exact=True).count()==1
        assert 'Synthetic Company' not in page.locator('body').inner_text()
        actual=page.evaluate("async()=>{const r=await fetch('/api/gst/workspace?period=2026-09&client_id=unauthorised');if(!r.ok)throw Error(r.status);return await r.json()}")
        assert actual['client_id']!='unauthorised' and actual['source']=='actual' and not actual['sample']
        assert len(actual['documents'])==len(before)
        page.get_by_role('button',name='Purchases',exact=True).click()
        if actual['documents']:
            doc=actual['documents'][0]
            page.get_by_label('Search workspace records').fill(doc['original_filename'])
            assert page.get_by_role('link',name='Review original').count()>=1
            assert doc['silver'].get('supplier_name','') in page.locator('body').inner_text()
        page.screenshot(path='artifacts/live-gst-purchases.png',full_page=True)
        print('PASS live actual purchases, search, corrections and selected-client scope',flush=True)
        for scope,count in [('month',1),('quarter',3),('year',12)]:
            if scope!='month':
                page.get_by_label('Reporting view').select_option(scope)
                page.wait_for_url(f'**scope={scope}',timeout=90000)
            page.get_by_text(f'of {count} months computed',exact=False).wait_for(timeout=30000)
            with page.expect_download(timeout=90000) as info:
                page.get_by_role('link',name='Download working papers',exact=True).click()
            with ZipFile(info.value.path()) as archive:
                manifest=json.loads(archive.read('manifest.json'))
                assert manifest['client_id']==actual['client_id'] and len(manifest['periods'])==count
                assert not manifest['sample'] and not manifest['portal_ready']
                for name,digest in manifest['sha256'].items():
                    assert hashlib.sha256(archive.read(name)).hexdigest()==digest
            print(f'PASS live {scope} view and verified working-paper ZIP',flush=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        after=page.evaluate("async()=>{const r=await fetch('/api/workspace?period=2026-09');return (await r.json()).documents.map(d=>[d.doc_id,d.silver?.total])}")
        assert before==after
        print('PASS mobile layout; actual customer records unchanged',flush=True)
        browser.close()


if __name__=='__main__':
    Path('artifacts').mkdir(exist_ok=True)
    main()
