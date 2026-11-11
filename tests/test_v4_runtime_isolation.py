import pytest
from app.config import Settings
from app.services.runtime_isolation import validate_runtime


def isolated_settings():
    return Settings(_env_file=None, deployment_generation='v4', gcp_project_id='synthetic-project',
        gcp_region='asia-south1', app_secret_key='s'*48, bigquery_dataset='gst_easy_v4_finance_analytics',
        gst_dataset_prefix='gst_easy_v4_', gcs_bucket_name='synthetic-project-gst-easy-v4-documents',
        gst_bills_queue='projects/synthetic-project/locations/asia-south1/queues/gst-easy-v4-bills',
        auth_mail_queue='projects/synthetic-project/locations/asia-south1/queues/gst-easy-v4-auth',
        gst_bills_worker_account='gst-easy-v4-api@synthetic-project.iam.gserviceaccount.com',
        auth_worker_account='gst-easy-v4-api@synthetic-project.iam.gserviceaccount.com')


@pytest.mark.parametrize('key,value', [('bigquery_dataset','gst_easy_v3_finance_analytics'),
    ('gst_dataset_prefix','gst_easy_v2_'),('gcs_bucket_name','synthetic-project-gst-easy-v3-documents'),
    ('gst_bills_queue','projects/synthetic-project/locations/asia-south1/queues/gst-easy-v3-bills'),
    ('auth_worker_url','https://gst-easy-v3-api-synthetic.a.run.app'),
    ('auth_public_url','https://gst-easy-v3-web-synthetic.a.run.app'),
    ('gst_bills_worker_account','gst-easy-v3-api@synthetic-project.iam.gserviceaccount.com'),
    ('demo_fallback',True),('app_secret_key','development-only-change-me')])
def test_v4_refuses_old_resources_callbacks_and_insecure_defaults(key,value):
    settings=isolated_settings()
    setattr(settings,key,value)
    with pytest.raises(RuntimeError):
        validate_runtime(settings)


def test_initial_private_v4_configuration_can_boot_before_urls_are_assigned():
    validate_runtime(isolated_settings())
