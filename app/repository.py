from datetime import datetime, timezone
from uuid import uuid4
from google.cloud import bigquery
from .models import ns
class FinanceRepository:
    def __init__(self,bq): self.bq=bq
    def d(self,row): return dict(row.items())
    def user_by_id(self,uid):
        if not uid: return None
        r=self.bq.one(f'SELECT * FROM `{self.bq.table("users")}` WHERE id=@id AND is_active=TRUE LIMIT 1',[bigquery.ScalarQueryParameter('id','STRING',str(uid))]); return ns(**self.d(r)) if r else None
    def user_by_email(self,email):
        r=self.bq.one(f'SELECT * FROM `{self.bq.table("users")}` WHERE email=@email LIMIT 1',[bigquery.ScalarQueryParameter('email','STRING',email.lower())]); return ns(**self.d(r)) if r else None
    def ensure_admin(self,password_hash):
        if not self.bq.one(f'SELECT id FROM `{self.bq.table("users")}` LIMIT 1'):
            rid=str(uuid4()); self.bq.insert('users',{'id':rid,'email':'admin@local','password_hash':password_hash,'full_name':'Administrator','role':'admin','is_active':True,'created_at':datetime.now(timezone.utc).isoformat()},rid)
    def accounts(self,active=False):
        where='WHERE is_active=TRUE' if active else ''; return [self._account(r) for r in self.bq.query(f'SELECT * FROM `{self.bq.table("accounts")}` {where} ORDER BY code')]
    def _account(self,r):
        a=ns(**self.d(r)); a.account_type=ns(value=a.account_type); return a
    def account(self,aid):
        r=self.bq.one(f'SELECT * FROM `{self.bq.table("accounts")}` WHERE id=@id',[bigquery.ScalarQueryParameter('id','STRING',str(aid))]); return ns(**self.d(r)) if r else None
    def documents(self,limit=100):
        rows=self.bq.query(f'SELECT * FROM `{self.bq.table("documents")}` ORDER BY uploaded_at DESC LIMIT @n',[bigquery.ScalarQueryParameter('n','INT64',limit)]); out=[]
        for r in rows:
            d=ns(**self.d(r)); d.document_type=ns(value=d.document_type); d.status=ns(value=d.status); d.extraction=self.extraction(d.id); out.append(d)
        return out
    def document(self,did):
        r=self.bq.one(f'SELECT * FROM `{self.bq.table("documents")}` WHERE id=@id',[bigquery.ScalarQueryParameter('id','STRING',did)])
        if not r: return None
        d=ns(**self.d(r)); d.document_type=ns(value=d.document_type); d.status=ns(value=d.status); d.extraction=self.extraction(d.id); return d
    def document_by_checksum(self,c): return self.bq.one(f'SELECT id FROM `{self.bq.table("documents")}` WHERE checksum_sha256=@c LIMIT 1',[bigquery.ScalarQueryParameter('c','STRING',c)])
    def extraction(self,did):
        r=self.bq.one(f'SELECT * FROM `{self.bq.table("document_extractions")}` WHERE document_id=@id LIMIT 1',[bigquery.ScalarQueryParameter('id','STRING',did)])
        if not r: return None
        e=ns(**self.d(r))
        rows=self.bq.query(f'SELECT * FROM `{self.bq.table("document_line_items")}` WHERE extraction_id=@id ORDER BY line_number',[bigquery.ScalarQueryParameter('id','STRING',str(e.id))]); e.line_items=[ns(**self.d(x)) for x in rows]; return e
    def recent_entries(self,limit=8): return [ns(**self.d(r)) for r in self.bq.query(f'SELECT * FROM `{self.bq.table("journal_entries")}` ORDER BY created_at DESC LIMIT @n',[bigquery.ScalarQueryParameter('n','INT64',limit)])]
    def audit_logs(self,limit=200): return [ns(**self.d(r)) for r in self.bq.query(f'SELECT * FROM `{self.bq.table("audit_logs")}` ORDER BY created_at DESC LIMIT @n',[bigquery.ScalarQueryParameter('n','INT64',limit)])]
    def audit(self,uid,action,entity,eid=None):
        rid=str(uuid4()); self.bq.insert('audit_logs',{'id':rid,'user_id':str(uid) if uid else None,'action':action,'entity':entity,'entity_id':str(eid) if eid else None,'old_value':None,'new_value':None,'created_at':datetime.now(timezone.utc).isoformat()},rid)
