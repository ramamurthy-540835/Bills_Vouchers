"""Preserve first-candidate policy metadata in audit, restoring legacy JSON shape.

Restricted to the authorized V3 Nature Labs synthetic tenant. No financial column,
invoice version, original evidence or prior audit row is changed/deleted.
"""
import json
from pathlib import Path

from google.cloud import bigquery
from google.oauth2.credentials import Credentials
from prepare_gst_new_v3 import cloud, PROJECT, REGION


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    bq = bigquery.Client(project=PROJECT, credentials=Credentials(cloud('auth', 'print-access-token')))
    finance = PROJECT + '.gst_easy_v3_finance_analytics'
    gold = PROJECT + '.gst_easy_v3_gold'
    ops = PROJECT + '.gst_easy_v3_ops'
    clients = list(bq.query(f'''SELECT DISTINCT c.id FROM `{finance}.clients` c
        JOIN `{finance}.client_memberships` m ON m.client_id=c.id AND m.is_active=TRUE AND m.access_role='owner'
        JOIN `{finance}.users` u ON u.id=m.user_id
        JOIN `{finance}.gst_client_profile` p ON p.client_id=c.id AND p.is_current=TRUE
        WHERE u.email='naturelabs1@demo.com' AND c.is_test=TRUE AND p.source='SYNTHETIC_TEST_ONLY'
        AND c.name='Nature Labs Synthetic Manufacturing Pvt Ltd' ''', location=REGION).result())
    assert len(clients) == 1
    config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('client', 'STRING', clients[0]['id'])])
    before = list(bq.query(f'''SELECT invoice_id,version,payload FROM `{gold}.gst_invoice`
        WHERE client_id=@client AND JSON_QUERY(payload,'$.auto_review') IS NOT NULL''',
        job_config=config, location=REGION).result())
    assert len(before) <= 2, 'Unexpected scope; inspect before modifying anything.'
    for row in before:
        payload = row['payload'] if isinstance(row['payload'], dict) else json.loads(row['payload'])
        assert payload['invoice_number'].startswith('NL1-') and payload['status'] == 'needs_review'
        assert not payload['auto_review']['enabled'] and payload['auto_review']['status'] != 'running'
    bq.query(f'''BEGIN TRANSACTION;
        UPDATE `{ops}.gst_bill_lock` SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
        ASSERT @@row_count=1 AS 'Storage guard missing';
        ASSERT NOT EXISTS(SELECT 1 FROM `{gold}.gst_invoice` WHERE client_id=@client
            AND JSON_QUERY(payload,'$.auto_review') IS NOT NULL
            AND (JSON_VALUE(payload,'$.auto_review.enabled')!='false' OR status!='needs_review')) AS 'Unexpected active policy';
        INSERT INTO `{ops}.gst_bill_audit`
        SELECT client_id,invoice_id,'v3-candidate-compatibility','auto_review_state',
          TO_JSON(STRUCT(version AS version,JSON_QUERY(payload,'$.auto_review') AS auto_review)),
          TO_JSON(STRUCT(version AS version,JSON_QUERY(payload,'$.auto_review') AS auto_review)),CURRENT_TIMESTAMP()
        FROM `{gold}.gst_invoice` WHERE client_id=@client AND JSON_QUERY(payload,'$.auto_review') IS NOT NULL;
        UPDATE `{gold}.gst_invoice` SET payload=JSON_REMOVE(payload,'$.auto_review')
        WHERE client_id=@client AND JSON_QUERY(payload,'$.auto_review') IS NOT NULL;
        COMMIT TRANSACTION;''', job_config=config, location=REGION).result()
    after = {r['invoice_id']: r for r in bq.query(f'SELECT invoice_id,version,payload FROM `{gold}.gst_invoice` WHERE client_id=@client', job_config=config, location=REGION).result()}
    for row in before:
        original = row['payload'] if isinstance(row['payload'], dict) else json.loads(row['payload'])
        original.pop('auto_review')
        saved = after[row['invoice_id']]['payload']
        assert original == (saved if isinstance(saved, dict) else json.loads(saved))
        assert row['version'] == after[row['invoice_id']]['version']
    report = {'tenant': 'authorized V3 Nature Labs synthetic workspace', 'policies_preserved': len(before),
              'financial_values_versions_originals_unchanged': True, 'prior_audit_retained': True}
    Path('artifacts/auto-review-v3/compatibility-repair.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
