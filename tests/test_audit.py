from app.models import User
from app.security import hash_password
from app.services.audit import log

def test_audit_log_keeps_actor_and_change(db):
    user=User(email="audit@example.com",full_name="Auditor",password_hash=hash_password("password")); db.add(user); db.commit()
    record=log(db,user_id=user.id,action="create",entity="account",entity_id="1000",new={"name":"Cash"})
    assert record.user_id==user.id and 'Cash' in record.new_value
