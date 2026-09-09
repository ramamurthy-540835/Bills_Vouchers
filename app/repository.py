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
    def clients(self, user_id=None):
        if user_id:
            sql=f'''SELECT c.* FROM `{self.bq.table("clients")}` c JOIN `{self.bq.table("client_memberships")}` m ON c.id=m.client_id WHERE m.user_id=@uid AND m.is_active=TRUE AND c.is_active=TRUE ORDER BY c.name'''
            return [ns(**self.d(r)) for r in self.bq.query(sql,[bigquery.ScalarQueryParameter('uid','STRING',str(user_id))])]
        return [ns(**self.d(r)) for r in self.bq.query(f'SELECT * FROM `{self.bq.table("clients")}` WHERE is_active=TRUE ORDER BY name')]
    def client(self, client_id):
        r=self.bq.one(f'SELECT * FROM `{self.bq.table("clients")}` WHERE id=@id AND is_active=TRUE',[bigquery.ScalarQueryParameter('id','STRING',str(client_id))]); return ns(**self.d(r)) if r else None
    def can_access_client(self,user_id,client_id):
        return bool(self.bq.one(f'SELECT 1 FROM `{self.bq.table("client_memberships")}` WHERE user_id=@u AND client_id=@c AND is_active=TRUE LIMIT 1',[bigquery.ScalarQueryParameter('u','STRING',str(user_id)),bigquery.ScalarQueryParameter('c','STRING',str(client_id))]))
    def accounts(self,client_id,active=False,limit=None,offset=0):
        where='AND a.is_active=TRUE' if active else ''
        sql=f'''SELECT a.*, COALESCE(b.current_balance,0) current_balance FROM `{self.bq.table("accounts")}` a LEFT JOIN `{self.bq.table("account_balances")}` b ON a.id=b.account_id WHERE a.client_id=@client {where} ORDER BY a.code'''
        params=[bigquery.ScalarQueryParameter('client','STRING',str(client_id))]
        if limit is not None: sql+=' LIMIT @limit OFFSET @offset'; params += [bigquery.ScalarQueryParameter('limit','INT64',limit),bigquery.ScalarQueryParameter('offset','INT64',offset)]
        return [self._account(r) for r in self.bq.query(sql,params)]
    def _account(self,r):
        a=ns(**self.d(r)); a.account_type=ns(value=a.account_type); return a
    def account(self,aid,client_id=None):
        params=[bigquery.ScalarQueryParameter('id','STRING',str(aid))]; scope=''
        if client_id: scope=' AND client_id=@client'; params.append(bigquery.ScalarQueryParameter('client','STRING',str(client_id)))
        r=self.bq.one(f'SELECT * FROM `{self.bq.table("accounts")}` WHERE id=@id{scope}',params); return ns(**self.d(r)) if r else None
    def documents(self,client_id,limit=100):
        rows=self.bq.query(f'SELECT * FROM `{self.bq.table("documents")}` WHERE client_id=@client ORDER BY uploaded_at DESC LIMIT @n',[bigquery.ScalarQueryParameter('client','STRING',str(client_id)),bigquery.ScalarQueryParameter('n','INT64',limit)]); out=[]
        for r in rows:
            d=ns(**self.d(r)); d.document_type=ns(value=d.document_type); d.status=ns(value=d.status); d.extraction=self.extraction(d.id); out.append(d)
        return out
    def document(self,did,client_id=None):
        params=[bigquery.ScalarQueryParameter('id','STRING',did)]; scope=''
        if client_id: scope=' AND client_id=@client'; params.append(bigquery.ScalarQueryParameter('client','STRING',str(client_id)))
        r=self.bq.one(f'SELECT * FROM `{self.bq.table("documents")}` WHERE id=@id{scope}',params)
        if not r: return None
        d=ns(**self.d(r)); d.document_type=ns(value=d.document_type); d.status=ns(value=d.status); d.extraction=self.extraction(d.id); return d
    def document_by_checksum(self,c): return self.bq.one(f'SELECT id FROM `{self.bq.table("documents")}` WHERE checksum_sha256=@c LIMIT 1',[bigquery.ScalarQueryParameter('c','STRING',c)])
    def extraction(self,did):
        r=self.bq.one(f'SELECT * FROM `{self.bq.table("document_extractions")}` WHERE document_id=@id LIMIT 1',[bigquery.ScalarQueryParameter('id','STRING',did)])
        if not r: return None
        e=ns(**self.d(r))
        rows=self.bq.query(f'SELECT * FROM `{self.bq.table("document_line_items")}` WHERE extraction_id=@id ORDER BY line_number',[bigquery.ScalarQueryParameter('id','STRING',str(e.id))]); e.line_items=[ns(**self.d(x)) for x in rows]; return e
    def recent_entries(self,client_id,limit=8): return [ns(**self.d(r)) for r in self.bq.query(f'SELECT * FROM `{self.bq.table("journal_entries")}` WHERE client_id=@client ORDER BY created_at DESC LIMIT @n',[bigquery.ScalarQueryParameter('client','STRING',str(client_id)),bigquery.ScalarQueryParameter('n','INT64',limit)])]
    def audit_logs(self,client_id,limit=50,offset=0): return [ns(**self.d(r)) for r in self.bq.query(f'SELECT * FROM `{self.bq.table("audit_logs")}` WHERE client_id=@client ORDER BY created_at DESC LIMIT @n OFFSET @offset',[bigquery.ScalarQueryParameter('client','STRING',str(client_id)),bigquery.ScalarQueryParameter('n','INT64',limit),bigquery.ScalarQueryParameter('offset','INT64',offset)])]
    def audit(self,uid,action,entity,eid=None,client_id=None):
        rid=str(uuid4()); self.bq.insert('audit_logs',{'id':rid,'client_id':str(client_id) if client_id else None,'user_id':str(uid) if uid else None,'action':action,'entity':entity,'entity_id':str(eid) if eid else None,'old_value':None,'new_value':None,'created_at':datetime.now(timezone.utc).isoformat()},rid)
