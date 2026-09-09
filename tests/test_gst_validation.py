from app.services.gst.validation import normalize_invoice_number, valid_gstin, validate_document


def test_gstin_checksum_and_normalization():
    assert valid_gstin("27AAPFU0939F1ZV")
    assert not valid_gstin("27AAPFU0939F1ZA")
    assert normalize_invoice_number(" inv / 12- a ") == "INV12A"


def test_tax_state_rules():
    result = validate_document(
        {"supplier_state_code": "27", "place_of_supply": "27", "cgst": "10", "sgst": "9", "igst": "0"}
    )
    assert any(x["code"] == "intra_state_tax_mismatch" for x in result["errors"])
    result = validate_document(
        {"supplier_state_code": "27", "place_of_supply": "29", "cgst": "0", "sgst": "0", "igst": "19"}
    )
    assert result["passed"]


def test_rate_hsn_duplicate_and_totals():
    result = validate_document(
        {
            "gst_rate": "17",
            "hsn": "123",
            "invoice_number": "A-1",
            "duplicate": True,
            "line_items": [{"total": "100"}],
            "total_amount": "101",
        },
        duplicate=True,
    )
    codes = {x["code"] for x in result["errors"]} | {x["code"] for x in result["warnings"]}
    assert {"unsupported_gst_rate", "invalid_hsn_sac", "duplicate_invoice", "line_total_mismatch"} <= codes
