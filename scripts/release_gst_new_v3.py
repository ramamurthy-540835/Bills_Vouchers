"""Update only the two V3 services created by this release, with revision guards."""
import argparse
import json
import subprocess
from uuid import UUID

from google.cloud import bigquery
from google.oauth2.credentials import Credentials

from audit_gst_new_v3 import assert_preserved
from prepare_gst_new_v3 import ART, PROJECT, REGION, PREFIX, account, cloud


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', required=True)
    parser.add_argument('--expected-api-revision', required=True)
    parser.add_argument('--expected-web-revision', required=True)
    parser.add_argument('--synthetic-client', required=True)
    args = parser.parse_args()
    client_id = str(UUID(args.synthetic_client))
    if subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip() != 'GST_NEW_V3':
        raise RuntimeError('Wrong branch')
    if subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip():
        raise RuntimeError('Commit reviewed source first')
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/GST_NEW_V3'], text=True).split()
    if not remote or remote[0] != source:
        raise RuntimeError('Remote source differs')
    build = json.loads(cloud('builds', 'describe', args.build, '--project', PROJECT, '--format=json'))
    if build['status'] != 'SUCCESS' or build.get('substitutions', {}).get('_REVISION') != source:
        raise RuntimeError('Build does not match reviewed source')
    before = {}
    images = {}
    for kind, expected in [('api', args.expected_api_revision), ('web', args.expected_web_revision)]:
        service = json.loads(cloud('run', 'services', 'describe', 'gst-easy-v3-' + kind,
                                  '--project', PROJECT, '--region', REGION, '--format=json'))
        if service['status']['latestReadyRevisionName'] != expected:
            raise RuntimeError('V3 revision changed; inspect before updating')
        if service['spec']['template']['spec']['serviceAccountName'] != account(kind):
            raise RuntimeError('Unexpected V3 identity')
        before[kind] = service
        repository = f'{REGION}-docker.pkg.dev/{PROJECT}/gst-easy-v3/{kind}'
        matches = [i for i in build['results']['images'] if i['name'] == repository + ':' + source]
        if len(matches) != 1:
            raise RuntimeError('Unexpected image')
        images[kind] = repository + '@' + matches[0]['digest']
    api_env = {e['name']: e.get('value') for e in before['api']['spec']['template']['spec']['containers'][0]['env']}
    web_env = {e['name']: e.get('value') for e in before['web']['spec']['template']['spec']['containers'][0]['env']}
    if (api_env.get('BIGQUERY_DATASET') != PREFIX + 'finance_analytics'
            or api_env.get('GST_DATASET_PREFIX') != PREFIX
            or api_env.get('GCS_BUCKET_NAME') != PROJECT + '-gst-easy-v3-documents'
            or web_env.get('BACKEND_URL') != before['api']['status']['url']):
        raise RuntimeError('V3 isolation or pairing differs')
    bq = bigquery.Client(project=PROJECT, credentials=Credentials(cloud('auth', 'print-access-token')))
    rows = list(bq.query(f"""SELECT c.id FROM `{PROJECT}.{PREFIX}finance_analytics.clients` c
        JOIN `{PROJECT}.{PREFIX}finance_analytics.gst_client_profile` p ON p.client_id=c.id
        WHERE c.id=@id AND c.is_test=TRUE AND p.source='SYNTHETIC_TEST_ONLY'
        AND c.name='GST Easy V3 Synthetic Acceptance Workspace'""",
        location=REGION, job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter('id', 'STRING', client_id)],
            maximum_bytes_billed=100000000)).result())
    if len(rows) != 1:
        raise RuntimeError('Global inference is authorized only for the synthetic acceptance business')
    assert_preserved()
    common = ['--project', PROJECT, '--region', REGION, '--quiet']
    cloud('run', 'services', 'update', 'gst-easy-v3-api', '--image', images['api'],
          '--update-env-vars', f'RELEASE_REVISION={source},GEMINI_ENABLED=true,GEMINI_MODEL=gemini-3.8-flash,GEMINI_LOCATION=global,GEMINI_ALLOWED_CLIENT_IDS={client_id}', *common)
    cloud('run', 'services', 'update', 'gst-easy-v3-web', '--image', images['web'],
          '--update-env-vars', 'RELEASE_REVISION=' + source, *common)
    after = {}
    for kind in ['api', 'web']:
        service = json.loads(cloud('run', 'services', 'describe', 'gst-easy-v3-' + kind,
                                  '--project', PROJECT, '--region', REGION, '--format=json'))
        after[kind] = {'url': service['status']['url'],
                       'revision': service['status']['latestReadyRevisionName'],
                       'previous_revision': before[kind]['status']['latestReadyRevisionName'],
                       'image': images[kind]}
    assert_preserved()
    report = {'source_commit': source, 'build': args.build, 'services': after,
              'global_inference': 'authorized synthetic acceptance business only',
              'existing_services_unchanged': True}
    (ART / 'release-update.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
