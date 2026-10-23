"""Read-only repeated-question acceptance using the authorized synthetic account."""
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from prepare_gst_new_v3 import cloud, PROJECT


def main():
    base=json.loads(Path('artifacts/intelligence-v3/deployment.json').read_text())['candidates']['web']['url']
    assert base.startswith('https://intelligence---gst-easy-v3-web-')
    password=cloud('secrets','versions','access','1','--secret=gst-easy-v3-naturelabs1-password','--project',PROJECT)
    output=Path('artifacts/intelligence-v3/assistant-sequence.json')
    observations=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        context=browser.new_context();page=context.new_page();page.set_default_timeout(180000)
        page.goto(base+'/login');page.get_by_label('Email',exact=True).fill('naturelabs1@demo.com')
        page.locator('input[type=password]').fill(password);del password
        page.get_by_role('button',name='Sign in',exact=True).click();page.wait_for_url('**/gst/workspace')
        csrf=context.request.get(base+'/api/auth/csrf').json()['token']
        history=[]
        questions=['Summarize confirmed purchases using the provided financial evidence.',
                   'Explain confirmed sales for the selected reporting period using the supplied facts.',
                   'Explain the reconciliation limitations visible in this workspace.']
        for number in range(25):
            question=questions[number%len(questions)];started=time.perf_counter()
            response=context.request.post(base+'/api/assistant/chat?period=2026-10',
                headers={'x-csrf-token':csrf,'origin':base},data={'question':question,'history':history[-6:]},timeout=180000)
            body=response.json()
            observation={'question_number':number+1,'status':response.status,'seconds':round(time.perf_counter()-started,3),
                'degraded':body.get('degraded',False),'failure_category':body.get('failure_category'),
                'source_count':len(body.get('sources',[])),'retry_after':response.headers.get('retry-after')}
            observations.append(observation);output.write_text(json.dumps({'url':base,'observations':observations},indent=2))
            print(json.dumps(observation),flush=True)
            if response.status==200:
                history.extend([{'role':'user','content':question},{'role':'assistant','content':body.get('answer','')[:1500]}])
            if response.status in {401,403}:break
            time.sleep(max(0,8-(time.perf_counter()-started)))
        browser.close()


if __name__=='__main__':main()
