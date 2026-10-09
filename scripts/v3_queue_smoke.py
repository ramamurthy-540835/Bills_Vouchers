"""Verify real queue/OIDC delivery using an empty ops job, never a customer bill."""
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
from google.cloud import bigquery
from google.oauth2.credentials import Credentials

from deploy_v3 import gcloud, WEB, API, PROJECT, REGION
from app.config import get_settings
from app.db import BigQueryRepository
from app.gst.store import BillStore
from app.services.gst.account import can

os.environ.setdefault('GCP_PROJECT_ID', PROJECT)
os.environ.setdefault('BIGQUERY_DATASET', 'finance_analytics')
get_settings.cache_clear()
repo = BigQueryRepository.__new__(BigQueryRepository)
repo.settings = get_settings()
repo.dataset = PROJECT + '.finance_analytics'
repo.client = bigquery.Client(project=PROJECT, credentials=Credentials(gcloud('auth', 'print-access-token').strip()))
with httpx.Client(base_url=WEB, timeout=120) as client:
    response = client.post('/api/auth/login', json={'email': os.environ['BV_TEST_EMAIL'], 'password': os.environ['BV_TEST_PASSWORD']}, headers={'Origin': WEB})
    response.raise_for_status()
    response = client.get('/api/gst/bills/dashboard?period=2026-09')
    response.raise_for_status()
    data = response.json()
    actor = SimpleNamespace(**data['user'])
    assert can(actor, 'bills:write', data['client_id'], repo)
    job_id = str(uuid4())
    store = BillStore(repo, data['client_id'])
    store.job(job_id, {'job_id': job_id, 'status': 'queued', 'actor_id': actor.id, 'period': '2026-09', 'files': [], 'diagnostic': 'empty queue delivery check'})
    gcloud('tasks', 'create-http-task', 'bill-' + job_id, '--project', PROJECT, '--location', REGION,
           '--queue', 'bills-v3', '--url', API + '/api/gst/bills/internal/process', '--method', 'POST',
           '--header', 'Content-Type:application/json', '--body-content', json.dumps({'client_id': data['client_id'], 'job_id': job_id}),
           '--oidc-service-account-email', '624683933018-compute@developer.gserviceaccount.com',
           '--oidc-token-audience', 'https://bills-voucher-foovqasysa-el.a.run.app')
    for attempt in range(30):
        response = client.get('/api/gst/bills/upload/' + job_id)
        response.raise_for_status()
        if response.json()['status'] == 'completed':
            break
        time.sleep(2)
    else:
        raise RuntimeError('Queue delivery did not finish: inspect task bill-' + job_id)
    assert response.json()['files'] == []
Path('artifacts/v3/queue-smoke.json').write_text(json.dumps({'passed': True, 'job_id': job_id, 'persisted_financial_records': 0, 'check': 'Cloud Tasks OIDC, uploader permissions, runtime BigQuery job read/write'}, indent=2))
print('PASS live Cloud Tasks delivery and permission check; zero financial records created.')
