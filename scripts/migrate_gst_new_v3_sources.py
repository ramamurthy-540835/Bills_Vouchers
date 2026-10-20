"""Add the source reconciliation audit table to V3 only."""
import json
import subprocess
from pathlib import Path
from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from prepare_gst_new_v3 import PROJECT, REGION, PREFIX, ART, cloud


def main():
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GST_NEW_V3':
        raise RuntimeError('Wrong branch')
    dataset=f'{PROJECT}.{PREFIX}ops'
    client=bigquery.Client(project=PROJECT,credentials=Credentials(cloud('auth','print-access-token')))
    if client.get_dataset(dataset).location.lower()!=REGION:
        raise RuntimeError('Unexpected V3 dataset location')
    sql=Path('migrations/v3_source_reconciliation.sql').read_text().replace('PROJECT',PROJECT).replace('V3_OPS',PREFIX+'ops')
    if f'`{dataset}.external_transaction_links`' not in sql:
        raise RuntimeError('Unexpected migration target')
    job=client.query(sql,location=REGION)
    job.result()
    table=client.get_table(dataset+'.external_transaction_links')
    actual=[(field.name,field.field_type) for field in table.schema]
    expected=[('client_id','STRING'),('batch_id','STRING'),('period','STRING'),('run_id','STRING'),
              ('actor_id','STRING'),('payload','JSON'),('created_at','TIMESTAMP')]
    if actual!=expected:
        raise RuntimeError('Existing audit schema differs; inspect instead of altering it')
    report={'table':table.full_table_id,'job_id':job.job_id,'operation':'create if absent',
            'existing_financial_tables_modified':False}
    (ART/'source-reconciliation-migration.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=='__main__':
    main()
