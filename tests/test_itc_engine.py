from app.services.gst.itc_engine import compute_itc
from app.services.gst.profiles import validate_gstin


def invoice(**extra):
    return {"supplier_gstin":"27AAPFU0939F1ZV", "invoice_number":"INV-1", "invoice_date":"2026-09-01", "igst":"0", "cgst":"90", "sgst":"90", "has_tax_invoice":True, "goods_or_services_received":True, **extra}


def test_checksum_error_code():
    assert validate_gstin("27AAPFU0939F1ZA")["code"] == "GSTIN_CHECKSUM_FAIL"


def test_blocked_motor_vehicle_and_resale_override():
    blocked = compute_itc({"purchaseRegister":[invoice(blocked_clause="17(5)(a)")], "gstr2b":[invoice()]})
    assert blocked["totals_by_head"]["cgst"]["ineligible_17_5"] == "90.00"
    allowed = compute_itc({"purchaseRegister":[invoice(blocked_clause="17(5)(a)", override_justification="Resale")], "gstr2b":[invoice()]})
    assert allowed["totals_by_head"]["cgst"]["net_eligible"] == "90.00"


def test_2b_rule_42_and_rule_37():
    deferred = compute_itc({"purchaseRegister":[invoice()], "gstr2b":[]})
    assert deferred["totals_by_head"]["cgst"]["deferred_to_next"] == "90.00"
    common = compute_itc({"profile":{"itc_rule_flags":{"rule_42_applicable":True}}, "purchaseRegister":[invoice()], "gstr2b":[invoice()], "turnover":{"total":"1000", "exempt":"300"}})
    assert common["totals_by_head"]["cgst"]["reversal_rule_42"] == "27.00"
    unpaid = compute_itc({"purchaseRegister":[invoice(unpaid_days=185)], "gstr2b":[invoice()]})
    assert unpaid["totals_by_head"]["cgst"]["reversal_rule_37"] == "90.00"
