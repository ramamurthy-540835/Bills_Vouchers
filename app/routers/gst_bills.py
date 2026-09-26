import csv
import json
import logging
import mimetypes
from datetime import date
from decimal import Decimal
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
from app.services.gst.rules import HEADS, ZERO, set_off
from app.gst.extract import extract
from app.gst.schemas.invoice import GstInvoice, Extraction
from app.gst.store import BillStore
from app.gst.template import template_bytes
from app.gst.validate_invoice import validate_invoice

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
        content_files.append((filename, content))
    job_id = str(uuid4())
    job = {'job_id': job_id, 'status': 'reading', 'files': []}
    store.job(job_id, job)
    existing = store.list()
    for filename, content in content_files:
        doc_id = str(uuid4())
        entry = {'filename': filename, 'status': 'reading', 'invoice_ids': []}
        job['files'].append(entry)
        store.job(job_id, job)
        try:
            raw_ref = store.upload_object(content, doc_id, filename, 'bronze', mimetypes.guess_type(filename)[0] or 'application/octet-stream')
            try:
                invoices = extract(content, filename, str(client.id), doc_id, profile, raw_ref,
                                   lambda a, b: store.usage(doc_id, a, b))
            except Exception:
                logger.exception('Bill extraction needs review', extra={'client_id': str(client.id), 'source_doc_id': doc_id})
                invoices = [GstInvoice(client_id=str(client.id), source_doc_id=doc_id,
                    extraction=Extraction(raw_ref=raw_ref, confidence=Decimal('0')))]
                entry['reason'] = 'We could not read all the bill details. Open the bill and enter them, or upload the Excel template.'
            if not invoices:
                raise ValueError('The file contains no bill rows.')
            validated = []
            for invoice in invoices:
                invoice = validate_invoice(invoice, profile, existing)
                store.save(invoice, user.id, 'upload', selected_period=period)
                existing.append(invoice)
                validated.append(invoice.model_dump(mode='json'))
                entry['invoice_ids'].append(invoice.invoice_id)
            store.upload_object(json.dumps(validated).encode(), doc_id, 'invoice.json', 'silver', 'application/json')
            entry['status'] = 'needs_attention' if any(i['status'] in {'needs_review', 'rejected'} for i in validated) else 'ready'
        except Exception:
            logger.exception('Bill upload incomplete', extra={'client_id': str(client.id), 'source_doc_id': doc_id})
            entry.update(status='needs_attention', reason='This upload could not be completed. Review saved bills before retrying.')
        store.job(job_id, job)
    job['status'] = 'completed'
    store.job(job_id, job)
    return job


@router.get('/upload/{job_id}')
def progress(job_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user)
    return store.job(job_id)


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
    credit = {h: ZERO for h in HEADS}
    output = {h: ZERO for h in HEADS}
    non_gst = ZERO
    confirmed = [i for i in invoices if i.status == 'confirmed']
    for invoice in confirmed:
        sign = Decimal('-1') if invoice.invoice_type == 'credit_note' else Decimal('1')
        if invoice.direction == 'sale':
            for h in HEADS:
                output[h] += sign * getattr(invoice.totals, h)
        elif invoice.itc.eligibility == 'eligible':
            for h in HEADS:
                credit[h] += sign * getattr(invoice.totals, h)
        else:
            non_gst += sign * invoice.totals.invoice_total
    calculation = set_off({h: max(ZERO, v) for h, v in output.items()}, {h: max(ZERO, v) for h, v in credit.items()})
    return clean({'client_id': str(client.id), 'period': period, 'profile': profile, 'sample': False,
        'user': {'id': str(user.id), 'full_name': user.full_name, 'email': user.email, 'role': user.role},
        'clients': [{'id': c.id, 'name': c.name} for c in FinanceRepository(repo).clients(user.id)],
        'can_write': can(user, 'bills:write', client.id, repo),
        'confirmed_count': len(confirmed), 'review_count': sum(i.status in {'needs_review', 'extracted'} for i in invoices),
        'bill_count': len(invoices), 'totals': {'eligible_credit': sum(credit.values(), ZERO),
        'output_tax': sum(output.values(), ZERO), 'cash_required': calculation['cash_required'], 'non_gst': non_gst},
        'heads': {'credit': credit, 'output': output, 'cash': calculation['cash_by_head']},
        'utilisation': calculation['utilisation']})


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
    body = await request.json()
    owned = {'client_id', 'invoice_id', 'source_doc_id', 'extraction', 'itc', 'status', 'review_reasons', 'sample', 'version', 'supply_type'}
    if owned.intersection(body):
        raise HTTPException(422, 'Only bill details may be edited.')
    try:
        invoice = GstInvoice.model_validate({**previous.model_dump(), **body, 'version': previous.version+1})
    except ValidationError:
        raise HTTPException(422, 'Check the bill fields and enter amounts as decimal text.') from None
    period = (invoice.invoice_date or date.today()).strftime('%Y-%m')
    invoice = validate_invoice(invoice, profile_for(repo, client.id, period), store.list())
    store.save(invoice, user.id, 'edit', previous, period)
    return invoice.model_dump(mode='json')


@router.post('/{invoice_id}/confirm')
def confirm(invoice_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    client, store = scope(request, repo, user, 'bills:write')
    previous = store.get(invoice_id)
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
    invoice = previous.model_copy(deep=True)
    invoice.status = 'rejected'
    invoice.version += 1
    store.save(invoice, user.id, 'reject', previous, (previous.invoice_date or date.today()).strftime('%Y-%m'))
    return invoice.model_dump(mode='json')
