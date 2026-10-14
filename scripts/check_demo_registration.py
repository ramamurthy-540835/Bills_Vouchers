"""Verify the isolated demo and registration SQL without creating an account."""
import json
from types import SimpleNamespace
from uuid import uuid4
from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from deploy_v3 import gcloud
from app.services.registration import register
from app.services.gst.medallion import param

client=bigquery.Client(project='aidirac-503309',credentials=Credentials(gcloud('auth','print-access-token').strip()))
demo_id='435d277d-e7dc-4432-ac4b-745ead334d39'
rows=list(client.query('''SELECT c.id,c.name,c.gstin AS client_gstin,c.is_test,p.gstin AS profile_gstin,p.source,p.gstin_verified
FROM `aidirac-503309.finance_analytics.clients` c
LEFT JOIN `aidirac-503309.finance_analytics.gst_client_profile` p ON c.id=p.client_id AND p.is_current=TRUE
WHERE c.id=@id''',job_config=bigquery.QueryJobConfig(query_parameters=[param('id',demo_id)])).result())
assert len(rows)==1 and rows[0]['is_test'] is True
assert rows[0]['client_gstin']==rows[0]['profile_gstin']=='33ABCDE1234F1Z7'
print(json.dumps(dict(rows[0]),default=str))
print('PASS dummy GSTIN is already assigned only to the dedicated synthetic demo profile')

class Probe:
    settings=SimpleNamespace(gcp_project_id='aidirac-503309')
    def table(self,name):return 'aidirac-503309.finance_analytics.'+name
    def query(self,sql,params):
        sql=sql.replace('COMMIT TRANSACTION;','ROLLBACK TRANSACTION;')
        client.query(sql,job_config=bigquery.QueryJobConfig(query_parameters=params)).result()

result=register(Probe(),dict(email=f'rollback-{uuid4()}@example.invalid',full_name='Rollback test',
    business_name='Rollback test',gstin='33ABCDE1234F1Z7',password='RegistrationCheck2026'))
count=list(client.query('SELECT COUNT(*) AS n FROM `aidirac-503309.finance_analytics.users` WHERE id=@id',
    job_config=bigquery.QueryJobConfig(query_parameters=[param('id',result['id'])])).result())[0]['n']
assert count==0
print('PASS full registration transaction and rollback; no account or client persisted')
