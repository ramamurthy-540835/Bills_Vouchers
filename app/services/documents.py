import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models import Document, DocumentStatus, DocumentType, User

ALLOWED_MIME={"image/jpeg", "image/png", "application/pdf"}
ALLOWED_EXT={".jpg", ".jpeg", ".png", ".pdf"}
MAGIC={"image/jpeg":(b"\xff\xd8\xff",),"image/png":(b"\x89PNG\r\n\x1a\n",),"application/pdf":(b"%PDF-",)}

class ObjectStore(Protocol):
    def upload(self, *, object_path: str, payload: bytes, mime_type: str) -> str: ...

class GCSObjectStore:
    def __init__(self, bucket_name: str): self.bucket_name=bucket_name
    def upload(self, *, object_path: str, payload: bytes, mime_type: str) -> str:
        try: from google.cloud import storage
        except ImportError as exc: raise RuntimeError("Install the cloud dependency group to use Google Cloud Storage.") from exc
        blob=storage.Client(project=get_settings().gcp_project_id).bucket(self.bucket_name).blob(object_path)
        blob.upload_from_string(payload, content_type=mime_type, checksum="auto")
        return f"gs://{self.bucket_name}/{object_path}"

async def validate_upload(upload: UploadFile) -> tuple[bytes,str,str]:
    filename=Path(upload.filename or "").name
    ext=Path(filename).suffix.lower()
    mime=upload.content_type or ""
    if ext not in ALLOWED_EXT or mime not in ALLOWED_MIME: raise HTTPException(400,"Only JPG, JPEG, PNG, and PDF documents are accepted.")
    payload=await upload.read()
    if not payload: raise HTTPException(400,"The uploaded file is empty.")
    if len(payload)>get_settings().max_upload_mb*1024*1024: raise HTTPException(413,"The document exceeds the maximum upload size.")
    if not any(payload.startswith(sig) for sig in MAGIC[mime]): raise HTTPException(400,"The file contents do not match its declared type.")
    return payload,filename,mime

def create_document(db: Session, *, user: User, document_type: DocumentType, filename: str, mime_type: str, payload: bytes, store: ObjectStore) -> Document:
    checksum=hashlib.sha256(payload).hexdigest()
    if db.scalar(select(Document).where(Document.checksum_sha256==checksum)): raise HTTPException(409,"This document has already been uploaded.")
    now=datetime.now(timezone.utc); document_id=str(uuid.uuid4()); suffix=Path(filename).suffix.lower()
    path=f"finance-documents/{now:%Y/%m}/{document_id}/original{suffix}"
    bucket=get_settings().gcs_bucket_name
    if not bucket: raise HTTPException(503,"GCS_BUCKET_NAME must be configured before uploads are enabled.")
    try: uri=store.upload(object_path=path,payload=payload,mime_type=mime_type)
    except Exception as exc: raise HTTPException(502,f"Document storage failed: {exc}") from exc
    document=Document(id=document_id,document_type=document_type,status=DocumentStatus.UPLOADED,original_filename=filename,mime_type=mime_type,file_size=len(payload),checksum_sha256=checksum,bucket_name=bucket,object_path=path,gcs_uri=uri,uploaded_by_id=user.id)
    db.add(document); db.commit(); db.refresh(document); return document
