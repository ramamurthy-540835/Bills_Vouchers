import csv
import logging
import mimetypes
from datetime import date
from decimal import InvalidOperation
from io import BytesIO, StringIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import Response
from openpyxl import Workbook
from pydantic import ValidationError

from app.db import get_db
from app.config import get_settings
from app.repository import FinanceRepository
from app.routes import active_client, current_user
from app.services.gst.account import can
from app.services.gst.medallion import Medallion, clean, period_value
from app.gst.schemas.invoice import GstInvoice
from app.gst.store import BillStore
from app.gst.template import template_bytes
from app.gst.validate_invoice import validate_invoice
from app.gst.file_checks import validate_file
from app.gst.report import calculate
from app.gst.matching import parse_gstr2b
from app.gst.jobs import enqueue, process_job, public_job
from app.services.tasks import verify_cloud_tasks_request

router = APIRouter(prefix='/api/gst/bills', tags=['Bills'])
logger = logging.getLogger(__name__)


def scope(request, repo, user, action='bills:read'):
    if not get_settings().gst_bills_enabled:
        raise HTTPException(404, 'Not found.')
    client = active_client(request, repo, user)
    if not can(user, action, client.id, repo):
        raise HTTPException(403, 'You do not have permission for this action.')
    return client, BillStore(repo, client.id)


def profile_for(repo, client_id, period):
    return Medallion(repo, client_id, period).profile() or {}


def safe_cell(value):
    value = str(value or '')
    return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value


def check_version(request, invoice):
    expected = request.headers.get('if-match')
    if expected and expected.strip('"') != str(invoice.version):
        raise HTTPException(409, 'This bill changed in another window. Reopen it before saving.')


@router.get('/template.xlsx')
def template(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    scope(request, repo, user)
    return Response(template_bytes(), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': "attachment; filename*=UTF-8''Bills%20%26%20Vouchers%20%E2%80%94%20GST%20Purchase%20Bills.xlsx"})


@router.post('/upload')
def upload(request: Request, files: list[UploadFile] = File(...), period: str = '', repo=Depends(get_db), user=Depends(current_user)):
    client, store = scope(request, repo, user, 'bills:write')
    period = period_value(period or date.today().strftime('%Y-%m'))
    profile = profile_for(repo, client.id, period)
    if not 1 <= len(files) <= 20:
        raise HTTPException(422, 'Choose between 1 and 20 bills.')
    content_files = []
    allowed = {'.pdf', '.jpg', '.jpeg', '.png', '.xlsx', '.csv'}
    for file in files:
        filename = Path((file.filename or 'bill').replace('\\', '/')).name
        if Path(filename).suffix.lower() not in allowed:
            raise HTTPException(422, 'Choose PDF, JPG, PNG, Excel or CSV files.')
        content = file.file.read(get_settings().max_upload_mb * 1024 * 1024 + 1)
        if not content or len(content) > get_settings().max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f'Each bill must be between 1 byte and {get_settings().max_upload_mb} MB.')
        if sum(len(c) for _, c in content_files) + len(content) > 25 * 1024 * 1024:
            raise HTTPException(413, 'Upload smaller batches, up to 25 MB per request.')
        try:
            validate_file(content, filename)
        except (ValueError, OSError):
            raise HTTPException(422, 'Check the file format and size. Use a valid PDF, photo or the provided spreadsheet template.') from None
        content_files.append((filename, content))
    job_id = str(uuid4())
    job = {'job_id': job_id, 'status': 'queued', 'actor_id': str(user.id), 'period': period, 'files': []}
    for filename, content in content_files:
        doc_id = str(uuid4())
        raw_ref = store.upload_object(content, doc_id, filename, 'bronze', mimetypes.guess_type(filename)[0] or 'application/octet-stream')
        job['files'].append({'filename': filename, 'doc_id': doc_id, 'raw_ref': raw_ref, 'status': 'reading', 'invoice_ids': []})
    store.job(job_id, job)
    if get_settings().gst_bills_queue:
        try:
            enqueue(str(client.id), job_id)
        except Exception:
            logger.exception('Bill job could not be queued')
            job['status'] = 'needs_attention'
            for entry in job['files']:
                entry.update(status='needs_attention', reason='Your original is saved, but reading could not start. Please retry this upload.')
            store.job(job_id, job)
            raise HTTPException(503, 'Your original bills were saved, but reading could not start. Please retry shortly.') from None
    else:
        process_job(store, profile, str(user.id), job)
    return public_job(job)


@router.post('/internal/process')
async def worker(request: Request, repo=Depends(get_db)):
    settings = get_settings()
    if not settings.gst_bills_enabled or not verify_cloud_tasks_request(request, settings.gst_bills_worker_audience or settings.gst_bills_worker_url, settings.gst_bills_worker_account):
        raise HTTPException(403, 'Access denied.')
    payload = await request.json()
    store = BillStore(repo, str(payload['client_id']))
    job = store.job(str(payload['job_id']))
    actor = FinanceRepository(repo).user_by_id(job['actor_id'])
    if actor:
        from app.services.gst.medallion import param
        role = repo.one(f"SELECT role FROM `{repo.table('client_user_role')}` WHERE client_id=@client_id AND email=@email AND is_current=TRUE ORDER BY effective_from DESC LIMIT 1", [param('client_id',store.client_id),param('email',actor.email.lower())])
        actor.role = str(role.role if role else actor.role).lower()
    if not actor or not can(actor, 'bills:write', store.client_id, repo):
        raise HTTPException(403, 'The uploader no longer has permission to save these bills.')
    from starlette.concurrency import run_in_threadpool
    await run_in_threadpool(process_job, store, profile_for(repo,store.client_id,job['period']), str(actor.id), job)
    return {'completed': True}


@router.get('/upload/{job_id}')
def progress(job_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user)
    return public_job(store.job(job_id))


@router.get('')
def list_bills(request: Request, period: str = '', status: str = '', repo=Depends(get_db), user=Depends(current_user)):
    client, store = scope(request, repo, user)
    period = period_value(period or date.today().strftime('%Y-%m'))
    return {'invoices': [i.model_dump(mode='json') for i in store.list(period, status)],
            'client_id': str(client.id), 'can_write': can(user, 'bills:write', client.id, repo)}


@router.get('/dashboard')
def dashboard(request: Request, period: str = '', repo=Depends(get_db), user=Depends(current_user)):
    client, store = scope(request, repo, user)
    period = period_value(period or request.session.get('period') or date.today().strftime('%Y-%m'))
    invoices = store.list(period)
    profile = profile_for(repo, client.id, period)
    calculation = calculate(invoices, profile, store.matching_rows(period))
    return clean({'client_id': str(client.id), 'period': period, 'profile': profile, 'sample': False,
        'user': {'id': str(user.id), 'full_name': user.full_name, 'email': user.email, 'role': user.role},
        'clients': [{'id': c.id, 'name': c.name} for c in FinanceRepository(repo).clients(user.id)],
        'can_write': can(user, 'bills:write', client.id, repo),
        'review_count': sum(i.status in {'needs_review', 'extracted'} for i in invoices),
        'bill_count': len(invoices), **calculation})


@router.post('/gstr2b')
async def import_gstr2b(request: Request, period: str, repo=Depends(get_db), user=Depends(current_user)):
    client, store = scope(request, repo, user, 'bills:write')
    period = period_value(period)
    content = await request.body()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, 'Choose a statement smaller than 10 MB.')
    try:
        records = parse_gstr2b(content, profile_for(repo, client.id, period), period)
    except (ValueError, TypeError, KeyError, InvalidOperation):
        raise HTTPException(422, 'Check that this is the GSTR-2B JSON for your GSTIN and selected period, without repeated invoices.') from None
    store.save_matching(period, records, user.id)
    return {'imported': len(records)}


@router.get('/working-papers')
def working_papers(request: Request, period: str, repo=Depends(get_db), user=Depends(current_user)):
    client, store = scope(request, repo, user)
    period = period_value(period)
    invoices = store.list(period)
    if any(i.sample for i in invoices):
        raise HTTPException(403, {'code': 'sample_data_blocked', 'message': 'Illustrations cannot be exported.'})
    report = calculate(invoices, profile_for(repo, client.id, period), store.matching_rows(period))
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'GST Easy summary'
    sheet.append(['Period', period])
    labels = {'eligible_credit': 'Usable Input Tax Credit', 'output_tax': 'GST Liability on Sales',
              'cash_required': 'Estimated GST Cash Requirement', 'non_gst': 'Purchases Without ITC',
              'recorded': 'As recorded in your bills', 'matched': 'After GSTR-2B Matching',
              'eligible': 'After ITC Eligibility Checks', 'noCredit': 'If No ITC Can Be Used'}
    for key, value in report['totals'].items():
        sheet.append([labels[key], str(value)])
    for key, value in report['scenarios'].items():
        sheet.append([labels[key], str(value)])
    decisions = workbook.create_sheet('Credit decisions')
    decisions.append(['Invoice', 'Supplier', 'Description', 'Matching', 'Eligibility', 'Rule', 'GST'])
    for row in report['decisions']:
        decisions.append([safe_cell(row[k]) for k in ('invoice_number', 'supplier_name', 'description', 'matching', 'eligibility', 'rule', 'tax')])
    output = BytesIO()
    workbook.save(output)
    return Response(output.getvalue(), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="GST-Easy-CA-working-papers-{period}.xlsx"'})


@router.get('/export')
def export(request: Request, period: str, format: str = 'xlsx', repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user)
    invoices = store.list(period_value(period))
    if any(i.sample for i in invoices):
        raise HTTPException(403, {'code': 'sample_data_blocked', 'message': 'Illustrations cannot be exported.'})
    headers = ['GSTIN of supplier', 'Trade/Legal name', 'Invoice number', 'Invoice type', 'Invoice Date', 'Invoice Value',
               'Place of supply', 'Supply Attract Reverse Charge', 'Taxable Value', 'Integrated Tax', 'Central Tax', 'State/UT Tax', 'Cess', 'ITC Availability']
    rows = [headers]
    for inv in invoices:
        if inv.direction != 'purchase' or inv.status != 'confirmed':
            continue
        rows.append([safe_cell(inv.supplier_gstin), safe_cell(inv.supplier_legal_name), safe_cell(inv.invoice_number),
                     inv.invoice_type, str(inv.invoice_date), str(inv.totals.invoice_total), inv.place_of_supply_state_code,
                     'Y' if inv.reverse_charge else 'N', *[str(getattr(inv.totals, f)) for f in ('taxable_value', 'igst', 'cgst', 'sgst', 'cess')], inv.itc.eligibility])
    if format == 'csv':
        stream = StringIO()
        csv.writer(stream).writerows(rows)
        data, mime = stream.getvalue().encode('utf-8-sig'), 'text/csv'
    elif format == 'xlsx':
        workbook = Workbook()
        workbook.active.title = 'Purchase register'
        for row in rows:
            workbook.active.append(row)
        buffer = BytesIO()
        workbook.save(buffer)
        data, mime = buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        raise HTTPException(422, 'Choose Excel or CSV.')
    return Response(data, media_type=mime, headers={'Content-Disposition': f'attachment; filename="GST-Easy-purchase-register-{period}.{format}"'})


@router.get('/{invoice_id}/original')
def original(invoice_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user)
    invoice = store.get(invoice_id)
    ref = invoice.extraction.raw_ref
    mime = mimetypes.guess_type(ref)[0] or 'application/octet-stream'
    return Response(store.download_object(ref), media_type=mime,
                    headers={'Content-Disposition': 'inline', 'Cache-Control': 'private, no-store'})


@router.get('/{invoice_id}')
def get_bill(invoice_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user)
    return store.get(invoice_id).model_dump(mode='json')


@router.patch('/{invoice_id}')
async def edit(invoice_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client, store = scope(request, repo, user, 'bills:write')
    previous = store.get(invoice_id)
    check_version(request, previous)
    body = await request.json()
    owned = {'client_id', 'invoice_id', 'source_doc_id', 'selected_period', 'extraction', 'itc', 'status', 'review_reasons', 'sample', 'version', 'supply_type'}
    if owned.intersection(body):
        raise HTTPException(422, 'Only bill details may be edited.')
    if 'reverse_charge_paid_reference' in body and user.role not in {'admin', 'tax_admin'}:
        raise HTTPException(403, 'A tax administrator must record reverse-charge payment evidence.')
    try:
        invoice = GstInvoice.model_validate({**previous.model_dump(), **body, 'version': previous.version+1})
    except ValidationError:
        raise HTTPException(422, 'Check the bill fields and enter amounts as decimal text.') from None
    period = invoice.invoice_date.strftime('%Y-%m') if invoice.invoice_date else previous.selected_period or date.today().strftime('%Y-%m')
    invoice = validate_invoice(invoice, profile_for(repo, client.id, period), store.list())
    store.save(invoice, user.id, 'edit', previous, period)
    return invoice.model_dump(mode='json')


@router.post('/{invoice_id}/confirm')
def confirm(invoice_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client, store = scope(request, repo, user, 'bills:write')
    previous = store.get(invoice_id)
    check_version(request, previous)
    if previous.sample:
        raise HTTPException(403, {'code': 'sample_data_blocked', 'message': 'Illustrations cannot be confirmed.'})
    period = (previous.invoice_date or date.today()).strftime('%Y-%m')
    invoice = validate_invoice(previous, profile_for(repo, client.id, period), store.list(), human_review=True)
    if invoice.review_reasons or previous.status == 'rejected':
        raise HTTPException(409, {'code': 'bill_needs_review', 'message': 'Resolve the highlighted bill details before confirming.'})
    invoice.status = 'confirmed'
    invoice.version += 1
    store.save(invoice, user.id, 'confirm', previous, period)
    return invoice.model_dump(mode='json')


@router.post('/{invoice_id}/reject')
def reject(invoice_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user, 'bills:write')
    previous = store.get(invoice_id)
    check_version(request, previous)
    invoice = previous.model_copy(deep=True)
    invoice.status = 'rejected'
    invoice.version += 1
    store.save(invoice, user.id, 'reject', previous, (previous.invoice_date or date.today()).strftime('%Y-%m'))
    return invoice.model_dump(mode='json')
