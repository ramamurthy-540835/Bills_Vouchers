from datetime import date,datetime,timezone
from decimal import Decimal,InvalidOperation
from fastapi import APIRouter,Depends,File,Form,HTTPException,Request,UploadFile
from fastapi.responses import RedirectResponse,StreamingResponse
from fastapi.templating import Jinja2Templates
import csv
from io import StringIO
from .db import get_db
from .models import AccountType,DocumentType
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
def fr(repo): return FinanceRepository(repo)
@router.get('/login')
def login_page(request:Request): return templates.TemplateResponse('login.html',ctx(request))
@router.post('/login')
def login(request:Request,email:str=Form(...),password:str=Form(...),repo=Depends(get_db)):
    user=fr(repo).user_by_email(email)
    if not user or not verify_password(password,user.password_hash): return templates.TemplateResponse('login.html',ctx(request,error='Invalid email or password'),status_code=400)
    request.session['user_id']=user.id; fr(repo).audit(user.id,'login','user',user.id); return RedirectResponse('/',303)
@router.post('/logout')
def logout(request:Request): request.session.clear(); return RedirectResponse('/login',303)
@router.get('/')
def dashboard(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    accounts=fr(repo).accounts(); entries=fr(repo).recent_entries(); return templates.TemplateResponse('dashboard.html',ctx(request,user=user,accounts=accounts,balances={},entries=entries))
@router.get('/accounts')
def accounts(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    rows=fr(repo).accounts(); return templates.TemplateResponse('accounts.html',ctx(request,user=user,accounts=rows,balances={},types=list(AccountType)))
@router.post('/accounts')
def create_account(code:str=Form(...),name:str=Form(...),account_type:AccountType=Form(...),repo=Depends(get_db),user=Depends(current_user)):
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    from uuid import uuid4
    repo.insert('accounts',{'id':str(uuid4()),'code':code.strip(),'name':name.strip(),'account_type':account_type.value,'is_active':True,'created_at':datetime.now(timezone.utc).isoformat()},str(uuid4())); return RedirectResponse('/accounts',303)
@router.get('/transactions')
def transactions(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    return templates.TemplateResponse('transactions.html',ctx(request,user=user,accounts=fr(repo).accounts(True),entries=fr(repo).recent_entries(100)))
@router.post('/transactions')
def create_transaction(reference:str=Form(...),description:str=Form(...),amount:str=Form(...),debit_account_id:str=Form(...),credit_account_id:str=Form(...),entry_date:date=Form(...),repo=Depends(get_db),user=Depends(current_user)):
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    try: value=Decimal(amount)
    except InvalidOperation: raise HTTPException(400,'Amount must be numeric.')
    if value<=0 or debit_account_id==credit_account_id: raise HTTPException(400,'Use a positive amount and two different accounts.')
    from uuid import uuid4
    eid=str(uuid4()); now=datetime.now(timezone.utc).isoformat(); repo.insert('journal_entries',{'id':eid,'entry_date':entry_date.isoformat(),'reference':reference.strip(),'description':description.strip(),'source':'manual','status':'posted','created_at':now},eid)
    for aid,debit,credit in [(debit_account_id,value,Decimal(0)),(credit_account_id,Decimal(0),value)]: repo.insert('journal_lines',{'id':str(uuid4()),'journal_entry_id':eid,'account_id':aid,'debit':str(debit),'credit':str(credit)},str(uuid4()))
    fr(repo).audit(user.id,'post','journal_entry',eid); return RedirectResponse('/transactions',303)
@router.get('/documents/upload')
def upload_document_page(request:Request,user=Depends(current_user)): return templates.TemplateResponse('document_upload.html',ctx(request,user=user,types=list(DocumentType)))
@router.post('/documents/upload')
async def upload_document(document_type:DocumentType=Form(...),file:UploadFile=File(...),repo=Depends(get_db),user=Depends(current_user)):
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    payload,filename,mime=await validate_upload(file); d=create_document(fr(repo),user,document_type,filename,mime,payload,GCSObjectStore(get_settings().gcs_bucket_name)); return {'document_id':d.id,'status':'Upload successful. Call /documents/{document_id}/scan.','gcs_uri':d.gcs_uri}
@router.post('/documents/{document_id}/scan')
def scan_document(document_id:str,repo=Depends(get_db),user=Depends(current_user)):
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    d=fr(repo).document(document_id)
    if not d: raise HTTPException(404,'Document not found.')
    try: e=process_with_gemini(fr(repo),d,GCSObjectStore(d.bucket_name).download(d.object_path)); EmbeddingService(fr(repo)).index(d,e); fr(repo).audit(user.id,'scan','document',d.id)
    except Exception as exc: raise HTTPException(502,f'Processing failed: {exc}') from exc
    return {'document_id':d.id,'status':'needs_review','model':get_settings().gemini_model,'vector_indexed':True}
@router.get('/documents')
def documents(request:Request,repo=Depends(get_db),user=Depends(current_user)): return templates.TemplateResponse('documents.html',ctx(request,user=user,documents=fr(repo).documents()))
@router.get('/documents/search')
def document_search(q:str,top_k:int=10,repo=Depends(get_db),user=Depends(current_user)): return {'query':q,'results':EmbeddingService(fr(repo)).search(q,top_k)}
@router.get('/documents/{document_id}/review')
def review_document(document_id:str,request:Request,repo=Depends(get_db),user=Depends(current_user)):
    d=fr(repo).document(document_id)
    if not d: raise HTTPException(404,'Document not found.')
    return templates.TemplateResponse('document_review.html',ctx(request,user=user,document=d,extraction=d.extraction))
@router.post('/documents/{document_id}/review')
def save_review(document_id:str, vendor_name:str=Form(''),invoice_number:str=Form(''),subtotal:str=Form(''),cgst:str=Form(''),sgst:str=Form(''),igst:str=Form(''),total_amount:str=Form(''),repo=Depends(get_db),user=Depends(current_user)):
    from google.cloud import bigquery
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    sets='vendor_name=@vendor, invoice_number=@invoice, subtotal=@subtotal, cgst=@cgst, sgst=@sgst, igst=@igst, total_amount=@total'
    params=[bigquery.ScalarQueryParameter('vendor','STRING',vendor_name or None),bigquery.ScalarQueryParameter('invoice','STRING',invoice_number or None)]
    for n,v in [('subtotal',subtotal),('cgst',cgst),('sgst',sgst),('igst',igst),('total',total_amount)]: params.append(bigquery.ScalarQueryParameter(n,'NUMERIC',v or None))
    repo.query(f'UPDATE `{repo.table("document_extractions")}` SET {sets} WHERE document_id=@id',params+[bigquery.ScalarQueryParameter('id','STRING',document_id)]); fr(repo).audit(user.id,'review','document',document_id); return RedirectResponse(f'/documents/{document_id}/review',303)
@router.get('/reports')
def reports(request:Request,start:date|None=None,end:date|None=None,repo=Depends(get_db),user=Depends(current_user)):
    rows=repo.query(f'SELECT a.account_type,a.name,COALESCE(SUM(l.debit-l.credit),0) AS balance FROM `{repo.table("accounts")}` a LEFT JOIN `{repo.table("journal_lines")}` l ON a.id=l.account_id GROUP BY a.account_type,a.name ORDER BY a.account_type,a.name')
    data={t:[] for t in ['asset','liability','equity','income','expense']}
    for r in rows: data.setdefault(r.account_type,[]).append((type('Account',(),{'name':r.name})(),r.balance or Decimal('0')))
    pnl={}; revenue=expenses=profit=Decimal('0'); cash={}
    return templates.TemplateResponse('reports.html',ctx(request,user=user,start=start,end=end,data=data,pnl=pnl,revenue=revenue,expenses=expenses,profit=profit,cash=cash))

@router.get('/audit-logs')
def audit_logs(request:Request,repo=Depends(get_db),user=Depends(current_user)):
    if user.role!='admin': raise HTTPException(403,'Admin access is required.')
    return templates.TemplateResponse('audit_logs.html',ctx(request,user=user,rows=fr(repo).audit_logs()))
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
    return {'documents':len(fr(repo).documents()),'recent_documents':[_doc_json(x) for x in fr(repo).documents(8)],'status':'ok'}

@router.get('/api/documents')
def api_documents(repo=Depends(get_db),user=Depends(current_user)): return [_doc_json(x) for x in fr(repo).documents()]

@router.get('/api/documents/search')
def api_document_search(q:str,top_k:int=10,repo=Depends(get_db),user=Depends(current_user)): return {'query':q,'results':EmbeddingService(fr(repo)).search(q,top_k)}

@router.post('/api/documents/upload')
async def api_upload(document_type:DocumentType=Form(...),file:UploadFile=File(...),repo=Depends(get_db),user=Depends(current_user)):
    if user.role=='viewer': raise HTTPException(403,'Viewer access is read-only.')
    payload,filename,mime=await validate_upload(file); d=create_document(fr(repo),user,document_type,filename,mime,payload,GCSObjectStore(get_settings().gcs_bucket_name)); return _doc_json(d)

@router.post('/api/documents/{document_id}/scan')
def api_scan(document_id:str,repo=Depends(get_db),user=Depends(current_user)): return scan_document(document_id,repo,user)

@router.get('/api/documents/{document_id}')
def api_document(document_id:str,repo=Depends(get_db),user=Depends(current_user)):
    d=fr(repo).document(document_id)
    if not d: raise HTTPException(404,'Document not found.')
    return _doc_json(d)

@router.get('/health')
def health(): return {'status':'ok','persistence':'bigquery','vector_search':True}
@router.get('/api/health')
def api_health(): return {'status':'ok','persistence':'bigquery','vector_search':True}
