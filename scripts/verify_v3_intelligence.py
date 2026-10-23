"""Authorized synthetic candidate checks and small-sample latency, no live promotion."""
import json
import sys
import time
import csv
from io import StringIO
from pathlib import Path

from playwright.sync_api import sync_playwright
from prepare_gst_new_v3 import cloud, PROJECT

ART=Path('artifacts/auto-review-v3')
BASE='https://auto-review---gst-easy-v3-web-foovqasysa-el.a.run.app'


def main():
    global BASE
    mode=sys.argv[1]
    assert mode in {'baseline','acceptance','performance'}
    if mode!='baseline':
        BASE=json.loads(Path('artifacts/intelligence-v3/deployment.json').read_text())['candidates']['web']['url']
        assert BASE.startswith('https://intelligence---gst-easy-v3-web-')
    report={'mode':mode,'url':BASE,'login_seconds':[],'bills_navigation_seconds':[],'checks':{}}
    output=ART/('intelligence-live-'+mode+'.json')
    def record(name,value=True):
        report['checks'][name]=value;output.write_text(json.dumps(report,indent=2));print(name,value,flush=True)
    password=cloud('secrets','versions','access','1','--secret=gst-easy-v3-naturelabs1-password','--project',PROJECT)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        for _ in range(3):
            context=browser.new_context(viewport={'width':1440,'height':1000})
            page=context.new_page();page.set_default_timeout(180000)
            page.goto(BASE+'/login');page.get_by_label('Email',exact=True).fill('naturelabs1@demo.com');page.locator('input[type=password]').fill(password)
            started=time.perf_counter();page.get_by_role('button',name='Sign in',exact=True).click();page.wait_for_url('**/gst/workspace')
            report['login_seconds'].append(round(time.perf_counter()-started,3))
            started=time.perf_counter();page.goto(BASE+'/bills?period=2026-10');page.get_by_label('Bill status',exact=True).wait_for()
            report['bills_navigation_seconds'].append(round(time.perf_counter()-started,3))
            if mode!='acceptance':context.close()
            else:break
        del password
        record('authorized_login_navigation')
        if mode!='acceptance':browser.close();return
        csrf=context.request.get(BASE+'/api/auth/csrf').json()['token']
        def req(method,path,**kwargs):
            return context.request.fetch(BASE+path,method=method,headers={'x-csrf-token':csrf,'origin':BASE,**kwargs.pop('headers',{})},timeout=180000,**kwargs)
        before=req('GET','/api/gst/bills?period=2026-10').json()
        assert before['invoices'] and all(i['client_id']==before['client_id'] for i in before['invoices'])
        excluded_ids=[]
        for invoice in before['invoices']:
            if invoice['invoice_number']=='V3INT-OFF-1023':
                assert invoice['status']!='confirmed' and invoice['extraction']['method']=='csv'
                assert invoice['line_items'][0]['description']=='SYNTHETIC TEST INVOICE - NOT VALID FOR TAX FILING'
                # Repair only this script's prior synthetic exclusion, using the
                # authorized invoice toggle; no direct database modification.
                if not invoice['auto_review']['requested_at']:
                    response=req('PATCH','/api/gst/bills/'+invoice['invoice_id']+'/auto-review',
                        data={'enabled':False},headers={'if-match':str(invoice['version'])})
                    assert response.status==200
                excluded_ids.append(invoice['invoice_id'])
        overview=req('GET','/api/gst/bills/intelligence?period=2026-10').json()
        assert not overview['policy']['enabled'], 'Do not overwrite an existing opt-in during acceptance'
        record('default_off_and_scoped_counts')
        selected=overview['policy']
        try:
            response=req('PATCH','/api/gst/bills/intelligence/policy',data={'enabled':True,'scope':'both'},headers={'if-match':str(selected['version'])})
            assert response.status==200,response.status
            selected=response.json()
            page.reload();page.get_by_role('switch',name='Business Auto Review').wait_for()
            assert page.get_by_role('switch',name='Business Auto Review').get_attribute('aria-checked')=='true'
            record('business_policy_persists')
            if overview['eligible']:
                response=req('POST','/api/gst/bills/intelligence/run?period=2026-10',headers={'if-match':str(selected['version'])})
                assert response.status==200,response.status
                job=response.json();deadline=time.monotonic()+600
                while job['status'] not in {'completed','needs_attention'} and time.monotonic()<deadline:
                    page.wait_for_timeout(5000);job=req('GET','/api/gst/bills/upload/'+job['job_id']).json()
                assert job['status']=='completed',job['status']
                assert all(e['status'] in {'needs_attention','cancelled'} for e in job['files']), 'No approved live GST policies were seeded'
                assert not set(excluded_ids)&{identity for entry in job['files'] for identity in entry['invoice_ids']}
                record('durable_existing_batch_manual_exceptions',len(job['files']))
                record('individual_exclusions_survive_later_batch')
            page.reload();page.get_by_role('region',name='Invoice Intelligence',exact=True).wait_for()
            for width in [1440,768,390]:
                page.set_viewport_size({'width':width,'height':1000})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(ART/f'intelligence-live-{width}.png'),full_page=True)
            record('responsive_intelligence')
            after=req('GET','/api/gst/bills?period=2026-10').json()
            def financial_records(values):
                return {i['invoice_id']:i['totals'] for i in values if i['status']=='confirmed'}
            assert financial_records(before['invoices'])==financial_records(after['invoices'])
            record('financial_statuses_unchanged')
            from app.gst.template import HEADERS
            supplier=next(i['supplier_gstin'] for i in before['invoices'] if i['direction']=='purchase')
            for suffix,choice in [('AUTO',''),('OFF','&auto_review=false')]:
                stream=StringIO();writer=csv.writer(stream);writer.writerow(HEADERS)
                writer.writerow([supplier,'V3INT-'+suffix+'-1023','23-10-2026','8537',
                    'SYNTHETIC TEST INVOICE - NOT VALID FOR TAX FILING','1000','18','90','90','0','0','1180','33','N'])
                content=stream.getvalue().encode()
                response=req('POST','/api/gst/bills/upload?period=2026-10&expected_client='+before['client_id']+choice,
                    multipart={'files':{'name':'synthetic-intelligence-'+suffix+'.csv','mimeType':'text/csv','buffer':content}})
                assert response.status==200,response.status
                job=response.json();deadline=time.monotonic()+600
                while job['status'] not in {'completed','needs_attention'} and time.monotonic()<deadline:
                    page.wait_for_timeout(5000);job=req('GET','/api/gst/bills/upload/'+job['job_id']).json()
                assert job['status']=='completed',job['status']
                ids=[identity for entry in job['files'] for identity in entry['invoice_ids']]
                assert len(ids)==1
                invoice=req('GET','/api/gst/bills/'+ids[0]).json()
                assert invoice['status']!='confirmed'
                assert invoice['auto_review']['enabled']==(suffix=='AUTO')
                assert invoice['auto_review']['requested_at']
                original=req('GET','/api/gst/bills/'+ids[0]+'/original')
                assert original.status==200 and original.body()==content
                record('future_policy_and_original_'+suffix)
            current_bills=req('GET','/api/gst/bills?period=2026-10').json()['invoices']
            assert financial_records(before['invoices'])==financial_records(current_bills)
            record('future_uploads_do_not_bypass_missing_policy')
            response=req('POST','/api/assistant/chat?period=2026-10',data={'question':'Which invoices need review?','history':[]})
            assert response.status==200,response.status
            assert response.json()['sources']
            record('deterministic_assistant_evidence')
        finally:
            current=req('GET','/api/gst/bills/intelligence?period=2026-10').json()['policy']
            response=req('PATCH','/api/gst/bills/intelligence/policy',data={'enabled':False,'scope':current['scope']},headers={'if-match':str(current['version'])})
            assert response.status==200
            record('business_policy_reset_off')
        browser.close()


if __name__=='__main__':main()
