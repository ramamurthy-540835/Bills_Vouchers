"""Local browser gate for actual-workspace presentation with synthetic test fixtures."""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.gst.filing_workspace import prepare_report, reporting_periods, working_papers  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass

    def do_GET(self):
        scope=parse_qs(urlparse(self.path).query).get('scope',['month'])[0]
        months,label=reporting_periods('2026-09',scope)
        data={name:[] for name in ('bronze_document','silver_invoice_header','silver_outward_invoice',
            'silver_gstr2b_invoice','gold_filing_summary','gold_itc_ledger','gold_gstr2b_match','gst_filing_status')}
        data['bronze_document']=[{'period':'2026-09','doc_id':'test-document','original_filename':'Test purchase.png'}]
        data['silver_invoice_header']=[{'doc_id':'test-document','total':'1333.50','supplier_name':'Fixture Supplier',
            'validation_status':'needs_review','validation_errors':['GSTIN_CHECKSUM']}]
        report=prepare_report('fixture','2026-09',scope,months,label,{'legal_name':'Test Customer'},data)
        report.update(user={'full_name':'Test','role':'client'},clients=[])
        download='/download' in self.path
        payload=working_papers(report) if download else json.dumps(report).encode()
        self.send_response(200)
        self.send_header('content-type','application/zip' if download else 'application/json')
        if download:
            self.send_header('content-disposition','attachment; filename=working-papers.zip')
        self.end_headers()
        self.wfile.write(payload)


def main():
    server=ThreadingHTTPServer(('127.0.0.1',8090),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    with (ROOT/'artifacts/gst-ui.log').open('w') as log:
        process=subprocess.Popen([r'C:\Users\BIS\Stephen\ITR\income-tax\.tools\node-v22.22.0-win-x64\node.exe',
            'node_modules/next/dist/bin/next','start','-p','3102'],cwd=ROOT/'frontend',
            env={**os.environ,'BACKEND_URL':'http://127.0.0.1:8090'},stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            time.sleep(3)
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
                context=browser.new_context(viewport={'width':1440,'height':1000})
                context.add_cookies([{'name':'session','value':'test=.signature','domain':'localhost','path':'/'}])
                page=context.new_page()
                errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto('http://localhost:3102/gst/workspace?period=2026-09',wait_until='networkidle')
                assert page.get_by_role('navigation',name='Main navigation').get_by_role('link',name='GST Workspace',exact=True).count()==1
                assert 'Demo workspace' not in page.get_by_role('navigation',name='Main navigation').inner_text()
                for scope,count in [('month',1),('quarter',3),('year',12)]:
                    page.get_by_label('Reporting view').select_option(scope)
                    page.wait_for_url(f'**scope={scope}') if scope!='month' else None
                    page.get_by_text(f'0 of {count} months computed',exact=False).wait_for()
                    for tab in ('Purchases','ITC decisions','Reconciliation','Sales','GSTR-2B','Downloads','Client profile','Readiness'):
                        page.get_by_role('button',name=tab,exact=True).click()
                        if tab=='Purchases':
                            assert 'Fixture Supplier' in page.locator('body').inner_text()
                            page.get_by_label('Search workspace records').fill('absent invoice')
                            assert 'No records match' in page.locator('body').inner_text()
                            page.get_by_label('Search workspace records').fill('Fixture')
                            assert page.get_by_role('link',name='Review original').count()==1
                    with page.expect_download() as info:
                        page.get_by_role('link',name='Download working papers',exact=True).click()
                    assert Path(info.value.path()).stat().st_size>1000
                    print(f'PASS {scope}: sections, source corrections, search and ZIP download',flush=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert not errors,errors
                page.screenshot(path=str(ROOT/'artifacts/gst-workspace-mobile.png'),full_page=True)
                browser.close()
        finally:
            process.terminate()
            process.wait(timeout=15)
            server.shutdown()


if __name__=='__main__':
    main()
