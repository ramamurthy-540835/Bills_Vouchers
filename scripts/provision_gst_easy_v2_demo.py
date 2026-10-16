"""Profiles-only V2 provisioning. NEVER uploads bills/statements or seeds totals."""
import argparse
import asyncio
import json
import os
from io import BytesIO
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from prepare_gst_easy_v2 import cloud, PROJECT, PREFIX, REGION


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true',required=True)
    parser.add_argument('--password-secret-version',required=True)
    args=parser.parse_args()
    expected=f'projects/{PROJECT}/secrets/gst-easy-v2-demo-password/versions/'
    if not args.password_secret_version.startswith(expected) or not args.password_secret_version[len(expected):].isdigit():
        raise RuntimeError('Use an explicit numeric version of the V2-only demo password secret')
    os.environ.update(GCP_PROJECT_ID=PROJECT,GCP_REGION=REGION,BIGQUERY_DATASET=PREFIX+'finance_analytics',GST_DATASET_PREFIX=PREFIX,
                      GCS_BUCKET_NAME=PROJECT+'-gst-easy-v2-documents',GST_BILLS_ENABLED='true',DEMO_OPERATOR_IDENTITY_ENABLED='true')
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
    settings=get_settings()
    if settings.bigquery_dataset!=PREFIX+'finance_analytics' or settings.gst_dataset_prefix!=PREFIX or settings.gcs_bucket_name!=PROJECT+'-gst-easy-v2-documents':
        raise RuntimeError('V2 isolation configuration mismatch')
    credentials=Credentials(cloud('auth','print-access-token'))
    repo=object.__new__(BigQueryRepository);repo.settings=settings;repo.dataset=PROJECT+'.'+settings.bigquery_dataset
    repo.client=bigquery.Client(project=PROJECT,credentials=credentials)
    # Enforce an explicit schema marker and never infer authorization from a GSTIN.
    dataset=repo.client.get_dataset(repo.dataset)
    if dataset.labels.get('application')!='gst-easy-v2':raise RuntimeError('Dataset is not labeled for V2')
    for field,kind in [('demo_operator_activated','BOOL'),('identity_provenance','STRING')]:
        repo.query(f'ALTER TABLE `{repo.table("users")}` ADD COLUMN IF NOT EXISTS {field} {kind}')
    password=cloud('secrets','versions','access',args.password_secret_version.rsplit('/',1)[1],
                   '--secret=gst-easy-v2-demo-password','--project',PROJECT)
    if not password_is_strong(password):raise RuntimeError('The secret fails the unchanged password policy; no account was created')
    manifest=json.loads(Path('demo bills/TEST_MANIFEST.json').read_text(encoding='utf-8'));businesses=manifest['businesses']
    if len(businesses)!=3 or any(not b['is_test'] or b['gstin_verified'] or b['provenance']!='SYNTHETIC_TEST_ONLY' for b in businesses):raise RuntimeError('Invalid synthetic profile manifest')
    finance=FinanceRepository(repo);email='naturelabs@demo.com';user=finance.user_by_email(email)
    if not user:
        register(repo,dict(email=email,full_name='Nature Labs Demo Administrator',business_name=businesses[0]['legal_name'],
                          password=password,confirm=password,country_code='+91',mobile_number='9000000101',gstin=businesses[0]['gstin']))
        user=finance.user_by_email(email)
    if not user or user.role!='client' or not verify_password(password,user.password_hash):raise RuntimeError('Existing demo identity does not match; refuse overwrite')
    del password
    bucket=storage.Client(project=PROJECT,credentials=credentials).bucket(settings.gcs_bucket_name)
    def marker(cid):
        blob=bucket.blob(cid+'/profile/workspace.json')
        if not blob.exists():blob.upload_from_string(json.dumps({'client_id':cid,'version':1}),content_type='application/json',if_generation_match=0)
    result=[]
    for b in businesses:
        matches=[c for c in finance.clients(user.id) if c.name==b['legal_name']]
        if len(matches)>1:raise RuntimeError('Duplicate demo membership; manual review required')
        if matches:cid=matches[0].id
        else:cid=create_customer(repo,user,dict(legal_name=b['legal_name'],gstin=b['gstin'],website_url=b['website_url'],
                 request_id=str(uuid5(NAMESPACE_URL,'gst-easy-v2-profile:'+b['key']))),storage_provisioner=marker)['client_id']
        marker(cid)
        repo.query(f"UPDATE `{repo.table('clients')}` SET is_test=TRUE WHERE id=@cid AND EXISTS(SELECT 1 FROM `{repo.table('client_memberships')}` WHERE client_id=@cid AND user_id=@uid AND access_role='owner' AND is_active=TRUE)",[param('cid',cid),param('uid',user.id)])
        body={key:b[key] for key in ['legal_name','trade_name','website_url','constitution','registration_type','filing_frequency','state_code','pan','principal_address','contact_email','contact_phone','gstin']}
        body.update(client_id=cid,contact_person='Nature Labs Demo Owner',complete_onboarding=True)
        request=Request({'type':'http','method':'POST','path':'/api/settings/profile','headers':[], 'session':{'user_id':user.id,'client_id':cid}})
        async def payload():return body
        request.json=payload
        asyncio.run(account.save_profile(request,repo,user))
        repo.query(f"UPDATE `{repo.table('gst_client_profile')}` SET source='SYNTHETIC_TEST_ONLY',gstin_verified=FALSE,business_nature=@activity WHERE client_id=@cid AND is_current=TRUE",[param('activity',b['business_nature']),param('cid',cid)])
        # Existing logo normalization and audit flow; only its storage dependency is V2-bound.
        account.logo_blob=lambda client_id:bucket.blob(str(client_id)+'/profile/logo.png')
        logo=UploadFile(filename=b['key']+'.png',file=BytesIO(Path('demo bills/logos',b['key']+'.png').read_bytes()))
        account.upload_logo(request,logo,repo,user)
        result.append({'client_id':cid,'business':b['legal_name'],'is_test':True,'gstin_verified':False})
    if len(finance.clients(user.id))!=3:raise RuntimeError('Demo identity has unexpected memberships')
    # Operator activation is explicit and V2-only. It is NOT email/mobile verification.
    repo.query(f"UPDATE `{repo.table('users')}` SET demo_operator_activated=TRUE,identity_provenance='SYNTHETIC_TEST_ONLY' WHERE id=@uid; INSERT INTO `{repo.table('auth_events')}` VALUES(GENERATE_UUID(),@uid,'synthetic_operator_activation',CURRENT_TIMESTAMP());",[param('uid',user.id)])
    report={'email':email,'businesses':result,'email_verified':False,'identity_source':'explicit V2 operator provisioning','financial_rows_seeded':0,'statements_imported':0,'password_delivery':'user-managed Secret Manager version; never logged'}
    Path('artifacts/gst_easy_v2/provisioning.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Provisioned exactly three V2 synthetic profiles. No invoices or statements imported.')


if __name__=='__main__':main()
