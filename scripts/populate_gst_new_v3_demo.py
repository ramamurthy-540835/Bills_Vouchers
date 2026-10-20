"""Authorized synthetic review through live HTTP APIs; resumable, no direct invoice SQL."""
import json
import hashlib
import mimetypes
import time
import subprocess
from pathlib import Path
from decimal import Decimal

from playwright.sync_api import sync_playwright
from prepare_gst_new_v3 import ART, PROJECT, cloud

ROOT=Path('demo bills/naturelabs1')
STATE=ART/'naturelabs1-processing.json'


def main():
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GST_NEW_V3':
        raise RuntimeError('Wrong branch')
    base=cloud('run','services','describe','gst-easy-v3-web','--project',PROJECT,'--region=asia-south1','--format=value(status.url)')
    assert base.startswith('https://gst-easy-v3-web-') and base.endswith('.run.app')
    manifest=json.loads((ROOT/'TEST_MANIFEST.json').read_text())
    profile=json.loads((ART/'naturelabs1-provisioning.json').read_text())
    cid=profile['businesses'][0]['client_id']
    state=json.loads(STATE.read_text()) if STATE.exists() else {'client_id':cid,'invoices':{}}
    assert state['client_id']==cid
    def save():STATE.write_text(json.dumps(state,indent=2))
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000})
        page=context.new_page(); page.set_default_timeout(180000)
        password=cloud('secrets','versions','access','1','--secret=gst-easy-v3-naturelabs1-password','--project',PROJECT)
        login=context.request.post(base+'/api/auth/login',headers={'Origin':base},
            data={'email':'naturelabs1@demo.com','password':password},timeout=180000)
        del password
        if login.status!=200:
            raise RuntimeError('Demo login failed with HTTP '+str(login.status))
        state['login']=True;save()
        csrf=context.request.get(base+'/api/auth/csrf',timeout=180000).json()['token']
        def call(method,path,**kwargs):
            version=kwargs.pop('version',None)
            headers={'Origin':base,'x-csrf-token':csrf}
            if version is not None:headers['if-match']=str(version)
            for attempt in range(3):
                response=context.request.fetch(base+path,method=method,headers=headers,timeout=180000,max_retries=2 if method=='GET' else 0,**kwargs)
                if response.status!=409 or version is None or attempt==2:
                    break
                if response.json().get('error',{}).get('code')!='bill_conflict':
                    break
                # A storage transaction may abort while the invoice is unchanged.
                # Never retry over another reviewer's newer invoice version.
                current=call('GET','/api/gst/bills/'+path.split('/')[4])
                if current['version']!=version:
                    break
                time.sleep(3*(attempt+1))
            if not response.ok:raise RuntimeError(f'{method} {path}: {response.status} {response.text()[:600]}')
            return response.json()
        listed=call('GET','/api/gst/bills?period=2026-10')
        assert listed['client_id']==cid
        history=call('GET','/api/gst/bills/history?period=2026-10')['jobs']
        completed={job['job_id'] for job in history if job['status']=='completed'}
        # Review ready documents first while durable workers finish the rest.
        fixtures=sorted(enumerate(manifest['invoices']),key=lambda pair:
            state['invoices'].get(pair[1]['invoice_number'],{}).get('job_id') not in completed)
        for index,fixture in fixtures:
            number=fixture['invoice_number'];entry=state['invoices'].setdefault(number,{})
            if entry.get('review_completed'):
                saved=next((i for i in listed['invoices'] if i['invoice_id']==entry['invoice_id']),None)
                assert saved and saved['status']==entry['status'],'Previously provisioned invoice changed; refusing to overwrite'
                continue
            if not entry.get('job_id'):
                # Never adopt an unrelated invoice just because its number matches.
                assert not any(i['invoice_number']==number for i in listed['invoices']), 'Existing identity without provisioning record requires review'
                filename=fixture['files'][index%3];content=(ROOT/filename).read_bytes()
                job=call('POST','/api/gst/bills/upload?period=2026-10',multipart={'files':{'name':filename,'mimeType':mimetypes.guess_type(filename)[0],'buffer':content}})
                entry.update(job_id=job['job_id'],filename=filename);save()
                print(f'{number}: uploaded; waiting for durable job',flush=True)
            deadline=time.monotonic()+2400
            recovery_attempts=0
            while True:
                job=call('GET','/api/gst/bills/upload/'+entry['job_id'])
                if job['status']=='completed':break
                if job.get('retryable') and recovery_attempts<3:
                    entry['job_result']=job;save()
                    call('POST','/api/gst/bills/upload/'+entry['job_id']+'/retry')
                    recovery_attempts+=1
                    print(f'{number}: recovering saved upload (attempt {recovery_attempts})',flush=True)
                    time.sleep(10)
                    continue
                if job['status']=='needs_attention' or time.monotonic()>deadline:
                    entry['job_result']=job;save();raise RuntimeError('Upload needs attention; saved job can be recovered without re-upload')
                time.sleep(20)
            ids=[i for f in job['files'] for i in f['invoice_ids']]
            if len(ids)!=1:raise RuntimeError(f'{number}: expected exactly one canonical invoice, got {len(ids)}')
            iid=ids[0];entry['invoice_id']=iid
            current=call('GET','/api/gst/bills/'+iid)
            entry.setdefault('extraction',current['extraction']);entry.setdefault('initial_review_reasons',current['review_reasons']);save()
            if not entry.get('review_completed'):
                assert current['client_id']==cid and not current['sample']
                body={key:fixture[key] for key in ['invoice_number','invoice_date','invoice_type','direction','place_of_supply_state_code','totals']}
                body['line_items']=[{k:v for k,v in line.items() if k!='unit_price'} for line in fixture['line_items']]
                for side in ['supplier','recipient']:
                    body[side+'_gstin']=fixture[side]['gstin'];body[side+'_legal_name']=fixture[side]['legal_name'];body[side+'_address']=fixture[side]['principal_address']
                body['reverse_charge']=False
                # These are explicitly authorized review corrections to the visible source, not extraction claims.
                current=call('PATCH','/api/gst/bills/'+iid,data=body,version=current['version'])
                expected=fixture['expected_status']
                if expected=='confirmed':current=call('POST','/api/gst/bills/'+iid+'/confirm',version=current['version'])
                elif expected=='rejected':current=call('POST','/api/gst/bills/'+iid+'/reject',data={'reason':'Synthetic demonstration: rejected by authorized demo reviewer; not for tax filing.'},version=current['version'])
                else:
                    # Missing invoice date is an honest review exercise; original remains intact.
                    current=call('PATCH','/api/gst/bills/'+iid,data={'invoice_date':None},version=current['version'])
                assert current['status']==expected,(number,current['review_reasons'])
                entry.update(review_completed=True,status=current['status']);save()
            print(f'{number}: {entry["status"]}',flush=True)
        if not state.get('statement_imported'):
            content=(ROOT/'gstr2b.json').read_bytes()
            history=call('GET','/api/gst/bills/gstr2b/history?period=2026-10')['statements']
            prior=next((s for s in history if s['sha256']==hashlib.sha256(content).hexdigest()),None)
            result={'imported':prior['record_count']} if prior else call('POST','/api/gst/bills/gstr2b?period=2026-10',data=content)
            state['statement_imported']=result;save()
        dashboard=call('GET','/api/gst/bills/dashboard?period=2026-10')
        actual={**dashboard['totals'],**{k:dashboard[k] for k in ['confirmed_sales','confirmed_purchases']},
                'pending_reviews':dashboard['review_count'],'reconciliation_mismatches':dashboard['mismatch_count'],'unmatched_invoices':dashboard['unmatched_count']}
        state['actual_kpis']=actual
        state['kpi_comparison']={key:Decimal(str(actual[key]))==Decimal(str(value)) for key,value in manifest['expected_kpis'].items()};save()
        assert all(state['kpi_comparison'].values()),state['kpi_comparison']
        state['reports']={}
        for kind in ['credit','liability','cash','without_itc','pending','mismatches','unmatched','sales','purchases']:
            report=call('GET',f'/api/gst/bills/reports?period=2026-10&kind={kind}')
            state['reports'][kind]={'row_count':report['row_count'],'title':report.get('title'),'can_export':report.get('can_export')};save()
            assert report['row_count']==manifest['expected_report_rows'][kind],(
                kind,report['row_count'],manifest['expected_report_rows'][kind])
        for width in [1440,390]:
            page.set_viewport_size({'width':width,'height':1000});page.goto(base+'/gst/workspace?period=2026-10')
            page.get_by_text('Manage your invoices',exact=True).wait_for()
            page.screenshot(path=str(ART/f'naturelabs1-dashboard-{width}.png'),full_page=True)
        state['url']=base;save();browser.close()
    print('Persisted synthetic invoices and all nine KPI comparisons passed. See sanitized processing report.')


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(type(exc).__name__+': '+str(exc).split('Call log:')[0].strip())
        raise SystemExit(1) from None

