from decimal import Decimal

import pytest

from app.gst.reconciliation import compare
from app.gst.report import calculate


def statement(invoice, **changes):
    return {'supplier_gstin': invoice.supplier_gstin, 'invoice_number': invoice.invoice_number,
            'invoice_date': str(invoice.invoice_date), 'itc_available': True,
            **invoice.totals.model_dump(), **changes}


def test_two_sided_evidence_and_financial_invariance(invoice, profile):
    invoice.status = 'confirmed'
    rows = [statement(invoice), statement(invoice, invoice_number='MISSING')]
    before = calculate([invoice], profile, rows)
    result = compare([invoice], rows)
    assert result['counts'] == {'exact': 1, 'missing_book': 1}
    assert result['cases'][0]['differences']['cgst'] == Decimal('0')
    assert calculate([invoice], profile, rows) == before
    assert not result['financial_override']


@pytest.mark.parametrize(('changes', 'status'), [
    ({'invoice_date': '2026-09-02'}, 'date_mismatch'),
    ({'cgst': '88.99'}, 'amount_mismatch'),
    ({'cgst': '89.00'}, 'within_tolerance'),
    ({'cgst': None}, 'incomplete_amounts'),
    ({'cgst': 'NaN'}, 'incomplete_amounts'),
])
def test_candidate_comparisons(invoice, changes, status):
    invoice.status = 'confirmed'
    result = compare([invoice], [statement(invoice, **changes)])
    assert result['counts'] == {status: 1}


def test_duplicate_candidates_never_pick_arbitrary_row(invoice):
    invoice.status = 'confirmed'
    row = statement(invoice)
    case = compare([invoice], [row, row])['cases'][0]
    assert case['status'] == 'ambiguous'
    assert len(case['statement_candidates']) == 2
    assert case['differences'] is None
    duplicate = invoice.model_copy(deep=True)
    duplicate.invoice_id = 'second'
    assert compare([invoice, duplicate], [row])['counts'] == {'ambiguous': 2}


def test_invoice_number_punctuation_preserved(invoice):
    invoice.status = 'confirmed'
    assert compare([invoice], [statement(invoice, invoice_number='INV1')])['counts'] == {
        'missing_statement': 1, 'missing_book': 1}


@pytest.mark.parametrize('change', [{'status': 'rejected'}, {'status': 'needs_review'}, {'sample': True}, {'direction': 'sale'}])
def test_only_confirmed_real_purchases_are_compared(invoice, change):
    invoice.status = 'confirmed'
    invoice = invoice.model_copy(update=change)
    result = compare([invoice], [statement(invoice)])
    assert result['confirmed_purchase_count'] == 0
    assert result['counts'] == {'missing_book': 1}


def test_notes_do_not_consume_b2b_invoice_evidence(invoice):
    invoice.status = 'confirmed'
    invoice.invoice_type = 'credit_note'
    assert compare([invoice], [statement(invoice)])['counts'] == {'unsupported_document': 1, 'missing_book': 1}


def test_private_source_fields_not_exposed(invoice):
    invoice.status = 'confirmed'
    case = compare([invoice], [statement(invoice, raw_ref='gs://private/evidence', secret='hidden')])['cases'][0]
    assert 'private' not in str(case) and 'hidden' not in str(case)


def test_empty_statement_keeps_unmatched_books(invoice):
    invoice.status = 'confirmed'
    result = compare([invoice], [])
    assert result['statement_count'] == 0
    assert result['counts'] == {'missing_statement': 1}


def test_statement_case_ids_do_not_depend_on_query_row_order(invoice):
    invoice.status='confirmed'
    rows=[statement(invoice),statement(invoice,invoice_number='ORPHAN'),statement(invoice,invoice_number='ANOTHER')]
    assert compare([invoice],rows)==compare([invoice],list(reversed(rows)))
