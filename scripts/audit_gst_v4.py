"""Read-only inventory and preservation checks for the independent V4 release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ART = Path('artifacts/v4-audit')
PROTECTED = ('bills-voucher', 'bills-voucher-web', 'gst-easy-v2-api',
             'gst-easy-v2-web', 'gst-easy-v3-api', 'gst-easy-v3-web')


def cloud(*args):
    sdk = Path(os.environ['LOCALAPPDATA']) / 'Google/Cloud SDK/google-cloud-sdk'
    return subprocess.check_output([str(sdk / 'platform/bundledpython/python.exe'),
        str(sdk / 'lib/gcloud.py'), *args], text=True,
        env={k: v for k, v in os.environ.items() if k.upper() != 'PYTHONPATH'}).strip()


def sanitize(resource):
    resource = json.loads(json.dumps(resource))
    for container in resource.get('spec', {}).get('template', {}).get('spec', {}).get('containers', []):
        for entry in container.get('env', []):
            if 'value' in entry and any(word in entry['name'] for word in ('PASSWORD', 'SECRET', 'API_KEY', 'TOKEN', 'CREDENTIAL')):
                entry['value'] = 'SHA256:' + hashlib.sha256(entry['value'].encode()).hexdigest()
    return resource


def snapshot(project, region):
    services = json.loads(cloud('run', 'services', 'list', '--project', project, '--format=json'))
    state = {'project': project, 'region': region, 'inventory': [
        {'name': s['metadata']['name'], 'url': s.get('status', {}).get('url')}
        for s in services], 'services': {}, 'iam': {}}
    for name in PROTECTED:
        state['services'][name] = sanitize(json.loads(cloud('run', 'services', 'describe', name,
            '--project', project, '--region', region, '--format=json')))
        state['iam'][name] = json.loads(cloud('run', 'services', 'get-iam-policy', name,
            '--project', project, '--region', region, '--format=json'))
    state['branches'] = subprocess.check_output(['git', 'ls-remote', 'origin',
        'refs/heads/GST_NEW_V3', 'refs/heads/GST-EASY-V2'], text=True).strip()
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['before', 'verify'])
    parser.add_argument('--project', required=True)
    parser.add_argument('--region', required=True)
    args = parser.parse_args()
    ART.mkdir(parents=True, exist_ok=True)
    before = ART / 'protected-before.json'
    if args.action == 'before' and before.exists():
        raise RuntimeError('Preserve the existing baseline snapshot')
    state = snapshot(args.project, args.region)
    if args.action == 'before':
        if any(s['name'] in {'gst-easy-v4-api', 'gst-easy-v4-web'} for s in state['inventory']):
            raise RuntimeError('V4 service names already exist; inspect before proceeding')
        before.write_text(json.dumps(state, indent=2), encoding='utf-8')
        print(json.dumps({'project': args.project, 'region': args.region,
            'v4_names_available': True, 'protected_services_captured': len(PROTECTED)}))
    else:
        original = json.loads(before.read_text())
        checks = {name: all(original['services'][name].get(k) == state['services'][name].get(k)
            for k in ('spec',)) and original['services'][name]['status']['traffic'] == state['services'][name]['status']['traffic']
            and original['iam'][name] == state['iam'][name] for name in PROTECTED}
        checks['source_branches'] = original['branches'] == state['branches']
        project_policy = ART / 'project-iam-before.json'
        if project_policy.exists():
            after_policy = json.loads(cloud('projects', 'get-iam-policy', args.project, '--format=json'))
            added_members = {'serviceAccount:gst-easy-v4-' + kind + '@' + args.project + '.iam.gserviceaccount.com'
                for kind in ('api', 'build')}
            def existing_grants(policy):
                return sorted((binding['role'], json.dumps(binding.get('condition'), sort_keys=True),
                    tuple(sorted(set(binding['members']) - added_members)))
                    for binding in policy.get('bindings', []) if set(binding['members']) - added_members)
            checks['existing_project_iam_grants'] = existing_grants(json.loads(project_policy.read_text())) == existing_grants(after_policy)
            (ART / 'project-iam-after.json').write_text(json.dumps(after_policy, indent=2))
        (ART / 'protected-after.json').write_text(json.dumps(state, indent=2))
        (ART / 'preservation.json').write_text(json.dumps(checks, indent=2))
        if not all(checks.values()):
            raise RuntimeError('Preservation check failed; inspect saved evidence')
        print(json.dumps(checks))


if __name__ == '__main__':
    main()
