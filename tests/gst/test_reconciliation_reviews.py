from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import Conflict

from app.gst import reconciliation_reviews as reviews


@pytest.fixture
def prepared(monkeypatch, invoice):
    invoice.status = 'confirmed'
    store = Mock()
    store.list.return_value = [invoice]
    store.matching_rows.return_value = []
    monkeypatch.setattr(reviews.returns, 'fingerprint', lambda *args:'a'*64)
    body = {'case_id':'bill:'+invoice.invoice_id,'source_hash':'a'*64,'version':0,
            'decision':'needs_correction','reason':'Supplier invoice requires correction.'}
    return store, SimpleNamespace(id='reviewer',role='tax_admin'), body


@pytest.mark.parametrize('role',['viewer','client'])
def test_clients_cannot_record_accountant_decisions(prepared, role):
    store, actor, body = prepared
    actor.role = role
    with pytest.raises(HTTPException) as error:reviews.record(store,'2026-09',actor,body)
    assert error.value.status_code == 403
    store.query.assert_not_called()


@pytest.mark.parametrize('changes',[{'version':True},{'version':-1},{'version':2**63},{'reason':' '},{'decision':'approve_itc'},
                                   {'source_hash':'bad'},{'decision':[]},{'case_id':None}])
def test_invalid_review_never_writes(prepared,changes):
    store, actor, body = prepared
    with pytest.raises(HTTPException) as error:reviews.record(store,'2026-09',actor,{**body,**changes})
    assert error.value.status_code == 422
    store.query.assert_not_called()


def test_stale_or_foreign_case_rejected(prepared):
    store, actor, body = prepared
    for changed, status in [({'source_hash':'b'*64},409),({'case_id':'bill:foreign'},404)]:
        with pytest.raises(HTTPException) as error:reviews.record(store,'2026-09',actor,{**body,**changed})
        assert error.value.status_code == status
    store.query.assert_not_called()


def test_concurrent_write_is_conflict_and_success_never_overrides_credit(prepared):
    store, actor, body = prepared
    store.query.side_effect = Conflict('Concurrent transaction')
    with pytest.raises(HTTPException) as error:reviews.record(store,'2026-09',actor,body)
    assert error.value.status_code == 409
    store.query.side_effect = None
    assert reviews.record(store,'2026-09',actor,body) == {'saved':True,'version':1,'financial_override':False}


def test_history_pagination_preserves_all_versions(prepared):
    store, _, _ = prepared
    store.query.return_value = [{'version':version,'evidence':'{"status":"amount_mismatch"}'} for version in range(51,0,-1)]
    result = reviews.history(store,'2026-09','bill:1')
    assert len(result['history']) == 50 and result['next_before_version'] == 2
    assert result['history'][0]['evidence']['status'] == 'amount_mismatch'


def test_old_review_marked_stale_without_hiding_case(prepared):
    store, _, body = prepared
    store.query.return_value = [{'case_id':body['case_id'],'version':1,'source_hash':'b'*64}]
    case = reviews.view(store,'2026-09')['cases'][0]
    assert case['review']['stale'] is True and case['status'] == 'missing_statement'
