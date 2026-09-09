from datetime import date,datetime,timezone
from decimal import Decimal,InvalidOperation
from fastapi import APIRouter,Depends,File,Form,HTTPException,Request,UploadFile
from fastapi.responses import JSONResponse,RedirectResponse,StreamingResponse,Response
from fastapi.templating import Jinja2Templates
import csv
from io import StringIO
from .db import get_db
from .models import AccountType,DocumentType,Role
from .repository import FinanceRepository
from .security import hash_password,verify_password
from .services.documents import GCSObjectStore,create_document,validate_upload
from .services.gemini import process_with_gemini
from .services.embeddings import EmbeddingService
from .config import get_settings

templates=Jinja2Templates(directory='app/templates'); router=APIRouter()
def current_user(request:Request,repo=Depends(get_db)):
    user=FinanceRepository(repo).user_by_id(request.session.get('user_id'))
    if not user: raise HTTPException(401,'Please log in.')
    return user
def ctx(request,**kwargs): return {'request':request,**kwargs}
def page(name,request,status_code=200,**kwargs): return templates.TemplateResponse(request=request,name=name,context=ctx(request,**kwargs),status_code=status_code)
def fr(repo): return FinanceRepository(repo)
def active_client(request,repo,user):
    clients=fr(repo).clients(user.id)
    if not clients: raise HTTPException(403,'You do not have access to a client.')
    selected=request.session.get('client_id')
    client=next((c for c in clients if c.id==selected),clients[0])
    request.session['client_id']=client.id
    return client
def client_context(request,repo,user):
    client=active_client(request,repo,user)
    return client,fr(repo).clients(user.id)
def extract_upload(repo,document,payload):
    extraction=process_with_gemini(fr(repo),document,payload)
    try: EmbeddingService(fr(repo)).index(document,extraction)
    except Exception: pass
    return extraction
@router.get('/login')
def login_page(request:Request): return page('login.html',request)
@router.post('/login')
def login(request:Request,email:str=Form(...),password:str=Form(...),repo=Depends(get_db)):
    user=fr(repo).user_by_email(email)
    if not user or not verify_password(password,user.password_hash): return page('login.html',request,status_code=400,error='Invalid email or password')
    request.session['user_id']=user.id; return RedirectResponse('/',303)
@router.get('/signup')
def signup_page(request:Request): return page('signup.html',request)
@router.post('/signup')
def signup(request:Request,email:str=Form(...),full_name:str=Form(...),password:str=Form(...),repo=Depends(get_db)):
    email=email.strip().lower(); full_name=full_name.strip()
    if len(password)<8: return page('signup.html',request,status_code=400,error='Use a password with at least 8 characters.')
    if fr(repo).user_by_email(email): return page('signup.html',request,status_code=400,error='An account already exists for this email.')
    from uuid import uuid4
    user_id=str(uuid4())
    repo.insert('users',{'id':user_id,'email':email,'password_hash':hash_password(password),'full_name':full_name or email,'role':'admin','is_active':True,'created_at':datetime.now(timezone.utc).isoformat()},user_id)
    # New test users receive access to every existing client as administrators.
    for client in fr(repo).clients(): repo.insert('client_memberships',{'id':str(uuid4()),'client_id':client.id,'user_id':user_id,'access_role':'admin','is_active':True,'created_at':datetime.now(timezone.utc).isoformat()},str(uuid4()))
    request.session['user_id']=user_id
    return RedirectResponse('/',303)
@router.post('/logout')
def logout(request:Request): request.session.clear(); return RedirectResponse('/login',303)
@router.post('/clients/select')
def select_client(request:Request,client_id:str=Form(...),repo=Depends(get_db),user=Depends(current_user)):
    if not fr(repo).can_access_client(user.id,client_id): raise HTTPException(403,'You do not have access to this client.')
    request.session['client_id']=client_id; return RedirectResponse(request.headers.get('referer','/'),303)
@router.get('/')
def dashboard(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    client,clients=client_context(request,repo,user); accounts=fr(repo).accounts(client.id); entries=fr(repo).recent_entries(client.id)
    monthly=repo.query(f'''SELECT FORMAT_DATE('%Y-%m', entry_date) period, SUM(IF(a.account_type='income',l.credit-l.debit,0)) income, SUM(IF(a.account_type='expense',l.debit-l.credit,0)) expenses FROM `{repo.table('journal_entries')}` e JOIN `{repo.table('journal_lines')}` l ON e.id=l.journal_entry_id JOIN `{repo.table('accounts')}` a ON a.id=l.account_id WHERE e.client_id=@client AND entry_date >= DATE_SUB(CURRENT_DATE(),INTERVAL 12 MONTH) GROUP BY period ORDER BY period DESC''',[__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('client','STRING',client.id)])
    yearly=repo.query(f'''SELECT EXTRACT(YEAR FROM entry_date) year, SUM(IF(a.account_type='income',l.credit-l.debit,0)) income, SUM(IF(a.account_type='expense',l.debit-l.credit,0)) expenses FROM `{repo.table('journal_entries')}` e JOIN `{repo.table('journal_lines')}` l ON e.id=l.journal_entry_id JOIN `{repo.table('accounts')}` a ON a.id=l.account_id WHERE e.client_id=@client GROUP BY year ORDER BY year DESC''',[__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('client','STRING',client.id)])
    powerbi_rows=repo.query(f'''SELECT month,SUM(income) income,SUM(expense) expenses FROM `{repo.table("powerbi_finance_dashboard")}` WHERE client_id=@client GROUP BY month ORDER BY month''',[__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('client','STRING',client.id)])
    monthly_chart=[{'period':str(r.month),'income':float(r.income or 0),'expenses':float(r.expenses or 0)} for r in powerbi_rows]
    return page('dashboard.html',request,user=user,client=client,clients=clients,accounts=accounts,recent=entries,monthly=monthly,monthly_chart=monthly_chart,yearly=yearly)
@router.get('/accounts')
def accounts(request:Request,page_num:int=1,repo=Depends(get_db),user=Depends(current_user)):
    client,clients=client_context(request,repo,user); page_num=max(1,page_num); per_page=10
    total=repo.one(f'SELECT COUNT(*) n FROM `{repo.table("accounts")}` WHERE client_id=@client',[__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('client','STRING',client.id)]).n
    rows=fr(repo).accounts(client.id,limit=per_page,offset=(page_num-1)*per_page); return page('accounts.html',request,user=user,client=client,clients=clients,accounts=rows,types=list(AccountType),page_num=page_num,has_next=total>page_num*per_page)
@router.post('/accounts')
def create_account(code:str=Form(...),name:str=Form(...),account_type:AccountType=Form(...),repo=Depends(get_db),user=Depends(current_user)):
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    from uuid import uuid4
    client=active_client(request,repo,user); repo.insert('accounts',{'id':str(uuid4()),'client_id':client.id,'code':code.strip(),'name':name.strip(),'account_type':account_type.value,'is_active':True,'created_at':datetime.now(timezone.utc).isoformat()},str(uuid4())); fr(repo).audit(user.id,'create','account',code.strip(),client.id); return RedirectResponse('/accounts',303)
@router.get('/transactions')
def transactions(request:Request,page_num:int=1,repo=Depends(get_db),user=Depends(current_user)):
    client,clients=client_context(request,repo,user); page_num=max(1,page_num); per_page=10
    total=repo.one(f'SELECT COUNT(*) n FROM `{repo.table("journal_entries")}` WHERE client_id=@client',[__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('client','STRING',client.id)]).n
    entries=fr(repo).recent_entries(client.id,1000)[(page_num-1)*per_page:page_num*per_page]
    return page('transactions.html',request,user=user,client=client,clients=clients,accounts=fr(repo).accounts(client.id,True),entries=entries,page_num=page_num,has_next=total>page_num*per_page)
@router.post('/transactions')
def create_transaction(reference:str=Form(...),description:str=Form(...),amount:str=Form(...),debit_account_id:str=Form(...),credit_account_id:str=Form(...),entry_date:date=Form(...),repo=Depends(get_db),user=Depends(current_user)):
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    try: value=Decimal(amount)
    except InvalidOperation: raise HTTPException(400,'Amount must be numeric.')
    if value<=0 or debit_account_id==credit_account_id: raise HTTPException(400,'Use a positive amount and two different accounts.')
    from uuid import uuid4
    client=active_client(request,repo,user)
    if not all(fr(repo).account(a,client.id) for a in [debit_account_id,credit_account_id]): raise HTTPException(400,'Accounts must belong to the selected client.')
    eid=str(uuid4()); now=datetime.now(timezone.utc).isoformat(); repo.insert('journal_entries',{'id':eid,'client_id':client.id,'entry_date':entry_date.isoformat(),'reference':reference.strip(),'description':description.strip(),'source':'manual','status':'posted','created_at':now},eid)
    for aid,debit,credit in [(debit_account_id,value,Decimal(0)),(credit_account_id,Decimal(0),value)]: repo.insert('journal_lines',{'id':str(uuid4()),'journal_entry_id':eid,'account_id':aid,'debit':str(debit),'credit':str(credit)},str(uuid4()))
    fr(repo).audit(user.id,'post','journal_entry',eid,client.id); return RedirectResponse('/transactions',303)
@router.get('/expenses')
def expenses(request:Request,start:date|None=None,end:date|None=None,category:str|None=None,repo=Depends(get_db),user=Depends(current_user)):
    client,clients=client_context(request,repo,user); accounts=fr(repo).accounts(client.id,True)
    from google.cloud import bigquery
    params=[bigquery.ScalarQueryParameter('client','STRING',client.id),bigquery.ScalarQueryParameter('start','DATE',start),bigquery.ScalarQueryParameter('end','DATE',end),bigquery.ScalarQueryParameter('category','STRING',category or None)]
    sql=f'''SELECT e.entry_date,e.reference,e.description,a.name category,l.debit amount FROM `{repo.table('journal_entries')}` e JOIN `{repo.table('journal_lines')}` l ON e.id=l.journal_entry_id JOIN `{repo.table('accounts')}` a ON a.id=l.account_id WHERE e.client_id=@client AND e.source='expense' AND a.account_type='expense' AND (@start IS NULL OR e.entry_date>=@start) AND (@end IS NULL OR e.entry_date<=@end) AND (@category IS NULL OR a.name=@category) ORDER BY e.entry_date DESC LIMIT 100'''
    rows=repo.query(sql,params)
    categories=repo.query(f"SELECT name FROM `{repo.table('accounts')}` WHERE client_id=@client AND account_type='expense' ORDER BY name",[bigquery.ScalarQueryParameter('client','STRING',client.id)])
    chart_rows=repo.query(f'''SELECT a.name category,SUM(l.debit) amount FROM `{repo.table('journal_entries')}` e JOIN `{repo.table('journal_lines')}` l ON e.id=l.journal_entry_id JOIN `{repo.table('accounts')}` a ON a.id=l.account_id WHERE e.client_id=@client AND e.source='expense' AND a.account_type='expense' AND (@start IS NULL OR e.entry_date>=@start) AND (@end IS NULL OR e.entry_date<=@end) GROUP BY category ORDER BY amount DESC''',params[:3])
    chart_data=[{'category':r.category,'amount':float(r.amount or 0)} for r in chart_rows]
    return page('expenses.html',request,user=user,client=client,clients=clients,accounts=accounts,entries=rows,categories=categories,chart_rows=chart_data,start=start,end=end,category=category)
@router.post('/expenses')
def create_expense(reference:str=Form(...),description:str=Form(...),amount:str=Form(...),expense_account_id:str=Form(...),payment_account_id:str=Form(...),entry_date:date=Form(...),repo=Depends(get_db),user=Depends(current_user)):
    try: value=Decimal(amount)
    except InvalidOperation: raise HTTPException(400,'Amount must be numeric.')
    if value<=0 or expense_account_id==payment_account_id: raise HTTPException(400,'Use a positive amount and two different accounts.')
    from uuid import uuid4
    client=active_client(request,repo,user)
    if not all(fr(repo).account(a,client.id) for a in [expense_account_id,payment_account_id]): raise HTTPException(400,'Accounts must belong to the selected client.')
    eid=str(uuid4()); now=datetime.now(timezone.utc).isoformat()
    repo.insert('journal_entries',{'id':eid,'client_id':client.id,'entry_date':entry_date.isoformat(),'reference':reference.strip(),'description':description.strip(),'source':'expense','status':'posted','created_at':now},eid)
    for aid,debit,credit in [(expense_account_id,value,Decimal(0)),(payment_account_id,Decimal(0),value)]: repo.insert('journal_lines',{'id':str(uuid4()),'journal_entry_id':eid,'account_id':aid,'debit':str(debit),'credit':str(credit)},str(uuid4()))
    fr(repo).audit(user.id,'post','expense',eid,client.id); return RedirectResponse('/expenses',303)
@router.get('/documents/upload')
def upload_document_page(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    client,clients=client_context(request,repo,user); return page('document_upload.html',request,user=user,client=client,clients=clients,types=list(DocumentType))
@router.post('/documents/upload')
async def upload_document(document_type:DocumentType=Form(...),file:UploadFile=File(...),repo=Depends(get_db),user=Depends(current_user)):
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    client=active_client(request,repo,user); payload,filename,mime=await validate_upload(file); d=create_document(fr(repo),user,client,document_type,filename,mime,payload,GCSObjectStore(get_settings().gcs_bucket_name))
    try: extract_upload(repo,d,payload)
    except Exception as exc: return JSONResponse(status_code=202,content={'document_id':d.id,'status':'File stored in GCS and metadata stored in BigQuery. Extraction is pending.','gcs_uri':d.gcs_uri,'processing_error':str(exc)[:500]})
    return {'document_id':d.id,'status':'File stored in GCS and extracted details stored in BigQuery.','gcs_uri':d.gcs_uri}
@router.post('/documents/{document_id}/scan')
def scan_document(document_id:str,repo=Depends(get_db),user=Depends(current_user)):
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    client=active_client(request,repo,user); d=fr(repo).document(document_id,client.id)
    if not d: raise HTTPException(404,'Document not found.')
    try: e=process_with_gemini(fr(repo),d,GCSObjectStore(d.bucket_name).download(d.object_path)); EmbeddingService(fr(repo)).index(d,e); fr(repo).audit(user.id,'scan','document',d.id)
    except Exception as exc: raise HTTPException(502,f'Processing failed: {exc}') from exc
    return {'document_id':d.id,'status':'needs_review','model':get_settings().gemini_model,'vector_indexed':True}
@router.get('/documents')
def documents(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    client,clients=client_context(request,repo,user); return page('documents.html',request,user=user,client=client,clients=clients,documents=fr(repo).documents(client.id))
@router.get('/documents/search')
def document_search(q:str,top_k:int=10,repo=Depends(get_db),user=Depends(current_user)): return {'query':q,'results':EmbeddingService(fr(repo)).search(q,top_k)}
@router.get('/documents/{document_id}/review')
def review_document(document_id:str,request:Request,repo=Depends(get_db),user=Depends(current_user)):
    client,clients=client_context(request,repo,user); d=fr(repo).document(document_id,client.id)
    if not d: raise HTTPException(404,'Document not found.')
    return page('document_review.html',request,user=user,client=client,clients=clients,document=d,extraction=d.extraction)
@router.get('/documents/{document_id}/file')
def document_file(document_id:str,request:Request,repo=Depends(get_db),user=Depends(current_user)):
    client=active_client(request,repo,user); d=fr(repo).document(document_id,client.id)
    if not d: raise HTTPException(404,'Document not found.')
    return Response(GCSObjectStore(d.bucket_name).download(d.object_path),media_type=d.mime_type,headers={'Content-Disposition':f'inline; filename="{d.client_filename or d.original_filename}"'})
@router.post('/documents/{document_id}/review')
def save_review(document_id:str, vendor_name:str=Form(''),invoice_number:str=Form(''),subtotal:str=Form(''),cgst:str=Form(''),sgst:str=Form(''),igst:str=Form(''),total_amount:str=Form(''),repo=Depends(get_db),user=Depends(current_user)):
    from google.cloud import bigquery
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    client=active_client(request,repo,user)
    if not fr(repo).document(document_id,client.id): raise HTTPException(404,'Document not found.')
    try: computed=sum(Decimal(x or '0') for x in [subtotal,cgst,sgst,igst])
    except InvalidOperation: raise HTTPException(400,'Amounts must be numeric.')
    sets='vendor_name=@vendor, invoice_number=@invoice, subtotal=@subtotal, cgst=@cgst, sgst=@sgst, igst=@igst, total_amount=@total'
    params=[bigquery.ScalarQueryParameter('vendor','STRING',vendor_name or None),bigquery.ScalarQueryParameter('invoice','STRING',invoice_number or None)]
    for n,v in [('subtotal',subtotal),('cgst',cgst),('sgst',sgst),('igst',igst)]: params.append(bigquery.ScalarQueryParameter(n,'NUMERIC',v or '0'))
    params.append(bigquery.ScalarQueryParameter('total','NUMERIC',str(computed)))
    repo.query(f'UPDATE `{repo.table("document_extractions")}` SET {sets} WHERE document_id=@id',params+[bigquery.ScalarQueryParameter('id','STRING',document_id)]); fr(repo).audit(user.id,'review','document',document_id,client.id); return RedirectResponse(f'/documents/{document_id}/review',303)
@router.get('/reports')
def reports(request:Request,start:date|None=None,end:date|None=None,repo=Depends(get_db),user=Depends(current_user)):
    client,clients=client_context(request,repo,user)
    rows=repo.query(f'SELECT a.account_type,a.name,COALESCE(SUM(l.debit-l.credit),0) AS balance FROM `{repo.table("accounts")}` a LEFT JOIN `{repo.table("journal_lines")}` l ON a.id=l.account_id WHERE a.client_id=@client GROUP BY a.account_type,a.name ORDER BY a.account_type,a.name',[__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('client','STRING',client.id)])
    data={t:[] for t in ['asset','liability','equity','income','expense']}
    for r in rows: data.setdefault(r.account_type,[]).append((type('Account',(),{'name':r.name})(),r.balance or Decimal('0')))
    pnl={}; revenue=expenses=profit=Decimal('0'); cash={}
    return page('reports.html',request,user=user,client=client,clients=clients,start=start,end=end,data=data,pnl=pnl,revenue=revenue,expenses=expenses,profit=profit,cash=cash)

@router.get('/powerbi')
def powerbi_model(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    client,clients=client_context(request,repo,user)
    from google.cloud import bigquery
    rows=repo.query(f'''SELECT month,category,SUM(income) income,SUM(expense) expense,STRING_AGG(DISTINCT data_source) sources FROM `{repo.table("powerbi_finance_dashboard")}` WHERE client_id=@client GROUP BY month,category ORDER BY month,category''',[bigquery.ScalarQueryParameter('client','STRING',client.id)])
    chart_data=[{'month':str(x.month),'category':x.category,'income':float(x.income or 0),'expense':float(x.expense or 0),'sources':x.sources} for x in rows]
    return page('powerbi.html',request,user=user,client=client,clients=clients,rows=rows,chart_data=chart_data)
@router.get('/audit-logs')
def audit_logs(request:Request,page_num:int=1,repo=Depends(get_db),user=Depends(current_user)):
    if user.role!='admin': raise HTTPException(403,'Admin access is required.')
    client,clients=client_context(request,repo,user); page_num=max(1,page_num); per_page=50
    count=repo.one(f'SELECT COUNT(*) n FROM `{repo.table("audit_logs")}` WHERE client_id=@client',[__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('client','STRING',client.id)]).n
    return page('audit_logs.html',request,user=user,client=client,clients=clients,rows=fr(repo).audit_logs(client.id,per_page,(page_num-1)*per_page),page_num=page_num,has_next=count>page_num*per_page)
@router.get('/users')
def users(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    if user.role!='admin': raise HTTPException(403,'Admin access is required.')
    client,clients=client_context(request,repo,user)
    rows=repo.query(f"SELECT u.id,u.email,u.full_name,u.role,u.is_active,u.created_at,m.access_role,m.is_active membership_active FROM `{repo.table('client_memberships')}` m JOIN `{repo.table('users')}` u ON u.id=m.user_id WHERE m.client_id=@client ORDER BY u.created_at DESC",[__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('client','STRING',client.id)])
    return page('users.html',request,user=user,client=client,clients=clients,users=rows,roles=list(Role))
@router.post('/users/{user_id}')
def update_user(user_id:str,role:Role=Form(...),is_active:bool=Form(False),repo=Depends(get_db),user=Depends(current_user)):
    if user.role!='admin': raise HTTPException(403,'Admin access is required.')
    repo.query(f"UPDATE `{repo.table('users')}` SET role=@role,is_active=@active WHERE id=@id",[__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('role','STRING',role.value),__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('active','BOOL',is_active),__import__('google.cloud.bigquery',fromlist=['ScalarQueryParameter']).ScalarQueryParameter('id','STRING',user_id)])
    client=active_client(request,repo,user); fr(repo).audit(user.id,'update','user',user_id,client.id); return RedirectResponse('/users',303)
@router.get('/settings')
def settings_page(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    client,clients=client_context(request,repo,user); return page('settings.html',request,user=user,client=client,clients=clients)
@router.post('/settings')
def update_settings(request:Request,full_name:str=Form(...),new_password:str=Form(''),repo=Depends(get_db),user=Depends(current_user)):
    if new_password and len(new_password)<8: return page('settings.html',request,status_code=400,user=user,error='Use a password with at least 8 characters.')
    from google.cloud import bigquery
    if new_password: repo.query(f"UPDATE `{repo.table('users')}` SET full_name=@name,password_hash=@password WHERE id=@id",[bigquery.ScalarQueryParameter('name','STRING',full_name.strip()),bigquery.ScalarQueryParameter('password','STRING',hash_password(new_password)),bigquery.ScalarQueryParameter('id','STRING',user.id)])
    else: repo.query(f"UPDATE `{repo.table('users')}` SET full_name=@name WHERE id=@id",[bigquery.ScalarQueryParameter('name','STRING',full_name.strip()),bigquery.ScalarQueryParameter('id','STRING',user.id)])
    client=active_client(request,repo,user); fr(repo).audit(user.id,'update','profile',user.id,client.id); return RedirectResponse('/settings',303)
@router.post('/settings/client')
def update_client(request:Request,name:str=Form(...),code:str=Form(...),gstin:str=Form(''),address:str=Form(''),repo=Depends(get_db),user=Depends(current_user)):
    if user.role!='admin': raise HTTPException(403,'Admin access is required.')
    from google.cloud import bigquery
    client=active_client(request,repo,user)
    repo.query(f'UPDATE `{repo.table("clients")}` SET name=@name,code=@code,gstin=@gstin,address=@address WHERE id=@id',[bigquery.ScalarQueryParameter('name','STRING',name.strip()),bigquery.ScalarQueryParameter('code','STRING',code.strip().upper()),bigquery.ScalarQueryParameter('gstin','STRING',gstin.strip() or None),bigquery.ScalarQueryParameter('address','STRING',address.strip() or None),bigquery.ScalarQueryParameter('id','STRING',client.id)])
    fr(repo).audit(user.id,'update','client',client.id,client.id); return RedirectResponse('/settings',303)
@router.post('/settings/client/create')
def create_client(request:Request,name:str=Form(...),code:str=Form(...),repo=Depends(get_db),user=Depends(current_user)):
    if user.role!='admin': raise HTTPException(403,'Admin access is required.')
    from uuid import uuid4
    client_id=str(uuid4()); now=datetime.now(timezone.utc).isoformat()
    repo.insert('clients',{'id':client_id,'code':code.strip().upper(),'name':name.strip(),'gstin':None,'address':None,'is_active':True,'created_at':now},client_id)
    membership_id=str(uuid4()); repo.insert('client_memberships',{'id':membership_id,'client_id':client_id,'user_id':user.id,'access_role':'admin','is_active':True,'created_at':now},membership_id)
    request.session['client_id']=client_id; fr(repo).audit(user.id,'create','client',client_id,client_id); return RedirectResponse('/settings',303)
def _doc_json(d):
    e=d.extraction
    return {'id':d.id,'document_type':d.document_type.value,'status':d.status.value,'original_filename':d.original_filename,'mime_type':d.mime_type,'file_size':d.file_size,'gcs_uri':d.gcs_uri,'uploaded_at':str(d.uploaded_at),'processing_error':d.processing_error,'extraction':({'vendor_name':e.vendor_name,'invoice_number':e.invoice_number,'gstin':e.gstin,'subtotal':str(e.subtotal) if e.subtotal is not None else None,'cgst':str(e.cgst) if e.cgst is not None else None,'sgst':str(e.sgst) if e.sgst is not None else None,'igst':str(e.igst) if e.igst is not None else None,'total_amount':str(e.total_amount) if e.total_amount is not None else None,'line_items':[{k:getattr(x,k,None) for k in ('item_name','description','quantity','unit','unit_price','tax','discount','total')} for x in e.line_items]} if e else None)}

@router.post('/api/auth/login')
async def api_login(request:Request,repo=Depends(get_db)):
    body=await request.json(); user=fr(repo).user_by_email(str(body.get('email','')))
    if not user or not verify_password(str(body.get('password','')),user.password_hash): raise HTTPException(401,'Invalid email or password.')
    request.session['user_id']=user.id; fr(repo).audit(user.id,'login','user',user.id); return {'id':user.id,'email':user.email,'full_name':user.full_name,'role':user.role}

@router.post('/api/auth/logout')
def api_logout(request:Request): request.session.clear(); return {'ok':True}

@router.get('/api/auth/me')
def api_me(user=Depends(current_user)): return {'id':user.id,'email':user.email,'full_name':user.full_name,'role':user.role}

@router.get('/api/dashboard')
def api_dashboard(repo=Depends(get_db),user=Depends(current_user)):
    client=fr(repo).clients(user.id)[0]
    return {'client_id':client.id,'documents':len(fr(repo).documents(client.id)),'recent_documents':[_doc_json(x) for x in fr(repo).documents(client.id,8)],'status':'ok'}

@router.get('/api/documents')
def api_documents(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    return [_doc_json(x) for x in fr(repo).documents(active_client(request,repo,user).id)]

@router.get('/api/documents/search')
def api_document_search(q:str,top_k:int=10,repo=Depends(get_db),user=Depends(current_user)): return {'query':q,'results':EmbeddingService(fr(repo)).search(q,top_k)}

@router.post('/api/documents/upload')
async def api_upload(document_type:DocumentType=Form(...),file:UploadFile=File(...),repo=Depends(get_db),user=Depends(current_user)):
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    client=active_client(request,repo,user); payload,filename,mime=await validate_upload(file); d=create_document(fr(repo),user,client,document_type,filename,mime,payload,GCSObjectStore(get_settings().gcs_bucket_name))
    try: extract_upload(repo,d,payload)
    except Exception as exc: return JSONResponse(status_code=202,content={'document_id':d.id,'status':'uploaded','gcs_uri':d.gcs_uri,'processing_error':str(exc)[:500]})
    return _doc_json(fr(repo).document(d.id))

@router.post('/api/documents/{document_id}/scan')
def api_scan(document_id:str,repo=Depends(get_db),user=Depends(current_user)): return scan_document(document_id,repo,user)

@router.get('/api/documents/{document_id}')
def api_document(document_id:str,repo=Depends(get_db),user=Depends(current_user)):
    d=fr(repo).document(document_id,active_client(request,repo,user).id)
    if not d: raise HTTPException(404,'Document not found.')
    return _doc_json(d)

@router.get('/health')
def health(): return {'status':'ok','persistence':'bigquery','vector_search':True}
@router.get('/api/health')
def api_health(): return {'status':'ok','persistence':'bigquery','vector_search':True}
