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
    parser.add_argument('--enable-naturelabs-demos', action='store_true')
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
    allowed_ids=[client_id]
    demo_enabled=args.enable_naturelabs_demos or api_env.get('DEMO_OPERATOR_IDENTITY_ENABLED')=='true'
    if demo_enabled:
        from pathlib import Path
        manual=json.loads(Path('demo bills/TEST_MANIFEST.json').read_text())
        preloaded=json.loads(Path('demo bills/naturelabs1/TEST_MANIFEST.json').read_text())
        expected={(name,email) for email,names in [
            ('naturelabs@demo.com',[b['legal_name'] for b in manual['businesses']]),
            ('naturelabs1@demo.com',[preloaded['business']['legal_name']])]
            for name in names}
        demos=list(bq.query(f"""SELECT DISTINCT c.id,c.name,u.email
          FROM `{PROJECT}.{PREFIX}finance_analytics.clients` c
          JOIN `{PROJECT}.{PREFIX}finance_analytics.gst_client_profile` p ON p.client_id=c.id AND p.is_current=TRUE
          JOIN `{PROJECT}.{PREFIX}finance_analytics.client_memberships` m ON m.client_id=c.id AND m.is_active=TRUE AND m.access_role='owner'
          JOIN `{PROJECT}.{PREFIX}finance_analytics.users` u ON u.id=m.user_id
          WHERE c.is_test=TRUE AND p.source='SYNTHETIC_TEST_ONLY' AND p.gstin_verified=FALSE
          AND u.role='client' AND u.demo_operator_activated=TRUE AND u.identity_provenance='SYNTHETIC_TEST_ONLY'
          AND u.email IN ('naturelabs@demo.com','naturelabs1@demo.com')""",
          location=REGION,job_config=bigquery.QueryJobConfig(maximum_bytes_billed=100000000)).result())
        if len(demos)!=4 or {(row['name'],row['email']) for row in demos}!=expected:
            raise RuntimeError('Demo business provenance/membership differs; refuse activation')
        allowed_ids.extend(str(row['id']) for row in demos)
    assert_preserved()
    common = ['--project', PROJECT, '--region', REGION, '--quiet']
    cloud('run', 'services', 'update', 'gst-easy-v3-api', '--image', images['api'],
          '--update-env-vars', f"^|^RELEASE_REVISION={source}|GEMINI_ENABLED=true|GEMINI_MODEL=gemini-3.8-flash|GEMINI_LOCATION=global|GEMINI_ALLOWED_CLIENT_IDS={','.join(allowed_ids)}|DEMO_OPERATOR_IDENTITY_ENABLED={str(demo_enabled).lower()}", *common)
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
              'global_inference': 'explicitly validated synthetic business allowlist only',
              'naturelabs_demo_activation': demo_enabled,
              'existing_services_unchanged': True}
    (ART / 'release-update.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
