import json
from typing import Any
from sqlalchemy.orm import Session
from ..models import AuditLog

def log(db: Session, *, user_id: int | None, action: str, entity: str, entity_id: str | int | None=None, old: Any=None, new: Any=None) -> AuditLog:
    record=AuditLog(user_id=user_id,action=action,entity=entity,entity_id=str(entity_id) if entity_id is not None else None,old_value=json.dumps(old,default=str) if old is not None else None,new_value=json.dumps(new,default=str) if new is not None else None)
    db.add(record); db.commit(); return record
