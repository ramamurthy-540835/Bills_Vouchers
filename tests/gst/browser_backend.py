"""Local browser-test backend. Never registered by the production application."""
import os
from types import SimpleNamespace
from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.sessions import SessionMiddleware
from app.config import get_settings
from app.db import get_db
from app.routes import current_user
from app.routers import gst_bills, gst_returns, gst_intake
from tests.gst import local_statements, local_businesses
from app.services.gst.profiles import company_checks
from app.services.access import navigation_permissions

os.environ['GST_BILLS_ENABLED']='true'
get_settings.cache_clear()
items={}
objects={}
jobs={}
auto_rules=[]
deleted_items={}
user=SimpleNamespace(id='browser-user',full_name='Browser User',email='browser@example.test',role='client')
profile={'legal_name':'Red Taxi','business_nature':'passenger_transport','gstin':'','filing_frequency':'monthly'}
mobile_service={'available':False}
persisted={'enabled':False,'path':'artifacts/gst_easy/report-fixtures.sqlite'}
profiles={'browser-client':profile,'browser-readonly':{**profile,'legal_name':'Synthetic Read Only'},
          'browser-sample':{**profile,'legal_name':'Synthetic Restricted Sample'}}

profiles.update(local_businesses.profiles(user.id))


def selected_client():
    id=getattr(user,'active_client','browser-client')
    return SimpleNamespace(id=id,name=profiles[id]['legal_name'],is_test=id=='browser-sample')

def selected_profile():
    value=profiles[selected_client().id]
    return {**value,'business_nature':'other','legal_name':'Synthetic Reports '+selected_client().id} if persisted['enabled'] else value



class Store:
    def query(self,*args):return auto_rules if 'SELECT policy FROM' in args[0] else []
    def table(self,*args):return 'synthetic.table'
    def assert_writable(self,period):pass
    def latest_period(self):return "2026-10"
    def __init__(self,repo,client_id):self.client_id=client_id
    def list(self,period=None,status=None):
        from tests.gst.persisted_reports import invoices
        source=invoices(persisted['path'],self.client_id) if persisted['enabled'] else items.values()
        return [i for i in source if i.client_id==self.client_id and (not status or i.status==status)
                and (not period or (str(i.invoice_date)[:7] if i.invoice_date else i.selected_period)==period)]
    def get(self,id):
        if persisted['enabled']:
            invoice=next((inv for inv in self.list() if inv.invoice_id==id),None)
            if invoice is None:raise HTTPException(404)
            return invoice
        if id not in items or items[id].client_id!=self.client_id:raise HTTPException(404)
        return items[id]
    def correction_queue(self,period,state='active',offset=0):
        rows=[]
        for invoice in self.list(period):
            stage=None
            if invoice.status=='rejected':
                stage=invoice.correction_state if invoice.correction_state in {'correction_requested','corrected'} else 'rejected'
            elif invoice.status=='needs_review' and invoice.correction_state=='resubmitted':
                stage='resubmitted'
            elif invoice.status=='confirmed' and invoice.correction_state=='approved':
                stage='approved'
            if stage and (stage==state or (state=='active' and stage!='approved')):
                rows.append({**invoice.model_dump(mode='json'),'correction_stage':stage})
        return {'invoices':rows[offset:offset+50],'has_more':len(rows)>offset+50}
    def save(self,invoice,*args,**kwargs):
        if persisted['enabled']:
            import sqlite3
            with sqlite3.connect(persisted['path']) as db:
                db.execute('INSERT OR REPLACE INTO invoices VALUES(?,?,?)',(invoice.invoice_id,self.client_id,invoice.model_dump_json()))
        else:items[invoice.invoice_id]=invoice
    def delete(self,invoice,*args):deleted_items[invoice.invoice_id]=invoice;del items[invoice.invoice_id]
    def deleted(self,period):return [i for i in deleted_items.values() if i.invoice_id not in items and i.client_id==self.client_id]
    def deleted_invoice(self,id):
        if id not in deleted_items or deleted_items[id].client_id!=self.client_id:raise HTTPException(404)
        return deleted_items[id]
    def job_history(self,period):return [job for job in jobs.values() if job['period']==period]
    def job(self,id,payload=None):
        if payload is not None:jobs[id]=payload
        return jobs[id]
    def upload_object(self,content,doc,filename,layer,mime):
        ref=f'gs://test/{self.client_id}/{layer}/bills/{doc}/{filename}';objects[ref]=content;return ref
    def download_object(self,ref,layer="bronze"):
        retained=local_statements.original(self.client_id,ref)
        if retained is not None:return retained
        if persisted['enabled']:
            from tests.gst.persisted_reports import original
            content=original(persisted['path'],ref)
            if content is None:raise HTTPException(404)
            return content
        return objects[ref]
    def usage(self,*args):pass
    def matching_rows(self,period):
        from tests.gst.persisted_reports import statements
        return statements(persisted['path'],self.client_id,period) if persisted['enabled'] else local_statements.records(self.client_id,period)
    def statement_history(self,period):return local_statements.history(self.client_id,period)
    def save_matching(self,period,records,actor,source=None):
        local_statements.save(self.client_id,period,records,actor,source,objects[source['raw_ref']])
    def claim_job(self,id,actor):return jobs[id]


def seed_auto_review(approved=True):
    from tests.gst.conftest import invoice as invoice_fixture, profile as profile_fixture
    selected = profile_fixture.__wrapped__()
    profiles[selected_client().id].update(selected)
    invoice = invoice_fixture.__wrapped__(selected)
    invoice.client_id=selected_client().id
    invoice.invoice_id='auto-synthetic'
    invoice.supplier_address='Synthetic supplier address, Tamil Nadu'
    invoice.recipient_address='Synthetic recipient address, Tamil Nadu'
    invoice.recipient_legal_name='Synthetic recipient'
    invoice.extraction.raw_ref=f'gs://test/{invoice.client_id}/bronze/original.csv'
    objects[invoice.extraction.raw_ref]=b'SYNTHETIC TEST INVOICE - NOT VALID FOR TAX FILING'
    items[invoice.invoice_id]=invoice
    auto_rules.clear()
    if approved:
        auto_rules.append({'policy':{'policy_id':'synthetic-review-only','approved_by':'synthetic-reviewer',
            'official_source':'SYNTHETIC_TEST_ONLY','identity_evidence':'synthetic-fixture',
            'review_status':'approved','supplier_gstin':invoice.supplier_gstin,'recipient_gstin':invoice.recipient_gstin,
            'hsn_sac':'8703','direction':'purchase','supply_type':'intra','place_of_supply':'33',
            'invoice_type':'tax_invoice','rate':'18','effective_from':'2026-09-01','effective_to':'2026-09-30',
            'review_expires_at':'2099-01-01T00:00:00+00:00'}})
    return {'invoice_id':invoice.invoice_id}


gst_bills.BillStore=Store
gst_bills.reconciliation_reviews.returns.fingerprint=lambda *args:'a'*64
gst_bills.dashboard_report.read_range=lambda store,months,evidence=True:{month:{'source_hash':'a'*64,
    'invoices':store.list(month),'statements':store.matching_rows(month),'filing':{'state':'draft','version':0}} for month in months}
gst_bills.active_client=lambda *args:selected_client()
gst_bills.profile_for=lambda *args:selected_profile()
gst_bills.can=lambda user,action,*args:action=='bills:read' or user.role!='viewer'
gst_bills.FinanceRepository=lambda repo:SimpleNamespace(clients=lambda uid:[SimpleNamespace(id=id,name=value['legal_name']) for id,value in profiles.items()])
app=FastAPI()
app.add_middleware(SessionMiddleware,secret_key="synthetic-local-browser-only")
app.include_router(gst_intake.router)
app.include_router(gst_bills.router)
# The browser harness has synthetic financial data. Keep the production guard:
# expose actual read routes, but never simulate approval or mutate real returns.
def local_return_scope(*args, **kwargs):
    client, store = gst_bills.scope(*args, **kwargs)
    client.is_test = True
    return client, store

gst_returns.scope = local_return_scope
gst_returns.profile_for = gst_bills.profile_for
app.include_router(gst_returns.router)
app.dependency_overrides[get_db]=lambda:object()
app.dependency_overrides[current_user]=lambda:user


@app.get('/api/local-preview')
def local_preview():
    """Open the synthetic local UI without real credentials; never shipped in app."""
    from fastapi.responses import RedirectResponse
    response=RedirectResponse('/settings/profile',status_code=303)
    response.set_cookie('session','local-browser-test',httponly=True,samesite='lax',max_age=3600)
    return response


@app.get('/api/auth/csrf')
def csrf():return {'token':'local-browser-test'}


@app.get('/api/settings/account')
def account_data():
    return {'client_id':getattr(user,'active_client','browser-client'),'profile':selected_profile(),
            'user':{'id':user.id,'email':user.email,'full_name':user.full_name,'role':user.role,
                    'mobile_number':'+919876543210','mobile_verified':False,'email_verified':True},
            'clients':[{'id':id,'name':value['legal_name']} for id,value in profiles.items()],
            'permissions':navigation_permissions(user,user.role=='client',selected_client()),'can_edit_profile':user.role!='viewer','is_owner':user.role=='client','require_otp':True,'mobile_verification_available':mobile_service['available'],
            'company_checks':company_checks(selected_profile())}


@app.post('/api/workspace/period')
def period():return {'ok':True}


@app.get('/api/health')
def health():return {'ok':True}


@app.post('/__test__/reset')
def reset():
    auto_rules.clear()
    local_statements.reset()
    local_businesses.reset()
    for cid in list(profiles):
        if cid not in {'browser-client','browser-readonly','browser-sample'}:
            del profiles[cid]
    persisted['enabled']=False
    items.clear();deleted_items.clear();objects.clear();jobs.clear();user.role='client';profile['gstin']=''
    mobile_service['available']=False
    user.is_platform_admin=False
    user.active_client='browser-client'
    return {'ok':True}


@app.post('/__test__/auto-review')
def auto_review_fixture(approved: bool = True):
    return seed_auto_review(approved)


@app.post('/__test__/sms-configured')
def sms_configured():
    mobile_service['available']=True
    return {'ok':True}


@app.post('/__test__/viewer')
def viewer():
    user.role='viewer'
    return {'ok':True}


@app.post('/__test__/role/{role}')
def change_role(role: str):
    if role not in {'client','viewer','tax_admin','admin'}:raise HTTPException(422)
    user.role=role
    user.is_platform_admin=role=='admin'
    return {'ok':True}


@app.get('/api/admin/workspace')
def admin_workspace():
    if not getattr(user,'is_platform_admin',False):raise HTTPException(403)
    return {'members':[{'full_name':'Synthetic Owner','email':'owner@example.invalid','access_role':'owner','is_active':True}],'events':[]}


@app.post('/api/workspace/client')
async def switch_client(request:Request):
    body=await request.json()
    if body.get('client_id') not in profiles:raise HTTPException(403)
    user.active_client=body['client_id']
    user.role='viewer' if user.active_client=='browser-readonly' else 'client'
    user.is_platform_admin=False
    return {'ok':True}


@app.post('/__test__/persisted-reports')
def persisted_reports():
    from tests.gst.persisted_reports import seed
    seed(persisted['path'])
    persisted['enabled']=True
    return {'ok':True,'storage':'local SQLite synthetic evidence'}


@app.post('/__test__/statement-profile')
def statement_profile():
    profile['gstin']='33ABCDE1234F1Z7'
    return {'ok':True}


@app.get('/api/businesses/current/gstin-verification')
def local_taxpayer_status():
    # Synthetic UI only; no credentials, storage mutations or external lookups.
    from app.services.gst.taxpayer_verification import presentation
    return {**presentation(selected_profile(),None,False,'manual'),'can_verify':False}


# These routes run production validation/services against an isolated local store.
# This harness does not replace production authentication or BigQuery acceptance.
@app.post('/api/settings/customers')
async def create_local_business(request: Request):
    from app.services.customer_workspace import create_customer
    if not request.cookies.get('session'):
        raise HTTPException(401, 'Sign in required')
    if request.headers.get('x-csrf-token') != 'local-browser-test':
        raise HTTPException(403, 'Invalid CSRF token')
    result = create_customer(local_businesses.Repository(), user, await request.json(),
                             storage_provisioner=local_businesses.storage)
    profiles.update(local_businesses.profiles(user.id))
    return result


@app.post('/api/settings/profile')
async def save_local_business(request: Request):
    from app.services.gst import account
    if not request.cookies.get('session'):
        raise HTTPException(401, 'Sign in required')
    if request.headers.get('x-csrf-token') != 'local-browser-test':
        raise HTTPException(403, 'Invalid CSRF token')
    account.active_client = lambda *args: selected_client()
    account.can = lambda actor, action, cid, repo: actor.role != 'viewer' and cid in local_businesses.profiles(actor.id)
    account.is_owner = lambda repo, actor, cid: cid in local_businesses.profiles(actor.id)
    account.Medallion = lambda *args: SimpleNamespace(profile=selected_profile)
    account.clear_cache = lambda *args: None
    result = await account.save_profile(request, local_businesses.Repository(), user)
    profiles.update(local_businesses.profiles(user.id))
    return result
