"""Read-only browser checks for Red Taxi demo; credentials supplied via environment."""
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile

from playwright.sync_api import sync_playwright


def main():
    base='https://preview---bills-voucher-web-foovqasysa-el.a.run.app'
    expected=json.loads(Path('artifacts/redtaxi-demo-2026-09/mock-data.json').read_text(encoding='utf-8'))
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.goto(base+'/demo?scenario=redtaxi&period=2026-09',timeout=90000)
        page.locator('input[type=text]').fill(os.environ['BV_TEST_EMAIL'])
        page.locator('input[type=password]').fill(os.environ['BV_TEST_PASSWORD'])
        page.get_by_role('button',name='Sign in',exact=True).click()
        page.wait_for_url(base+'/',timeout=90000)
        page.goto(base+'/demo?scenario=redtaxi&period=2026-09',timeout=90000)
        page.get_by_role('heading',name='Red Taxi Coimbatore — DEMONSTRATION',exact=True).wait_for(timeout=30000)
        assert page.get_by_text('Eligible input credit',exact=True).count()==1
        assert 'Synthetic data' in page.locator('body').inner_text()
        page.screenshot(path='artifacts/redtaxi-demo-dashboard.png',full_page=True)
        for tab,rows in [('Sales',6),('Gstr2b',18)]:
            page.get_by_role('tab',name=tab,exact=True).click()
            assert page.locator('[role=tabpanel] tbody tr').count()==rows
        page.get_by_role('tab',name='Search',exact=True).click()
        page.get_by_label('Search documents',exact=True).fill('diesel')
        page.get_by_role('button',name='Search',exact=True).click()
        page.get_by_text('2 results',exact=False).wait_for(timeout=30000)
        with page.expect_download(timeout=90000) as info:
            page.get_by_role('link',name='Download auditor pack and PNG prompts',exact=True).click()
        with ZipFile(info.value.path()) as archive:
            bundle=json.loads(archive.read('mock-data.json'))
            assert bundle==expected
            manifest=json.loads(archive.read('manifest.json'))
            for name,digest in manifest['sha256'].items():
                assert hashlib.sha256(archive.read(name)).hexdigest()==digest
            assert archive.read('PNG-PROMPTS.md').decode('utf-8').count('## RTX-DEMO-')==26
            assert 'README-AUDITORS.md' in archive.namelist()
        print('PASS populated Red Taxi dashboard, registers, search and auditor pack matching Python output',flush=True)
        live=page.evaluate("async()=>{const r=await fetch('/api/workspace?period=2026-09');if(!r.ok)throw Error(r.status);return await r.json()}")
        assert all(d['doc_id']!='b84d90fd51bc39ddf9b1d1c207d0e6e6' and not d['doc_id'].startswith('demo-') for d in live['documents'])
        print('PASS unrelated PNG absent from active records; no mock purchases in live customer tables',flush=True)
        page.get_by_role('tab',name='Dashboard',exact=True).click()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        print('PASS responsive dashboard',flush=True)
        browser.close()


if __name__=='__main__':
    main()
