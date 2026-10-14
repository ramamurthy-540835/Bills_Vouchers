from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import BadRequest

from app.gst import returns


@pytest.mark.parametrize('action',['approve','reject'])
def test_preparer_cannot_review_own_snapshot(action):
    with pytest.raises(HTTPException) as exc:
        returns.authorize_transition({'state':'under_review','maker_id':'same'},action,SimpleNamespace(id='same',role='tax_admin'),'Reviewed evidence')
    assert exc.value.status_code==403


@pytest.mark.parametrize('role',['client','viewer'])
def test_unprivileged_cannot_approve(role):
    with pytest.raises(HTTPException) as exc:
        returns.authorize_transition({'state':'under_review','maker_id':'maker'},'approve',SimpleNamespace(id='other',role=role),'Reviewed evidence')
    assert exc.value.status_code==403


def test_distinct_reviewer_and_explicit_reopen_reason():
    actor=SimpleNamespace(id='reviewer',role='tax_admin')
    assert returns.authorize_transition({'state':'under_review','maker_id':'maker'},'approve',actor,'Source evidence reviewed')=='approved'
    with pytest.raises(HTTPException) as exc:
        returns.authorize_transition({'state':'approved'},'reopen',actor,'')
    assert exc.value.status_code==422
    assert returns.authorize_transition({'state':'approved'},'reopen',actor,'Correct supplier invoice')=='reopened'


def test_cannot_jump_to_filed_or_approve_unreviewed():
    actor=SimpleNamespace(id='reviewer',role='tax_admin')
    for action,state in [('filed','approved'),('approve','prepared')]:
        with pytest.raises(HTTPException):
            returns.authorize_transition({'state':state,'maker_id':'maker'},action,actor,'Reviewed')


def test_stale_source_transaction_returns_conflict(monkeypatch):
    monkeypatch.setattr(returns,'current',lambda *args:{'state':'prepared','version':2,'maker_id':'maker','source_hash':'old','snapshot_id':'s'})
    store=Mock();store.query.side_effect=BadRequest('Source changed')
    with pytest.raises(HTTPException) as exc:
        returns.change(store,'2026-09',SimpleNamespace(id='maker',role='client'),'review',2)
    assert exc.value.status_code==409


def test_stale_version_does_not_write(monkeypatch):
    monkeypatch.setattr(returns,'current',lambda *args:{'state':'prepared','version':2})
    store=Mock()
    with pytest.raises(HTTPException) as exc:
        returns.change(store,'2026-09',SimpleNamespace(id='maker',role='client'),'review',1)
    assert exc.value.status_code==409
    store.query.assert_not_called()
