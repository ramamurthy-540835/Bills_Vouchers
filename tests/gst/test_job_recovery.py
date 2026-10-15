from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.gst.job_state import retryable
from app.gst.jobs import public_job, run_job, process_job


@pytest.mark.parametrize('status,minutes,expected', [
    ('queued', 36, True), ('reading', 36, True), ('queued', 34, False),
    ('reading', 34, False), ('completed', 100, False), ('needs_attention', 0, True),
])
def test_recovery_requires_failed_or_stale_job(status, minutes, expected):
    job = {'job_id': 'job', 'status': status, 'files': [], 'worker_token': 'private', 'recovery_version': 1,
           '_updated_at': str(datetime.now(timezone.utc) - timedelta(minutes=minutes))}
    assert retryable(job) is expected
    assert public_job(job)['retryable'] is expected
    assert 'worker_token' not in public_job(job) and '_updated_at' not in public_job(job)


def test_legacy_unfenced_worker_is_not_automatically_recovered():
    assert not retryable({'status': 'reading', '_updated_at': str(datetime.now(timezone.utc)-timedelta(days=1))})


def test_active_worker_conflict_does_not_change_job():
    store = Mock()
    store.claim_job.side_effect = HTTPException(409, 'active worker')
    with pytest.raises(HTTPException):
        run_job(store, {}, 'actor', {'job_id': 'job'})
    store.job.assert_not_called()


def test_completed_delivery_is_noop():
    store = Mock()
    store.claim_job.return_value = {'job_id': 'job', 'status': 'completed'}
    assert run_job(store, {}, 'actor', {'job_id': 'job'})['status'] == 'completed'
    store.list.assert_not_called()
    store.job.assert_not_called()


def test_storage_failure_retains_progress_and_exposes_recovery():
    job = {'job_id': 'job', 'status': 'reading', 'period': '2026-09',
           'files': [{'status': 'reading', 'raw_ref': 'original', 'invoice_ids': []}]}
    store = Mock()
    store.claim_job.return_value = deepcopy(job)
    store.list.return_value = []
    store.download_object.side_effect = RuntimeError('storage unavailable')
    with pytest.raises(RuntimeError, match='storage unavailable'):
        run_job(store, {}, 'actor', job)
    recorded = store.job.call_args.args[1]
    assert recorded['status'] == 'needs_attention'
    assert recorded['files'][0]['raw_ref'] == 'original'
    assert public_job(recorded)['retryable']


def test_filing_lock_is_not_reported_as_duplicate(invoice, profile, monkeypatch):
    monkeypatch.setattr('app.gst.jobs.extract', lambda *args: [invoice.model_copy(deep=True)])
    store = Mock(client_id=invoice.client_id)
    store.list.return_value = []
    store.download_object.return_value = b'content'
    store.upload_object.return_value = 'silver'
    store.save.side_effect = HTTPException(409, 'This filing period is frozen.')
    job = {'job_id': 'job', 'status': 'queued', 'period': '2026-09',
           'files': [{'filename': 'bill.pdf', 'doc_id': 'doc', 'raw_ref': 'original', 'status': 'reading', 'invoice_ids': []}]}
    with pytest.raises(HTTPException, match='frozen'):
        process_job(store, profile, 'actor', job)
    assert job['status'] != 'completed'


def test_invoice_write_failure_resumes_from_saved_extraction(invoice, profile, monkeypatch):
    extract = Mock(return_value=[invoice.model_copy(deep=True)])
    monkeypatch.setattr('app.gst.jobs.extract', extract)
    blobs = {'original': b'content'}
    saved = []
    def upload(content, *args):
        blobs['silver'] = content
        return 'silver'
    store = Mock(client_id=invoice.client_id)
    store.list.side_effect = lambda: saved.copy()
    store.download_object.side_effect = lambda ref, **kwargs: blobs[ref]
    store.upload_object.side_effect = upload
    job = {'job_id': 'job', 'status': 'queued', 'period': '2026-09',
           'files': [{'filename': 'bill.pdf', 'doc_id': 'doc', 'raw_ref': 'original', 'status': 'reading', 'invoice_ids': []}]}
    store.save.side_effect = RuntimeError('write failed')
    with pytest.raises(RuntimeError, match='write failed'):
        process_job(store, profile, 'actor', job)
    assert job['files'][0]['extracted_ref'] == 'silver'
    store.save.side_effect = lambda value, *args, **kwargs: saved.append(value)
    process_job(store, profile, 'actor', job)
    extract.assert_called_once()
    assert len(saved) == 1 and job['status'] == 'completed'
