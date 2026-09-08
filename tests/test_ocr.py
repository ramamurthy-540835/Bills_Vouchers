from decimal import Decimal
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import Document, DocumentStatus, DocumentType, User
from app.security import hash_password
from app.services.ocr import process_result

def test_document_ai_result_is_saved_for_review():
    engine=create_engine("sqlite://"); Base.metadata.create_all(engine); db=sessionmaker(bind=engine)()
    user=User(email="a@b.c",full_name="A",password_hash=hash_password("password")); db.add(user); db.commit()
    doc=Document(id="d",document_type=DocumentType.BILL,status=DocumentStatus.PROCESSING,original_filename="a.jpg",mime_type="image/jpeg",file_size=3,checksum_sha256="a"*64,bucket_name="b",object_path="p",gcs_uri="gs://b/p",uploaded_by_id=user.id); db.add(doc); db.commit()
    def entity(t,v,props=[]): return SimpleNamespace(type_=t,mention_text=v,properties=props)
    result=SimpleNamespace(entities=[entity("supplier_name","Acme"),entity("total_amount","1,250.00")],text="Acme")
    extracted=process_result(db,doc,result)
    assert extracted.vendor_name=="Acme" and extracted.total_amount==Decimal("1250.00") and doc.status==DocumentStatus.NEEDS_REVIEW
