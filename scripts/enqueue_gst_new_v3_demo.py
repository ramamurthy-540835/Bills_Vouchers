"""Queue the authorized V3 synthetic fixtures through live uploads, resumably."""
import json
import mimetypes
import subprocess
from pathlib import Path
import httpx
from prepare_gst_new_v3 import ART,PROJECT,cloud


def main():
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GST_NEW_V3':
        raise RuntimeError('Wrong branch')
    base=cloud('run','services','describe','gst-easy-v3-web','--project',PROJECT,
               '--region=asia-south1','--format=value(status.url)')
    if not base.startswith('https://gst-easy-v3-web-') or not base.endswith('.run.app'):
        raise RuntimeError('Unexpected service')
    root=Path('demo bills/naturelabs1')
    manifest=json.loads((root/'TEST_MANIFEST.json').read_text())
    profile=json.loads((ART/'naturelabs1-provisioning.json').read_text())
    cid=profile['businesses'][0]['client_id']
    state_path=ART/'naturelabs1-processing.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {'client_id':cid,'invoices':{}}
    if state['client_id']!=cid:
        raise RuntimeError('Saved state belongs to a different workspace')
    password=cloud('secrets','versions','access','1','--secret=gst-easy-v3-naturelabs1-password','--project',PROJECT)
    with httpx.Client(base_url=base,timeout=180,headers={'Origin':base}) as client:
        response=client.post('/api/auth/login',json={'email':'naturelabs1@demo.com','password':password})
        del password
        if response.status_code!=200:
            raise RuntimeError('Demo login failed: '+str(response.status_code))
        csrf=client.get('/api/auth/csrf')
        csrf.raise_for_status()
        client.headers['x-csrf-token']=csrf.json()['token']
        current=client.get('/api/gst/bills?period=2026-10')
        current.raise_for_status()
        if current.json()['client_id']!=cid:
            raise RuntimeError('Wrong selected business')
        for index,fixture in enumerate(manifest['invoices']):
            entry=state['invoices'].setdefault(fixture['invoice_number'],{})
            if entry.get('job_id'):
                continue
            if any(row['invoice_number']==fixture['invoice_number'] for row in current.json()['invoices']):
                raise RuntimeError('Untracked invoice already exists; inspect instead of adopting it')
            filename=fixture['files'][index%3]
            response=client.post('/api/gst/bills/upload?period=2026-10',
                files={'files':(filename,(root/filename).read_bytes(),mimetypes.guess_type(filename)[0])})
            if not response.is_success:
                raise RuntimeError('Upload failed: '+str(response.status_code)+'; inspect saved jobs before retrying')
            entry.update(job_id=response.json()['job_id'],filename=filename)
            state_path.write_text(json.dumps(state,indent=2))
            print(fixture['invoice_number']+': durable upload job queued',flush=True)
    print('All fixture uploads queued. Processing and reviewed confirmation are separate.',flush=True)


if __name__=='__main__':
    main()
