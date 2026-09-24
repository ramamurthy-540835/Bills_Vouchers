"""Preview browser gate. Pass test credentials through environment, never source files."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    base = os.environ.get('BV_TEST_URL', 'https://preview---bills-voucher-web-foovqasysa-el.a.run.app').rstrip('/')
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1000})
        page.goto(base+'/demo', timeout=90000)
        assert page.url.endswith('/login')
        page.locator('input[type=text]').fill(os.environ['BV_TEST_EMAIL'])
        page.locator('input[type=password]').fill(os.environ['BV_TEST_PASSWORD'])
        page.get_by_role('button',name='Sign in',exact=True).click()
        page.wait_for_url(base+'/',timeout=90000)
        before = page.evaluate("async()=>{let r=await fetch('/api/workspace?period=2026-09');if(!r.ok)throw Error(r.status);return (await r.json()).documents.map(d=>[d.doc_id,d.silver?.total])}")
        page.goto(base+'/demo?period=2026-09',timeout=90000)
        page.get_by_text('Demo workspace · Synthetic data',exact=True).wait_for(timeout=30000)
        assert page.get_by_role('navigation',name='Main navigation').get_by_role('link',name='Assistant').count()==1
        with page.expect_download() as download_info:
            page.get_by_role('button',name='Download mock JSON',exact=True).click()
        download = download_info.value
        payload = json.loads(Path(download.path()).read_text(encoding='utf-8'))
        assert payload['sample'] and 'user' not in payload
        print('PASS live Demo and synthetic-only JSON download',flush=True)
        page.get_by_label('Demo scenario').select_option('large')
        page.wait_for_function("!document.querySelector('select[aria-label=\"Demo scenario\"]').disabled")
        page.get_by_role('tab',name='Search',exact=True).click()
        page.get_by_label('Search documents',exact=True).fill('metro')
        page.get_by_role('button',name='Search',exact=True).click()
        page.get_by_text('24 results',exact=False).wait_for(timeout=30000)
        print('PASS live mock search and pagination data',flush=True)
        page.get_by_role('tab',name='Assistant',exact=True).click()
        page.get_by_label('Your question',exact=True).fill('What is the exact cash required for this synthetic period? Cite the financial summary.')
        page.get_by_role('button',name='Ask assistant',exact=True).click()
        page.locator('.chat-message.assistant').first.wait_for(timeout=90000)
        assert page.locator('.chat-message.assistant .chat-sources a').count()>0
        print('PASS actual deployed Gemini conversation and source citation',flush=True)
        page.screenshot(path='artifacts/live-demo-assistant.png',full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.goto(base+'/assistant?period=2026-09',timeout=90000)
        page.get_by_role('heading',name='Ask your finance assistant',exact=True).wait_for(timeout=30000)
        assert 'Synthetic Company' not in page.locator('body').inner_text()
        page.get_by_label('Your question',exact=True).fill('What validated financial totals are available for this period? Cite the Gold summary and do not include unreviewed bills.')
        page.get_by_role('button',name='Ask assistant',exact=True).click()
        page.locator('.chat-message.assistant').first.wait_for(timeout=90000)
        assert 'synthetic demo' not in page.locator('.chat-message.assistant').first.inner_text().lower()
        print('PASS live customer assistant remains separate from demo conversation',flush=True)
        after = page.evaluate("async()=>{let r=await fetch('/api/workspace?period=2026-09');if(!r.ok)throw Error(r.status);return (await r.json()).documents.map(d=>[d.doc_id,d.silver?.total])}")
        assert before==after
        print('PASS existing customer documents unchanged',flush=True)
        browser.close()


if __name__=='__main__':
    main()
