import hashlib
import io
import json
from zipfile import ZipFile

import pytest
from fastapi import HTTPException

from app.services.gst.filing_workspace import prepare_report, reporting_periods, scoped_rows, working_papers


def report(scope='month', data=None):
    months, label = reporting_periods('2026-09', scope)
    tables = {name: [] for name in ('bronze_document','silver_invoice_header','silver_outward_invoice',
        'silver_gstr2b_invoice','gold_filing_summary','gold_itc_ledger','gold_gstr2b_match','gst_filing_status')}
    tables.update(data or {})
    return prepare_report('client-a','2026-09',scope,months,label,{},tables)


def test_reporting_period_boundaries():
    assert reporting_periods('2026-01','quarter')[0] == ['2026-01','2026-02','2026-03']
    assert reporting_periods('2026-09','quarter')[0] == ['2026-07','2026-08','2026-09']
    months, label = reporting_periods('2026-03','year')
    assert len(months)==12 and months[0]=='2025-04' and months[-1]=='2026-03' and label=='FY 2025-26'
    assert reporting_periods('2026-04','year')[0][0]=='2026-04'
    for period, scope in [('2026-13','month'),('2026-09','all')]:
        with pytest.raises(HTTPException):
            reporting_periods(period,scope)


def test_actual_sources_visible_but_not_counted_as_gold():
    result=report(data={'bronze_document':[{'doc_id':'a','period':'2026-09','original_filename':'bill.png'}],
        'silver_invoice_header':[{'doc_id':'a','total':'1333.50','validation_status':'needs_review',
                                 'validation_errors':['GSTIN_CHECKSUM','INVOICE_DATE_MISSING']} ]})
    assert result['summary'] is None and not result['sample'] and not result['portal_ready']
    assert result['documents'][0]['silver']['total']=='1333.50'
    assert result['documents'][0]['issues'][0]['message'].startswith('Correct the supplier GSTIN')
    assert {'GSTIN_REQUIRED','DOCUMENT_REVIEW','GOLD_MISSING','PORTAL_SCHEMA_UNVERIFIED'} <= {c['code'] for c in result['checks']}


def test_consolidation_uses_latest_runs_and_does_not_net_across_months():
    result=report('quarter',{'gold_filing_summary':[
        {'period':'2026-07','run_id':'old','computed_at':'2026-09-01','cash_required':'999'},
        {'period':'2026-07','run_id':'new','computed_at':'2026-09-02','cash_required':'100','cash_by_head':{'igst':'100'},'output_by_head':{'igst':'100'}},
        {'period':'2026-08','run_id':'aug','computed_at':'2026-09-02','cash_required':'0','eligible_by_head':{'igst':'100'}}],
        'gold_itc_ledger':[{'period':'2026-07','doc_id':'a','run_id':'old','blocked_igst':'999'},
                           {'period':'2026-07','doc_id':'a','run_id':'new','blocked_igst':'1'}]})
    assert result['summary']['cash_required']=='100.00'  # Later credit cannot erase earlier cash liability.
    assert result['summary']['credit_adjustments']['blocked']['igst']=='1.00'
    assert len(result['ledger'])==1 and not result['calculation_complete']


def test_zip_manifest_and_spreadsheet_safety():
    result=report(data={'silver_outward_invoice':[{'invoice_no':'=HYPERLINK("bad")','period':'2026-09'}]})
    with ZipFile(io.BytesIO(working_papers(result))) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        assert not manifest['sample'] and not manifest['portal_ready']
        for name,digest in manifest['sha256'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==digest
        assert "'=HYPERLINK" in archive.read('sales_register.csv').decode('utf-8-sig')
        assert json.loads(archive.read('preparation.json'))['client_id']=='client-a'
    with pytest.raises(HTTPException):
        working_papers({**result,'sample':True})


def test_every_report_query_binds_client_and_periods():
    class Repo:
        def table(self,name):
            return 'project.dataset.'+name
        def query(self,sql,params):
            assert 'client_id=@client_id AND period IN UNNEST(@periods)' in sql
            assert params[0].value=='client-a'
            assert params[1].values==['2026-09']
            return []
    assert scoped_rows(Repo(),'client-a',['2026-09'],'bronze_document')==[]
