"""GST client-profile validation; secrets deliberately have no representation here."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from urllib.parse import urlsplit, urlunsplit
import re

from .validation import BASE36, GSTIN_RE, VALID_STATE_CODES


def website_url(value) -> str:
    """Validate a public website reference without fetching it or claiming ownership."""
    if not isinstance(value, str):
        raise ValueError('Enter a website URL as text.')
    value = value.strip()
    if not value:
        return ''
    if len(value) > 2000 or any(char.isspace() or ord(char) < 32 for char in value) or '\\' in value:
        raise ValueError('Enter a valid website URL, up to 2000 characters, without spaces.')
    if '://' not in value:
        value = 'https://' + value
    try:
        parts = urlsplit(value)
        host = (parts.hostname or '').encode('idna').decode('ascii').lower()
        port = parts.port
        labels = host.split('.')
        if (parts.scheme not in {'http', 'https'} or parts.username is not None or parts.password is not None
                or len(host) > 253 or len(labels) < 2 or labels[-1] in {'local','localhost','internal'}
                or labels[-1].isdigit() or port not in {None,80,443}
                or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels)):
            raise ValueError()
    except (ValueError, UnicodeError):
        raise ValueError('Use an http:// or https:// public website domain without login credentials or a custom port.') from None
    return urlunsplit((parts.scheme, host + (f':{port}' if port else ''), parts.path, parts.query, parts.fragment))


def company_checks(profile):
    profile = profile or {}
    gstin = str(profile.get('gstin') or '')
    validation = validate_gstin(gstin) if gstin else {'valid': False, 'message': 'No GSTIN saved.'}
    try:
        website = website_url(profile.get('website_url') or '')
    except ValueError:
        website = ''
    return {'gstin_format_valid': validation['valid'], 'gstin_format_message': validation['message'],
            'government_verification': 'not_connected', 'website_url': website,
            'website_ownership_verified': False,
            'official_search_url': 'https://services.gst.gov.in/services/searchtp'}


def validate_gstin(gstin: str | None) -> dict:
    value = (gstin or "").strip().upper()
    if not GSTIN_RE.fullmatch(value):
        return {"valid": False, "code": "GSTIN_FORMAT_FAIL", "message": "GSTIN format is invalid."}
    if value[:2] not in VALID_STATE_CODES:
        return {"valid": False, "code": "GST_STATE_CODE_FAIL", "message": "GSTIN state code is invalid."}
    total, factor = 0, 2
    for char in reversed(value[:14]):
        product = BASE36.index(char) * factor
        total += product // 36 + product % 36
        factor = 1 if factor == 2 else 2
    if BASE36[(36 - total % 36) % 36] != value[14]:
        return {"valid": False, "code": "GSTIN_CHECKSUM_FAIL", "message": "GSTIN checksum is invalid."}
    return {"valid": True, "code": "GSTIN_VALID", "message": "GSTIN format and checksum are valid.", "gstin": value,
            "pan": value[2:12], "state_code": value[:2], "entity_code": value[12]}


def prepare_profile(payload: dict, client_id: str, user_id: str) -> dict:
    result = validate_gstin(payload.get("gstin"))
    if not result["valid"]:
        raise ValueError(result["code"])
    supplied_pan = str(payload.get("pan") or result["pan"]).upper()
    if supplied_pan != result["pan"]:
        raise ValueError("GSTIN_PAN_MISMATCH")
    if not payload.get("legal_name"):
        raise ValueError("LEGAL_NAME_REQUIRED")
    now = datetime.now(timezone.utc).isoformat()
    return {**payload, "profile_id": str(uuid4()), "client_id": client_id, "gstin": result["gstin"], "pan": result["pan"],
            "state_code": result["state_code"], "entity_code": result["entity_code"], "effective_from": now,
            "effective_to": None, "is_current": True, "created_by": user_id, "created_at": now,
            "source": payload.get("source", "MANUAL"), "gstin_verified": False,
            **({'website_url': website_url(payload['website_url'])} if 'website_url' in payload else {})}
