"""Tenant-bound persisted intake; no implicit financial promotion."""

import hashlib
import json
from uuid import uuid5, NAMESPACE_URL
from zipfile import BadZipFile
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from starlette.concurrency import run_in_threadpool
from google.api_core.exceptions import BadRequest, Conflict
from app.db import get_db
from app.routes import current_user
from app.routers.gst_bills import scope
from app.gst.intake import parse, preview, MAX_BYTES
from app.services.gst.medallion import param, clean

router = APIRouter(prefix="/api/gst/bills/intake", tags=["Source intake"])


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
