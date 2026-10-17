"""Complete visual checks and recheck corrected AI grounding without re-seeding data."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from prepare_gst_easy_v2 import ART, PROJECT, cloud


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['visuals','assistant'],required=True);args=parser.parse_args()
    path=ART/'naturelabs1-acceptance.json';results=json.loads(path.read_text());base=results['url']
    assert base.startswith('https://gst-easy-v2-web-')
    state=json.loads((ART/'naturelabs1-processing.json').read_text())
    def record(key,value):
        results['checks'][key]=value;path.write_text(json.dumps(results,indent=2));print(key+': recorded',flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page();page.set_default_timeout(120000)
        page.goto(base+'/login',wait_until='domcontentloaded');page.get_by_label('Email',exact=True).fill('naturelabs1@demo.com')
        password=cloud('secrets','versions','access','1','--secret=gst-easy-v2-naturelabs1-password','--project',PROJECT)
        page.locator('input[type=password]').fill(password);del password
        page.get_by_role('button',name='Sign in',exact=True).click();page.wait_for_url('**/gst/workspace')
        csrf=context.request.get(base+'/api/auth/csrf',timeout=180000).json()['token']
        def req(method,url,**kwargs):
            return context.request.fetch(base+url,method=method,headers={'Origin':base,'x-csrf-token':csrf},timeout=180000,max_retries=2 if method=='GET' else 0,**kwargs)
        if args.mode=='visuals':
            for width in [1440,900,390]:
                page.set_viewport_size({'width':width,'height':1000})
                for route,label in [('/gst/workspace','dashboard'),('/settings/profile','profile'),('/bills','bills'),('/reports/usable-itc','itc')]:
                    print(f'Rendering {label} at {width}px',flush=True)
                    page.goto(base+route+'?period=2026-10',wait_until='domcontentloaded')
                    page.locator('h1').wait_for()
                    if label=='dashboard':page.get_by_text('₹5,781.60',exact=True).first.wait_for()
                    elif label=='profile':page.get_by_text('https://naturelabs-manufacturing.example.test',exact=True).first.wait_for()
                    else:page.locator('table tbody tr').first.wait_for()
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1'),f'{label}: overflow at {width}'
                    page.screenshot(path=str(ART/f'naturelabs1-{label}-{width}.png'),full_page=True,animations='disabled')
                record('responsive_'+str(width),True)
                if width==390:
                    page.locator('.mobile-tabs summary').click()
                    page.locator('.mobile-tabs').get_by_role('link',name='Reports',exact=True).click()
                    page.wait_for_url('**/reports?**');record('mobile_report_navigation',True)
            for width in [1440,390]:
                page.set_viewport_size({'width':width,'height':1000})
                page.goto(base+'/bills?period=2026-10&invoice='+state['invoices']['NL1-P-001']['invoice_id'],wait_until='domcontentloaded')
                preview=page.get_by_role('link',name='Open full original invoice',exact=True);preview.wait_for()
                page.wait_for_function("document.querySelector('.original-invoice-preview')?.getAttribute('aria-busy')==='false'")
                assert preview.locator('img').count()==1
                assert preview.get_attribute('href')==page.get_by_role('link',name='View Original Bill',exact=True).get_attribute('href')
                page.screenshot(path=str(ART/f'naturelabs1-review-{width}.png'),full_page=True,animations='disabled')
                record('original_preview_'+str(width),True)
            page.reload(wait_until='domcontentloaded');assert '/login' not in page.url;record('refresh',True)
        else:
            previous=ART/'naturelabs1-assistant-before-correction.json'
            if not previous.exists():previous.write_text(json.dumps({k:v for k,v in results['checks'].items() if k.startswith('assistant_')},indent=2))
            before=req('GET','/api/gst/bills?period=2026-10').json()
            for question in ['What are our total confirmed sales?','What is our usable ITC?','Which invoices need review?','Which purchase invoices are unmatched?','What is the estimated GST cash requirement?']:
                response=req('POST','/api/assistant/chat?period=2026-10',data={'question':question,'history':[]})
                record('assistant_'+question,{'status':response.status,'response':response.json()});assert response.status==200
                answer=response.json();assert answer['sample'] is True and 'synthetic' in answer['answer'].lower()
                allowed={'gold-summary',*(i['invoice_id'] for i in before['invoices'])}
                assert all(s['id'] in allowed for s in answer['sources'])
                text=answer['answer'].replace(',','')
                if 'confirmed sales' in question:assert '190918.16' in text
                if 'usable ITC' in question:assert '5781.60' in text
                if 'cash requirement' in question:assert '18178.56' in text
                if 'unmatched' in question:
                    assert text.count('NL1-P-005')==1 and text.count('NL1-P-009')==1
                    assert 'NL1-P-010' not in text or 'unsupported' in text.lower()
            assert req('GET','/api/gst/bills?period=2026-10').json()==before
            record('assistant_reconciliation_corrected',True);record('read_only_assistant_preserved_invoices',True)
        assert req('POST','/api/auth/logout').status==200;record('logout',True)
        assert req('GET','/api/gst/bills?period=2026-10').status==401;record('logged_out_denied',True)
        browser.close()


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(type(exc).__name__+': '+str(exc).split('Call log:')[0].strip())
        raise SystemExit(1) from None
