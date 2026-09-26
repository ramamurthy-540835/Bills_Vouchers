import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException
from google.cloud import storage

from app.config import get_settings
from app.services.gst.medallion import param
from .schemas.invoice import GstInvoice
from .validate_invoice import financial_year


class BillStore:
    def __init__(self, repo, client_id):
        self.repo, self.client_id = repo, str(client_id)
        project = repo.settings.gcp_project_id
        if not re.fullmatch(r'[a-z][a-z0-9-]+', project):
            raise ValueError('Invalid configured project')
        self.project = project

    def table(self, dataset, name):
        return f'`{self.project}.{dataset}.{name}`'

    def query(self, sql, params=()):
        return self.repo.query(sql, [param('client_id', self.client_id), *params])

    def list(self, period=None, status=None):
        clause = ''
        params = []
        if period:
            clause += ' AND period=@period'
            params.append(param('period', period))
        if status:
            clause += ' AND status=@status'
            params.append(param('status', status))
        return [GstInvoice.model_validate(json.loads(row['payload']) if isinstance(row['payload'], str) else row['payload'])
                for row in self.query(f'SELECT payload FROM {self.table("gold", "gst_invoice")} WHERE client_id=@client_id{clause} ORDER BY updated_at DESC', params)]

    def get(self, invoice_id):
        rows = self.query(f'SELECT payload FROM {self.table("gold", "gst_invoice")} WHERE client_id=@client_id AND invoice_id=@id', [param('id', invoice_id)])
        if not rows:
            raise HTTPException(404, 'Bill not found.')
        payload = rows[0]['payload']
        return GstInvoice.model_validate(json.loads(payload) if isinstance(payload, str) else payload)

    def save(self, invoice, actor, action, previous=None, selected_period=None):
        if invoice.client_id != self.client_id or invoice.sample:
            raise HTTPException(403, {'code': 'sample_data_blocked', 'message': 'Illustrations cannot be saved.'})
        table = self.table('gold', 'gst_invoice')
        lock = self.table('ops', 'gst_bill_lock')
        self.query(f'MERGE {lock} T USING (SELECT @client_id client_id) S ON T.client_id=S.client_id WHEN NOT MATCHED THEN INSERT (client_id,touched_at) VALUES (@client_id,CURRENT_TIMESTAMP())')
        payload = invoice.model_dump_json()
        params = [param('id', invoice.invoice_id), param('payload', payload),
                  param('before', previous.model_dump_json() if previous else 'null'),
                  param('expected', previous.version if previous else 0, 'INT64'),
                  param('version', invoice.version, 'INT64'), param('actor', str(actor)), param('action', action),
                  param('period', invoice.invoice_date.strftime('%Y-%m') if invoice.invoice_date else selected_period),
                  param('fy', financial_year(invoice.invoice_date) if invoice.invoice_date else None, 'INT64'),
                  param('supplier', invoice.supplier_gstin), param('number', invoice.invoice_number.strip().upper()),
                  param('status', invoice.status)]
        sql = f'''BEGIN TRANSACTION;
        UPDATE {lock} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id=@client_id;
        ASSERT COALESCE((SELECT version FROM {table} WHERE client_id=@client_id AND invoice_id=@id),0)=@expected AS 'Bill changed; reload';
        ASSERT @status='rejected' OR NOT EXISTS(SELECT 1 FROM {table} WHERE client_id=@client_id AND supplier_gstin=@supplier AND invoice_number=@number AND financial_year=@fy AND invoice_id!=@id AND status!='rejected') AS 'Duplicate invoice';
        DELETE FROM {table} WHERE client_id=@client_id AND invoice_id=@id;
        INSERT INTO {table} (client_id,invoice_id,source_doc_id,invoice_date,period,financial_year,supplier_gstin,invoice_number,direction,status,eligibility,taxable_value,cgst,sgst,igst,cess,invoice_total,payload,version,created_at,updated_at)
        SELECT @client_id,@id,JSON_VALUE(@payload,'$.source_doc_id'),CAST(JSON_VALUE(@payload,'$.invoice_date') AS DATE),@period,@fy,@supplier,@number,JSON_VALUE(@payload,'$.direction'),@status,JSON_VALUE(@payload,'$.itc.eligibility'),
        CAST(JSON_VALUE(@payload,'$.totals.taxable_value') AS NUMERIC),CAST(JSON_VALUE(@payload,'$.totals.cgst') AS NUMERIC),CAST(JSON_VALUE(@payload,'$.totals.sgst') AS NUMERIC),CAST(JSON_VALUE(@payload,'$.totals.igst') AS NUMERIC),CAST(JSON_VALUE(@payload,'$.totals.cess') AS NUMERIC),CAST(JSON_VALUE(@payload,'$.totals.invoice_total') AS NUMERIC),PARSE_JSON(@payload),@version,CURRENT_TIMESTAMP(),CURRENT_TIMESTAMP();
        DELETE FROM {self.table('silver', 'gst_invoice_line')} WHERE client_id=@client_id AND invoice_id=@id;
        INSERT INTO {self.table('silver', 'gst_invoice_line')}
        SELECT @client_id,@id,position+1,CAST(JSON_VALUE(@payload,'$.invoice_date') AS DATE),JSON_VALUE(line,'$.description'),JSON_VALUE(line,'$.hsn_sac'),CAST(JSON_VALUE(line,'$.quantity') AS NUMERIC),JSON_VALUE(line,'$.unit'),CAST(JSON_VALUE(line,'$.gst_rate') AS NUMERIC),CAST(JSON_VALUE(line,'$.taxable_value') AS NUMERIC),CAST(JSON_VALUE(line,'$.cgst') AS NUMERIC),CAST(JSON_VALUE(line,'$.sgst') AS NUMERIC),CAST(JSON_VALUE(line,'$.igst') AS NUMERIC),CAST(JSON_VALUE(line,'$.cess') AS NUMERIC)
        FROM UNNEST(JSON_QUERY_ARRAY(@payload,'$.line_items')) line WITH OFFSET position;
        INSERT INTO {self.table('ops', 'gst_bill_audit')} VALUES (@client_id,@id,@actor,@action,PARSE_JSON(@before),PARSE_JSON(@payload),CURRENT_TIMESTAMP());
        COMMIT TRANSACTION;'''
        self.query(sql, params)

    def job(self, job_id, payload=None):
        table = self.table('ops', 'gst_bill_job')
        if payload is not None:
            self.query(f'''MERGE {table} T USING (SELECT @client_id client_id,@id job_id) S
                ON T.client_id=S.client_id AND T.job_id=S.job_id
                WHEN MATCHED THEN UPDATE SET payload=PARSE_JSON(@payload),updated_at=CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT VALUES (@client_id,@id,PARSE_JSON(@payload),CURRENT_TIMESTAMP())''',
                [param('id', job_id), param('payload', json.dumps(payload))])
            return payload
        rows = self.query(f'SELECT payload FROM {table} WHERE client_id=@client_id AND job_id=@id', [param('id', job_id)])
        if not rows:
            raise HTTPException(404, 'Upload not found.')
        value = rows[0]['payload']
        return json.loads(value) if isinstance(value, str) else value

    def usage(self, doc_id, input_tokens, output_tokens):
        self.query(f'INSERT INTO {self.table("ops", "extraction_log")} VALUES (@client_id,@doc,@model,@input,@output,CURRENT_TIMESTAMP())',
                   [param('doc', doc_id), param('model', get_settings().gemini_model), param('input', input_tokens, 'INT64'), param('output', output_tokens, 'INT64')])

    def upload_object(self, content, doc_id, filename, layer, mime):
        # Stable client UUID prevents business-name collisions and tenant path traversal.
        safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', filename)[:180]
        day = datetime.now(timezone.utc).strftime('%Y/%m/%d')
        key = f'{self.client_id}/{layer}/bills/{day}/{doc_id}/{safe_name}'
        bucket = storage.Client(project=self.project).bucket(get_settings().gcs_bucket_name)
        bucket.blob(key).upload_from_string(content, content_type=mime)
        return f'gs://{bucket.name}/{key}'

    def download_object(self, ref):
        prefix = f'gs://{get_settings().gcs_bucket_name}/{self.client_id}/bronze/bills/'
        if not ref.startswith(prefix):
            raise HTTPException(404, 'Original bill not found.')
        key = ref.split('/', 3)[3]
        return storage.Client(project=self.project).bucket(get_settings().gcs_bucket_name).blob(key).download_as_bytes()
