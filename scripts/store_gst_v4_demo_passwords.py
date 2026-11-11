"""New random V4 demo credentials, delivered only through Secret Manager."""
import json
import secrets
import subprocess
from v4_support import ART, PROJECT, cloud
from prepare_gst_v4 import secret_input


def main():
    if subprocess.check_output(['git','branch','--show-current'],text=True).strip()!='GSTv4':
        raise RuntimeError('Only GSTv4 is authorized')
    for user in ('naturelabs','naturelabs1'):
        name='gst-easy-v4-'+user+'-password'
        existing=json.loads(cloud('secrets','list','--project',PROJECT,'--filter=name:'+name,'--format=json'))
        if existing:
            if len(existing)!=1 or existing[0].get('labels',{}).get('application')!='gst-easy-v4':
                raise RuntimeError('Unowned credential secret; inspect before reuse')
        else:
            cloud('secrets','create',name,'--project',PROJECT,'--replication-policy=automatic',
                '--labels=application=gst-easy-v4,purpose=synthetic-demo')
        versions=json.loads(cloud('secrets','versions','list',name,'--project',PROJECT,'--format=json'))
        if not versions:
            secret_input('secrets','versions','add',name,'--project',PROJECT,'--data-file=-',
                value='V4a'+secrets.token_urlsafe(30)+'7')
    (ART/'demo-credentials.json').write_text(json.dumps({'accounts':['naturelabs@demo.com','naturelabs1@demo.com'],
        'delivery':'V4-only Secret Manager secrets; no plaintext passwords in reports',
        'existing_v3_credentials_changed':False},indent=2))
    print('New V4 synthetic credentials available in V4-only Secret Manager secrets')


if __name__=='__main__':main()
