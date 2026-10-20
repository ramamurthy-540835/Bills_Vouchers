from types import SimpleNamespace
import pytest
from app.services.model_access import model_location


def test_default_preserves_regional_processing():
    settings=SimpleNamespace(gemini_location='',gemini_allowed_client_ids='',gcp_region='asia-south1')
    assert model_location('business',settings)=='asia-south1'


def test_explicit_synthetic_allowlist_prevents_other_business_processing():
    settings=SimpleNamespace(gemini_location='global',gemini_allowed_client_ids='synthetic-a, synthetic-b',
                             gcp_region='asia-south1')
    assert model_location('synthetic-a',settings)=='global'
    for client in [None,'','other','synthetic-a,synthetic-b']:
        with pytest.raises(ValueError):model_location(client,settings)


def test_global_processing_fails_closed_without_explicit_allowlist():
    settings=SimpleNamespace(gemini_location='global',gemini_allowed_client_ids='',gcp_region='asia-south1')
    with pytest.raises(ValueError):
        model_location('business',settings)


def test_extraction_does_not_send_disallowed_tenant_data(monkeypatch):
    from unittest.mock import Mock
    from app.gst import extract
    settings = SimpleNamespace(gemini_enabled=True, gemini_location='global',
                               gemini_allowed_client_ids='synthetic', gcp_region='asia-south1',
                               gcp_project_id='test', external_timeout_seconds=30)
    monkeypatch.setattr(extract, 'get_settings', lambda: settings)
    transport = Mock()
    monkeypatch.setattr(extract.genai, 'Client', transport)
    with pytest.raises(ValueError):
        extract.extract(b'not-transmitted', 'invoice.png', 'other', 'doc', {}, 'private', Mock())
    transport.assert_not_called()
