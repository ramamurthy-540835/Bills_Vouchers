from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.gst.store import BillStore
from app.routers.gst_bills import selected_period


@pytest.mark.parametrize('explicit,session,expected',[
    ('',{},'2026-09'),
    ('2026-04',{},'2026-04'),
    ('',{'period':'2026-03'},'2026-03'),
    ('2026-04',{'period':'2026-03'},'2026-04'),
])
def test_demo_opens_populated_month_and_respects_selection(explicit,session,expected):
    store=Mock();store.latest_period.return_value='2026-09'
    assert selected_period(SimpleNamespace(session=session),SimpleNamespace(is_test=True),store,explicit)==expected
    assert store.latest_period.call_count==(0 if explicit or session else 1)


def test_regular_client_keeps_current_month_default():
    store=Mock()
    assert selected_period(SimpleNamespace(session={}),SimpleNamespace(is_test=False),store)==date.today().strftime('%Y-%m')
    store.latest_period.assert_not_called()


def test_empty_demo_uses_current_month():
    store=Mock();store.latest_period.return_value=None
    assert selected_period(SimpleNamespace(session={}),SimpleNamespace(is_test=True),store)==date.today().strftime('%Y-%m')


def test_latest_period_query_is_tenant_bound():
    repo=Mock(settings=SimpleNamespace(gcp_project_id='test-project'))
    repo.query.return_value=[{'period':'2026-09'}]
    assert BillStore(repo,'only-this-client').latest_period()=='2026-09'
    sql,params=repo.query.call_args.args
    assert 'WHERE client_id=@client_id' in sql and "status='confirmed'" in sql
    assert params[0].name=='client_id' and params[0].value=='only-this-client'
