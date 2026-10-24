"""Declared-rate arithmetic, explicitly separate from legal rate determination."""

from decimal import Decimal, ROUND_HALF_UP

VERSION = "declared-rate-arithmetic-1"
HEADS = ("cgst", "sgst", "igst", "cess")
CENT = Decimal(".01")


def amount(value):
    if isinstance(value, float):
        raise ValueError("Use decimal text.")
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("Use a finite nonnegative amount.")
    return result


def price_breakdown(price, rate, inclusive=False, discount="0"):
    """Price and discount share the supplied tax-inclusive/exclusive basis."""
    value, percent, reduction = amount(price), amount(rate), amount(discount)
    if reduction > value or percent > 100:
        raise ValueError("Invalid discount or declared rate.")
    net = value - reduction
    taxable = net / (1 + percent / 100) if inclusive else net
    taxable = taxable.quantize(CENT, rounding=ROUND_HALF_UP)
    tax = (net - taxable if inclusive else taxable * percent / 100).quantize(CENT, rounding=ROUND_HALF_UP)
    return {
        "taxable_value": str(taxable),
        "gst": str(tax),
        "total": str(taxable + tax),
        "rule_version": VERSION,
        "legal_rate_verified": False,
    }


def line_price_check(line):
    """Compare supplied unit-price evidence with recorded taxable value.

    This checks declared-rate arithmetic only. It cannot decide whether a
    discount is legally deductible or whether a rate applies to the supply.
    """
    if line.unit_price is None and line.discount_amount is None and line.price_basis is None:
        return None
    if line.unit_price is None or line.price_basis is None:
        return 'line_price_incomplete'
    if line.quantity <= 0 or line.unit_price < 0 or (line.discount_amount or Decimal(0)) < 0:
        return 'line_price_invalid'
    gross = line.quantity * line.unit_price
    discount = line.discount_amount or Decimal(0)
    if discount > gross:
        return 'line_price_invalid'
    try:
        result = price_breakdown(gross, line.gst_rate, line.price_basis == 'tax_inclusive', discount)
    except ValueError:
        return 'line_price_invalid'
    if abs(Decimal(result['taxable_value']) - line.taxable_value) > CENT:
        return 'line_valuation_mismatch'
    return None


def compare_invoice(invoice, source=None):
    rows = []
    own_state = invoice.supplier_gstin[:2] or invoice.supplier_state_code
    pos = invoice.place_of_supply_state_code
    known = bool(own_state and pos)
    intra = own_state == pos
    for index, line in enumerate(invoice.line_items, 1):
        tax = line.taxable_value * line.gst_rate / 100
        expected = {
            "cgst": (tax / 2 if intra else Decimal(0)).quantize(CENT, rounding=ROUND_HALF_UP),
            "sgst": (tax / 2 if intra else Decimal(0)).quantize(CENT, rounding=ROUND_HALF_UP),
            "igst": (Decimal(0) if intra else tax).quantize(CENT, rounding=ROUND_HALF_UP),
        }
        actual = {h: getattr(line, h) for h in expected}
        delta = {h: actual[h] - expected[h] for h in expected}
        wrong_head = line.igst != 0 if intra else line.cgst != 0 or line.sgst != 0
        classification = (
            "INSUFFICIENT_DATA"
            if not known
            else "TAX_HEAD_MISMATCH"
            if wrong_head
            else "MATCHED"
            if all(v == 0 for v in delta.values())
            else "ROUNDING_DIFFERENCE"
            if all(abs(v) <= CENT for v in delta.values())
            else "AMOUNT_MISMATCH"
        )
        rows.append(
            {
                "line": index,
                "classification": classification,
                "declared_rate": str(line.gst_rate),
                "extracted_gst_amount": str(sum(actual.values())),
                "system_calculated_gst_amount": str(sum(expected.values())),
                "difference_amount": str(sum(delta.values())),
                "difference_percentage": str((sum(delta.values()) / sum(expected.values()) * 100).quantize(CENT))
                if sum(expected.values())
                else None,
                "expected_heads": {h: str(v) for h, v in expected.items()},
                "head_differences": {h: str(v) for h, v in delta.items()},
                "cess_review_required": line.cess != 0,
            }
        )
    return {
        "invoice_id": invoice.invoice_id,
        "version": invoice.version,
        "rule_version": VERSION,
        "legal_rate_verified": False,
        "qualification": "Arithmetic at the declared rate only. HSN rate, place-of-supply exceptions, cess and legal eligibility require verified rules and review.",
        "source_gst_amount": str(sum(getattr(source.totals, h) for h in HEADS)) if source else None,
        "extracted_gst_amount": str(sum(getattr(invoice.totals, h) for h in HEADS)),
        "approved_gst_amount": str(sum(getattr(invoice.totals, h) for h in HEADS))
        if invoice.status == "confirmed"
        else None,
        "rows": rows,
    }
