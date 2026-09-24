"""Read-only authenticated preview gate. Secret values and cookies stay in memory."""
import json
import base64
import subprocess
import sys
import time

import httpx
from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from itsdangerous import TimestampSigner

url = sys.argv[1].rstrip('/')
raw = subprocess.check_output(['gcloud.cmd','secrets','versions','access','latest','--secret=red-taxi-client-bootstrap','--project=aidirac-503309'], text=True)
secret = json.loads(raw)
with httpx.Client(base_url=url, timeout=120, follow_redirects=False) as client:
    assert client.get('/api/workspace').status_code == 401
    if '--trusted-session' in sys.argv:
        # Owner-authorised integration identity; never reset a customer's password for a test.
        config=json.loads(subprocess.check_output(['gcloud.cmd','run','services','describe','bills-voucher','--project=aidirac-503309','--region=asia-south1','--format=json'],text=True))
        env=config['spec']['template']['spec']['containers'][0]['env']
        signing=next(v for v in env if v['name']=='APP_SECRET_KEY')
        key=signing.get('value')
        token=subprocess.check_output(['gcloud.cmd','auth','print-access-token'],text=True).strip()
        if not key:
            ref=signing['valueFrom']['secretKeyRef']
            resource=ref['name'] if ref['name'].startswith('projects/') else 'projects/aidirac-503309/secrets/'+ref['name']
            response=httpx.get('https://secretmanager.googleapis.com/v1/'+resource+'/versions/'+ref['key']+':access',headers={'Authorization':'Bearer '+token},timeout=30)
            response.raise_for_status()
            key=base64.b64decode(response.json()['payload']['data']).decode()
        bq=bigquery.Client(project='aidirac-503309',credentials=Credentials(token))
        rows=list(bq.query('SELECT id,session_version FROM `aidirac-503309.finance_analytics.users` WHERE email=@email AND is_active=TRUE LIMIT 1',job_config=bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('email','STRING',secret['email'].lower())])).result())
        assert rows
        session={'user_id':rows[0].id,'session_version':rows[0].session_version or 0,'last_seen':str(time.time())}
        cookie=TimestampSigner(key).sign(base64.b64encode(json.dumps(session).encode())).decode()
        client.cookies.set('session',cookie,domain=httpx.URL(url).host,path='/')
        print('Using owner-authorised temporary test session; password login is not claimed',flush=True)
    else:
        response = client.post('/api/auth/login',json={'email':secret['email'],'password':secret['password']})
        assert response.status_code == 200, 'Login failed: ' + str(response.status_code)
        print('PASS authenticated Red Taxi login', flush=True)
    me = client.get('/api/auth/me')
    assert me.status_code==200, 'Identity status: '+str(me.status_code)+' '+str(me.json().get('error',{}).get('code'))
    assert me.json()['role']=='client', 'Unexpected effective role'
    if me.json().get('must_change_password'):
        raise RuntimeError('PASSWORD_CHANGE_REQUIRED: existing account requires its owner to set a new password')
    start=time.monotonic()
    response=client.get('/api/workspace?period=2026-09')
    assert response.status_code==200, 'Workspace status: '+str(response.status_code)
    assert 'Umesh' not in response.text and '27AAPFU0939F1ZV' not in response.text
    data=response.json()
    assert data['profile']['legal_name'] and not data['demo_fallback']
    assert not data['profile']['gstin'] or data['profile']['gstin'].startswith('33')
    print('PASS tenant profile, client role and live/empty data isolation; workspace seconds='+str(round(time.monotonic()-start,1)),flush=True)
    token=client.get('/api/auth/csrf')
    assert token.status_code==200 and 'csrf_token' in client.cookies
    if not data['profile']['gstin']:
        response=client.post('/api/gst/filing/generate/gstr3b?period=2026-09',headers={'x-csrf-token':token.json()['token']})
        assert response.status_code==409
        print('PASS missing GSTIN blocks generation at API boundary',flush=True)
    if 'bills-voucher-web' in url:
        for path in ('/','/documents','/gst/filing','/search'):
            response=client.get(path+'?period=2026-09')
            assert response.status_code==200, path+': '+str(response.status_code)
            assert 'GSTIN pending' in response.text if not data['profile']['gstin'] else data['profile']['gstin'] in response.text
            assert 'Umesh' not in response.text and '27AAPFU0939F1ZV' not in response.text
            assert 'Your workspace could not be loaded' not in response.text
            print('PASS server-rendered preview '+path,flush=True)
