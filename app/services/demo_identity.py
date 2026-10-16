"""Explicit operator activation of synthetic identities, disabled outside V2.

This is not email verification. Mail/mobile verification flags stay false.
The operator must possess the V2 provisioning credential and activate the row.
"""
from app.config import get_settings


def identity_can_sign_in(user):
    if getattr(user, 'email_verified', None) is not False:
        return True
    settings = get_settings()
    return (settings.demo_operator_identity_enabled
            and settings.bigquery_dataset == 'gst_easy_v2_finance_analytics'
            and settings.gst_dataset_prefix == 'gst_easy_v2_'
            and settings.gcs_bucket_name == 'aidirac-503309-gst-easy-v2-documents'
            and getattr(user, 'demo_operator_activated', False) is True
            and getattr(user, 'identity_provenance', '') == 'SYNTHETIC_TEST_ONLY'
            and getattr(user, 'email', '') == 'naturelabs@demo.com'
            and getattr(user, 'role', '') == 'client')



def isolated_v2_demo():
    settings = get_settings()
    return (settings.demo_operator_identity_enabled
            and settings.bigquery_dataset == 'gst_easy_v2_finance_analytics'
            and settings.gst_dataset_prefix == 'gst_easy_v2_'
            and settings.gcs_bucket_name == 'aidirac-503309-gst-easy-v2-documents')
