from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
import json

import pytest
from fastapi import HTTPException

from app.gst import dashboard


@pytest.fixture
def source(monkeypatch, invoice):
    invoice.status = 'confirmed'
    data = {'2026-09': {'source_hash': 'a'*64, 'invoices': [invoice], 'statements': [],
                       'filing': {'state': 'draft', 'version': 0}}}
    empty = {'source_hash': 'b'*64, 'invoices': [], 'statements': [], 'filing': {'state': 'draft', 'version': 0}}
    monkeypatch.setattr(dashboard, 'read_range', lambda store, months, evidence=True:
                        {month: deepcopy(data.get(month, empty)) for month in months})
    return SimpleNamespace(client_id='a'), data


def test_quarter_does_not_spend_previous_month_credit(source, invoice, profile):
    store, data = source
    sale = invoice.model_copy(deep=True);sale.direction = 'sale';sale.invoice_id = 'sale'
    data['2026-08'] = deepcopy(data['2026-09'])
    data['2026-08']['invoices'] = [sale]
    row = dashboard.build(store, '2026-09', 'quarter', lambda _: profile)
    assert row['periods'] == ['2026-07', '2026-08', '2026-09']
    assert row['confirmed_sales'] == row['confirmed_purchases'] == Decimal('1180')
    # September purchase credit cannot pay August output tax in this range view.
    assert row['scenarios'] == dict.fromkeys(('recorded','matched','eligible','noCredit'), Decimal('180'))
    assert row['heads']['cash']['cgst'] == Decimal('90')
    assert row['unmatched_count'] == 1 and row['mismatch_count'] == 0
    assert row['confirmed_count'] == 2


def test_notes_review_rejected_and_synthetic_are_not_confirmed_sales(source, invoice, profile):
    store, data = source
    note = invoice.model_copy(deep=True);note.invoice_type='credit_note';note.invoice_id='note';note.invoice_number='CN-1'
    pending = invoice.model_copy(deep=True);pending.status='needs_review';pending.invoice_id='pending'
    rejected = invoice.model_copy(deep=True);rejected.status='rejected';rejected.invoice_id='rejected'
    sample = invoice.model_copy(deep=True);sample.sample=True;sample.direction='sale';sample.invoice_id='sample'
    data['2026-09']['invoices'] += [note,pending,rejected,sample]
    result = dashboard.build(store,'2026-09','month',lambda _:profile)
    assert result['confirmed_purchases']==0 and result['confirmed_sales']==0
    assert result['confirmed_count']==2 and result['review_count']==1 and result['bill_count']==5
    assert result['mismatch_count']==1  # Unsupported credit-note reconciliation stays visible.


def test_stale_preparation_and_financial_year(source, profile):
    store, data = source
    data['2026-09']['filing']={'state':'prepared','version':1,'source_hash':'old'}
    result=dashboard.build(store,'2026-09','financial_year',lambda _:profile)
    assert len(result['monthly'])==12
    assert result['periods'][0]=='2026-04' and result['periods'][-1]=='2027-03'
    assert next(row for row in result['monthly'] if row['period']=='2026-09')['filing']['source_changed']


@pytest.mark.parametrize('field,value',[('source_hash','changed'),('filing',{'state':'approved','version':2})])
def test_changes_during_read_are_rejected(source, profile, monkeypatch, field, value):
    store,data=source
    first=deepcopy(data);last=deepcopy(data);last['2026-09'][field]=value
    monkeypatch.setattr(dashboard,'read_range',Mock(side_effect=[first,last]))
    with pytest.raises(HTTPException) as error:
        dashboard.build(store,'2026-09','month',lambda _:profile)
    assert error.value.status_code==409


def test_scope_and_size_fail_closed(source, invoice, profile, monkeypatch):
    store,_=source;invoice.client_id='foreign'
    with pytest.raises(HTTPException) as error:
        dashboard.build(store,'2026-09','month',lambda _:profile)
    assert error.value.status_code==403
    invoice.client_id='a';monkeypatch.setattr(dashboard,'MAX_ROWS',0)
    with pytest.raises(HTTPException) as error:
        dashboard.build(store,'2026-09','month',lambda _:profile)
    assert error.value.status_code==422
    for period,scope in [('bad','month'),('2000-01','financial_year'),('2099-12','financial_year'),('2026-09','all')]:
        with pytest.raises(HTTPException):
            dashboard.build(store,period,scope,lambda _:profile)


def test_batched_sql_is_bounded_parameterized_and_preserves_evidence(invoice):
    store=Mock(client_id='a')
    store.table.side_effect=lambda layer,name:f'`project.{layer}.{name}`'
    store.repo.table.side_effect=lambda name:f'project.finance.{name}'
    store.query.return_value=[{'period':'2026-09','source_hash':'hash','states':'[]',
                               'invoices':json.dumps([invoice.model_dump(mode='json')]),'statements':'[]'}]
    result=dashboard.read_range(store,['2026-09'])
    assert result['2026-09']['invoices'][0].invoice_id==invoice.invoice_id
    assert result['2026-09']['filing']=={'state':'draft','version':0}
    sql,params=store.query.call_args.args
    assert '2026-09' not in sql and 'LIMIT 10001' in sql
    assert 'WHERE client_id=@client_id AND period=@month0' in sql
    assert params[0].value=='2026-09'
    store.query.return_value[0]['states']='[{"state":"draft"},{"state":"approved"}]'
    with pytest.raises(HTTPException) as error:dashboard.read_range(store,['2026-09'])
    assert error.value.status_code==409
