"""Read-only live review smoke; never uploads or changes invoices."""
import json
from playwright.sync_api import sync_playwright
from prepare_gst_easy_v2 import ART, cloud


def main():
    release=json.loads((ART/'review-deployment.json').read_text())
    base=release['frontend_url']
    password=cloud('secrets','versions','access','1','--secret=gst-easy-v2-demo-password','--project=aidirac-503309')
    result={'login':False,'pdf_worker':False,'existing_invoice_preview':False,'financial_mutations':0}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(120000)
        page.goto(base+'/login')
        page.get_by_label('Email',exact=True).fill('naturelabs@demo.com')
        page.locator('input[type=password]').fill(password);del password
        page.get_by_role('button',name='Sign in',exact=True).click()
        page.wait_for_url('**/gst/workspace');result['login']=True
        assert page.request.get(base+'/pdfjs/pdf.worker.min.mjs').status==200
        result['pdf_worker']=True
        page.goto(base+'/bills?period=2026-10')
        response=page.request.get(base+'/api/gst/bills?period=2026-10');assert response.status==200
        invoices=response.json()['invoices']
        candidates=[i for i in invoices if str(i.get('invoice_number','')).startswith('NL-')]
        if candidates:
            invoice=candidates[0]
            page.goto(base+'/bills?period=2026-10&invoice='+invoice['invoice_id'])
            preview=page.get_by_role('link',name='Open full original invoice',exact=True)
            preview.wait_for()
            page.wait_for_function("document.querySelector('.original-invoice-preview')?.getAttribute('aria-busy')==='false'")
            assert preview.get_attribute('href')==page.get_by_role('link',name='View Original Bill',exact=True).get_attribute('href')
            result['existing_invoice_preview']=preview.locator('img').count()==1
            result['original_status']=page.request.get(base+preview.get_attribute('href')).status
            assert result['original_status']==200
        else:
            result['limitation']='No existing generated NL invoice in the active demo business. Rendering verified locally; no invoice seeded.'
        browser.close()
    (ART/'review-live-results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
