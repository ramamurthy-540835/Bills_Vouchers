"""Accept password through hidden terminal input, never arguments or files."""
from getpass import getpass
from prepare_gst_easy_v2 import cloud, exists, PROJECT
from app.security import password_is_strong


def main():
    secret='gst-easy-v2-naturelabs1-password'
    if exists('secrets','versions','describe','1','--secret',secret,'--project',PROJECT):
        raise RuntimeError('Version already exists; refusing to replace this credential')
    value=getpass('New isolated demo password (hidden): ')
    if not password_is_strong(value):
        raise RuntimeError('Password fails existing policy')
    if not exists('secrets','describe',secret,'--project',PROJECT):
        cloud('secrets','create',secret,'--project',PROJECT,'--replication-policy=automatic',
              '--labels=application=gst-easy-v2,purpose=synthetic-demo')
    cloud('secrets','versions','add',secret,'--project',PROJECT,'--data-file=-',input=value)
    del value
    print('Stored isolated demo password in Secret Manager; no plaintext file created.')


if __name__=='__main__':main()
