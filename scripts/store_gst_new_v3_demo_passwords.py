"""Store operator-supplied demo passwords through hidden stdin, never source."""
from getpass import getpass
from app.security import password_is_strong
from prepare_gst_new_v3 import PROJECT, cloud, exists


def main():
    for name in ['naturelabs1','naturelabs']:
        secret='gst-easy-v3-'+name+'-password'
        if exists('secrets','versions','describe','1','--secret',secret,'--project',PROJECT):
            print(name+': existing version retained')
            continue
        value=getpass(name+' password (hidden): ')
        if not password_is_strong(value):
            raise RuntimeError('Password fails unchanged policy')
        if not exists('secrets','describe',secret,'--project',PROJECT):
            cloud('secrets','create',secret,'--project',PROJECT,'--replication-policy=automatic',
                  '--labels=application=gst-easy-v3,purpose=synthetic-demo')
        cloud('secrets','versions','add',secret,'--project',PROJECT,'--data-file=-',input=value)
        del value
        print(name+': stored securely')


if __name__=='__main__':
    main()
