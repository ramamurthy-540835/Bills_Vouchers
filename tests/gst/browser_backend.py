"""Local browser-test backend. Never registered by the production application."""
import os
from types import SimpleNamespace
from fastapi import FastAPI, HTTPException
from app.config import get_settings
from app.db import get_db
from app.routes import current_user
from app.routers import gst_bills

os.environ['GST_BILLS_ENABLED']='true'
get_settings.cache_clear()
items={}
objects={}
jobs={}
deleted_items={}
user=SimpleNamespace(id='browser-user',full_name='Browser User',email='browser@example.test',role='client')
profile={'legal_name':'Red Taxi','business_nature':'passenger_transport','gstin':'','filing_frequency':'monthly'}


class Store:
    def query(self,*args):return []
    def table(self,*args):return 'synthetic.table'
    def assert_writable(self,period):pass
    def __init__(self,repo,client_id):self.client_id=client_id
    def list(self,period=None,status=None):
        return [i for i in items.values() if i.client_id==self.client_id and (not status or i.status==status)]
    def get(self,id):
        if id not in items or items[id].client_id!=self.client_id:raise HTTPException(404)
        return items[id]
    def save(self,invoice,*args,**kwargs):items[invoice.invoice_id]=invoice
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
    def download_object(self,ref,layer="bronze"):return objects[ref]
    def usage(self,*args):pass
    def matching_rows(self,period):return []


gst_bills.BillStore=Store
gst_bills.reconciliation_reviews.returns.fingerprint=lambda *args:'a'*64
gst_bills.active_client=lambda *args:SimpleNamespace(id='browser-client')
gst_bills.profile_for=lambda *args:profile
gst_bills.can=lambda user,action,*args:action=='bills:read' or user.role!='viewer'
gst_bills.FinanceRepository=lambda repo:SimpleNamespace(clients=lambda uid:[SimpleNamespace(id='browser-client',name='Red Taxi')])
app=FastAPI()
app.include_router(gst_bills.router)
app.dependency_overrides[get_db]=lambda:object()
app.dependency_overrides[current_user]=lambda:user


@app.get('/api/auth/csrf')
def csrf():return {'token':'local-browser-test'}


@app.get('/api/settings/account')
def account_data():
    return {'client_id':'browser-client','profile':profile,
            'user':{'id':user.id,'email':user.email,'full_name':user.full_name,'role':user.role,
                    'mobile_number':'+919876543210','mobile_verified':False},
            'clients':[{'id':'browser-client','name':'Synthetic Business'}],
            'can_edit_profile':user.role!='viewer','is_owner':True,'require_otp':True}


@app.post('/api/workspace/period')
def period():return {'ok':True}


@app.get('/api/health')
def health():return {'ok':True}


@app.post('/__test__/reset')
def reset():
    items.clear();deleted_items.clear();objects.clear();jobs.clear();user.role='client';profile['gstin']=''
    return {'ok':True}


@app.post('/__test__/viewer')
def viewer():
    user.role='viewer'
    return {'ok':True}
