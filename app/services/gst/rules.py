"""Decimal-only rules. Eligibility under 17(5) does not override rate conditions."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

HEADS = ("igst", "cgst", "sgst", "cess")
ZERO = Decimal("0")


def amount(value=0):
    if isinstance(value, float):
        raise ValueError("Money must be a decimal string, never a float")
    result = Decimal(str(value or 0))
    if not result.is_finite():
        raise ValueError("Money must be finite")
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def heads(row):
    return {h: amount(row.get(h, 0)) for h in HEADS}


def deadline(invoice_date):
    dt = date.fromisoformat(str(invoice_date)[:10])
    fy_end = dt.year + 1 if dt.month >= 4 else dt.year
    return date(fy_end, 11, 30)


def rule(line, profile, matched=True, as_of=None):
    """Returns bucket and reference, before proportional R42/R43 reversals."""
    category = line.get("itc_category", "other")
    if category == "fuel":
        return "non_gst", "NON-GST"
    if profile.get("composition_flag") or profile.get("itc_rate_restricted"):
        return "blocked", "RATE-CONDITION-NO-ITC"
    passenger = profile.get("business_nature") in {"passenger_transport", "eco_operator"}
    ref = "ELIGIBLE"
    if category in {"vehicle", "insurance_repair"} and int(line.get("seating_capacity") or 13) <= 13:
        section = "17(5)(a)" if category == "vehicle" else "17(5)(ab)"
        if not passenger:
            return "blocked", section
        ref = section + "-EXEMPT-PASSENGER-TRANSPORT"
    elif line.get("blocked_clause"):
        return "blocked", str(line["blocked_clause"])
    if not line.get("has_tax_invoice", True) or not line.get("goods_or_services_received", True):
        return "deferred", "16(2)"
    if line.get("invoice_date") and (as_of or date.today()) > deadline(line["invoice_date"]):
        return "blocked", "16(4)"
    if int(line.get("unpaid_days") or 0) > 180:
        return "reversal", "R37"
    if not matched:
        return "deferred", "2B-UNMATCHED"
    return "eligible", ref


def set_off(output, eligible, eco=None):
    """49A/49B, Rule 88A; CGST/SGST cannot cross-utilise, cess stays separate.

    Section 9(5) ECO liabilities are cash-only, outside the credit set-off.
    Exhaust IGST credit before other credit, assigning its remainder to the
    largest uncovered central/state liability to minimise stranded balances.
    """
    due, credit = heads(output), heads(eligible)
    if any(v < ZERO for v in (*due.values(), *credit.values())):
        raise ValueError("Set-off requires non-negative amounts")
    usage = []

    def use(source, target):
        value = min(credit[source], due[target])
        credit[source] -= value
        due[target] -= value
        if value:
            usage.append({"from": source, "to": target, "amount": str(value)})

    use("igst", "igst")
    order = sorted(("cgst", "sgst"), key=lambda h: max(ZERO, due[h] - credit[h]), reverse=True)
    for h in order:
        use("igst", h)
    for h in ("cgst", "sgst"):
        use(h, h)
        use(h, "igst")
    use("cess", "cess")
    cash = {h: due[h] + heads(eco or {})[h] for h in HEADS}
    return {"net_payable_by_head": due, "cash_by_head": cash,
            "cash_required": sum(cash.values(), ZERO), "credit_carried": credit, "utilisation": usage}


def common_reversal(line, profile, taxes):
    """R42 common inputs / R43 monthly common-capital reversal.

    Missing attribution is deferred rather than silently treating it as eligible.
    Tax administrators supply the period's turnover basis in itc_rule_flags.
    """
    if not line.get("common_credit"):
        return {h: ZERO for h in HEADS}, None
    flags = profile.get("itc_rule_flags") or {}
    if isinstance(flags, str):
        import json
        flags = json.loads(flags)
    if not flags.get("turnover_total"):
        return taxes.copy(), "R43-BASIS-MISSING" if line.get("capital_goods") else "R42-BASIS-MISSING"
    total, exempt = amount(flags["turnover_total"]), amount(flags.get("turnover_exempt"))
    if total <= ZERO or exempt < ZERO or exempt > total:
        raise ValueError("Invalid common-credit turnover basis")
    ratio = exempt / total
    non_business = Decimal("0.05") if flags.get("non_business_use") and not line.get("capital_goods") else ZERO
    divisor = Decimal("60") if line.get("capital_goods") else Decimal("1")
    return {h: amount(min(taxes[h], taxes[h] * (ratio + non_business) / divisor)) for h in HEADS}, "R43" if line.get("capital_goods") else "R42"
