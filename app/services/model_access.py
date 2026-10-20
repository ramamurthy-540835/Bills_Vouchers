"""Explicit inference location and tenant allowlist for isolated acceptance."""
from app.config import get_settings


def model_location(client_id, settings=None):
    settings = settings or get_settings()
    allowed = {value.strip() for value in getattr(settings,'gemini_allowed_client_ids','').split(',') if value.strip()}
    location = getattr(settings,'gemini_location','') or settings.gcp_region
    if location == 'global' and not allowed:
        raise ValueError('Global AI processing requires an explicit business allowlist.')
    if allowed and str(client_id) not in allowed:
        raise ValueError('Automatic AI processing is not enabled for this business.')
    return location
