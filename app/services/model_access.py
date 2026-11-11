"""Explicit inference location and tenant allowlist for isolated acceptance."""
from app.config import get_settings


class ModelAccessDenied(ValueError):
    """Processing policy denial, distinct from an unreadable document."""


def model_location(client_id, settings=None):
    settings = settings or get_settings()
    allowed = {value.strip() for value in getattr(settings,'gemini_allowed_client_ids','').split(',') if value.strip()}
    location = getattr(settings,'gemini_location','') or settings.gcp_region
    if location == 'global' and not allowed:
        raise ModelAccessDenied('Global AI processing requires an explicit business allowlist.')
    if allowed and str(client_id) not in allowed:
        raise ModelAccessDenied('Automatic AI processing is not enabled for this business.')
    return location


def extraction_model_location(client_id, settings=None):
    """Owner-approved global customer access applies only to invoice extraction."""
    settings=settings or get_settings()
    if not str(client_id or '').strip():
        raise ModelAccessDenied('An authorized business is required for document reading.')
    if (str(client_id or '').strip() and getattr(settings,'gemini_customer_extraction_global_enabled',False)
            and getattr(settings,'gemini_location','')=='global'):
        return 'global'
    return model_location(client_id,settings)
