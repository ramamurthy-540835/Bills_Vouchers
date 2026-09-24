"""Tenant-bound medallion storage. Sample figures never enter this module."""
import hashlib
import json
import re
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
from threading import RLock
from time import monotonic
from typing import Any

from fastapi import HTTPException
from google.cloud import bigquery

from ...config import get_settings
from .rules import HEADS, ZERO, amount, common_reversal, heads, rule, set_off
from .validation import valid_gstin

_cache: dict[tuple, tuple[float, Any]] = {}
_cache_lock = RLock()


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def live_only(payload=None):
    if get_settings().demo_fallback or (payload and (payload.get("sample") or payload.get("mode") == "sample")):
        raise HTTPException(403, {"code": "sample_data_blocked", "message": "Sample data cannot be saved or exported."})


def period_value(value):
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", str(value)):
        raise HTTPException(422, "Period must be YYYY-MM.")
    return str(value)


def param(name, value, kind="STRING"):
    return bigquery.ScalarQueryParameter(name, kind, value)


def clear_cache(client_id, period=None):
    with _cache_lock:
        for key in list(_cache):
            if key[1] == client_id and (period is None or key[2] == period):
                del _cache[key]


class Medallion:
    def __init__(self, repo, client_id, period):
        self.repo = repo
        self.client_id = str(client_id)
        self.period = period_value(period)
        self.params = [param("client_id", self.client_id), param("period", self.period)]

    def rows(self, table, extra="", params=None, period=True):
        scope = "client_id=@client_id" + (" AND period=@period" if period else "")
        return [dict(r.items()) for r in self.repo.query(
            f"SELECT * FROM `{self.repo.table(table)}` WHERE {scope} {extra}", self.params + (params or []))]

    def profile(self):
        rows = self.rows("gst_client_profile", "AND is_current=TRUE ORDER BY effective_from DESC LIMIT 1", period=False)
        return rows[0] if rows else None

    def status(self):
        rows = self.rows("gst_filing_status", "AND is_current=TRUE ORDER BY effective_from DESC LIMIT 1")
        return rows[0] if rows else {"state": "draft"}

    def writable(self):
        live_only()
        if self.status()["state"] == "locked":
            raise HTTPException(409, "This filing period is locked.")

    def source_writable(self):
        self.writable()
        if self.status()["state"] != "draft":
            raise HTTPException(409, "Source data is frozen after validation. Start with a draft period.")

    def upsert(self, table, row, keys):
        """Parameterised DML, avoiding streaming buffers on immediately reviewed rows."""
        live_only(row)
        if row.get("client_id") != self.client_id:
            raise HTTPException(403, "Tenant mismatch.")
        row = clean(row)
        schema = self.repo.client.get_table(self.repo.table(table)).schema
        known = {f.name: f for f in schema}
        expressions = []
        for name in row:
            field = known[name]
            if field.mode == "REPEATED":
                expr = f"JSON_VALUE_ARRAY(@payload, '$.{name}')"
            elif field.field_type == "JSON":
                expr = f"JSON_QUERY(PARSE_JSON(@payload), '$.{name}')"
            else:
                kind = {"INTEGER": "INT64", "FLOAT": "FLOAT64", "BOOLEAN": "BOOL"}.get(field.field_type, field.field_type)
                expr = f"CAST(JSON_VALUE(@payload, '$.{name}') AS {kind})"
            expressions.append(f"{expr} AS `{name}`")
        # Names come only from server-owned schemas and callers, never request keys.
        on = " AND ".join(f"T.`{k}`=S.`{k}`" for k in keys)
        assignments = ", ".join(f"`{k}`=S.`{k}`" for k in row if k not in keys)
        columns = ", ".join(f"`{k}`" for k in row)
        values = ", ".join(f"S.`{k}`" for k in row)
        freshness = " AND S.computed_at >= T.computed_at" if table == 'gold_filing_summary' else ''
        self.repo.query(f"""MERGE `{self.repo.table(table)}` T
          USING (SELECT {', '.join(expressions)}) S ON T.client_id=@client_id AND {on}
          WHEN MATCHED{freshness} THEN UPDATE SET {assignments}
          WHEN NOT MATCHED THEN INSERT ({columns}) VALUES ({values})""",
          self.params + [param("payload", encode(row))])
        clear_cache(self.client_id, self.period)

    def workspace(self):
        key = (self.repo.dataset, self.client_id, self.period)
        with _cache_lock:
            saved = _cache.get(key)
            if saved and monotonic() - saved[0] < 300:
                return deepcopy(saved[1])
        profile = self.profile()
        bronze = self.rows("bronze_document", "ORDER BY uploaded_at DESC LIMIT 500")
        silver = self.rows("silver_invoice_header", "ORDER BY extracted_at DESC LIMIT 500")
        summaries = self.rows("gold_filing_summary", "LIMIT 1")
        summary = summaries[0] if summaries else None
        run_id = summary["run_id"] if summary else ""
        ledger = self.rows("gold_itc_ledger", "AND run_id=@run_id ORDER BY doc_id,line_no", [param("run_id", run_id)]) if run_id else []
        matches = self.rows("gold_gstr2b_match", "AND run_id=@run_id", [param("run_id", run_id)]) if run_id else []
        by_doc = {r["doc_id"]: r for r in silver}
        posted = {r["doc_id"] for r in ledger}
        documents = []
        for r in bronze:
            s = by_doc.get(r["doc_id"])
            stage = "In ledger" if r["doc_id"] in posted else "Validated" if s and s["validation_status"] == "validated" else "Extracted" if s else "Landed"
            documents.append({**r, "stage": stage, "silver": s})
        result = clean({"client_id": self.client_id, "period": self.period, "profile": profile,
                       "mode": "live" if summary else "empty", "documents": documents,
                       "counts": {"documents": len(bronze), "review": sum(r["validation_status"] == "needs_review" for r in silver),
                                  "posted": len(posted), "failed": sum(r["validation_status"] == "failed" for r in silver)},
                       "pipeline": {"bronze": len(bronze), "silver": len(silver), "gold": len(posted),
                                    "updated_at": max([r["uploaded_at"] for r in bronze] + [r["extracted_at"] for r in silver], default=None)},
                       "summary": summary, "ledger": ledger, "matches": matches,
                       "filing": self.status(), "has_silver": bool(silver),
                       "outward_count": len(self.rows("silver_outward_invoice"))})
        with _cache_lock:
            if len(_cache) >= 512:
                _cache.pop(next(iter(_cache)))
            _cache[key] = (monotonic(), result)
        return deepcopy(result)

    def recompute(self):
        self.source_writable()
        profile = self.profile() or {}
        headers = self.rows("silver_invoice_header", "AND validation_status='validated'")
        lines = self.rows("silver_invoice_line")
        imports = self.rows("silver_gstr2b_invoice")
        outward = self.rows("silver_outward_invoice")
        source_hash = hashlib.sha256(encode([profile, *[sorted(rows, key=encode) for rows in (headers, lines, imports, outward)], date.today()]).encode()).hexdigest()
        prior = self.rows("gold_filing_summary", "LIMIT 1")
        if prior and prior[0].get("input_hash") == source_hash:
            return clean(prior[0])
        # Content-derived revision: concurrent jobs cannot interleave different inputs in one run.
        revision = int(source_hash[:16], 16)
        run_id = f"itc_{self.period}_{profile.get('gstin') or 'pending'}_r{revision}"
        valid = {r["doc_id"]: r for r in headers}
        normalize = lambda s: re.sub(r"[^A-Z0-9]", "", str(s or "").upper())
        index = {(r["supplier_gstin"], normalize(r["invoice_no"])): r for r in imports}
        matched_keys, match_map = set(), {}
        stamp = now()
        for header in headers:
            key = (header["supplier_gstin"], normalize(header["invoice_no"]))
            match = index.get(key)
            delta = sum((abs(amount(header.get(h)) - amount(match.get(h))) for h in HEADS), ZERO) if match else ZERO
            status = "matched" if match and delta <= amount("1") else "amount_mismatch" if match else "unmatched_books"
            match_map[header["doc_id"]] = status
            if match:
                matched_keys.add(key)
            self.upsert("gold_gstr2b_match", {"client_id": self.client_id, "period": self.period, "doc_id": header["doc_id"], "supplier_gstin": key[0], "invoice_no": header["invoice_no"], "match_status": status, "delta": delta, "run_id": run_id, "computed_at": stamp}, ["client_id", "period", "doc_id", "run_id"])
        for key, row in index.items():
            if key not in matched_keys:
                self.upsert("gold_gstr2b_match", {"client_id": self.client_id, "period": self.period, "doc_id": "2b_" + hashlib.sha256(encode(key).encode()).hexdigest()[:24], "supplier_gstin": key[0], "invoice_no": row["invoice_no"], "match_status": "unmatched_2b", "delta": ZERO, "run_id": run_id, "computed_at": stamp}, ["client_id", "period", "doc_id", "run_id"])
        eligible, booked, restricted, late, output, eco = ({h: ZERO for h in HEADS} for _ in range(6))
        non_gst = ZERO
        for line in lines:
            if line["doc_id"] not in valid:
                continue
            header = valid[line["doc_id"]]
            taxes = heads(line)
            bucket, ref = rule({**line, "invoice_date": header["invoice_date"]}, profile, match_map[line["doc_id"]] == "matched")
            late_bucket, _ = rule({**line, "invoice_date": header["invoice_date"]}, profile, True)
            entry = {"client_id": self.client_id, "period": self.period, "doc_id": line["doc_id"], "line_no": line["line_no"], "run_id": run_id, "reason_code": bucket, "rule_ref": ref, "invoice_no": header["invoice_no"], "description": line["description"], "non_gst": ZERO, "computed_at": stamp}
            for group in ("eligible", "blocked", "deferred", "reversal"):
                for h in HEADS:
                    entry[f"{group}_{h}"] = taxes[h] if bucket == group else ZERO
            if bucket == "eligible":
                reversals, reversal_ref = common_reversal(line, profile, taxes)
                if reversal_ref:
                    missing = reversal_ref.endswith("BASIS-MISSING")
                    entry["rule_ref"] = reversal_ref
                    entry["reason_code"] = "deferred" if missing else "eligible"
                    for h in HEADS:
                        entry[f"eligible_{h}"] -= reversals[h]
                        entry[f"{'deferred' if missing else 'reversal'}_{h}"] += reversals[h]
            if bucket == "non_gst":
                entry["non_gst"] = amount(line.get("taxable_value"))
                non_gst += entry["non_gst"]
            else:
                for h in HEADS:
                    booked[h] += taxes[h]
                    if match_map[line["doc_id"]] == "matched":
                        restricted[h] += taxes[h]
                    if late_bucket == "eligible":
                        late[h] += taxes[h]
                    eligible[h] += entry[f"eligible_{h}"]
            self.upsert("gold_itc_ledger", entry, ["client_id", "period", "doc_id", "line_no", "run_id"])
        for row in outward:
            target = eco if row.get("eco_9_5") and profile.get("is_eco_9_5") else output
            for h in HEADS:
                target[h] += amount(row.get(h))
        settled = set_off(output, eligible, eco)
        summary = {"client_id": self.client_id, "period": self.period, "run_id": run_id, "input_hash": source_hash,
                   "as_booked": set_off(output, booked, eco)["cash_required"], "restricted_2b": set_off(output, restricted, eco)["cash_required"],
                   "fully_compliant": settled["cash_required"], "if_late_file": set_off(output, late, eco)["cash_required"],
                   "output_by_head": output, "eligible_by_head": eligible, "input_by_head": booked, "eco_by_head": eco,
                   "net_payable_by_head": settled["net_payable_by_head"], "cash_by_head": settled["cash_by_head"],
                   "cash_required": settled["cash_required"], "non_gst": non_gst, "computed_at": stamp}
        self.upsert("gold_filing_summary", summary, ["client_id", "period"])
        return clean(summary)

    def validate_filing(self):
        profile = self.profile() or {}
        if not valid_gstin(profile.get("gstin", "")):
            raise HTTPException(409, "Add a valid GSTIN to the client profile before filing.")
        if get_settings().gst_schema_version != "bv-draft-2026-09":
            raise HTTPException(409, "GST_SCHEMA_VERSION_MISMATCH")
        workspace = self.workspace()
        if not workspace["summary"]:
            raise HTTPException(409, "Run ITC computation first.")
        if workspace["counts"]["review"] or workspace["counts"]["failed"]:
            raise HTTPException(409, "Resolve invoice validation issues first.")
        if any(str(r["rule_ref"]).endswith("BASIS-MISSING") for r in workspace["ledger"]):
            raise HTTPException(409, "Set the period turnover basis for common-credit reversals.")
        if any(r["match_status"] == "amount_mismatch" for r in workspace["matches"]):
            raise HTTPException(409, "Resolve GSTR-2B amount differences first.")
        return workspace
