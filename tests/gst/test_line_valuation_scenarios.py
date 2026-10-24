"""Declared-price arithmetic contracts; legal valuation remains separately reviewed."""

from decimal import Decimal

import pytest

from app.gst.auto_review import evaluate
from app.gst.comparison import line_price_check
from app.gst.schemas.invoice import LineItem
from app.gst.validate_invoice import validate_invoice
from tests.gst.test_auto_review import store as base_store_fixture


@pytest.fixture(name='store')
def store_fixture(invoice):
    return base_store_fixture.__wrapped__(invoice)


def test_scenario_C05_quantity_times_unit_price_mismatch_requires_review(store, profile):
    invoice = store.state.current
    line = invoice.line_items[0]
    line.quantity = Decimal('2')
    line.unit_price = Decimal('600')
    line.price_basis = 'tax_exclusive'
    assert line_price_check(line) == 'line_valuation_mismatch'
    assert 'line_valuation_mismatch' in validate_invoice(invoice, profile).review_reasons
    _, reasons, _, _ = evaluate(store, invoice, profile)
    assert 'line_valuation_mismatch' in reasons


def test_scenario_C07_inclusive_price_cannot_be_recorded_as_exclusive(store, profile):
    invoice = store.state.current
    line = invoice.line_items[0]
    line.unit_price = Decimal('1180')
    line.price_basis = 'tax_inclusive'
    assert line_price_check(line) is None  # 1180 inclusive at declared 18% has taxable value 1000.
    line.taxable_value = Decimal('1180')
    assert 'line_valuation_mismatch' in validate_invoice(invoice, profile).review_reasons
    _, reasons, _, _ = evaluate(store, invoice, profile)
    assert 'line_valuation_mismatch' in reasons


def test_scenario_C08_exclusive_price_cannot_be_recorded_as_inclusive(store, profile):
    invoice = store.state.current
    line = invoice.line_items[0]
    line.unit_price = Decimal('1000')
    line.price_basis = 'tax_exclusive'
    assert line_price_check(line) is None
    line.taxable_value = Decimal('847.46')
    assert 'line_valuation_mismatch' in validate_invoice(invoice, profile).review_reasons
    _, reasons, _, _ = evaluate(store, invoice, profile)
    assert 'line_valuation_mismatch' in reasons


def test_scenario_D06_per_unit_double_rounding_cannot_override_line_tax(store, profile):
    invoice = store.state.current
    invoice.place_of_supply_state_code = '29'
    line = invoice.line_items[0]
    line.quantity = Decimal('3')
    line.unit_price = Decimal('0.03')
    line.price_basis = 'tax_exclusive'
    line.taxable_value = Decimal('0.09')
    line.cgst = line.sgst = Decimal('0')
    line.igst = Decimal('0.03')  # Rounding 0.0054 per unit first yields 0.03.
    invoice.totals.taxable_value = Decimal('0.09')
    invoice.totals.cgst = invoice.totals.sgst = Decimal('0')
    invoice.totals.igst = Decimal('0.03')
    invoice.totals.invoice_total = Decimal('0.12')
    assert line_price_check(line) is None
    _, reasons, checks, _ = evaluate(store, invoice, profile)
    assert not checks['gst_calculation']
    assert any('independently calculated tax heads' in reason for reason in reasons)


def test_scenario_D07_mixed_inclusive_and_exclusive_lines_reconcile_independently(store, profile):
    invoice = store.state.current
    inclusive = invoice.line_items[0]
    inclusive.unit_price = Decimal('1180')
    inclusive.price_basis = 'tax_inclusive'
    exclusive = inclusive.model_copy(deep=True)
    exclusive.unit_price = Decimal('1000')
    exclusive.price_basis = 'tax_exclusive'
    invoice.line_items.append(exclusive)
    invoice.totals.taxable_value = Decimal('2000')
    invoice.totals.cgst = invoice.totals.sgst = Decimal('180')
    invoice.totals.invoice_total = Decimal('2360')
    _, reasons, checks, _ = evaluate(store, invoice, profile)
    assert not reasons and all(checks.values())
    exclusive.taxable_value = Decimal('847.46')
    _, reasons, _, _ = evaluate(store, invoice, profile)
    assert 'line_valuation_mismatch' in reasons


@pytest.mark.parametrize('basis,unit_price,discount,expected', [
    ('tax_exclusive', '1000', '100', '900'),
    ('tax_inclusive', '1180', '118', '900'),
])
def test_explicit_discount_price_basis_uses_decimal_arithmetic(basis, unit_price, discount, expected):
    line = LineItem(unit_price=unit_price, quantity='1', discount_amount=discount,
                    price_basis=basis, taxable_value=expected, gst_rate='18')
    assert line_price_check(line) is None


def test_incomplete_or_excess_discount_price_evidence_requires_review():
    line = LineItem(unit_price='100', taxable_value='100')
    assert line_price_check(line) == 'line_price_incomplete'
    line.price_basis = 'tax_exclusive'
    line.discount_amount = Decimal('101')
    assert line_price_check(line) == 'line_price_invalid'


def test_legacy_lines_without_source_price_remain_readable(invoice, profile):
    assert line_price_check(invoice.line_items[0]) is None
    assert 'line_valuation_mismatch' not in validate_invoice(invoice, profile).review_reasons
