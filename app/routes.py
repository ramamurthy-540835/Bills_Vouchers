from datetime import date
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from io import StringIO
import csv
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import Account, AccountType, Document, DocumentType, JournalEntry, User
from .security import hash_password, verify_password
from .services.accounting import account_balance, post_entry
from .services.documents import GCSObjectStore, create_document, validate_upload
from .services.ocr import review_update
from .services.razorpay import record_event, verify_signature
from .config import get_settings
from .services.reporting import balances, cash_flow, profit_and_loss

templates=Jinja2Templates(directory="app/templates")
router=APIRouter()

def current_user(request: Request, db: Session=Depends(get_db)) -> User:
    user_id=request.session.get("user_id")
    user=db.get(User,user_id) if user_id else None
    if not user or not user.is_active: raise HTTPException(401,"Please log in.")
    return user

def ctx(request, **kwargs): return {"request":request, **kwargs}

@router.get("/login")
def login_page(request: Request): return templates.TemplateResponse("login.html",ctx(request))
@router.post("/login")
def login(request: Request, email: str=Form(...), password: str=Form(...), db: Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==email.lower()))
    if not user or not verify_password(password,user.password_hash): return templates.TemplateResponse("login.html",ctx(request,error="Invalid email or password"),status_code=400)
    request.session["user_id"]=user.id; return RedirectResponse("/",303)
@router.post("/logout")
def logout(request: Request): request.session.clear(); return RedirectResponse("/login",303)

@router.get("/")
def dashboard(request: Request, db: Session=Depends(get_db), user: User=Depends(current_user)):
    accounts=db.scalars(select(Account).order_by(Account.code)).all()
    recent=db.scalars(select(JournalEntry).order_by(JournalEntry.created_at.desc()).limit(8)).all()
    return templates.TemplateResponse("dashboard.html",ctx(request,user=user,accounts=accounts,balances={a.id:account_balance(db,a) for a in accounts},recent=recent))

@router.get("/accounts")
def accounts(request: Request, db: Session=Depends(get_db), user: User=Depends(current_user)):
    rows=db.scalars(select(Account).order_by(Account.code)).all()
    return templates.TemplateResponse("accounts.html",ctx(request,user=user,accounts=rows,balances={a.id:account_balance(db,a) for a in rows},types=list(AccountType)))
@router.post("/accounts")
def create_account(code: str=Form(...), name: str=Form(...), account_type: AccountType=Form(...), db: Session=Depends(get_db), user: User=Depends(current_user)):
    if user.role.value == "viewer": raise HTTPException(403,"Viewer access is read-only.")
    db.add(Account(code=code.strip(),name=name.strip(),account_type=account_type))
    try: db.commit()
    except Exception: db.rollback(); raise HTTPException(400,"Account code and name must be unique.")
    return RedirectResponse("/accounts",303)

@router.get("/transactions")
def transactions(request: Request, db: Session=Depends(get_db), user: User=Depends(current_user)):
    return templates.TemplateResponse("transactions.html",ctx(request,user=user,accounts=db.scalars(select(Account).where(Account.is_active.is_(True)).order_by(Account.name)).all(),entries=db.scalars(select(JournalEntry).order_by(JournalEntry.entry_date.desc()).limit(100)).all()))
@router.post("/transactions")
def create_transaction(reference: str=Form(...), description: str=Form(...), amount: str=Form(...), debit_account_id: int=Form(...), credit_account_id: int=Form(...), entry_date: date=Form(...), db: Session=Depends(get_db), user: User=Depends(current_user)):
    if user.role.value == "viewer": raise HTTPException(403,"Viewer access is read-only.")
    try: post_entry(db,entry_date=entry_date,reference=reference.strip(),description=description.strip(),amount=Decimal(amount),debit_account_id=debit_account_id,credit_account_id=credit_account_id)
    except (ValueError,InvalidOperation) as exc: raise HTTPException(400,str(exc))
    return RedirectResponse("/transactions",303)

@router.get("/documents/upload")
def upload_document_page(request: Request, user: User=Depends(current_user)):
    return templates.TemplateResponse("document_upload.html",ctx(request,user=user,types=list(DocumentType)))

@router.post("/documents/upload")
async def upload_document(document_type: DocumentType=Form(...), file: UploadFile=File(...), db: Session=Depends(get_db), user: User=Depends(current_user)):
    if user.role.value == "viewer": raise HTTPException(403,"Viewer access is read-only.")
    payload,filename,mime=await validate_upload(file)
    document=create_document(db,user=user,document_type=document_type,filename=filename,mime_type=mime,payload=payload,store=GCSObjectStore(__import__("app.config",fromlist=["get_settings"]).get_settings().gcs_bucket_name))
    return {"document_id":document.id,"status":"Upload Successful. Processing Document...","gcs_uri":document.gcs_uri}

@router.get("/documents")
def documents(request: Request, db: Session=Depends(get_db), user: User=Depends(current_user)):
    return templates.TemplateResponse("documents.html",ctx(request,user=user,documents=db.scalars(select(Document).order_by(Document.uploaded_at.desc()).limit(100)).all()))

@router.get("/documents/{document_id}/review")
def review_document(document_id: str, request: Request, db: Session=Depends(get_db), user: User=Depends(current_user)):
    document=db.get(Document,document_id)
    if not document: raise HTTPException(404,"Document not found.")
    return templates.TemplateResponse("document_review.html",ctx(request,user=user,document=document,extraction=document.extraction))

@router.post("/documents/{document_id}/review")
def save_review(document_id: str, request: Request, vendor_name: str=Form(""), invoice_number: str=Form(""), subtotal: str=Form(""), cgst: str=Form(""), sgst: str=Form(""), igst: str=Form(""), total_amount: str=Form(""), db: Session=Depends(get_db), user: User=Depends(current_user)):
    document=db.get(Document,document_id)
    if not document or not document.extraction: raise HTTPException(404,"OCR extraction not found.")
    review_update(db,document.extraction,{"vendor_name":vendor_name,"invoice_number":invoice_number,"subtotal":subtotal,"cgst":cgst,"sgst":sgst,"igst":igst,"total_amount":total_amount})
    return RedirectResponse(f"/documents/{document_id}/review",303)

@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session=Depends(get_db)):
    raw_body=await request.body()
    if not verify_signature(raw_body,request.headers.get("X-Razorpay-Signature"),get_settings().razorpay_webhook_secret):
        raise HTTPException(400,"Invalid Razorpay webhook signature.")
    payment=record_event(db,raw_body)
    return {"status":"duplicate" if payment is None else "processed"}

@router.get("/reports")
def reports(request: Request, start: date|None=None, end: date|None=None, db: Session=Depends(get_db), user: User=Depends(current_user)):
    data=balances(db,start,end); pnl,revenue,expenses,profit=profit_and_loss(db,start,end)
    return templates.TemplateResponse("reports.html",ctx(request,user=user,start=start,end=end,data=data,pnl=pnl,revenue=revenue,expenses=expenses,profit=profit,cash=cash_flow(db,start,end)))

@router.get("/reports/export.csv")
def export_reports(start: date|None=None,end:date|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    output=StringIO(); writer=csv.writer(output); writer.writerow(["Account","Type","Balance"])
    for typ,rows in balances(db,start,end).items():
        for account,value in rows: writer.writerow([account.name,typ.value,f"{value:.2f}"])
    return StreamingResponse(iter([output.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=finance-report.csv"})

@router.get("/health")
def health(): return {"status":"ok"}

def bootstrap_admin(db: Session) -> None:
    if not db.scalar(select(User).limit(1)): db.add(User(email="admin@local",full_name="Administrator",password_hash=hash_password("ChangeMe123!"))); db.commit()
