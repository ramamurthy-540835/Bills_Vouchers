"""Exact field retention and explicit uncertainty, never fabricated extraction."""
import json
from decimal import Decimal

import pytest

from app.gst.extract import ExtractionResponseError, extraction_schema, parse_response
from app.gst.schemas.invoice import Extraction, GstInvoice


def provider_payload(invoice):
    payload = invoice.model_dump(mode='json')
    payload['confidence'] = '0.99'
    return payload


def parse(payload):
    return parse_response(json.dumps(payload), 'authorized-client', 'source-document', 'private-original')


def test_selected_recipient_context_alone_is_not_invoice_evidence():
    with pytest.raises(ExtractionResponseError):
        parse({'recipient_gstin': '33ZZZPC9876Y1ZW', 'confidence': '0.99'})


def test_one_unreadable_total_does_not_erase_readable_identity_or_line_values(invoice):
    payload = provider_payload(invoice)
    payload['totals']['invoice_total'] = 'not readable'
    result = parse(payload)
    assert result.invoice_number == invoice.invoice_number
    assert result.supplier_gstin == invoice.supplier_gstin
    assert result.line_items[0].taxable_value == Decimal('1000.00')
    assert result.totals.cgst == Decimal('90.00')
    assert result.totals.invoice_total == 0
    assert 'invalid:totals.invoice_total' in result.extraction.field_issues
    assert result.extraction.confidence <= Decimal('0.84')


def test_missing_numeric_values_are_distinct_from_real_source_zero(invoice):
    payload = provider_payload(invoice)
    payload['totals']['cgst'] = None
    payload['totals']['igst'] = '0'
    del payload['line_items'][0]['taxable_value']
    result = parse(payload)
    assert 'missing:totals.cgst' in result.extraction.field_issues
    assert 'missing:line_items.0.taxable_value' in result.extraction.field_issues
    assert all('totals.igst' not in value for value in result.extraction.field_issues)
    assert result.supplier_legal_name == invoice.supplier_legal_name


@pytest.mark.parametrize('source,expected', [('₹1,180.00','1180.00'), ('INR 1,18,000.00','118000.00'),
                                         ('Rs. 1,180.00','1180.00'), (' 1180.00 ','1180.00')])
def test_unambiguous_currency_formatting_is_normalized_exactly(invoice, source, expected):
    payload = provider_payload(invoice)
    payload['totals']['invoice_total'] = source
    result = parse(payload)
    assert result.totals.invoice_total == Decimal(expected)
    assert not result.extraction.field_issues


@pytest.mark.parametrize('source', ['1.180,00', '1,18.00', 'NaN', 'Infinity', '1,180.001', True, {}, []])
def test_ambiguous_nonfinite_or_overprecision_amounts_are_flagged_not_guessed(invoice, source):
    payload = provider_payload(invoice)
    payload['totals']['invoice_total'] = source
    result = parse(payload)
    assert result.totals.invoice_total == 0
    assert 'invalid:totals.invoice_total' in result.extraction.field_issues
    assert result.invoice_number == invoice.invoice_number


def test_provider_json_decimal_literals_preserve_exact_decimal_values(invoice):
    payload = provider_payload(invoice)
    payload['line_items'][0]['unit_price'] = 'DECIMAL_PLACEHOLDER'
    text = json.dumps(payload).replace('"DECIMAL_PLACEHOLDER"', '0.123456')
    result = parse_response(text, 'a', 'doc', 'original')
    assert result.line_items[0].unit_price == Decimal('0.123456')
    assert not result.extraction.field_issues


@pytest.mark.parametrize('date', ['31/02/2026', 'not a date', {'day':1}])
def test_bad_date_retains_other_fields_and_marks_specific_correction(invoice, date):
    payload = provider_payload(invoice)
    payload['invoice_date'] = date
    result = parse(payload)
    assert result.invoice_date is None
    assert result.totals.invoice_total == invoice.totals.invoice_total
    assert 'invalid:invoice_date' in result.extraction.field_issues


def test_invalid_nested_shape_and_enum_keep_usable_fields(invoice):
    payload = provider_payload(invoice)
    payload['direction'] = {'invented':'sale'}
    payload['line_items'][0]['price_basis'] = 'unknown'
    payload['line_items'].append(None)
    payload['recipient_gstin'] = None
    result = parse(payload)
    assert result.supplier_gstin == invoice.supplier_gstin
    assert result.line_items[0].cgst == Decimal('90')
    assert 'invalid:direction' in result.extraction.field_issues
    assert 'invalid:line_items' in result.extraction.field_issues
    assert 'missing:recipient_gstin' in result.extraction.field_issues


@pytest.mark.parametrize('text', ['', 'not json', '[]', 'null', '{"debug":"No invoice located"}', '{"invoice_number":'])
def test_unusable_provider_response_is_typed_and_does_not_expose_payload(text):
    with pytest.raises(ExtractionResponseError) as caught:
        parse_response(text, 'a', 'doc', 'original')
    assert caught.value.code == 'invalid_extraction_response'
    assert 'debug' not in str(caught.value)


def test_field_diagnostics_use_existing_storage_contract(invoice):
    payload = provider_payload(invoice)
    payload['totals']['cgst'] = None
    result = parse(payload)
    stored = result.model_dump(mode='json')
    assert 'field_issues' not in stored['extraction']
    assert 'field_issue:missing:totals.cgst' in stored['extraction']['document_flags']
    restored = GstInvoice.model_validate(stored)
    assert restored.extraction.field_issues == ['missing:totals.cgst']
    assert Extraction.model_validate(stored['extraction']).field_issues == ['missing:totals.cgst']


def test_unknown_source_values_have_nullable_provider_schema():
    schema = extraction_schema()
    assert schema['properties']['totals']['properties']['invoice_total']['nullable'] is True
    assert schema['properties']['line_items']['items']['properties']['taxable_value']['nullable'] is True
    assert 'field_issues' not in schema['properties']


def test_missing_confidence_is_not_an_uneditable_source_field_task(invoice):
    payload = provider_payload(invoice)
    del payload['confidence']
    result = parse(payload)
    assert result.extraction.confidence == 0
    assert result.extraction.field_issues == []
    assert 'extraction_confidence_unavailable' in result.extraction.document_flags


def test_existing_bill_of_supply_supplier_gstin_exception_is_preserved(invoice):
    payload = provider_payload(invoice)
    payload['invoice_type'] = 'bill_of_supply'
    payload['supplier_gstin'] = None
    result = parse(payload)
    assert result.supplier_gstin == ''
    assert 'missing:supplier_gstin' not in result.extraction.field_issues


def test_invalid_totals_container_uses_only_editable_leaf_issues(invoice):
    payload = provider_payload(invoice)
    payload['totals'] = 'unreadable'
    result = parse(payload)
    assert 'missing:totals.invoice_total' in result.extraction.field_issues
    assert all(value.split(':',1)[1] != 'totals' for value in result.extraction.field_issues)


def test_plain_json_fence_and_percent_rate_remain_exact(invoice):
    payload = provider_payload(invoice)
    payload['line_items'][0]['gst_rate'] = '18%'
    text = '```json\n' + json.dumps(payload) + '\n```'
    result = parse_response(text, 'a', 'doc', 'original')
    assert result.line_items[0].gst_rate == Decimal('18')
    assert result.extraction.confidence == Decimal('0.99')


def test_model_cannot_control_server_owned_workflow_or_field_diagnostics(invoice):
    payload = provider_payload(invoice)
    payload.update(client_id='other', invoice_id='attacker-id', status='confirmed', sample=True,
                   auto_review={'enabled':True,'status':'auto_confirmed'})
    payload['extraction'] = {'method':'manual','confidence':'1','document_flags':[]}
    result = parse(payload)
    assert result.client_id == 'authorized-client'
    assert result.invoice_id != 'attacker-id'
    assert result.status == 'extracted'
    assert not result.auto_review.enabled
    assert not result.sample
    assert result.extraction.method == 'gemini'
def test_empty_canonical_response_does_not_create_a_blank_invoice():
    import json
    import pytest
    from app.gst.extract import ExtractionResponseError, parse_response
    with pytest.raises(ExtractionResponseError):
        parse_response(json.dumps({'invoice_number':'','supplier_gstin':'','line_items':[],'totals':{},'confidence':'0'}),'client','doc','private/original')
