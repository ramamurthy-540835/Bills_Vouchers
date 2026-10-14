from types import SimpleNamespace
from unittest.mock import Mock
from app.gst.naming import bill_filename
from app.gst.store import BillStore
from app.config import get_settings


def test_canonical_name_sanitizes_invoice_number_and_keeps_extension(invoice):
    invoice.invoice_number='INV/2026-001'
    invoice.extraction.raw_ref='gs://bucket/client/scan.PDF'
    assert bill_filename(invoice)==f'{invoice.supplier_gstin}_INV_2026-001.pdf'


def test_named_original_keeps_source_and_uses_client_directory(invoice,monkeypatch):
    import app.gst.store as module
    monkeypatch.setenv('GCS_BUCKET_NAME','test-bucket');get_settings.cache_clear()
    invoice.extraction.raw_ref=f'gs://test-bucket/{invoice.client_id}/bronze/bills/2026/10/14/doc/photo.png'
    bucket=Mock(name='bucket');bucket.name='test-bucket'
    monkeypatch.setattr(module.storage,'Client',lambda **kwargs:SimpleNamespace(bucket=lambda name:bucket))
    store=BillStore(SimpleNamespace(settings=SimpleNamespace(gcp_project_id='test-project')),invoice.client_id)
    store.name_original(invoice)
    target=bucket.copy_blob.call_args.args[2]
    assert target.startswith(f'{invoice.client_id}/bronze/bills/')
    assert target.endswith('/'+bill_filename(invoice))
    bucket.blob.return_value.delete.assert_not_called()
    assert invoice.extraction.raw_ref=='gs://test-bucket/'+target
    get_settings.cache_clear()
