import json
import re
import random
import time
from datetime import datetime, timezone

from fastapi import HTTPException
from google.cloud import storage
from google.api_core.exceptions import BadRequest, Conflict, PreconditionFailed

from app.config import get_settings
from app.services.gst.medallion import param
from .schemas.invoice import GstInvoice, AutoReview
from .validate_invoice import financial_year
from .naming import bill_filename
from .job_state import JobState, payload as job_payload


class BillStore(JobState):
    intelligence_version = None
    def __init__(self, repo, client_id):
        self.repo, self.client_id = repo, str(client_id)
        project = repo.settings.gcp_project_id
        if not re.fullmatch(r'[a-z][a-z0-9-]+', project):
            raise ValueError('Invalid configured project')
        self.project = project

    def table(self, dataset, name):
        prefix = getattr(self.repo.settings, 'gst_dataset_prefix', '')
        if prefix and not re.fullmatch(r'[a-z][a-z0-9_]*_', prefix):
            raise ValueError('Invalid canonical dataset prefix')
        if dataset not in {'gold', 'silver', 'bronze', 'ops'} or not re.fullmatch(r'[a-z][a-z0-9_]*', name):
            raise ValueError('Invalid canonical table')
        return f'`{self.project}.{prefix}{dataset}.{name}`'

    def query(self, sql, params=()):
        parameters = [param('client_id', self.client_id), *params]
        transaction = sql.lstrip().upper().startswith('BEGIN TRANSACTION;')
        for attempt in range(3):
            try:
                return self.repo.query(sql, parameters)
            except (BadRequest, Conflict) as exc:
                message = str(exc).lower()
                if 'worker claim lost' in message:
                    raise RuntimeError('Worker claim lost; stop processing this upload.') from None
                if 'filing period frozen' in message:
                    raise HTTPException(409, 'This filing period is frozen. An authorized reopen is required.') from None
                # Replay only a transaction explicitly rolled back by contention.
                # Timeouts/unknown commit outcomes and business assertions are NOT
                # retryable. Every replay rechecks versions, tenant and worker fences.
                aborted = 'transaction is aborted due to concurrent update' in message
                if not transaction or not aborted or attempt == 2:
                    raise
                time.sleep(random.uniform(0.1, 0.2) * (2 ** attempt))
        raise RuntimeError('Transaction retry exhausted')  # Defensive unreachable guard.

    def latest_period(self):
        rows = self.query(f'''SELECT COALESCE(MAX(IF(status='confirmed',period,NULL)),MAX(period)) AS period
            FROM {self.table('gold', 'gst_invoice')} WHERE client_id=@client_id AND status!='rejected' ''')
        return rows[0]['period'] if rows else None

    def duplicate_candidates(self, invoice):
        if not invoice.invoice_date or not invoice.invoice_number:
            return []
        rows=self.query(f'''SELECT payload FROM {self.table('gold','gst_invoice')}
            WHERE client_id=@client_id AND supplier_gstin=@supplier AND invoice_number=@number
            AND financial_year=@fy AND invoice_id!=@id LIMIT 1''',
            [param('supplier',invoice.supplier_gstin.strip().upper()),param('number',invoice.invoice_number.strip().upper()),
             param('fy',financial_year(invoice.invoice_date),'INT64'),param('id',invoice.invoice_id)])
        return [GstInvoice.model_validate(json.loads(r['payload']) if isinstance(r['payload'],str) else r['payload']) for r in rows]

    def list(self, period=None, status=None):
        clause = ''
        params = []
        if period:
            clause += ' AND period=@period'
            params.append(param('period', period))
        if status:
            clause += ' AND status=@status'
            params.append(param('status', status))
        return self.auto_policies([GstInvoice.model_validate(json.loads(row['payload']) if isinstance(row['payload'], str) else row['payload'])
                for row in self.query(f'SELECT payload FROM {self.table("gold", "gst_invoice")} WHERE client_id=@client_id{clause} ORDER BY updated_at DESC', params)])

    def get(self, invoice_id):
        rows = self.query(f'SELECT payload FROM {self.table("gold", "gst_invoice")} WHERE client_id=@client_id AND invoice_id=@id', [param('id', invoice_id)])
        if not rows:
            raise HTTPException(404, 'Bill not found.')
        payload = rows[0]['payload']
        return self.auto_policies([GstInvoice.model_validate(json.loads(payload) if isinstance(payload, str) else payload)])[0]

    def auto_policies(self, invoices):
        # Keep new policy metadata out of the strict canonical invoice schema
        # consumed by older revisions. Policy and invoice writes share one txn.
        if not invoices:
            return invoices
        rows = self.query(f'''SELECT invoice_id,after_payload FROM {self.table('ops','gst_bill_audit')}
            WHERE client_id=@client_id AND action='auto_review_state'
            AND invoice_id IN UNNEST(JSON_VALUE_ARRAY(@auto_ids))
            QUALIFY ROW_NUMBER() OVER(PARTITION BY invoice_id ORDER BY created_at DESC)=1''',
            [param('auto_ids', json.dumps([i.invoice_id for i in invoices]))])
        policies = {row['invoice_id']: row['after_payload'] for row in rows if row.get('after_payload') is not None}
        for invoice in invoices:
            payload = policies.get(invoice.invoice_id)
            if payload is None:
                continue
            state = json.loads(payload) if isinstance(payload, str) else payload
            policy = AutoReview.model_validate(state['auto_review'])
            if state['version'] != invoice.version and policy.enabled:
                policy.status = 'cancelled'
                policy.job_id = ''
                policy.checks = {}
                policy.rule_ids = []
                policy.reasons = ['The invoice changed in another revision. Run Auto Review again against the current version.']
            invoice.auto_review = policy
        return invoices

    def correction_queue(self, period, state='active', offset=0):
        # Legacy rejected invoices have no correction_state. Keep them actionable.
        stage = """CASE
          WHEN status='rejected' THEN CASE
            WHEN JSON_VALUE(payload,'$.correction_state') IN ('correction_requested','corrected')
            THEN JSON_VALUE(payload,'$.correction_state') ELSE 'rejected' END
          WHEN status='needs_review' AND JSON_VALUE(payload,'$.correction_state')='resubmitted'
            THEN 'resubmitted'
          WHEN status='confirmed' AND JSON_VALUE(payload,'$.correction_state')='approved'
            THEN 'approved' END"""
        rows = self.query(f"""WITH scoped AS (
            SELECT invoice_id,payload,updated_at,{stage} AS correction_stage
            FROM {self.table('gold','gst_invoice')}
            WHERE client_id=@client_id AND period=@period)
            SELECT payload,correction_stage FROM scoped
            WHERE (@state='active' AND correction_stage IN
                ('rejected','correction_requested','corrected','resubmitted'))
              OR correction_stage=@state
            ORDER BY updated_at DESC,invoice_id LIMIT 51 OFFSET @offset""",
            [param('period',period),param('state',state),param('offset',offset,'INT64')])
        return {'invoices': [{**GstInvoice.model_validate(
            json.loads(row['payload']) if isinstance(row['payload'],str) else row['payload']
            ).model_dump(mode='json'), 'correction_stage': row['correction_stage']} for row in rows[:50]],
            'has_more': len(rows)>50}

    def writable_sql(self):
        return f"""ASSERT NOT EXISTS(SELECT 1 FROM `{self.repo.table('gst_filing_status')}`
            WHERE client_id=@client_id AND period IN (@period,@previous_period) AND is_current=TRUE
            AND state NOT IN ('draft','reopened')) AS 'Filing period frozen';
            ASSERT NOT EXISTS(SELECT 1 FROM {self.table('ops','gst_return_current')}
            WHERE client_id=@client_id AND period IN (@period,@previous_period)
            AND state IN ('under_review','approved','exported','filed')) AS 'Filing period frozen';"""

    def assert_writable(self, period):
        try:
            self.query(self.writable_sql(),[param('period',period),param('previous_period',period)])
        except BadRequest as exc:
            if 'filing period frozen' in str(exc).lower():
                raise HTTPException(409, 'This filing period is frozen. An authorized reopen is required.') from None
            raise

    def save(self, invoice, actor, action, previous=None, selected_period=None):
        if invoice.client_id != self.client_id or invoice.sample:
            raise HTTPException(403, {'code': 'sample_data_blocked', 'message': 'Illustrations cannot be saved.'})
        table = self.table('gold', 'gst_invoice')
        lock = self.table('ops', 'gst_bill_lock')
        if selected_period and not invoice.selected_period:
            invoice.selected_period = selected_period
        if invoice.supplier_gstin and invoice.invoice_number and invoice.extraction.raw_ref:
            self.name_original(invoice)
        payload = invoice.model_dump_json(exclude={'auto_review'})
        policy_state = json.dumps({'version': invoice.version, 'auto_review': invoice.auto_review.model_dump(mode='json')})
        before_policy = json.dumps({'version': previous.version if previous else 0,
            'auto_review': previous.auto_review.model_dump(mode='json') if previous else AutoReview().model_dump(mode='json')})
        params = [param('id', invoice.invoice_id), param('payload', payload),
                  param('previous_period', (previous.invoice_date.strftime('%Y-%m') if previous.invoice_date else previous.selected_period) if previous else invoice.selected_period),
                  param('before', previous.model_dump_json(exclude={'auto_review'}) if previous else 'null'),
                  param('auto_policy', policy_state), param('before_auto_policy', before_policy),
                  param('expected', previous.version if previous else 0, 'INT64'),
                  param('version', invoice.version, 'INT64'), param('actor', str(actor)), param('action', action),
                  param('period', invoice.invoice_date.strftime('%Y-%m') if invoice.invoice_date else invoice.selected_period),
                  param('fy', financial_year(invoice.invoice_date) if invoice.invoice_date else None, 'INT64'),
                  param('supplier', invoice.supplier_gstin), param('number', invoice.invoice_number.strip().upper()),
                  param('status', invoice.status)]
        fence, fence_params = self.worker_fence()
        params.extend(fence_params)
        if self.intelligence_version is not None:
            from .intelligence import policy_sql
            fence += f'''ASSERT EXISTS(SELECT 1 FROM ({policy_sql(self)})
                WHERE JSON_VALUE(after_payload,'$.enabled')='true'
                AND CAST(JSON_VALUE(after_payload,'$.version') AS INT64)=@intelligence_version) AS 'Bill changed; business policy cancelled';'''
            params.append(param('intelligence_version',self.intelligence_version,'INT64'))
        if action == 'auto_review_decision':
            fence += f'''ASSERT EXISTS(SELECT 1 FROM `{self.repo.table('client_memberships')}`
                WHERE client_id=@client_id AND user_id=@actor AND is_active=TRUE
                AND access_role IN ('owner','client','admin','accountant','tax_admin')) AS 'Bill changed; review membership revoked';'''
        sql = f'''BEGIN TRANSACTION;
        ASSERT (SELECT COUNT(*) FROM {lock} WHERE client_id='__guard__')=1 AS 'Storage guard missing';
        UPDATE {lock} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
        {self.writable_sql()}
        {fence}
        ASSERT @expected>0 OR @action='restore' OR NOT EXISTS(SELECT 1 FROM {self.table('ops', 'gst_bill_audit')} WHERE client_id=@client_id AND invoice_id=@id AND action='delete') AS 'Bill changed; restore deleted evidence explicitly';
        ASSERT @action!='restore' OR (SELECT CAST(JSON_VALUE(before_payload,'$.version') AS INT64) FROM {self.table('ops', 'gst_bill_audit')} WHERE client_id=@client_id AND invoice_id=@id AND action='delete' ORDER BY created_at DESC LIMIT 1)=@version-1 AS 'Bill changed; reload';
        ASSERT COALESCE((SELECT version FROM {table} WHERE client_id=@client_id AND invoice_id=@id),0)=@expected AS 'Bill changed; reload';
        ASSERT @number='' OR @fy IS NULL OR NOT EXISTS(SELECT 1 FROM {table} WHERE client_id=@client_id AND supplier_gstin=@supplier AND invoice_number=@number AND financial_year=@fy AND invoice_id!=@id) AS 'Duplicate invoice';
        DELETE FROM {table} WHERE client_id=@client_id AND invoice_id=@id;
        INSERT INTO {table} (client_id,invoice_id,source_doc_id,invoice_date,period,financial_year,supplier_gstin,invoice_number,direction,status,eligibility,taxable_value,cgst,sgst,igst,cess,invoice_total,payload,version,created_at,updated_at)
        SELECT @client_id,@id,JSON_VALUE(@payload,'$.source_doc_id'),CAST(JSON_VALUE(@payload,'$.invoice_date') AS DATE),@period,@fy,@supplier,@number,JSON_VALUE(@payload,'$.direction'),@status,JSON_VALUE(@payload,'$.itc.eligibility'),
        CAST(JSON_VALUE(@payload,'$.totals.taxable_value') AS NUMERIC),CAST(JSON_VALUE(@payload,'$.totals.cgst') AS NUMERIC),CAST(JSON_VALUE(@payload,'$.totals.sgst') AS NUMERIC),CAST(JSON_VALUE(@payload,'$.totals.igst') AS NUMERIC),CAST(JSON_VALUE(@payload,'$.totals.cess') AS NUMERIC),CAST(JSON_VALUE(@payload,'$.totals.invoice_total') AS NUMERIC),PARSE_JSON(@payload),@version,CURRENT_TIMESTAMP(),CURRENT_TIMESTAMP();
        DELETE FROM {self.table('silver', 'gst_invoice_line')} WHERE client_id=@client_id AND invoice_id=@id;
        INSERT INTO {self.table('silver', 'gst_invoice_line')}
        SELECT @client_id,@id,position+1,CAST(JSON_VALUE(@payload,'$.invoice_date') AS DATE),JSON_VALUE(line,'$.description'),JSON_VALUE(line,'$.hsn_sac'),CAST(JSON_VALUE(line,'$.quantity') AS NUMERIC),JSON_VALUE(line,'$.unit'),CAST(JSON_VALUE(line,'$.gst_rate') AS NUMERIC),CAST(JSON_VALUE(line,'$.taxable_value') AS NUMERIC),CAST(JSON_VALUE(line,'$.cgst') AS NUMERIC),CAST(JSON_VALUE(line,'$.sgst') AS NUMERIC),CAST(JSON_VALUE(line,'$.igst') AS NUMERIC),CAST(JSON_VALUE(line,'$.cess') AS NUMERIC)
        FROM UNNEST(JSON_QUERY_ARRAY(@payload,'$.line_items')) line WITH OFFSET position;
        INSERT INTO {self.table('ops', 'gst_bill_audit')} VALUES (@client_id,@id,@actor,@action,PARSE_JSON(@before),PARSE_JSON(@payload),CURRENT_TIMESTAMP());
        INSERT INTO {self.table('ops', 'gst_bill_audit')} VALUES (@client_id,@id,@actor,'auto_review_state',PARSE_JSON(@before_auto_policy),PARSE_JSON(@auto_policy),CURRENT_TIMESTAMP());
        COMMIT TRANSACTION;'''
        try:
            self.query(sql, params)
        except (BadRequest, Conflict) as exc:
            if 'filing period frozen' in str(exc).lower():
                raise HTTPException(409, 'This filing period is frozen. An authorized reopen is required.') from None
            if any(word in str(exc).lower() for word in ('duplicate invoice', 'bill changed', 'concurrent', 'transaction is aborted')):
                raise HTTPException(409, {'code': 'bill_conflict', 'message': 'This bill was saved or changed in another request. Refresh your bills before retrying.'}) from None
            raise

    def matching_rows(self, period):
        rows = self.query(f'SELECT payload FROM {self.table("silver", "gst_bills_gstr2b")} WHERE client_id=@client_id AND period=@period', [param('period', period)])
        return [json.loads(r['payload']) if isinstance(r['payload'], str) else r['payload'] for r in rows]

    def deleted(self, period):
        rows = self.query(f'''SELECT a.before_payload AS payload FROM {self.table('ops', 'gst_bill_audit')} a
            WHERE a.client_id=@client_id AND a.action='delete'
            AND COALESCE(SUBSTR(JSON_VALUE(a.before_payload,'$.invoice_date'),1,7),JSON_VALUE(a.before_payload,'$.selected_period'))=@period
            AND NOT EXISTS(SELECT 1 FROM {self.table('gold', 'gst_invoice')} i WHERE i.client_id=@client_id AND i.invoice_id=a.invoice_id)
            QUALIFY ROW_NUMBER() OVER(PARTITION BY a.invoice_id ORDER BY a.created_at DESC)=1
            ORDER BY a.created_at DESC LIMIT 100''', [param('period', period)])
        return [GstInvoice.model_validate(json.loads(r['payload']) if isinstance(r['payload'],str) else r['payload']) for r in rows]

    def deleted_invoice(self, invoice_id):
        rows = self.query(f'''SELECT before_payload AS payload FROM {self.table('ops', 'gst_bill_audit')}
            WHERE client_id=@client_id AND invoice_id=@id AND action='delete'
            ORDER BY created_at DESC LIMIT 1''', [param('id',invoice_id)])
        if not rows:
            raise HTTPException(404, 'Deleted bill not found.')
        payload = rows[0]['payload']
        return self.auto_policies([GstInvoice.model_validate(json.loads(payload) if isinstance(payload,str) else payload)])[0]

    def job_history(self, period):
        rows = self.query(f'''SELECT payload,updated_at FROM {self.table('ops', 'gst_bill_job')}
            WHERE client_id=@client_id AND JSON_VALUE(payload,'$.period')=@period
            ORDER BY updated_at DESC LIMIT 100''', [param('period',period)])
        return [{**(json.loads(r['payload']) if isinstance(r['payload'],str) else r['payload']), '_updated_at':str(r['updated_at'])} for r in rows]

    def intelligence_job_counts(self, period):
        rows=self.query(f'''SELECT
            COALESCE(SUM(IF(JSON_VALUE(payload,'$.status') IN ('queued','reading'),
                (SELECT COUNT(*) FROM UNNEST(JSON_QUERY_ARRAY(payload,'$.files')) f
                 WHERE JSON_VALUE(f,'$.status') IN ('queued','reading')),0)),0) AS processing,
            COUNTIF(JSON_VALUE(payload,'$.status')='needs_attention') AS failed,
            COALESCE(SUM((SELECT COUNT(*) FROM UNNEST(JSON_QUERY_ARRAY(payload,'$.files')) f
                WHERE JSON_VALUE(f,'$.reason') LIKE '%No duplicate was added%')),0) AS duplicates
            FROM {self.table('ops','gst_bill_job')} WHERE client_id=@client_id AND JSON_VALUE(payload,'$.period')=@period''',[param('period',period)])
        return dict(rows[0]) if rows else {'processing':0,'failed':0,'duplicates':0}

    def delete(self, invoice, actor):
        if invoice.client_id != self.client_id:
            raise HTTPException(404, 'Bill not found.')
        try:
            self.query(f'''BEGIN TRANSACTION;
                UPDATE {self.table('ops', 'gst_bill_lock')} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
                ASSERT @@row_count=1 AS 'Storage guard missing';
                {self.writable_sql()}
                ASSERT (SELECT version FROM {self.table('gold', 'gst_invoice')} WHERE client_id=@client_id AND invoice_id=@id)=@expected AS 'Bill changed';
                INSERT INTO {self.table('ops', 'gst_bill_audit')} VALUES (@client_id,@id,@actor,'delete',PARSE_JSON(@before),NULL,CURRENT_TIMESTAMP());
                DELETE FROM {self.table('silver', 'gst_invoice_line')} WHERE client_id=@client_id AND invoice_id=@id;
                DELETE FROM {self.table('gold', 'gst_invoice')} WHERE client_id=@client_id AND invoice_id=@id;
                COMMIT TRANSACTION;''', [param('id', invoice.invoice_id), param('expected', invoice.version, 'INT64'),
                    param('actor', str(actor)), param('before', invoice.model_dump_json(exclude={'auto_review'})),
                    param('period',invoice.invoice_date.strftime('%Y-%m') if invoice.invoice_date else invoice.selected_period),
                    param('previous_period',invoice.selected_period)])
        except (BadRequest, Conflict) as exc:
            if 'filing period frozen' in str(exc).lower():
                raise HTTPException(409, 'This filing period is frozen. An authorized reopen is required.') from None
            if any(word in str(exc).lower() for word in ('bill changed', 'concurrent', 'aborted')):
                raise HTTPException(409, 'This bill changed. Refresh before deleting.') from None
            raise

    def save_matching(self, period, records, actor, source=None):
        self.assert_writable(period)
        try:
            self.query(f'''DECLARE previous_rows JSON;
            BEGIN TRANSACTION;
            UPDATE {self.table('ops', 'gst_bill_lock')} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
            ASSERT @@row_count=1 AS 'Storage guard missing';
            {self.writable_sql()}
            ASSERT @source='null' OR NOT EXISTS(SELECT 1 FROM {self.table('ops','gst_bill_audit')}
                WHERE client_id=@client_id AND action='gstr2b_source' AND JSON_VALUE(after_payload,'$.sha256')=JSON_VALUE(@source,'$.sha256')) AS 'Statement already imported';
            SET previous_rows=(SELECT TO_JSON(ARRAY_AGG(payload)) FROM {self.table('silver','gst_bills_gstr2b')} WHERE client_id=@client_id AND period=@period);
            DELETE FROM {self.table('silver', 'gst_bills_gstr2b')} WHERE client_id=@client_id AND period=@period;
            INSERT INTO {self.table('silver', 'gst_bills_gstr2b')}
            SELECT @client_id,@period,JSON_VALUE(row,'$.supplier_gstin'),JSON_VALUE(row,'$.invoice_number'),PARSE_JSON(row),CURRENT_TIMESTAMP()
            FROM UNNEST(JSON_QUERY_ARRAY(@payload)) row;
            INSERT INTO {self.table('ops', 'gst_bill_audit')} VALUES (@client_id,NULL,@actor,'import_gstr2b',previous_rows,PARSE_JSON(@payload),CURRENT_TIMESTAMP());
            IF @source!='null' THEN
              INSERT INTO {self.table('ops','gst_bill_audit')} VALUES (@client_id,NULL,@actor,'gstr2b_source',NULL,PARSE_JSON(@source),CURRENT_TIMESTAMP());
            END IF;
            COMMIT TRANSACTION;''', [param('period', period),param('previous_period',period), param('payload', json.dumps(records, default=str)), param('actor', str(actor)),param('source',json.dumps(source))])
        except (BadRequest,Conflict) as exc:
            if any(word in str(exc).lower() for word in ('statement already imported','concurrent','aborted')):
                raise HTTPException(409, 'This statement was already imported or another import changed the period. Refresh before retrying.') from None
            raise

    def statement_history(self,period):
        rows=self.query(f'''SELECT after_payload AS payload,created_at,actor_id FROM {self.table('ops','gst_bill_audit')}
            WHERE client_id=@client_id AND action='gstr2b_source' AND JSON_VALUE(after_payload,'$.period')=@period
            ORDER BY created_at DESC LIMIT 100''',[param('period',period)])
        return [{**(json.loads(r['payload']) if isinstance(r['payload'],str) else r['payload']),
                 'imported_at':str(r['created_at']),'actor_id':r['actor_id']} for r in rows]

    def job(self, job_id, payload=None):
        table = self.table('ops', 'gst_bill_job')
        if payload is not None and self.worker_token:
            fence, params = self.worker_fence()
            self.query(f'''BEGIN TRANSACTION;
                UPDATE {self.table('ops','gst_bill_lock')} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
                ASSERT @@row_count=1 AS 'Storage guard missing';
                {fence}
                IF JSON_VALUE(@payload,'$.status') IN ('completed','needs_attention') THEN
                  INSERT INTO {self.table('ops','gst_bill_audit')}
                  SELECT @client_id,NULL,JSON_VALUE(payload,'$.actor_id'),'job_finished',payload,PARSE_JSON(@payload),CURRENT_TIMESTAMP()
                  FROM {table} WHERE client_id=@client_id AND job_id=@id;
                END IF;
                UPDATE {table} SET payload=PARSE_JSON(@payload),updated_at=CURRENT_TIMESTAMP()
                WHERE client_id=@client_id AND job_id=@id;
                COMMIT TRANSACTION;''', [*params,param('id',job_id),param('payload',job_payload(payload))])
            return payload
        if payload is not None:
            self.query(f'''MERGE {table} T USING (SELECT @client_id client_id,@id job_id) S
                ON T.client_id=S.client_id AND T.job_id=S.job_id
                WHEN MATCHED THEN UPDATE SET payload=PARSE_JSON(@payload),updated_at=CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN INSERT VALUES (@client_id,@id,PARSE_JSON(@payload),CURRENT_TIMESTAMP())''',
                [param('id', job_id), param('payload', json.dumps(payload))])
            return payload
        rows = self.query(f'SELECT payload,updated_at FROM {table} WHERE client_id=@client_id AND job_id=@id', [param('id', job_id)])
        if not rows:
            raise HTTPException(404, 'Upload not found.')
        value = rows[0]['payload']
        return {**(json.loads(value) if isinstance(value, str) else value), '_updated_at':str(rows[0]['updated_at'])}

    def usage(self, doc_id, input_tokens, output_tokens):
        self.query(f'INSERT INTO {self.table("ops", "extraction_log")} VALUES (@client_id,@doc,@model,@input,@output,CURRENT_TIMESTAMP())',
                   [param('doc', doc_id), param('model', get_settings().gemini_model), param('input', input_tokens, 'INT64'), param('output', output_tokens, 'INT64')])

    def upload_object(self, content, doc_id, filename, layer, mime):
        # Stable client UUID prevents business-name collisions and tenant path traversal.
        safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', filename)[:180]
        day = datetime.now(timezone.utc).strftime('%Y/%m/%d')
        key = f'{self.client_id}/{layer}/bills/{day}/{doc_id}/{safe_name}'
        bucket = storage.Client(project=self.project).bucket(get_settings().gcs_bucket_name)
        blob = bucket.blob(key)
        try:
            blob.upload_from_string(content, content_type=mime, if_generation_match=0)
        except PreconditionFailed:
            # A retry may reuse identical evidence, never overwrite different bytes.
            if blob.download_as_bytes() != content:
                raise HTTPException(409, 'Stored evidence differs from this upload. Start a new upload; the original was retained.') from None
        return f'gs://{bucket.name}/{key}'

    def name_original(self, invoice):
        ref = invoice.extraction.raw_ref
        prefix = f'gs://{get_settings().gcs_bucket_name}/{self.client_id}/bronze/bills/'
        if not ref.startswith(prefix):
            raise HTTPException(404, 'Original bill not found.')
        key = ref.split('/', 3)[3]
        target = key.rsplit('/', 1)[0] + '/' + bill_filename(invoice)
        if key != target:
            bucket = storage.Client(project=self.project).bucket(get_settings().gcs_bucket_name)
            source = bucket.blob(key)
            source.reload()
            try:
                bucket.copy_blob(source, bucket, target, if_generation_match=0,
                                 if_source_generation_match=source.generation)
            except PreconditionFailed:
                try:
                    identical = bucket.blob(target).download_as_bytes() == source.download_as_bytes(if_generation_match=source.generation)
                except PreconditionFailed:
                    raise HTTPException(409, 'Original evidence changed while naming this bill. Refresh before retrying.') from None
                if not identical:
                    raise HTTPException(409, 'The canonical filename already holds different evidence. Originals were retained for review.') from None
            invoice.extraction.raw_ref = f'gs://{bucket.name}/{target}'

    def download_object(self, ref, layer='bronze'):
        if layer not in {'bronze','silver'}:
            raise HTTPException(404, 'Original bill not found.')
        prefix = f'gs://{get_settings().gcs_bucket_name}/{self.client_id}/{layer}/bills/'
        if not ref.startswith(prefix):
            raise HTTPException(404, 'Original bill not found.')
        key = ref.split('/', 3)[3]
        return storage.Client(project=self.project).bucket(get_settings().gcs_bucket_name).blob(key).download_as_bytes()
