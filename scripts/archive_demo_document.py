"""Inspect or reversibly archive one explicitly named, unposted test document.

Never deletes a bucket prefix. Original bytes and scoped source rows are retained
under archive/unrelated-demo before the document leaves the active workspace.
"""
import argparse
import json
import subprocess
from pathlib import Path

from google.cloud import bigquery, storage
from google.oauth2.credentials import Credentials

PROJECT='aidirac-503309'
DATASET=PROJECT+'.finance_analytics'
BUCKET=PROJECT+'-bills-voucher-documents'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--doc-id',required=True)
    parser.add_argument('--period',required=True)
    parser.add_argument('--expected-filename',required=True)
    parser.add_argument('--client-id')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    credentials=Credentials(subprocess.check_output(['gcloud.cmd','auth','print-access-token'],text=True).strip())
    bq=bigquery.Client(project=PROJECT,credentials=credentials)
    gcs=storage.Client(project=PROJECT,credentials=credentials)
    params=[bigquery.ScalarQueryParameter('doc','STRING',args.doc_id),bigquery.ScalarQueryParameter('period','STRING',args.period)]
    def query(sql):
        return list(bq.query(sql,job_config=bigquery.QueryJobConfig(query_parameters=params)).result())
    rows=query(f'SELECT * FROM `{DATASET}.bronze_document` WHERE doc_id=@doc AND period=@period')
    if len(rows)!=1:
        raise RuntimeError('Expected exactly one active source document. No changes made.')
    source=dict(rows[0].items())
    if source['original_filename']!=args.expected_filename:
        raise RuntimeError('Filename does not match the explicitly selected document.')
    client=source['client_id']
    if args.apply and args.client_id!=client:
        raise RuntimeError('Apply requires the inspected, exact client ID.')
    params.append(bigquery.ScalarQueryParameter('client','STRING',client))
    if query(f"SELECT doc_id FROM `{DATASET}.gold_itc_ledger` WHERE client_id=@client AND period=@period AND doc_id=@doc"):
        raise RuntimeError('Document has Gold history; use a reviewed reversal workflow instead.')
    states=query(f"SELECT state FROM `{DATASET}.gst_filing_status` WHERE client_id=@client AND period=@period AND is_current=TRUE")
    if any(r.state!='draft' for r in states):
        raise RuntimeError('The period is no longer draft; archive refused.')
    tables={}
    for table in ('bronze_document','silver_invoice_header','silver_invoice_line'):
        tables[table]=[dict(r.items()) for r in query(f'SELECT * FROM `{DATASET}.{table}` WHERE client_id=@client AND period=@period AND doc_id=@doc')]
    prefix=f'archive/unrelated-demo/{client}/{args.doc_id}/'
    if not source['gcs_uri'].startswith('gs://'+BUCKET+'/bronze/'):
        raise RuntimeError('Expected a Bronze object in the configured customer bucket.')
    path=source['gcs_uri'].removeprefix('gs://'+BUCKET+'/')
    bucket=gcs.bucket(BUCKET)
    blobs=[]
    for name in (path,f'silver/{client}/{args.doc_id}.json'):
        blob=bucket.get_blob(name)
        if blob:
            blobs.append(blob)
    if not blobs or blobs[0].name!=path:
        raise RuntimeError('Original source is missing; no changes made.')
    plan={'client_id':client,'doc_id':args.doc_id,'period':args.period,'filename':args.expected_filename,
          'archive_prefix':'gs://'+BUCKET+'/'+prefix,'objects':[b.name for b in blobs],
          'row_counts':{t:len(r) for t,r in tables.items()},'rows':tables}
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/document-archive-plan.json').write_text(json.dumps(plan,default=str,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in plan.items() if k!='rows'},indent=2),flush=True)
    if not args.apply:
        print('Inspection only. No cloud records changed.')
        return
    for blob in blobs:
        destination=prefix+('source'+Path(blob.name).suffix if blob.name==path else 'silver.json')
        copied=bucket.copy_blob(blob,bucket,destination,if_generation_match=0,if_source_generation_match=blob.generation)
        if copied.crc32c!=blob.crc32c or copied.size!=blob.size:
            raise RuntimeError('Archive copy failed integrity verification. Active records retained.')
    bucket.blob(prefix+'manifest.json').upload_from_string(json.dumps(plan,default=str,indent=2),content_type='application/json',if_generation_match=0)
    params.append(bigquery.ScalarQueryParameter('hash','STRING',source['content_hash']))
    params.append(bigquery.ScalarQueryParameter('filename','STRING',args.expected_filename))
    # Recheck guards inside the deletion transaction; only the named unposted source is removed.
    statements=[f"ASSERT (SELECT COUNT(*) FROM `{DATASET}.bronze_document` WHERE client_id=@client AND period=@period AND doc_id=@doc AND content_hash=@hash AND original_filename=@filename)=1 AS 'Source changed';",
        f"ASSERT (SELECT COUNT(*) FROM `{DATASET}.gold_itc_ledger` WHERE client_id=@client AND period=@period AND doc_id=@doc)=0 AS 'Gold records appeared';",
        f"ASSERT (SELECT COUNT(*) FROM `{DATASET}.gst_filing_status` WHERE client_id=@client AND period=@period AND is_current=TRUE AND state!='draft')=0 AS 'Period frozen';"]
    statements.extend(f'DELETE FROM `{DATASET}.{table}` WHERE client_id=@client AND period=@period AND doc_id=@doc;' for table in tables)
    query('BEGIN TRANSACTION;\n'+'\n'.join(statements)+'\nCOMMIT TRANSACTION;')
    for blob in blobs:
        blob.delete(if_generation_match=blob.generation)
    bucket.blob(prefix+'completed.json').upload_from_string(json.dumps({'archived':True,'doc_id':args.doc_id,'active_rows_removed':True}),content_type='application/json',if_generation_match=0)
    print('Archived verified source bytes and row snapshots; removed only this document from active Bronze/Silver.')


if __name__=='__main__':
    main()
