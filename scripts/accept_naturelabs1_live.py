"""Live acceptance of the new tenant only. No mocked API responses."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from prepare_gst_easy_v2 import ART, PROJECT, cloud


def main():
    base=cloud('run','services','describe','gst-easy-v2-web','--project',PROJECT,'--region=asia-south1','--format=value(status.url)')
    assert base.startswith('https://gst-easy-v2-web-')
    state=json.loads((ART/'naturelabs1-processing.json').read_text());cid=state['client_id']
    results={'url':base,'checks':{},'limitations':[]}
    def record(name,value):
        results['checks'][name]=value
        (ART/'naturelabs1-acceptance.json').write_text(json.dumps(results,indent=2))
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page();page.set_default_timeout(180000)
        page.goto(base+'/login');page.get_by_label('Email',exact=True).fill('naturelabs1@demo.com')
        password=cloud('secrets','versions','access','1','--secret=gst-easy-v2-naturelabs1-password','--project',PROJECT)
        page.locator('input[type=password]').fill(password);del password
        page.get_by_role('button',name='Sign in',exact=True).click();page.wait_for_url('**/gst/workspace');record('login',True)
        csrf=context.request.get(base+'/api/auth/csrf',timeout=180000).json()['token']
        def req(method,path,**kwargs):
            return context.request.fetch(base+path,method=method,headers={'Origin':base,'x-csrf-token':csrf},timeout=180000,**kwargs)
        before=req('GET','/api/gst/bills?period=2026-10').json()
        assert before['client_id']==cid and len(before['invoices'])==23
        record('persisted_status_counts',{s:sum(i['status']==s for i in before['invoices']) for s in ['confirmed','needs_review','rejected']})
        for slug in ['usable-itc','gst-liability','cash-requirement','purchases-without-itc','pending-reviews','reconciliation-mismatches','unmatched-invoices','sales-register','purchase-register']:
            page.goto(base+'/reports/'+slug+'?period=2026-10')
            page.get_by_role('link',name='← Back to Reports',exact=True).wait_for()
            assert 'No records found' not in page.locator('body').inner_text()
            record('report_page_'+slug,True)
        for route in ['/settings/me','/settings/account','/settings/password','/settings/profile','/help','/search','/assistant','/gst/filing']:
            page.goto(base+route+'?period=2026-10')
            assert '/login' not in page.url
            record('page_'+route,True)
        for q in ['NL1-P-001','Fictional Supplier','Fictional Customer']:
            response=req('GET','/api/pipeline/search?period=2026-10&q='+q.replace(' ','%20'))
            record('search_'+q,{'status':response.status,'body':response.json()})
            assert response.status==200
        for inv in before['invoices']:
            response=req('GET','/api/gst/bills/'+inv['invoice_id']+'/original')
            assert response.status==200 and len(response.body())>1000
        record('all_originals_accessible',True)
        foreign=json.loads((ART/'provisioning.json').read_text())['businesses'][0]['client_id']
        response=req('POST','/api/workspace/client',data={'client_id':foreign})
        record('foreign_business_switch_denied',response.status in {403,404})
        assert response.status in {403,404}
        assert req('GET','/api/gst/bills?period=2026-10').json()['client_id']==cid
        # Test the intentionally retained synthetic return/export guards.
        for path in ['/api/gst/bills/export?period=2026-10','/api/gst/returns/working-paper?period=2026-10']:
            response=req('GET',path);record('restricted_'+path,response.status);assert response.status==403
        response=req('POST','/api/gst/returns/prepare?period=2026-10',data={'version':0})
        record('synthetic_return_preparation_blocked',response.status==403);assert response.status==403
        duplicate=Path('demo bills/naturelabs1/gstr2b-duplicate-invalid.json').read_bytes()
        response=req('POST','/api/gst/bills/gstr2b?period=2026-10',data=duplicate)
        record('duplicate_statement_rejected',response.status==422);assert response.status==422
        response=req('GET','/api/gst/returns?period=2026-10');record('return_status_loaded',response.status==200);assert response.status==200
        for question in ['What are our total confirmed sales?','What is our usable ITC?','Which invoices need review?','Which purchase invoices are unmatched?','What is the estimated GST cash requirement?']:
            response=req('POST','/api/assistant/chat?period=2026-10',data={'question':question,'history':[]})
            record('assistant_'+question,{'status':response.status,'response':response.json()})
            if response.status!=200:results['limitations'].append('Live AI response unavailable: '+question)
        after=req('GET','/api/gst/bills?period=2026-10').json()
        assert after==before;record('read_only_assistant_preserved_invoices',True)
        for width in [1440,900,390]:
            page.set_viewport_size({'width':width,'height':1000})
            for route,label in [('/gst/workspace','dashboard'),('/settings/profile','profile'),('/bills','bills'),('/reports/usable-itc','itc')]:
                page.goto(base+route+'?period=2026-10');page.wait_for_load_state('networkidle')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
                page.screenshot(path=str(ART/f'naturelabs1-{label}-{width}.png'),full_page=True)
            record('responsive_'+str(width),True)
        page.reload();assert '/login' not in page.url;record('refresh',True)
        response=req('POST','/api/auth/logout');record('logout',response.status==200)
        response=req('GET','/api/gst/bills?period=2026-10');record('logged_out_denied',response.status==401);assert response.status==401
        browser.close()
    print('Live acceptance recorded; inspect AI answers and screenshots before claiming readiness.')


if __name__=='__main__':main()
