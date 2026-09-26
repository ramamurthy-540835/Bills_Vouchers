"""Read-only inspection of the owner-requested preview seed target."""
import json
import subprocess
from google.cloud import bigquery
from google.oauth2.credentials import Credentials

token = subprocess.check_output(['gcloud.cmd', 'auth', 'print-access-token'], text=True).strip()
client = bigquery.Client(project='aidirac-503309', credentials=Credentials(token))
sql = """SELECT client_id, legal_name, gstin, is_current FROM
`aidirac-503309.finance_analytics.gst_client_profile`
WHERE LOWER(legal_name) LIKE '%red%taxi%' AND is_current=TRUE"""
profiles = [dict(r.items()) for r in client.query(sql).result()]
print(json.dumps(profiles, default=str))
for profile in profiles:
    params = [bigquery.ScalarQueryParameter('client', 'STRING', profile['client_id'])]
    for table in ['bronze_document', 'silver_invoice_header', 'silver_invoice_line',
                  'silver_outward_invoice', 'silver_gstr2b_invoice', 'gold_filing_summary',
                  'gold_itc_ledger', 'gold_gstr2b_match', 'gst_filing_status']:
        rows = client.query(f'SELECT period,COUNT(*) AS n FROM `aidirac-503309.finance_analytics.{table}` WHERE client_id=@client GROUP BY period', job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
        print(table, json.dumps([dict(r.items()) for r in rows], default=str), flush=True)
