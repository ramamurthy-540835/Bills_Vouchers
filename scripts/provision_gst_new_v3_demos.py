"""Idempotent V3-only synthetic profile provisioning. No financial data seeded."""
import asyncio
import json
import os
import subprocess
from io import BytesIO
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from prepare_gst_new_v3 import PROJECT, REGION, PREFIX, ART, cloud


def main():
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GST_NEW_V3':
        raise RuntimeError('Wrong branch')
    os.environ.update(GCP_PROJECT_ID=PROJECT,GCP_REGION=REGION,BIGQUERY_DATASET=PREFIX+'finance_analytics',
        GST_DATASET_PREFIX=PREFIX,GCS_BUCKET_NAME=PROJECT+'-gst-easy-v3-documents',
        GST_BILLS_ENABLED='true',DEMO_OPERATOR_IDENTITY_ENABLED='true')
    from app.config import get_settings
    get_settings.cache_clear()
    from app.db import BigQueryRepository
    from app.repository import FinanceRepository
    from app.security import password_is_strong, verify_password
    from app.services.registration import register
    from app.services.customer_workspace import create_customer
    from app.services.gst.medallion import param
    from app.services.gst import account
    from google.cloud import bigquery, storage
    from google.oauth2.credentials import Credentials
    from starlette.requests import Request
    from fastapi import UploadFile
    credentials=Credentials(cloud('auth','print-access-token'))
    repo=object.__new__(BigQueryRepository)
    repo.settings=get_settings();repo.dataset=PROJECT+'.'+PREFIX+'finance_analytics'
    repo.client=bigquery.Client(project=PROJECT,credentials=credentials,location=REGION)
    if repo.client.get_dataset(repo.dataset).labels.get('application')!='gst-easy-v3':
        raise RuntimeError('Target is not the isolated V3 dataset')
    # Schema already exists from isolated V3 initialization; never migrate silently.
    fields={field.name for field in repo.client.get_table(repo.table('users')).schema}
    if not {'demo_operator_activated','identity_provenance'}<=fields:
        raise RuntimeError('Missing reviewed synthetic identity schema')
    bucket=storage.Client(project=PROJECT,credentials=credentials).bucket(repo.settings.gcs_bucket_name)
    finance=FinanceRepository(repo)
    reports=[]
    for name in ['naturelabs1','naturelabs']:
        root=Path('demo bills/naturelabs1') if name=='naturelabs1' else Path('demo bills')
        manifest=json.loads((root/'TEST_MANIFEST.json').read_text(encoding='utf-8'))
        businesses=[manifest['business']] if name=='naturelabs1' else manifest['businesses']
        if any(not b['is_test'] or b['gstin_verified'] or b['provenance']!='SYNTHETIC_TEST_ONLY' for b in businesses):
            raise RuntimeError('Invalid synthetic provenance')
        email=name+'@demo.com'
        password=cloud('secrets','versions','access','1','--secret='+'gst-easy-v3-'+name+'-password','--project',PROJECT)
        if not password_is_strong(password):
            raise RuntimeError('Password fails unchanged policy')
        user=finance.user_by_email(email)
        if not user:
            result=register(repo,dict(email=email,full_name='Nature Labs Demo User',
                business_name=businesses[0]['legal_name'],password=password,confirm=password,
                country_code='+91',mobile_number='9000000201' if name=='naturelabs1' else '9000000101',
                gstin=businesses[0]['gstin']))
            # No mail is sent to synthetic addresses. Operator activation is distinct
            # from actual mailbox verification.
            repo.query(f"UPDATE `{repo.table('auth_outbox')}` SET status='ignored' WHERE id=@id AND status='pending'",
                       [param('id',result['mail_id'])])
            user=finance.user_by_email(email)
        if not user or user.role!='client' or not verify_password(password,user.password_hash):
            raise RuntimeError('Existing identity differs; refusing to overwrite')
        del password
        def marker(cid):
            blob=bucket.blob(str(cid)+'/profile/workspace.json')
            if not blob.exists():
                blob.upload_from_string(json.dumps({'client_id':str(cid),'version':1}),
                                        content_type='application/json',if_generation_match=0)
        result=[]
        for business in businesses:
            matches=[c for c in finance.clients(user.id) if c.name==business['legal_name']]
            if len(matches)>1:
                raise RuntimeError('Duplicate authorized business names')
            if matches:
                cid=matches[0].id
            else:
                cid=create_customer(repo,user,dict(legal_name=business['legal_name'],gstin=business['gstin'],
                    website_url=business['website_url'],request_id=str(uuid5(NAMESPACE_URL,'v3-demo:'+name+business['key']))),
                    storage_provisioner=marker)['client_id']
            owners=repo.query(f"""SELECT client_id FROM `{repo.table('client_memberships')}`
                WHERE client_id=@cid AND user_id=@uid AND access_role='owner' AND is_active=TRUE""",
                [param('cid',cid),param('uid',user.id)])
            if len(owners)!=1:
                raise RuntimeError('Expected explicit owner membership')
            marker(cid)
            repo.query(f"UPDATE `{repo.table('clients')}` SET is_test=TRUE WHERE id=@cid",[param('cid',cid)])
            body={key:business[key] for key in ['legal_name','trade_name','website_url','constitution','registration_type',
                'filing_frequency','state_code','pan','principal_address','contact_email','contact_phone','gstin']}
            body.update(client_id=cid,contact_person='Nature Labs Demo Owner',complete_onboarding=True)
            request=Request({'type':'http','method':'POST','path':'/api/settings/profile','headers':[],
                             'session':{'user_id':user.id,'client_id':cid}})
            async def payload():
                return body
            request.json=payload
            asyncio.run(account.save_profile(request,repo,user))
            repo.query(f"""UPDATE `{repo.table('gst_client_profile')}` SET source='SYNTHETIC_TEST_ONLY',
                gstin_verified=FALSE,business_nature=@activity WHERE client_id=@cid AND is_current=TRUE""",
                [param('activity',business['business_nature']),param('cid',cid)])
            account.logo_blob=lambda client_id:bucket.blob(str(client_id)+'/profile/logo.png')
            logo_path=root/'logo.png' if name=='naturelabs1' else root/'logos'/(business['key']+'.png')
            account.upload_logo(request,UploadFile(filename=business['key']+'.png',file=BytesIO(logo_path.read_bytes())),repo,user)
            result.append({'client_id':str(cid),'business':business['legal_name'],'is_test':True,'gstin_verified':False})
        if len(finance.clients(user.id))!=len(businesses):
            raise RuntimeError('Unexpected memberships; refusing activation')
        repo.query(f"""UPDATE `{repo.table('users')}` SET demo_operator_activated=TRUE,
            identity_provenance='SYNTHETIC_TEST_ONLY' WHERE id=@uid;
            INSERT INTO `{repo.table('auth_events')}`
            SELECT GENERATE_UUID(),@uid,'synthetic_operator_activation',CURRENT_TIMESTAMP()
            FROM UNNEST([1]) WHERE NOT EXISTS(SELECT 1 FROM `{repo.table('auth_events')}`
            WHERE user_id=@uid AND action='synthetic_operator_activation');""",[param('uid',user.id)])
        report={'email':email,'businesses':result,'email_verified':False,'provenance':'SYNTHETIC_TEST_ONLY',
                'financial_rows_seeded':0,'password_delivery':'V3-only Secret Manager version 1'}
        (ART/(name+'-provisioning.json')).write_text(json.dumps(report,indent=2))
        reports.append(report)
    print(json.dumps(reports))


if __name__=='__main__':
    main()
