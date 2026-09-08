import hashlib,uuid
from datetime import datetime,timezone
from pathlib import Path
from fastapi import HTTPException,UploadFile
from ..config import get_settings
from ..models import DocumentStatus
ALLOWED_MIME={'image/jpeg','image/png','application/pdf'}; ALLOWED_EXT={'.jpg','.jpeg','.png','.pdf'}; MAGIC={'image/jpeg':(b'\xff\xd8\xff',),'image/png':(b'\x89PNG\r\n\x1a\n',),'application/pdf':(b'%PDF-',)}
class GCSObjectStore:
    def __init__(self,bucket): self.bucket=bucket
    def _bucket(self):
        from google.cloud import storage
        return storage.Client(project=get_settings().gcp_project_id).bucket(self.bucket)
    def upload(self,object_path,payload,mime_type):
        b=self._bucket().blob(object_path); b.upload_from_string(payload,content_type=mime_type,checksum='auto'); return f'gs://{self.bucket}/{object_path}'
    def download(self,object_path): return self._bucket().blob(object_path).download_as_bytes()
async def validate_upload(upload:UploadFile):
    filename=Path(upload.filename or '').name; ext=Path(filename).suffix.lower(); mime=upload.content_type or ''
    if ext not in ALLOWED_EXT or mime not in ALLOWED_MIME: raise HTTPException(400,'Only JPG, JPEG, PNG, and PDF documents are accepted.')
    data=await upload.read()
    if not data: raise HTTPException(400,'The uploaded file is empty.')
    if len(data)>get_settings().max_upload_mb*1024*1024: raise HTTPException(413,'The document exceeds the maximum upload size.')
    if not any(data.startswith(x) for x in MAGIC[mime]): raise HTTPException(400,'The file contents do not match its declared type.')
    return data,filename,mime
def create_document(repo,user,document_type,filename,mime,payload,store):
    from google.cloud import bigquery
    from uuid import uuid4
    checksum=hashlib.sha256(payload).hexdigest()
    if repo.document_by_checksum(checksum): raise HTTPException(409,'This document has already been uploaded.')
    s=get_settings()
    if not s.gcs_bucket_name: raise HTTPException(503,'GCS_BUCKET_NAME must be configured.')
    now=datetime.now(timezone.utc); did=str(uuid4()); path=f'finance-documents/{now:%Y/%m}/{did}/original{Path(filename).suffix.lower()}'
    try: uri=store.upload(path,payload,mime)
    except Exception as exc: raise HTTPException(502,f'Document storage failed: {exc}') from exc
    repo.bq.insert('documents',{'id':did,'document_type':document_type.value,'status':DocumentStatus.UPLOADED.value,'original_filename':filename,'mime_type':mime,'file_size':len(payload),'checksum_sha256':checksum,'bucket_name':s.gcs_bucket_name,'object_path':path,'gcs_uri':uri,'uploaded_by_id':str(user.id),'uploaded_at':now.isoformat(),'processing_error':None},did)
    return repo.document(did)
