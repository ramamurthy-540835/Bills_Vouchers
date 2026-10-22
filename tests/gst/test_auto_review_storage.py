import json
from types import SimpleNamespace
from unittest.mock import Mock

from pydantic import ConfigDict, create_model

from app.gst.schemas.invoice import AutoReview, GstInvoice
from app.gst.store import BillStore


def make_store(invoice):
    repo = Mock(settings=SimpleNamespace(gcp_project_id='test-project', gst_dataset_prefix='gst_easy_v3_'))
    repo.table.side_effect = lambda name: 'test-project.finance.' + name
    repo.query.return_value = []
    store = BillStore(repo, invoice.client_id)
    store.name_original = Mock()
    return store


def test_policy_and_invoice_commit_atomically_without_breaking_legacy_schema(invoice):
    store = make_store(invoice)
    previous = invoice.model_copy(deep=True)
    invoice.auto_review = AutoReview(enabled=True, requested_by='owner')
    invoice.version += 1
    store.save(invoice, 'owner', 'auto_review_policy', previous, '2026-09')
    sql, params = store.repo.query.call_args.args
    values = {p.name: p.value for p in params}
    legacy = create_model('LegacyInvoice', __config__=ConfigDict(extra='forbid'),
        **{name: (field.annotation, field) for name, field in GstInvoice.model_fields.items() if name != 'auto_review'})
    assert legacy.model_validate_json(values['payload']).invoice_id == invoice.invoice_id
    assert 'auto_review' not in json.loads(values['before'])
    state = json.loads(values['auto_policy'])
    assert state['auto_review']['enabled'] is True and state['version'] == invoice.version
    assert sql.index("'auto_review_state'") < sql.index('COMMIT TRANSACTION;')
    assert '@expected' in sql and 'Duplicate invoice' in sql and 'Filing period frozen' in sql


def test_policy_read_is_tenant_scoped_and_old_revision_edit_cancels_pending_decision(invoice):
    store = make_store(invoice)
    policy = AutoReview(enabled=True, status='running', job_id='old-job').model_dump(mode='json')
    store.repo.query.return_value = [{'invoice_id': invoice.invoice_id, 'after_payload':
        json.dumps({'version': invoice.version - 1, 'auto_review': policy})}]
    result = store.auto_policies([invoice])[0]
    assert result.auto_review.enabled is True
    assert result.auto_review.status == 'cancelled' and not result.auto_review.job_id
    sql, params = store.repo.query.call_args.args
    assert 'client_id=@client_id' in sql
    assert {p.name: p.value for p in params}['client_id'] == invoice.client_id


def test_current_policy_survives_refresh_and_empty_policy_defaults_off(invoice):
    store = make_store(invoice)
    assert not store.auto_policies([invoice])[0].auto_review.enabled
    policy = AutoReview(enabled=True, requested_by='owner').model_dump(mode='json')
    store.repo.query.return_value = [{'invoice_id': invoice.invoice_id, 'after_payload':
        {'version': invoice.version, 'auto_review': policy}}]
    assert store.auto_policies([invoice])[0].auto_review.enabled
