"""Local browser-test backend. Never registered by the production application."""
import os
from types import SimpleNamespace
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from app.config import get_settings
from app.db import get_db
from app.routes import current_user
from app.routers import gst_bills

os.environ['GST_BILLS_ENABLED']='true'
get_settings.cache_clear()
items={}
objects={}
jobs={}
user=SimpleNamespace(id='browser-user',full_name='Browser User',email='browser@example.test',role='client')
profile={'legal_name':'Red Taxi','business_nature':'passenger_transport','gstin':'','filing_frequency':'monthly'}


class Store:
    def __init__(self,repo,client_id):self.client_id=client_id
    def list(self,period=None,status=None):
        return [i for i in items.values() if i.client_id==self.client_id and (not status or i.status==status)]
    def get(self,id):
        if id not in items or items[id].client_id!=self.client_id:raise HTTPException(404)
        return items[id]
    def save(self,invoice,*args,**kwargs):items[invoice.invoice_id]=invoice
    def job(self,id,payload=None):
        if payload is not None:jobs[id]=payload
        return jobs[id]
    def upload_object(self,content,doc,filename,layer,mime):
        ref=f'gs://test/{self.client_id}/{layer}/bills/{doc}/{filename}';objects[ref]=content;return ref
    def download_object(self,ref):return objects[ref]
    def usage(self,*args):pass


gst_bills.BillStore=Store
gst_bills.active_client=lambda *args:SimpleNamespace(id='browser-client')
gst_bills.profile_for=lambda *args:profile
gst_bills.can=lambda *args:True
gst_bills.FinanceRepository=lambda repo:SimpleNamespace(clients=lambda uid:[SimpleNamespace(id='browser-client',name='Red Taxi')])
app=FastAPI()
app.include_router(gst_bills.router)
app.dependency_overrides[get_db]=lambda:object()
app.dependency_overrides[current_user]=lambda:user


@app.get('/api/auth/csrf')
def csrf():return {'token':'local-browser-test'}


@app.post('/api/workspace/period')
def period():return {'ok':True}


@app.get('/api/health')
def health():return {'ok':True}
