"""Validate approved Zoho credentials and configure only the GST Easy preview."""
import argparse
import json
import smtplib
import ssl
from pathlib import Path

from deploy_v3 import PROJECT, REGION, gcloud, state, unchanged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--host', default='smtppro.zoho.in', choices=['smtppro.zoho.in', 'smtp.zoho.in'])
    args = parser.parse_args()
    sender = 'ai@aidirac.com'
    version = '1'
    password = gcloud('secrets', 'versions', 'access', version,
                      '--secret', 'ZOHO_SMTP_PASSWORD', '--project', PROJECT).rstrip('\r\n')
    try:
        with smtplib.SMTP(args.host, 587, timeout=20) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(sender, password)
    except smtplib.SMTPAuthenticationError as exc:
        print(json.dumps({'smtp_authenticated': False, 'smtp_code': exc.smtp_code,
                          'host': args.host, 'deployment_changed': False}))
        raise SystemExit(1) from None
    finally:
        password = None
    print(json.dumps({'smtp_authenticated': True, 'host': args.host, 'email_sent': False}), flush=True)
    if not args.apply:
        return
    versions = json.loads(gcloud('secrets', 'versions', 'list', 'bills-voucher-app-secret',
                                 '--project', PROJECT, '--filter=state=ENABLED',
                                 '--sort-by=~createTime', '--limit=1', '--format=json(name)'))
    signing_version = versions[0]['name'].rsplit('/', 1)[-1]
    signing_key = gcloud('secrets', 'versions', 'access', signing_version,
                         '--secret', 'bills-voucher-app-secret', '--project', PROJECT).rstrip('\r\n')
    if len(signing_key) < 32:
        raise RuntimeError('Existing application signing secret does not meet the worker requirement.')
    signing_key = None
    before = state('bills-voucher')
    web_before = state('bills-voucher-web')
    tagged = next(row for row in before if row.get('tag') == 'gst-easy')
    runtime = json.loads(gcloud('run', 'services', 'describe', 'bills-voucher', '--project', PROJECT,
                               '--region', REGION, '--format=json'))
    if runtime['status']['latestReadyRevisionName'] != tagged['revisionName']:
        raise RuntimeError('Service template is not the GST Easy preview; inspect before deploying.')
    image = runtime['spec']['template']['spec']['containers'][0]['image']
    if '@sha256:' not in image:
        raise RuntimeError('Expected an immutable image digest.')
    values = {'SMTP_HOST': args.host, 'SMTP_PORT': '587', 'SMTP_USERNAME': sender,
              'SMTP_SENDER': sender,
              'AUTH_PUBLIC_URL': 'https://gst-easy---bills-voucher-web-foovqasysa-el.a.run.app'}
    gcloud('run', 'deploy', 'bills-voucher', '--project', PROJECT, '--region', REGION,
           '--image', image, '--no-traffic', '--tag', 'gst-easy', '--quiet',
           '--update-env-vars', ','.join(key + '=' + value for key, value in values.items()),
           '--update-secrets', 'SMTP_PASSWORD=ZOHO_SMTP_PASSWORD:' + version
           + ',APP_SECRET_KEY=bills-voucher-app-secret:' + signing_version)
    after = state('bills-voucher')
    unchanged(before, after, 'gst-easy')
    unchanged(web_before, state('bills-voucher-web'), 'gst-easy')
    report = {'smtp_authenticated': True, 'email_sent': False, 'sender': sender,
              'host': args.host, 'secret_version': version, 'image': image,
              'signing_secret_version': signing_version,
              'before': before, 'after': after, 'existing_traffic_unchanged': True}
    output = Path('artifacts/gst_easy/mail-configuration.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
