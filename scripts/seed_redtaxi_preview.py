"""Owner-requested synthetic load into the empty September Red Taxi workspace.

Dry run by default. This exceptional fixture loader does not change normal API
sample-data guards. It refuses nonempty periods and commits all tables atomically.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from google.cloud import bigquery, storage
from google.oauth2.credentials import Credentials
from app.services.gst.redtaxi_mock import generate_redtaxi_mock_data
from app.services.gst.rules import set_off

PROJECT = 'aidirac-503309'
DATASET = PROJECT + '.finance_analytics'
CLIENT = '02f66f3a-0981-4db9-8bd3-1870855c4c09'
PERIOD = '2026-09'
BUCKET = PROJECT + '-bills-voucher-documents'
RUN = 'synthetic_redtaxi_202609_seed42_v1'


def prepare():
    bundle = generate_redtaxi_mock_data(PERIOD, 42)
    stamp = datetime.now(timezone.utc).isoformat()
    tables = {name: [] for name in ['bronze_document', 'silver_invoice_header',
        'silver_invoice_line', 'silver_outward_invoice', 'silver_gstr2b_invoice',
        'gold_itc_ledger', 'gold_gstr2b_match', 'gold_filing_summary']}
    evidence = {}
    for doc in bundle['documents']:
        doc_id = doc['doc_id']
        header = doc['silver']
        body = json.dumps({'notice': 'SYNTHETIC SAMPLE - NOT VALID FOR GST FILING',
            'scenario': doc['scenario'], 'invoice': header,
            'description': doc['search_text']}, indent=2).encode()
        path = f'demos/redtaxi/{PERIOD}/{RUN}/{doc_id}.json'
        evidence[path] = body
        tables['bronze_document'].append({'doc_id': doc_id, 'client_id': CLIENT,
            'period': PERIOD, 'gcs_uri': f'gs://{BUCKET}/{path}',
            'content_hash': hashlib.sha256(body).hexdigest(), 'mime_type': 'application/json',
            'byte_size': len(body), 'original_filename': header['invoice_no']+'-SAMPLE.json',
            'source_channel': 'SYNTHETIC_DEMO', 'uploaded_by': 'owner-requested-synthetic-seed',
            'uploaded_at': stamp, 'ingest_date': stamp[:10]})
        tables['silver_invoice_header'].append({**header, 'doc_id': doc_id,
            'client_id': CLIENT, 'period': PERIOD, 'extracted_at': stamp,
            'extraction_engine': 'SYNTHETIC_FIXTURE_NOT_OCR',
            'reviewed_by': 'SYNTHETIC_REVIEW_EXAMPLE' if header['validation_status']=='validated' else None,
            'reviewed_at': stamp if header['validation_status']=='validated' else None})
    tables['silver_invoice_line'] = [{**r, 'client_id': CLIENT, 'extracted_at': stamp} for r in bundle['lines']]
    tables['silver_outward_invoice'] = [{**r, 'client_id': CLIENT, 'created_at': stamp,
        'place_of_supply': '33', 'eco_9_5': False} for r in bundle['outward']]
    tables['silver_gstr2b_invoice'] = [{**r, 'client_id': CLIENT, 'import_id': RUN,
        'imported_at': stamp} for r in bundle['gstr2b']]
    for name in ['gold_itc_ledger', 'gold_gstr2b_match', 'gold_filing_summary']:
        tables[name] = [{**r, 'client_id': CLIENT, 'run_id': RUN, 'computed_at': stamp}
                       for r in bundle['gold_tables'][name]]
    summary = tables['gold_filing_summary'][0]
    summary.update(input_hash=RUN,
        as_booked=set_off(summary['output_by_head'], summary['input_by_head'], summary['eco_by_head'])['cash_required'],
        fully_compliant=summary['cash_required'])
    # Leave unsupported comparison variants NULL rather than inventing figures.
    return bundle, tables, evidence


def expression(field):
    value = f"JSON_VALUE(row, '$.{field.name}')"
    if field.mode == 'REPEATED':
        return f"JSON_VALUE_ARRAY(row, '$.{field.name}')"
    if field.field_type == 'JSON':
        return f"JSON_QUERY(PARSE_JSON(row), '$.{field.name}')"
    kind = {'INTEGER':'INT64', 'FLOAT':'FLOAT64', 'BOOLEAN':'BOOL'}.get(field.field_type, field.field_type)
    return f'CAST({value} AS {kind})'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    bundle, tables, evidence = prepare()
    token = subprocess.check_output(['gcloud.cmd', 'auth', 'print-access-token'], text=True).strip()
    credentials = Credentials(token)
    bq = bigquery.Client(project=PROJECT, credentials=credentials)
    params = [bigquery.ScalarQueryParameter('client', 'STRING', CLIENT),
              bigquery.ScalarQueryParameter('period', 'STRING', PERIOD)]
    config = bigquery.QueryJobConfig(query_parameters=params, maximum_bytes_billed=100_000_000)
    def query(sql):
        return list(bq.query(sql, job_config=config).result())
    profile = query(f"SELECT legal_name,gstin FROM `{DATASET}.gst_client_profile` WHERE client_id=@client AND is_current=TRUE")
    assert len(profile)==1 and profile[0].legal_name=='Red Taxi' and not profile[0].gstin, 'Unexpected client profile'
    scope = 'client_id=@client AND period=@period'
    counts = {table: query(f'SELECT COUNT(*) n FROM `{DATASET}.{table}` WHERE {scope}')[0].n for table in tables}
    print(json.dumps({'client_id': CLIENT, 'period': PERIOD, 'existing': counts,
        'planned': {k:len(v) for k,v in tables.items()}, 'dashboard_totals': bundle['dashboard']['totals']}, default=str), flush=True)
    assert not any(counts.values()), 'Refusing to overwrite a nonempty workspace; inspect the previous load first.'
    states = query(f"SELECT state FROM `{DATASET}.gst_filing_status` WHERE {scope} AND is_current=TRUE")
    assert not states or all(r.state=='draft' for r in states), 'Filing period is frozen'
    statements = ['BEGIN TRANSACTION;']
    statements.append(f"ASSERT (SELECT COUNT(*) FROM `{DATASET}.gst_client_profile` WHERE client_id=@client AND is_current=TRUE AND legal_name='Red Taxi' AND COALESCE(gstin,'')='')=1 AS 'Profile changed';")
    statements.append(f"ASSERT (SELECT COUNT(*) FROM `{DATASET}.gst_filing_status` WHERE {scope} AND is_current=TRUE AND state!='draft')=0 AS 'Period frozen';")
    for table, rows in tables.items():
        schema = bq.get_table(f'{DATASET}.{table}').schema
        names = {f.name for f in schema}
        rows = [{k:v for k,v in r.items() if k in names} for r in rows]
        tables[table] = rows
        fields = [f for f in schema if any(f.name in r for r in rows)]
        param_name = 'rows_'+table
        params.append(bigquery.ArrayQueryParameter(param_name, 'STRING', [json.dumps(r, default=str) for r in rows]))
        statements.append(f"ASSERT (SELECT COUNT(*) FROM `{DATASET}.{table}` WHERE {scope})=0 AS 'Workspace no longer empty';")
        columns = ','.join('`'+f.name+'`' for f in fields)
        values = ','.join(expression(f) for f in fields)
        statements.append(f'INSERT INTO `{DATASET}.{table}` ({columns}) SELECT {values} FROM UNNEST(@{param_name}) row;')
    statements.append('COMMIT TRANSACTION;')
    output = Path('artifacts/redtaxi-bigquery-seed')
    output.mkdir(parents=True, exist_ok=True)
    (output/'rows.json').write_text(json.dumps(tables, indent=2, default=str), encoding='utf-8')
    if not args.apply:
        print('Dry run complete. No cloud records changed.', flush=True)
        return
    bucket = storage.Client(project=PROJECT, credentials=credentials).bucket(BUCKET)
    for path, body in evidence.items():
        blob = bucket.blob(path)
        if blob.exists():
            assert blob.download_as_bytes()==body, 'Existing sample evidence differs'
        else:
            blob.upload_from_string(body, content_type='application/json', if_generation_match=0)
    job = bq.query('\n'.join(statements), job_config=bigquery.QueryJobConfig(
        query_parameters=params, maximum_bytes_billed=100_000_000,
        labels={'purpose':'redtaxi-synthetic-preview'}))
    job.result()
    for table, rows in tables.items():
        assert query(f'SELECT COUNT(*) n FROM `{DATASET}.{table}` WHERE {scope}')[0].n == len(rows)
    manifest = {'sample': True, 'client_id': CLIENT, 'period': PERIOD, 'run_id': RUN,
        'bigquery_job': job.job_id, 'counts': {k:len(v) for k,v in tables.items()},
        'dashboard_totals': bundle['dashboard']['totals'], 'evidence_objects': list(evidence)}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('COMMITTED AND VERIFIED '+json.dumps(manifest), flush=True)


if __name__=='__main__':
    main()
