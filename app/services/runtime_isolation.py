"""Fail closed when V4 is accidentally configured to use an older environment."""
from urllib.parse import urlsplit


def validate_runtime(settings):
    if settings.deployment_generation != 'v4':
        return
    if not settings.gcp_project_id or settings.gcp_region in {'', 'global'}:
        raise RuntimeError('V4 requires an explicit project and regional data location')
    expected = {
        'bigquery_dataset': 'gst_easy_v4_finance_analytics',
        'gst_dataset_prefix': 'gst_easy_v4_',
        'gcs_bucket_name': settings.gcp_project_id + '-gst-easy-v4-documents',
        'gst_bills_queue': f'projects/{settings.gcp_project_id}/locations/{settings.gcp_region}/queues/gst-easy-v4-bills',
        'auth_mail_queue': f'projects/{settings.gcp_project_id}/locations/{settings.gcp_region}/queues/gst-easy-v4-auth',
        'gst_bills_worker_account': f'gst-easy-v4-api@{settings.gcp_project_id}.iam.gserviceaccount.com',
        'auth_worker_account': f'gst-easy-v4-api@{settings.gcp_project_id}.iam.gserviceaccount.com',
    }
    for key, value in expected.items():
        if getattr(settings, key) != value:
            raise RuntimeError('Unsafe V4 resource configuration: ' + key)
    if len(settings.app_secret_key) < 32 or settings.bootstrap_admin_password or settings.red_taxi_client_bootstrap or settings.demo_fallback:
        raise RuntimeError('Unsafe V4 session or legacy bootstrap configuration')
    for key, service in [('gst_bills_worker_url', 'api'), ('gst_bills_worker_audience', 'api'),
                         ('auth_worker_url', 'api'), ('auth_worker_audience', 'api'), ('auth_public_url', 'web')]:
        value = getattr(settings, key)
        if not value:
            continue  # Initial private deployment has no generated callback URL yet.
        url = urlsplit(value)
        if (url.scheme != 'https' or not url.hostname or url.port or url.path not in {'', '/'} or url.query or url.fragment
                or not url.hostname.startswith('gst-easy-v4-' + service + '-') or not url.hostname.endswith('.run.app')):
            raise RuntimeError('Unsafe V4 callback configuration: ' + key)
