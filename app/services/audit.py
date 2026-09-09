def log(repo, *, user_id, action, entity, entity_id=None, old=None, new=None):
    return repo.audit(user_id, action, entity, entity_id)
