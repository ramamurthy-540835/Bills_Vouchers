"""Copy the approved sender credential into a separate V3 secret, never stdout.

Reads the existing approved SMTP credential only; never changes its versions,
IAM, or consumers. V3 runtime receives access only to the new secret.
"""
import json
import subprocess

from prepare_gst_new_v3 import PROJECT, ENV, account, cloud, exists


def main():
    if subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip() != 'GST_NEW_V3':
        raise RuntimeError('Wrong branch')
    target = 'gst-easy-v3-smtp-password'
    if exists('secrets', 'describe', target, '--project', PROJECT):
        raise RuntimeError('V3 mail secret already exists; inspect rather than overwrite.')
    result = subprocess.run(
        ['gcloud.cmd', 'secrets', 'versions', 'access', '1',
         '--secret=gst-easy-v2-smtp-password', '--project', PROJECT],
        env=ENV, capture_output=True, check=True)
    if not result.stdout.strip():
        raise RuntimeError('Approved sender credential is empty.')
    cloud('secrets', 'create', target, '--project', PROJECT,
          '--replication-policy=automatic', '--labels=application=gst-easy-v3')
    # Binary stdin: credential never enters a command argument, file or log.
    provision = subprocess.run(
        ['gcloud.cmd', 'secrets', 'versions', 'add', target, '--project', PROJECT, '--data-file=-'],
        env=ENV, input=result.stdout.rstrip(b'\r\n'), capture_output=True)
    if provision.returncode:
        raise RuntimeError('V3 mail credential provisioning failed.')
    cloud('secrets', 'add-iam-policy-binding', target, '--project', PROJECT,
          '--member=serviceAccount:'+account('api'), '--role=roles/secretmanager.secretAccessor')
    print(json.dumps({'secret': target, 'version': '1', 'source_modified': False,
                      'inbox_delivery_confirmed': False}))


if __name__ == '__main__':
    main()
