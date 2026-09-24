"""GST client-profile validation; secrets deliberately have no representation here."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .validation import BASE36, GSTIN_RE, VALID_STATE_CODES


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
            "source": payload.get("source", "MANUAL")}
