"""Release a pushed V3 commit to candidate tags; preserve all live traffic."""
import io
import json
import subprocess
import zipfile
from pathlib import Path

from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from prepare_gst_new_v3 import cloud, PROJECT, REGION, account

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts/auto-review-v3'
GIT = ['git', '-c', 'safe.directory=' + ROOT.as_posix()]
TAG = 'auto-review'
TARGETS = {'gst-easy-v3-api', 'gst-easy-v3-web'}


def git(*args):
    return subprocess.check_output([*GIT, *args], cwd=ROOT, text=True).strip()


def services():
    return {s['metadata']['name']: s for s in json.loads(cloud(
        'run', 'services', 'list', '--project', PROJECT, '--format=json'))}


def traffic(service, exclude_tag=None):
    return sorted((t.get('tag', ''), t['revisionName'], t.get('percent', 0))
                  for t in service['status']['traffic'] if not exclude_tag or t.get('tag') != exclude_tag)


def baseline():
    return {s['metadata']['name']: s for s in json.loads(
        (ART / 'services-before.json').read_text(encoding='utf-16'))}


def verify_preserved():
    current = services()
    for name, previous in baseline().items():
        if name in TARGETS:
            assert traffic(previous) == traffic(current[name], TAG), name + ' live traffic changed'
        else:
            assert previous['spec'] == current[name]['spec'] and previous['status'] == current[name]['status'], name
    (ART / 'preservation.json').write_text(json.dumps({'verified': True, 'services': sorted(current)}, indent=2))
    print('Existing traffic and non-V3 service configurations preserved.', flush=True)


def build():
    assert git('branch', '--show-current') == 'GST_NEW_V3'
    source = git('rev-parse', 'HEAD')
    assert git('ls-remote', 'origin', 'refs/heads/GST_NEW_V3').split()[0] == source
    assert not git('diff', '--name-only') and not git('diff', '--cached', '--name-only'), 'Tracked changes must be committed.'
    destination = ART / 'build-source'
    assert not destination.exists(), 'Inspect an existing snapshot; do not overwrite it.'
    archive = subprocess.check_output([*GIT, 'archive', '--format=zip', source], cwd=ROOT)
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        for name in zipped.namelist():
            if name.endswith('/') or Path(name).name.startswith('.env'):
                continue
            if not (name.startswith(('app/', 'frontend/')) or name in {
                'Dockerfile', 'requirements.txt', 'pyproject.toml', 'docs/README-REDTAXI-AUDITORS.md',
                '.gcloudignore', '.dockerignore', 'cloudbuild-gst-easy-v3.yaml'}):
                continue
            target = destination / name
            assert target.resolve().is_relative_to(destination.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zipped.read(name))
    result = json.loads(cloud('builds', 'submit', str(destination), '--project', PROJECT,
        '--config', str(destination / 'cloudbuild-gst-easy-v3.yaml'), '--substitutions=_REVISION=' + source,
        '--gcs-source-staging-dir=gs://aidirac-503309-gst-easy-v3-builds/auto-review', '--async', '--format=json', '--quiet'))
    (ART / 'build.json').write_text(json.dumps({'commit': source, 'id': result['id']}, indent=2))
    print('Build submitted:', result['id'], 'source:', source, flush=True)


def deploy():
    metadata = json.loads((ART / 'build.json').read_text())
    assert git('ls-remote', 'origin', 'refs/heads/GST_NEW_V3').split()[0] == metadata['commit']
    build = json.loads(cloud('builds', 'describe', metadata['id'], '--project', PROJECT, '--format=json'))
    assert build['status'] == 'SUCCESS' and build['substitutions']['_REVISION'] == metadata['commit']
    current = services()
    previous = baseline()
    for name in TARGETS:
        assert previous[name]['spec'] == current[name]['spec'] and previous[name]['status'] == current[name]['status']
        assert not any(t.get('tag') == TAG for t in current[name]['status']['traffic'])
    env = {v['name']: v.get('value') for v in current['gst-easy-v3-api']['spec']['template']['spec']['containers'][0]['env']}
    assert env['GST_DATASET_PREFIX'] == 'gst_easy_v3_' and env['BIGQUERY_DATASET'] == 'gst_easy_v3_finance_analytics'
    assert env['GCS_BUCKET_NAME'] == PROJECT + '-gst-easy-v3-documents'
    client = bigquery.Client(project=PROJECT, credentials=Credentials(cloud('auth', 'print-access-token')))
    for dataset in ['gst_easy_v3_ops', 'gst_easy_v3_finance_analytics']:
        assert client.get_dataset(PROJECT + '.' + dataset).labels.get('application') == 'gst-easy-v3'
    for migration in ['v3_auto_review_rules.sql', 'v3_auth_mail_repairs.sql']:
        sql = (ROOT / 'migrations' / migration).read_text(encoding='utf-8')
        sql = sql.replace('PROJECT.V3_OPS', PROJECT + '.gst_easy_v3_ops').replace('PROJECT.V3_FINANCE', PROJECT + '.gst_easy_v3_finance_analytics')
        client.query(sql, location=REGION).result()
    api = current['gst-easy-v3-api']['status']['url']
    web = current['gst-easy-v3-web']['status']['url']
    candidate_api = api.replace('https://', 'https://' + TAG + '---')
    candidate_web = web.replace('https://', 'https://' + TAG + '---')
    values = {
        'api': {'GST_BILLS_WORKER_URL': candidate_api, 'GST_BILLS_WORKER_AUDIENCE': api,
                'ALLOWED_ORIGINS': env.get('ALLOWED_ORIGINS', web) + ',' + candidate_web,
                'AUTH_PUBLIC_URL': candidate_web, 'RELEASE_REVISION': metadata['commit']},
        'web': {'BACKEND_URL': candidate_api, 'BACKEND_ID_TOKEN_AUDIENCE': api, 'RELEASE_REVISION': metadata['commit']},
    }
    report = {**metadata, 'candidates': {}, 'images': {}, 'promoted': False}
    for kind in ['api', 'web']:
        name = 'gst-easy-v3-' + kind
        assert current[name]['spec']['template']['spec']['serviceAccountName'] == account(kind)
        expected = f'{REGION}-docker.pkg.dev/{PROJECT}/gst-easy-v3/{kind}'
        image = next(i for i in build['results']['images'] if i['name'] == expected + ':' + metadata['commit'])
        digest = expected + '@' + image['digest']
        flags = ART / (kind + '-flags.json')
        flags.write_text(json.dumps({'--update-env-vars': values[kind]}))
        cloud('run', 'services', 'update', name, '--project', PROJECT, '--region', REGION,
              '--image', digest, '--flags-file', str(flags), '--no-traffic', '--tag', TAG, '--quiet')
        tag = next(t for t in services()[name]['status']['traffic'] if t.get('tag') == TAG)
        assert tag['url'] == (candidate_api if kind == 'api' else candidate_web)
        report['candidates'][kind] = tag
        report['images'][kind] = digest
        (ART / 'deployment.json').write_text(json.dumps(report, indent=2))
    verify_preserved()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    import sys
    {'build': build, 'deploy': deploy, 'verify': verify_preserved}[sys.argv[1]]()
