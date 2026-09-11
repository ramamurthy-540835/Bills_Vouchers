from functools import lru_cache
import json
import logging
import re
from contextvars import ContextVar

from fastapi import Depends

from .config import get_settings
from .services.retry import retry_call


logger = logging.getLogger("bills_voucher.bigquery")
request_id_context: ContextVar[str] = ContextVar("request_id", default="system")


class BigQueryRepository:
    def __init__(self):
        from google.cloud import bigquery

        s = get_settings()
        if not s.gcp_project_id:
            raise RuntimeError("GCP_PROJECT_ID is required for BigQuery-only mode.")
        self.client = bigquery.Client(project=s.gcp_project_id)
        self.settings = s
        self.dataset = f"{s.gcp_project_id}.{s.bigquery_dataset}"

    def table(self, name):
        return f"{self.dataset}.{name}"

    def query(self, sql, params=None):
        from google.cloud import bigquery

        s = self.settings
        request_id = re.sub(r"[^a-z0-9_-]", "-", request_id_context.get().lower())[:63] or "system"
        config = bigquery.QueryJobConfig(query_parameters=params or [], maximum_bytes_billed=s.max_query_bytes, labels={"request_id": request_id})
        job = retry_call(lambda: self.client.query(sql, job_config=config))
        rows = list(retry_call(lambda: job.result(timeout=s.query_timeout_seconds)))
        logger.debug(json.dumps({"event": "bigquery_query", "bytes_billed": getattr(job, "total_bytes_billed", None), "rows": len(rows)}))
        return rows

    def insert(self, table, row, row_id=None):
        errors = retry_call(
            lambda: self.client.insert_rows_json(
                self.table(table),
                [row],
                row_ids=[row_id] if row_id else None,
                timeout=self.settings.query_timeout_seconds,
            )
        )
        if errors:
            raise RuntimeError(f"BigQuery insert failed: {errors}")

    def update(self, table, set_sql, where_sql, params):
        self.query(f"UPDATE `{self.table(table)}` SET {set_sql} WHERE {where_sql}", params)

    def one(self, sql, params=None):
        rows = self.query(sql, params)
        return rows[0] if rows else None


@lru_cache
def get_repository():
    return BigQueryRepository()


def get_db(repo: BigQueryRepository = Depends(get_repository)):
    return repo
