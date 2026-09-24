"""Idempotent Red Taxi bootstrap; never log secret payloads."""
import json
import logging

from ...config import get_settings
from ...repository import FinanceRepository
from ...security import hash_password
from .medallion import Medallion, now, param
from .profiles import validate_gstin


def bootstrap(repo):
    raw = get_settings().red_taxi_client_bootstrap
    if not raw:
        return
    payload = json.loads(raw)
    gstin = str(payload.get("gstin") or "").strip().upper()
    if gstin and (not gstin.startswith("33") or not validate_gstin(gstin)["valid"]):
        logging.getLogger("bills_voucher").error("RED_TAXI_GSTIN_STATE_MISMATCH")
        raise RuntimeError("RED_TAXI_GSTIN_STATE_MISMATCH")
    client_id = FinanceRepository(repo).ensure_client_user(payload["email"], hash_password(payload["password"]), payload.get("client_name", "Red Taxi"))
    params = [param("client_id", client_id), param("email", payload["email"].lower())]
    repo.query(f"""BEGIN TRANSACTION;
      UPDATE `{repo.table('client_user_role')}` SET effective_to=CURRENT_TIMESTAMP(),is_current=FALSE
        WHERE client_id=@client_id AND email=@email AND is_current=TRUE AND role!='client';
      INSERT INTO `{repo.table('client_user_role')}` (email,client_id,role,effective_from,effective_to,is_current)
        SELECT @email,@client_id,'client',CURRENT_TIMESTAMP(),NULL,TRUE FROM UNNEST([1])
        WHERE NOT EXISTS (SELECT 1 FROM `{repo.table('client_user_role')}` WHERE client_id=@client_id AND email=@email AND is_current=TRUE);
      COMMIT TRANSACTION;""", params)
    store = Medallion(repo, client_id, now()[:7])
    existing = store.profile()
    # Preserve a verified, existing profile if the secret's GSTIN is deferred.
    if existing and ((not gstin and (not existing.get("gstin") or str(existing.get("gstin")).startswith("33"))) or (gstin and existing.get("gstin") == gstin)):
        return
    stamp = now()
    profile = {"profile_id": "red-taxi-" + (gstin or "pending"), "client_id": client_id,
               "gstin": gstin, "legal_name": payload.get("legal_name") or payload.get("client_name", "Red Taxi"),
               "trade_name": payload.get("trade_name") or payload.get("client_name", "Red Taxi"),
               "state_code": gstin[:2] or None, "business_nature": payload.get("business_nature", "passenger_transport"),
               "filing_frequency": payload.get("filing_frequency", "monthly"), "is_eco_9_5": bool(payload.get("is_eco_9_5", False)),
               "has_rcm_supplies": bool(payload.get("has_rcm_supplies", False)), "composition_flag": False,
               "itc_rate_restricted": bool(payload.get("itc_rate_restricted", False)),
               "status": "active" if gstin else "incomplete", "effective_from": stamp, "effective_to": None,
               "is_current": True, "source": "SECRET_BOOTSTRAP", "created_by": "bootstrap", "created_at": stamp}
    if existing:
        repo.query(f"UPDATE `{repo.table('gst_client_profile')}` SET is_current=FALSE,effective_to=CURRENT_TIMESTAMP() WHERE client_id=@client_id AND is_current=TRUE", params)
    store.upsert("gst_client_profile", profile, ["client_id", "profile_id"])
