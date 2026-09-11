"""Deterministic GST purchase-register to GSTR-2B matching helpers."""
from decimal import Decimal

from .validation import normalize_invoice_number


def match_invoice(book, two_b):
    same_gstin = (book.supplier_gstin or "").upper() == (two_b.supplier_gstin or "").upper()
    same_number = normalize_invoice_number(book.invoice_number) == normalize_invoice_number(two_b.invoice_number)
    amount_gap = abs(Decimal(str(book.total_amount or 0)) - Decimal(str(two_b.total_amount or 0)))
    date_gap = abs((book.invoice_date - two_b.invoice_date).days) if book.invoice_date and two_b.invoice_date else 99
    if same_gstin and same_number and amount_gap <= Decimal("1") and date_gap <= 3:
        return "exact_match", Decimal("100"), None
    if same_gstin and amount_gap <= Decimal("10") and date_gap <= 31:
        return "probable_match", Decimal("90"), "invoice_number_format"
    if same_gstin and amount_gap <= Decimal("100"):
        return "partial_match", Decimal("70"), "value_or_date"
    return "needs_review", Decimal("0"), "no_reliable_match"
