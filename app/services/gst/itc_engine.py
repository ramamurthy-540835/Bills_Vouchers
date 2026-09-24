"""Pure, Decimal-only ITC computation used by APIs and scenario comparisons."""
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Any

HEADS = ("igst", "cgst", "sgst", "cess")
ZERO = Decimal("0")

def d(value) -> Decimal: return Decimal(str(value or 0))
def money(value): return d(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def heads(row): return {h: d(row.get(h)) for h in HEADS}
def deadline(invoice_date: date):
    fy_end = invoice_date.year + 1 if invoice_date.month >= 4 else invoice_date.year
    return date(fy_end, 11, 30)
def compute_itc(data: dict) -> dict:
    profile, scenario = data.get("profile") or {}, data.get("scenario") or {}
    two_b = {(str(x.get("supplier_gstin", "")).upper(), str(x.get("invoice_number", "")).replace(" ", "").upper()): x for x in data.get("gstr2b", [])}
    totals: dict[str, dict[str, Any]] = {h: {"gross": ZERO, "ineligible_17_5": ZERO, "ineligible_16_2": ZERO, "reversal_rule_42": ZERO, "reversal_rule_43": ZERO, "reversal_rule_37": ZERO, "reclaimed": ZERO, "net_eligible": ZERO, "deferred_to_next": ZERO} for h in HEADS}
    lines: list[dict] = []
    warnings: list[str] = []
    today = date.today()
    for invoice in data.get("purchaseRegister", []):
        item = heads(invoice); key = (str(invoice.get("supplier_gstin", "")).upper(), str(invoice.get("invoice_number", "")).replace(" ", "").upper())
        match = two_b.get(key); status, reason = "MATCHED", None
        for h in HEADS: totals[h]["gross"] += item[h]
        if not invoice.get("has_tax_invoice", True): status, reason = "INELIGIBLE_16_2", "MISSING_TAX_INVOICE"
        elif not invoice.get("goods_or_services_received", True): status, reason = "INELIGIBLE_16_2", "GOODS_NOT_RECEIVED"
        elif not match and not scenario.get("allow_unmatched_2b", False): status, reason = "ITC_DEFERRED", "IN_BOOKS_NOT_IN_2B"
        elif match and not match.get("filing_status", True): status, reason = "INELIGIBLE_16_2", "SUPPLIER_RETURN_NOT_FILED"
        elif invoice.get("blocked_clause") and not invoice.get("override_justification"): status, reason = "INELIGIBLE_17_5", invoice["blocked_clause"]
        elif invoice.get("invoice_date") and today > deadline(date.fromisoformat(str(invoice["invoice_date"])[:10])): status, reason = "TIME_BARRED_16_4", "TIME_BARRED_16_4"
        elif invoice.get("unpaid_days", 0) > 180: status, reason = "REVERSED_RULE_37", "RULE_37"
        for h in HEADS:
            if status == "INELIGIBLE_16_2" or status == "TIME_BARRED_16_4": totals[h]["ineligible_16_2"] += item[h]
            elif status == "INELIGIBLE_17_5": totals[h]["ineligible_17_5"] += item[h]
            elif status == "ITC_DEFERRED": totals[h]["deferred_to_next"] += item[h]
            elif status == "REVERSED_RULE_37": totals[h]["reversal_rule_37"] += item[h]
            else: totals[h]["net_eligible"] += item[h]
        lines.append({"invoice_ref": invoice.get("invoice_number"), "status": status, "reason": reason, "amounts": {h: str(money(item[h])) for h in HEADS}})
    turnover = data.get("turnover") or {}; ratio = (d(turnover.get("exempt")) / d(turnover.get("total"))) if d(turnover.get("total")) else ZERO
    if (profile.get("itc_rule_flags") or {}).get("rule_42_applicable"):
        for h in HEADS:
            reversal = money(totals[h]["net_eligible"] * ratio)
            totals[h]["reversal_rule_42"] += reversal; totals[h]["net_eligible"] -= reversal
    for h in HEADS:
        for k in totals[h]: totals[h][k] = str(money(totals[h][k]))
    return {"totals_by_head": totals, "line_items": lines, "recon_summary": {"matched": sum(x["status"] == "MATCHED" for x in lines), "in_books_only": sum(x["status"] == "ITC_DEFERRED" for x in lines)}, "workings": {"rule_42": {"E": str(d(turnover.get("exempt"))), "F": str(d(turnover.get("total"))), "ratio": str(ratio.quantize(Decimal("0.0001"))) }}, "warnings": warnings}
