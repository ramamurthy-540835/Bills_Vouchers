"""Configure V2 email using the existing approved sender; never mutate old services."""
import json
import smtplib
import ssl

from deploy_gst_easy_v2 import environment_file, snapshot_unchanged
from prepare_gst_easy_v2 import ART, PROJECT, REGION, account, cloud, exists


def main():
    snapshot_unchanged()
    old = json.loads(cloud('run', 'services', 'describe', 'bills-voucher',
                          '--project', PROJECT, '--region', REGION, '--format=json'))
    original = {v['name']: v for v in old['spec']['template']['spec']['containers'][0]['env']}
    host = original['SMTP_HOST']['value']
    sender = original['SMTP_SENDER']['value']
    username = original['SMTP_USERNAME']['value']
    port = original['SMTP_PORT']['value']
    ref = original['SMTP_PASSWORD']['valueFrom']['secretKeyRef']
    assert host == 'smtppro.zoho.in' and sender == 'ai@aidirac.com' and port == '587'
    secret = 'gst-easy-v2-smtp-password'
    if not exists('secrets', 'describe', secret, '--project', PROJECT):
        cloud('secrets', 'create', secret, '--project', PROJECT,
              '--replication-policy=automatic', '--labels=application=gst-easy-v2')
    metadata = json.loads(cloud('secrets', 'describe', secret, '--project', PROJECT, '--format=json'))
    assert metadata.get('labels', {}).get('application') == 'gst-easy-v2'
    versions = json.loads(cloud('secrets', 'versions', 'list', secret, '--project', PROJECT, '--format=json'))
    if not versions:
        password = cloud('secrets', 'versions', 'access', ref['key'], '--secret', ref['name'], '--project', PROJECT)
        cloud('secrets', 'versions', 'add', secret, '--project', PROJECT, '--data-file=-', input=password)
    else:
        password = cloud('secrets', 'versions', 'access', '1', '--secret', secret, '--project', PROJECT)
    # Authenticate without sending email, printing credentials or creating accounts.
    with smtplib.SMTP(host, int(port), timeout=30) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(username, password)
    del password
    cloud('secrets', 'add-iam-policy-binding', secret, '--project', PROJECT,
          '--member=serviceAccount:' + account('api'), '--role=roles/secretmanager.secretAccessor')
    queue = 'gst-easy-v2-auth'
    if not exists('tasks', 'queues', 'describe', queue, '--project', PROJECT, '--location', REGION):
        cloud('tasks', 'queues', 'create', queue, '--project', PROJECT, '--location', REGION,
              '--max-concurrent-dispatches=1', '--max-dispatches-per-second=1', '--max-attempts=5')
    cloud('tasks', 'queues', 'add-iam-policy-binding', queue, '--project', PROJECT, '--location', REGION,
          '--member=serviceAccount:' + account('api'), '--role=roles/cloudtasks.enqueuer')
    current = json.loads(cloud('run', 'services', 'describe', 'gst-easy-v2-api',
                              '--project', PROJECT, '--region', REGION, '--format=json'))
    values = {v['name']: v.get('value', '') for v in current['spec']['template']['spec']['containers'][0]['env']
              if 'valueFrom' not in v}
    assert values['BIGQUERY_DATASET'] == 'gst_easy_v2_finance_analytics'
    api = current['status']['url']
    values.update(SMTP_HOST=host, SMTP_PORT=port, SMTP_USERNAME=username, SMTP_SENDER=sender,
                  AUTH_MAIL_QUEUE=f'projects/{PROJECT}/locations/{REGION}/queues/{queue}',
                  AUTH_WORKER_URL=api, AUTH_WORKER_AUDIENCE=api, AUTH_WORKER_ACCOUNT=account('api'))
    cloud('run', 'services', 'update', 'gst-easy-v2-api', '--project', PROJECT, '--region', REGION,
          '--env-vars-file', environment_file('api-mail', values),
          '--update-secrets=SMTP_PASSWORD=' + secret + ':1', '--quiet')
    report = dict(sender=sender, queue=queue, smtp_authentication_passed=True,
                  existing_services_unchanged=snapshot_unchanged(),
                  delivery_acceptance='Pending actual user registration/verification; no test email sent.')
    (ART / 'email-configuration.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
