"""Text-visible PDF safety signals using generated synthetic originals."""

import json
from io import BytesIO
from types import SimpleNamespace

from reportlab.pdfgen import canvas

from app.gst.extract import extract
from app.gst.validate_invoice import validate_invoice


def synthetic_pdf(pages):
    output = BytesIO()
    document = canvas.Canvas(output)
    for number, detail in pages:
        document.drawString(72, 750, f'Invoice No: {number}')
        document.drawString(72, 720, f'Synthetic invoice evidence, not for tax filing: {detail}')
        document.showPage()
    document.save()
    return output.getvalue()


def parsed_pdf(monkeypatch, invoice, profile, pages):
    import app.gst.extract as module

    settings = module.get_settings().model_copy(update={'gemini_enabled': True,
        'gemini_location': 'asia-south1', 'gemini_allowed_client_ids': ''})
    monkeypatch.setattr(module, 'get_settings', lambda: settings)
    payload = invoice.model_dump(mode='json')
    payload['confidence'] = '1'
    reply = SimpleNamespace(text=json.dumps(payload), usage_metadata=SimpleNamespace(
        prompt_token_count=1, candidates_token_count=1))
    monkeypatch.setattr(module.genai, 'Client', lambda **_kwargs: SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **_kwargs: reply)))
    original = synthetic_pdf(pages)
    result = extract(original, 'synthetic.pdf', invoice.client_id, 'doc', profile,
                     'private-original', lambda *_args: None)[0]
    return original, result


def test_scenario_A06_multi_page_single_invoice_retains_all_pages(monkeypatch, invoice, profile):
    original, result = parsed_pdf(monkeypatch, invoice, profile,
                                  [('INV-1', 'first page'), ('INV-1', 'line-item continuation')])
    assert original.startswith(b'%PDF-')
    assert result.extraction.raw_ref == 'private-original'
    assert result.extraction.page_count == 2
    assert result.extraction.document_flags == []


def test_scenario_A07_multiple_invoice_numbers_block_single_record(monkeypatch, invoice, profile):
    _, result = parsed_pdf(monkeypatch, invoice, profile,
                           [('INV-1', 'first invoice'), ('INV-2', 'second invoice')])
    assert result.extraction.page_count == 2
    assert 'multiple_invoice_numbers' in result.extraction.document_flags
    assert 'multiple_invoice_numbers' in validate_invoice(result, profile).review_reasons
    assert 'multiple_invoice_numbers' in validate_invoice(result, profile, human_review=True).review_reasons


def test_scenario_A08_duplicate_text_page_requires_review(monkeypatch, invoice, profile):
    _, result = parsed_pdf(monkeypatch, invoice, profile,
                           [('INV-1', 'same page'), ('INV-1', 'same page')])
    assert 'duplicate_pdf_page' in result.extraction.document_flags
    assert 'duplicate_pdf_page' in validate_invoice(result, profile).review_reasons
    assert 'duplicate_pdf_page' not in validate_invoice(result, profile, human_review=True).review_reasons
