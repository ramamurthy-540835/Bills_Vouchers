from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import PreconditionFailed

from app.gst import store as storage


@pytest.fixture
def setup(monkeypatch):
    bucket=Mock();bucket.name='private-bucket'
    client=Mock();client.bucket.return_value=bucket
    monkeypatch.setattr(storage.storage,'Client',lambda **kwargs:client)
    monkeypatch.setattr(storage,'get_settings',lambda:SimpleNamespace(gcs_bucket_name='private-bucket'))
    store=storage.BillStore(SimpleNamespace(settings=SimpleNamespace(gcp_project_id='test-project')),'a')
    return store,bucket


def test_upload_is_create_only_and_identical_retry_is_idempotent(setup):
    store,bucket=setup
    blob=bucket.blob.return_value
    first=store.upload_object(b'original','doc','original.pdf','bronze','application/pdf')
    assert blob.upload_from_string.call_args.kwargs['if_generation_match']==0
    blob.upload_from_string.side_effect=PreconditionFailed('exists')
    blob.download_as_bytes.return_value=b'original'
    assert store.upload_object(b'original','doc','original.pdf','bronze','application/pdf')==first
    with pytest.raises(HTTPException) as error:
        store.upload_object(b'different','doc','original.pdf','bronze','application/pdf')
    assert error.value.status_code==409


def test_name_copy_pins_source_and_never_replaces_existing_evidence(setup, invoice):
    store,bucket=setup
    original='gs://private-bucket/a/bronze/bills/date/doc/original.pdf'
    invoice.extraction.raw_ref=original
    source=Mock(generation=123);target=Mock()
    bucket.blob.side_effect=lambda key:source if key.endswith('original.pdf') else target
    store.name_original(invoice)
    assert bucket.copy_blob.call_args.kwargs=={'if_generation_match':0,'if_source_generation_match':123}
    assert invoice.extraction.raw_ref!=original
    invoice.extraction.raw_ref=original
    bucket.copy_blob.side_effect=PreconditionFailed('exists')
    source.download_as_bytes.return_value=b'original';target.download_as_bytes.return_value=b'original'
    store.name_original(invoice)
    source.download_as_bytes.assert_called_with(if_generation_match=123)
    invoice.extraction.raw_ref=original;target.download_as_bytes.return_value=b'different'
    with pytest.raises(HTTPException) as error:store.name_original(invoice)
    assert error.value.status_code==409 and invoice.extraction.raw_ref==original


def test_foreign_storage_reference_is_rejected_before_access(setup,invoice):
    store,bucket=setup
    invoice.extraction.raw_ref='gs://private-bucket/other/bronze/bills/doc/file.pdf'
    for action in (lambda:store.name_original(invoice),lambda:store.download_object(invoice.extraction.raw_ref)):
        with pytest.raises(HTTPException) as error:action()
        assert error.value.status_code==404
    bucket.blob.assert_not_called()
