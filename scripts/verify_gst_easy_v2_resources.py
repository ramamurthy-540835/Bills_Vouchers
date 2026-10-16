"""Read-only checks for V2 isolation, profile counts and preserved old services."""
import json

from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from deploy_gst_easy_v2 import api_environment, snapshot_unchanged
from prepare_gst_easy_v2 import ART, PROJECT, REGION, cloud, account


def main():
    deployed = json.loads((ART / 'deployment.json').read_text())
    expected = api_environment(deployed['source_commit'])
    expected.update(GST_BILLS_WORKER_URL=deployed['backend_url'],
                    GST_BILLS_WORKER_AUDIENCE=deployed['backend_url'],
                    ALLOWED_ORIGINS=deployed['frontend_url'], AUTH_PUBLIC_URL=deployed['frontend_url'])
    revisions = {}
    for kind in ['api', 'web']:
        service = json.loads(cloud('run', 'services', 'describe', 'gst-easy-v2-' + kind,
                            '--project', PROJECT, '--region', REGION, '--format=json'))
        spec = service['spec']['template']['spec']
        assert spec['serviceAccountName'] == account(kind)
        env = {item['name']: item.get('value', '') for item in spec['containers'][0]['env']}
        target = expected if kind == 'api' else dict(BACKEND_URL=deployed['backend_url'],
            BACKEND_ID_TOKEN_AUDIENCE=deployed['backend_url'], RELEASE_REVISION=deployed['source_commit'])
        assert all(env.get(key) == value for key, value in target.items()), kind
        assert not any(key.startswith('~') for key in env), kind
        revisions[kind] = service['status']['latestReadyRevisionName']
    client = bigquery.Client(project=PROJECT, credentials=Credentials(cloud('auth', 'print-access-token')))
    tables = {'gst_easy_v2_gold.gst_invoice': 0, 'gst_easy_v2_silver.gst_bills_gstr2b': 0,
              'gst_easy_v2_finance_analytics.users': 1, 'gst_easy_v2_finance_analytics.clients': 3}
    counts = {table: list(client.query(f'SELECT COUNT(*) n FROM `{PROJECT}.{table}`').result())[0].n
              for table in tables}
    assert counts == tables, counts
    rows = list(client.query(f'''SELECT COUNT(*) n FROM `{PROJECT}.gst_easy_v2_finance_analytics.clients`
                                WHERE is_test=TRUE''').result())
    assert rows[0].n == 3
    report = dict(revisions=revisions, row_counts=counts,
                  existing_services_unchanged=snapshot_unchanged(), runtime_configuration_verified=True)
    (ART / 'resource-verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
