"""Apply additive schema and validate tenant-bound DML without persisting test bills."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from app.gst.schemas.invoice import GstInvoice, LineItem, Totals
from app.gst.store import BillStore

token = subprocess.check_output(['gcloud.cmd', 'auth', 'print-access-token'], text=True).strip()
client = bigquery.Client(project='aidirac-503309', credentials=Credentials(token))
job = client.query(Path('infra/bq/migrations/007_gst_invoice.sql').read_text(), location='asia-south1')
job.result()
print('Applied additive migration:', job.job_id)


class Probe:
    settings = SimpleNamespace(gcp_project_id='aidirac-503309')
    def query(self, sql, params):
        # The serialization guard and all invoice/line/audit inserts are rolled back.
        if sql.startswith('MERGE'):
            sql = 'BEGIN TRANSACTION; ' + sql + '; ROLLBACK TRANSACTION;'
        else:
            sql = sql.replace('COMMIT TRANSACTION;', 'ROLLBACK TRANSACTION;')
        probe = client.query(sql, location='asia-south1', job_config=bigquery.QueryJobConfig(query_parameters=params))
        probe.result()
        print('Rolled-back SQL verification:', probe.job_id)
        return []


invoice = GstInvoice(client_id='v3-sql-rollback-check', source_doc_id='rollback-only',
    supplier_legal_name='Rollback verification', invoice_number='ROLLBACK', invoice_date='2026-09-01',
    line_items=[LineItem(description='Rollback verification', hsn_sac='1234', taxable_value='100', gst_rate='18', cgst='9', sgst='9')],
    totals=Totals(taxable_value='100', cgst='9', sgst='9', invoice_total='118'))
BillStore(Probe(), invoice.client_id).save(invoice, 'verification', 'rollback-check')
count = list(client.query('SELECT COUNT(*) n FROM `aidirac-503309.gold.gst_invoice` WHERE client_id=@client_id',
    job_config=bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('client_id','STRING',invoice.client_id)])))[0]['n']
assert count == 0
Path('artifacts/v3').mkdir(parents=True, exist_ok=True)
Path('artifacts/v3/migration.json').write_text(json.dumps({'migration':'007_gst_invoice','job_id':job.job_id,'sql_rollback_check':'passed','persisted_test_invoices':0}, indent=2))
