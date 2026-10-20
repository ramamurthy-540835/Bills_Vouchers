"""Tenant-bound persisted intake; no implicit financial promotion."""

import hashlib
import json
from uuid import uuid5, NAMESPACE_URL
from datetime import datetime, timezone
from zipfile import BadZipFile
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from google.api_core.exceptions import BadRequest, Conflict
from app.db import get_db
from app.routes import current_user
from app.routers.gst_bills import scope
from app.gst.intake import parse, preview, MAX_BYTES, FIELDS
from app.services.gst.medallion import param, clean
from app.services.gst.medallion import period_value

router = APIRouter(prefix="/api/gst/bills/intake", tags=["Source intake"])


@router.post("/columns")
async def intake_columns(request: Request, file: UploadFile = File(...), repo=Depends(get_db), user=Depends(current_user)):
    scope(request, repo, user, "bills:write")
    try:
        rows = parse(await file.read(MAX_BYTES + 1), file.filename or "")
        if not rows or any(not isinstance(row, dict) for row in rows):
            raise ValueError()
        columns = sorted({str(key) for row in rows for key in row})
        if len(columns) > 100 or any(len(key) > 200 for key in columns):
            raise ValueError()
    except (ValueError, TypeError, KeyError, BadZipFile, StopIteration, UnicodeError):
        raise HTTPException(422, "Use a nonempty CSV, XLSX or JSON array with at most 100 named columns.") from None
    return {"columns": columns, "supported_fields": sorted(FIELDS),
            "suggested_mapping": {key: key for key in columns if key in FIELDS}}


@router.post("/preview")
async def intake_preview(
    request: Request,
    source: str = Form(...),
    mapping: str = Form("{}"),
    file: UploadFile = File(...),
    repo=Depends(get_db),
    user=Depends(current_user),
):
    scope(request, repo, user, "bills:write")
    content = await file.read(MAX_BYTES + 1)
    try:
        field_mapping = json.loads(mapping)
        if not isinstance(field_mapping, dict):
            raise ValueError()
        rows = parse(content, file.filename or "", field_mapping)
        result = preview(source, rows)
    except (ValueError, TypeError, KeyError, BadZipFile, StopIteration, UnicodeError):
        raise HTTPException(422, "Check the source, file format, size, column mapping and record schema.") from None
    return {
        **result,
        "accepted": result["accepted"][:25],
        "accepted_count": len(result["accepted"]),
        "source_hash": hashlib.sha256(content).hexdigest(),
        "preview_limit": 25,
    }


@router.post("/batches")
async def intake_batch(
    request: Request,
    source: str = Form(...),
    mapping: str = Form("{}"),
    file: UploadFile = File(...),
    repo=Depends(get_db),
    user=Depends(current_user),
):
    _, store = scope(request, repo, user, "bills:write")
    content = await file.read(MAX_BYTES + 1)
    return await run_in_threadpool(
        stage_batch, store, str(user.id), source, mapping, content, file.filename or "import.json"
    )


def stage_batch(store, actor, source, mapping, content, filename):
    """Storage round trips run off the ASGI event loop."""
    try:
        field_mapping = json.loads(mapping)
        if not isinstance(field_mapping, dict):
            raise ValueError()
        result = preview(source, parse(content, filename, field_mapping))
    except (ValueError, TypeError, KeyError, BadZipFile, StopIteration, UnicodeError):
        raise HTTPException(422, "Invalid source import. Preview and correct the file before retrying.") from None
    digest = hashlib.sha256(content + source.encode() + json.dumps(field_mapping, sort_keys=True).encode()).hexdigest()
    batch = str(uuid5(NAMESPACE_URL, store.client_id + ":intake:" + digest))
    existing = store.query(
        f"SELECT payload FROM {store.table('ops', 'bulk_import_batches')} WHERE client_id=@client_id AND batch_id=@batch",
        [param("batch", batch)],
    )
    if existing:
        return {"batch_id": batch, "replayed": True, "financial_records_created": 0}
    ref = store.upload_object(content, batch, filename, "bronze", "application/octet-stream")
    summary = {
        **result,
        "accepted_count": len(result["accepted"]),
        "accepted": None,
        "source_system": source,
        "source_hash": digest,
        "original_ref": ref,
        "status": "staged",
    }
    try:
        store.query(
            f"""BEGIN TRANSACTION;
          UPDATE {store.table("ops", "gst_bill_lock")} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
          ASSERT @@row_count=1 AS 'Storage guard missing';
          IF NOT EXISTS(SELECT 1 FROM {store.table("ops", "bulk_import_batches")} WHERE client_id=@client_id AND batch_id=@batch) THEN
            INSERT INTO {store.table("ops", "integration_source_records")}
            SELECT @client_id,@batch,JSON_VALUE(row,'$.source_system'),JSON_VALUE(row,'$.source_record_id'),
              CAST(JSON_VALUE(row,'$.source_version') AS INT64),JSON_VALUE(row,'$.source_hash'),PARSE_JSON(row),
              CASE WHEN EXISTS(SELECT 1 FROM {store.table("ops", "integration_source_records")} old
                   WHERE old.client_id=@client_id AND old.source_system=JSON_VALUE(row,'$.source_system')
                   AND old.source_record_id=JSON_VALUE(row,'$.source_record_id')
                   AND old.source_version>=CAST(JSON_VALUE(row,'$.source_version') AS INT64))
                   THEN 'duplicate_or_conflict' ELSE 'staged' END,CURRENT_TIMESTAMP()
            FROM UNNEST(JSON_QUERY_ARRAY(@records)) row;
            INSERT INTO {store.table("ops", "bulk_import_batches")}
            VALUES(@client_id,@batch,@actor,PARSE_JSON(@summary),CURRENT_TIMESTAMP());
          END IF;
          COMMIT TRANSACTION;""",
            [
                param("batch", batch),
                param("actor", actor),
                param("records", json.dumps(result["accepted"])),
                param("summary", json.dumps(summary)),
            ],
        )
    except (Conflict, BadRequest):
        raise HTTPException(
            409, "Import could not be committed. Retry the same file safely; financial records have not been changed."
        ) from None
    return {"batch_id": batch, "status": "staged", "financial_records_created": 0}


@router.get("/batches")
def intake_history(request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user)
    rows = store.query(f"""SELECT batch_id,created_at,payload FROM {store.table("ops", "bulk_import_batches")}
                      WHERE client_id=@client_id ORDER BY created_at DESC LIMIT 50""")
    return clean({"batches": [dict(row) for row in rows]})


@router.get("/batches/{batch_id}")
def intake_details(batch_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user)
    batches = store.query(
        f"SELECT payload FROM {store.table('ops', 'bulk_import_batches')} WHERE client_id=@client_id AND batch_id=@batch",
        [param("batch", batch_id)],
    )
    if not batches:
        raise HTTPException(404, "Import not found.")
    rows = store.query(
        f"""SELECT source_system,source_record_id,source_version,status,payload
        FROM {store.table("ops", "integration_source_records")}
        WHERE client_id=@client_id AND batch_id=@batch ORDER BY source_record_id LIMIT 10000""",
        [param("batch", batch_id)],
    )
    return clean({"batch_id": batch_id, "summary": batches[0]["payload"], "records": [dict(row) for row in rows]})


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


@router.get("/batches/{batch_id}/original")
def intake_original(batch_id: str, request: Request, repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user)
    rows = store.query(
        f"SELECT payload FROM {store.table('ops','bulk_import_batches')} WHERE client_id=@client_id AND batch_id=@batch",
        [param('batch', batch_id)])
    if len(rows) != 1:
        raise HTTPException(404, 'Import not found.')
    ref = decoded(rows[0]['payload']).get('original_ref', '')
    if not isinstance(ref, str) or not ref:
        raise HTTPException(404, 'Original source evidence is unavailable.')
    # BillStore enforces the current bucket, client UUID and bronze prefix.
    content = store.download_object(ref)
    import re
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', ref.rsplit('/', 1)[-1])[:180] or 'source.bin'
    return Response(content, media_type='application/octet-stream', headers={
        'Content-Disposition':f'attachment; filename="{filename}"',
        'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})


@router.post("/batches/{batch_id}/reconcile")
def reconcile_batch(batch_id: str, request: Request, period: str, repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user, "bills:write")
    period = period_value(period)
    return reconcile_staged(store, batch_id, period, str(user.id))


def reconcile_staged(store, batch_id, period, actor):
    from app.gst import returns
    from app.gst.schemas.invoice import GstInvoice
    from app.gst.source_reconciliation import reconcile

    batches = store.query(
        f"SELECT batch_id FROM {store.table('ops','bulk_import_batches')} WHERE client_id=@client_id AND batch_id=@batch",
        [param('batch', batch_id)])
    if len(batches) != 1:
        raise HTTPException(404, 'Import not found.')
    observed = datetime.now(timezone.utc).isoformat()
    source_digest = returns.fingerprint(store, period)
    sources = store.query(f"""SELECT batch_id,status,payload FROM {store.table('ops','integration_source_records')}
        WHERE client_id=@client_id AND (
          batch_id=@batch OR SUBSTR(JSON_VALUE(payload,'$.invoice_date'),1,7)=@period
          OR STRUCT(source_system,source_record_id) IN (
            SELECT AS STRUCT source_system,source_record_id
            FROM {store.table('ops','integration_source_records')}
            WHERE client_id=@client_id AND
              (batch_id=@batch OR SUBSTR(JSON_VALUE(payload,'$.invoice_date'),1,7)=@period)))
        ORDER BY created_at,source_system,source_record_id LIMIT 20001""",
        [param('batch', batch_id), param('period', period)])
    invoices = store.query(f"""SELECT payload FROM {store.table('gold','gst_invoice')}
        WHERE client_id=@client_id AND period=@period ORDER BY invoice_id LIMIT 10001""",
        [param('period', period)])
    if len(sources) > 20000 or len(invoices) > 10000:
        raise HTTPException(422, 'Reconciliation exceeds the bounded review limit. Narrow the period before retrying.')
    sources = [{**dict(row), 'payload': decoded(row['payload'])} for row in sources]
    records = [row for row in sources if row['batch_id'] == batch_id]
    related = [row for row in sources if row['batch_id'] != batch_id]
    canonical = [GstInvoice.model_validate(decoded(row['payload'])) for row in invoices]
    report = reconcile(records, related, canonical, store.client_id, period)
    digest = hashlib.sha256(json.dumps(
        {'batch': batch_id, 'period': period, 'sources': sources, 'canonical': source_digest},
        sort_keys=True, default=str).encode()).hexdigest()
    run_id = str(uuid5(NAMESPACE_URL, store.client_id + ':source-reconciliation:' + digest))
    report.update(run_id=run_id, batch_id=batch_id, observed_at=observed, source_digest=source_digest,
                  historical_snapshot=True,
                  source_evidence=[{'batch_id': row['batch_id'], **{key: row['payload'].get(key)
                      for key in ('source_system','source_record_id','source_version','source_hash')}} for row in sources])
    payload = json.dumps(report)
    if len(payload.encode()) > 5 * 1024 * 1024:
        raise HTTPException(422, 'Reconciliation evidence exceeds 5 MB. Use smaller import batches.')
    try:
        store.query(f"""BEGIN TRANSACTION;
            UPDATE {store.table('ops','gst_bill_lock')} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
            ASSERT @@row_count=1 AS 'Storage guard missing';
            ASSERT {returns.fingerprint_sql(store)}=@digest AS 'Source changed';
            INSERT INTO {store.table('ops','external_transaction_links')}
            SELECT @client_id,@batch,@period,@run,@actor,PARSE_JSON(@payload),CURRENT_TIMESTAMP()
            FROM UNNEST([1])
            WHERE NOT EXISTS(SELECT 1 FROM {store.table('ops','external_transaction_links')}
                             WHERE client_id=@client_id AND run_id=@run);
            COMMIT TRANSACTION;""",
            [param('batch', batch_id), param('period', period), param('run', run_id),
             param('actor', actor), param('payload', payload), param('digest', source_digest)])
    except (Conflict, BadRequest) as exc:
        if isinstance(exc, Conflict) or any(text in str(exc).lower() for text in ('source changed','concurrent','aborted')):
            raise HTTPException(409, 'The reconciliation snapshot could not be saved. Refresh and retry; no financial invoices were changed.') from None
        raise
    saved = store.query(f"""SELECT payload FROM {store.table('ops','external_transaction_links')}
        WHERE client_id=@client_id AND run_id=@run""", [param('run', run_id)])
    if len(saved) != 1:
        raise HTTPException(409, 'Reconciliation evidence is unavailable. Retry safely.')
    return clean(decoded(saved[0]['payload']))


@router.get("/batches/{batch_id}/reconciliations")
def reconciliation_history(batch_id: str, request: Request, period: str, repo=Depends(get_db), user=Depends(current_user)):
    _, store = scope(request, repo, user)
    period = period_value(period)
    rows = store.query(f"""SELECT run_id,actor_id,created_at,payload FROM {store.table('ops','external_transaction_links')}
        WHERE client_id=@client_id AND batch_id=@batch AND period=@period ORDER BY created_at DESC LIMIT 20""",
        [param('batch', batch_id), param('period', period)])
    return clean({'snapshots': [{**dict(row), 'payload': decoded(row['payload'])} for row in rows]})
