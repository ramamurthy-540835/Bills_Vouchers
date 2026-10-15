"""Fenced worker claims and audited recovery using the existing durable job table."""
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from google.api_core.exceptions import BadRequest, Conflict

from app.services.gst.medallion import param

# Cloud Tasks dispatch deadline is 30 minutes; allow five minutes for termination.
STALE_MINUTES = 35


def retryable(job):
    if job['status'] == 'needs_attention':
        return True
    if job['status'] not in {'queued', 'reading'} or job.get('recovery_version') != 1 or not job.get('_updated_at'):
        return False
    updated = datetime.fromisoformat(str(job['_updated_at']))
    return updated <= datetime.now(timezone.utc) - timedelta(minutes=STALE_MINUTES)


def payload(job):
    return json.dumps({key: value for key, value in job.items() if not key.startswith('_')})


class JobState(ABC):
    worker_token = None
    worker_job_id = None

    @abstractmethod
    def table(self, dataset, name):
        raise NotImplementedError

    @abstractmethod
    def query(self, sql, params=()):
        raise NotImplementedError

    @abstractmethod
    def writable_sql(self):
        raise NotImplementedError

    @abstractmethod
    def job(self, job_id, payload=None):
        raise NotImplementedError

    def worker_fence(self):
        if not self.worker_token:
            return '', []
        return (f'''ASSERT EXISTS(SELECT 1 FROM {self.table('ops','gst_bill_job')}
            WHERE client_id=@client_id AND job_id=@worker_job
            AND JSON_VALUE(payload,'$.worker_token')=@worker_token
            AND JSON_VALUE(payload,'$.status')='reading'
            AND updated_at>TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL {STALE_MINUTES} MINUTE)) AS 'Worker claim lost';''',
            [param('worker_job', self.worker_job_id), param('worker_token', self.worker_token)])

    def transition_job(self, job, previous, actor, action):
        try:
            self.query(f'''BEGIN TRANSACTION;
                UPDATE {self.table('ops','gst_bill_lock')} SET touched_at=CURRENT_TIMESTAMP() WHERE client_id='__guard__';
                ASSERT @@row_count=1 AS 'Storage guard missing';
                {self.writable_sql()}
                UPDATE {self.table('ops','gst_bill_job')} SET payload=PARSE_JSON(@payload),updated_at=CURRENT_TIMESTAMP()
                WHERE client_id=@client_id AND job_id=@id AND updated_at=@updated;
                ASSERT @@row_count=1 AS 'Upload changed';
                INSERT INTO {self.table('ops','gst_bill_audit')}
                VALUES (@client_id,NULL,@actor,@action,PARSE_JSON(@before),PARSE_JSON(@payload),CURRENT_TIMESTAMP());
                COMMIT TRANSACTION;''', [param('id', job['job_id']), param('payload', payload(job)),
                param('before', payload(previous)), param('updated', previous['_updated_at'], 'TIMESTAMP'),
                param('actor', str(actor)), param('action', action), param('period', job['period']),
                param('previous_period', job['period'])])
        except (BadRequest, Conflict) as exc:
            if any(word in str(exc).lower() for word in ('upload changed', 'concurrent', 'aborted')):
                raise HTTPException(409, 'This upload changed in another request. Refresh its status.') from None
            raise
        return job

    def claim_job(self, job_id, actor):
        previous = self.job(job_id)
        if previous['status'] == 'completed':
            return previous
        if previous['status'] == 'reading' and not retryable(previous):
            raise HTTPException(409, 'This upload already has an active worker.')
        if previous['status'] not in {'queued', 'reading', 'needs_attention'}:
            raise HTTPException(409, 'This upload cannot be processed.')
        job = {**previous, 'status': 'reading', 'worker_token': uuid4().hex, 'recovery_version': 1}
        job.pop('reason', None)
        self.transition_job(job, previous, actor, 'job_claim')
        self.worker_token, self.worker_job_id = job['worker_token'], job_id
        return job

    def retry_job(self, job_id, actor='system'):
        previous = self.job(job_id)
        if not retryable(previous):
            raise HTTPException(409, 'Only failed uploads or uploads inactive for 35 minutes can be retried.')
        job = json.loads(payload(previous))
        job['status'] = 'queued'
        job['recovery_version'] = 1
        job.pop('worker_token', None)
        job.pop('reason', None)
        for entry in job['files']:
            if not entry.get('invoice_ids'):
                entry['status'] = 'reading'
                entry.pop('reason', None)
        return self.transition_job(job, previous, actor, 'job_retry')
