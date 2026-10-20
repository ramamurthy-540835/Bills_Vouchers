import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from google.api_core.exceptions import Conflict
from app.routers import gst_intake
from app.gst import returns
from tests.gst.test_source_reconciliation import source


def test_snapshot_is_bound_audited_and_never_updates_financial_records(monkeypatch,invoice):
    store=SimpleNamespace(client_id=invoice.client_id,repo=SimpleNamespace(table=lambda name:'p.finance.'+name),
                          table=lambda dataset,name:f'p.{dataset}.{name}')
    monkeypatch.setattr(returns,'fingerprint',lambda *args:'digest')
    invoice.status='confirmed'
    saved={}
    def query(sql,params=()):
        values={p.name:p.value for p in params}
        assert 'client_id=@client_id' in sql
        if 'BEGIN TRANSACTION' in sql:
            assert "ASSERT" in sql and "AS 'Source changed'" in sql
            assert values['actor']=='reviewer'
            assert 'UPDATE p.gold.gst_invoice' not in sql
            assert 'INSERT INTO p.gold' not in sql
            saved.update(json.loads(values['payload']))
            return []
        if 'bulk_import_batches' in sql:return [{'batch_id':'batch'}]
        if 'integration_source_records' in sql:
            assert values['period']=='2026-09'
            return [{'batch_id':'batch',**source(invoice)}]
        if 'gst_invoice' in sql:return [{'payload':invoice.model_dump(mode='json')}]
        if 'external_transaction_links' in sql:return [{'payload':saved}]
        raise AssertionError(sql)
    store.query=query
    result=gst_intake.reconcile_staged(store,'batch','2026-09','reviewer')
    assert result['counts']=={'matched':1}
    assert result['financial_records_changed']==0
    assert result['historical_snapshot'] is True
    first=result['run_id']
    assert gst_intake.reconcile_staged(store,'batch','2026-09','reviewer')['run_id']==first


def test_unknown_batch_does_not_read_other_data():
    store=SimpleNamespace(query=Mock(return_value=[]),table=lambda *args:'table')
    with pytest.raises(HTTPException) as exc:
        gst_intake.reconcile_staged(store,'foreign','2026-09','user')
    assert exc.value.status_code==404
    assert store.query.call_count==1


def test_concurrent_changes_do_not_save_stale_snapshot(monkeypatch):
    store=SimpleNamespace(client_id='a',repo=SimpleNamespace(table=lambda name:'p.finance.'+name),
                          table=lambda dataset,name:f'p.{dataset}.{name}')
    monkeypatch.setattr(returns,'fingerprint',lambda *args:'digest')
    store.query=Mock(side_effect=[[{'batch_id':'batch'}],[],[],Conflict('concurrent change')])
    with pytest.raises(HTTPException) as exc:
        gst_intake.reconcile_staged(store,'batch','2026-09','user')
    assert exc.value.status_code==409


def test_original_source_uses_scoped_store_and_private_download(monkeypatch):
    store=SimpleNamespace(query=Mock(return_value=[{'payload':{'original_ref':'gs://v3/tenant/bronze/file.json'}}]),
                          table=lambda *args:'p.ops.bulk_import_batches',download_object=Mock(return_value=b'[]'))
    monkeypatch.setattr(gst_intake,'scope',lambda *args:(None,store))
    response=gst_intake.intake_original('batch',None,None,None)
    assert response.body==b'[]'
    assert response.headers['cache-control']=='private, no-store'
    assert response.headers['content-disposition']=='attachment; filename="file.json"'
    store.download_object.assert_called_once_with('gs://v3/tenant/bronze/file.json')
    assert 'client_id=@client_id' in store.query.call_args.args[0]
