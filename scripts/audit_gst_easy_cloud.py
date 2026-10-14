"""Read cloud configuration and schema metadata; never read customer rows/secrets."""
import json
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery
from google.oauth2.credentials import Credentials

from deploy_v3 import gcloud


def main():
    project = 'aidirac-503309'
    client = bigquery.Client(project=project, credentials=Credentials(gcloud('auth', 'print-access-token').strip()))
    report = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'datasets': {}, 'services': {}}
    for name in ('finance_analytics', 'gold', 'silver', 'ops'):
        dataset = client.get_dataset(project + '.' + name)
        tables = []
        for item in client.list_tables(dataset):
            table = client.get_table(item.reference)
            tables.append({'name': table.table_id, 'fields': [{'name': field.name, 'type': field.field_type, 'mode': field.mode} for field in table.schema],
                           'partition_field': table.time_partitioning.field if table.time_partitioning else None,
                           'clustering': table.clustering_fields, 'row_count_metadata': table.num_rows})
        report['datasets'][name] = {'location': dataset.location, 'tables': tables}
    for name in ('bills-voucher', 'bills-voucher-web'):
        data = json.loads(gcloud('run', 'services', 'describe', name, '--project', project, '--region', 'asia-south1', '--format=json'))
        template = data.get('spec', {}).get('template', {}).get('spec', {})
        report['services'][name] = {'traffic': data.get('status', {}).get('traffic', []),
            'template_service_account': template.get('serviceAccountName'),
            'env_names_only': sorted({entry['name'] for container in template.get('containers', []) for entry in container.get('env', [])}),
            'invocation_policy': json.loads(gcloud('run', 'services', 'get-iam-policy', name, '--project', project, '--region', 'asia-south1', '--format=json'))}
    policy = json.loads(gcloud('projects', 'get-iam-policy', project, '--format=json'))
    accounts = {data['template_service_account'] for data in report['services'].values()}
    report['runtime_project_roles'] = {account: [binding['role'] for binding in policy.get('bindings', [])
        if 'serviceAccount:' + account in binding.get('members', [])] for account in accounts if account}
    report['queue'] = json.loads(gcloud('tasks', 'queues', 'describe', 'bills-v3', '--project', project, '--location', 'asia-south1', '--format=json'))
    bucket = json.loads(gcloud('storage', 'buckets', 'describe', 'gs://' + project + '-bills-voucher-documents', '--format=json'))
    report['bucket'] = {key: bucket.get(key) for key in ('location', 'public_access_prevention', 'uniform_bucket_level_access', 'soft_delete_policy', 'retention_policy', 'versioning_enabled')}
    output = Path('docs/GST_EASY_CLOUD_BASELINE.json')
    output.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({'output': str(output), 'datasets': {name: {'location': value['location'], 'table_count': len(value['tables'])} for name, value in report['datasets'].items()}, 'runtime_project_roles': report['runtime_project_roles']}))


if __name__ == '__main__':
    main()
