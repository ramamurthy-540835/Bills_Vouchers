"""Hash other V2 tenants' persisted records without exposing their contents."""
import argparse
import json
from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from prepare_gst_easy_v2 import ART, PROJECT, cloud


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['before','after'],required=True);args=parser.parse_args()
    cid=json.loads((ART/'naturelabs1-provisioning.json').read_text())['businesses'][0]['client_id']
    client=bigquery.Client(project=PROJECT,credentials=Credentials(cloud('auth','print-access-token')))
    tables=[('gst_easy_v2_gold','gst_invoice','client_id'),('gst_easy_v2_silver','gst_bills_gstr2b','client_id'),
            ('gst_easy_v2_finance_analytics','gst_client_profile','client_id'),
            ('gst_easy_v2_finance_analytics','client_memberships','client_id'),('gst_easy_v2_finance_analytics','clients','id')]
    result={}
    for dataset,table,field in tables:
        rows=list(client.query(f'SELECT COUNT(*) AS count, BIT_XOR(FARM_FINGERPRINT(TO_JSON_STRING(t))) AS fingerprint FROM `{PROJECT}.{dataset}.{table}` t WHERE {field} != @cid',
                               job_config=bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('cid','STRING',cid)])).result())
        result[dataset+'.'+table]=dict(rows[0])
    path=ART/f'naturelabs1-other-tenants-{args.phase}.json'
    if args.phase=='before' and path.exists():raise RuntimeError('Preservation baseline already exists; refusing overwrite')
    path.write_text(json.dumps(result,indent=2))
    if args.phase=='after':assert result==json.loads((ART/'naturelabs1-other-tenants-before.json').read_text()),'Other tenant records changed; investigate concurrent activity'
    target=list(client.query(f'SELECT invoice_id FROM `{PROJECT}.gst_easy_v2_gold.gst_invoice` WHERE client_id != @cid LIMIT 1',
                            job_config=bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('cid','STRING',cid)])).result())
    if target:(ART/'naturelabs1-isolation-target.json').write_text(json.dumps({'invoice_id':target[0]['invoice_id']}))
    print('Other-tenant preservation '+args.phase+' snapshot verified.')


if __name__=='__main__':main()
