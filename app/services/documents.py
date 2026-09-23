import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile

from ..config import get_settings
from ..models import DocumentStatus

ALLOWED_MIME = {"image/jpeg", "image/png", "application/pdf"}
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".pdf"}
MAGIC = {"image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG\r\n\x1a\n",), "application/pdf": (b"%PDF-",)}


class GCSObjectStore:
    def __init__(self, bucket):
        self.bucket = bucket

    def _bucket(self):
        from google.cloud import storage  # type: ignore[attr-defined]

        return storage.Client(project=get_settings().gcp_project_id).bucket(self.bucket)

    def upload(self, object_path, payload, mime_type):
        b = self._bucket().blob(object_path)
        b.upload_from_string(payload, content_type=mime_type, checksum="auto", timeout=get_settings().external_timeout_seconds)
        return f"gs://{self.bucket}/{object_path}"

    def download(self, object_path):
        return self._bucket().blob(object_path).download_as_bytes(timeout=get_settings().external_timeout_seconds)

    def signed_url(self, object_path, minutes: int = 5):
        return self._bucket().blob(object_path).generate_signed_url(version="v4", expiration=minutes * 60, method="GET")


async def validate_upload(upload: UploadFile):
    filename = Path(upload.filename or "").name
    ext = Path(filename).suffix.lower()
    mime = upload.content_type or ""
    if ext not in ALLOWED_EXT or mime not in ALLOWED_MIME:
        raise HTTPException(400, "Only JPG, JPEG, PNG, and PDF documents are accepted.")
    data = await upload.read()
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "The document exceeds the maximum upload size.")
    if not any(data.startswith(x) for x in MAGIC[mime]):
        raise HTTPException(400, "The file contents do not match its declared type.")
    return data, filename, mime


def create_document(repo, user, client, document_type, filename, mime, payload, store):
    from uuid import uuid4

    checksum = hashlib.sha256(payload).hexdigest()
    duplicate = repo.document_by_checksum(checksum, client.id)
    if duplicate:
        raise HTTPException(409, {"code": "DUPLICATE_DOCUMENT", "message": "This exact file has already been uploaded for this customer.", "document_id": str(duplicate.id)})
    s = get_settings()
    if not s.gcs_bucket_name:
        raise HTTPException(503, "GCS_BUCKET_NAME must be configured.")
    now = datetime.now(timezone.utc)
    did = str(uuid4())
    ext = Path(filename).suffix.lower()
    # A stable, human-readable file name is kept alongside a UUID.  The UUID
    # prevents collisions while the SHA-256 check prevents duplicate bills.
    stem = re.sub(r"[^a-z0-9]+", "-", Path(filename).stem.lower()).strip("-")[:80] or "document"
    customer_id = str(client.id)
    safe_type = document_type.value.replace(" ", "-").lower()
    generated_name = f"{safe_type}_{stem}_{now:%Y%m%dT%H%M%SZ}_{did[:8]}{ext}"
    # Bronze is immutable source evidence.  Silver/Gold are BigQuery-derived
    # records, preserving the original file while supporting clean/curated use.
    path = f"bronze/customer_id={customer_id}/document_type={safe_type}/ingest_date={now:%Y-%m-%d}/{did}/{generated_name}"
    try:
        uri = store.upload(path, payload, mime)
    except Exception as exc:
        raise HTTPException(502, f"Document storage failed: {exc}") from exc
    repo.bq.insert(
        "documents",
        {
            "id": did,
            "client_id": str(client.id),
            "document_type": document_type.value,
            "status": DocumentStatus.UPLOADED.value,
            "original_filename": filename,
            "client_filename": generated_name,
            "storage_layer": "BRONZE",
            "curated_filename": generated_name,
            "mime_type": mime,
            "file_size": len(payload),
            "checksum_sha256": checksum,
            "bucket_name": s.gcs_bucket_name,
            "object_path": path,
            "gcs_uri": uri,
            "uploaded_by_id": str(user.id),
            "uploaded_at": now.isoformat(),
            "processing_error": None,
        },
        did,
    )
    return repo.document(did)
