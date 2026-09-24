"""Real BQ/GCS pipeline gate using isolated synthetic tenant IDs in staging.

Credentials remain in process memory. No customer records or traffic are changed.
"""
import os
import subprocess
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from google.cloud import bigquery, storage
from google.oauth2.credentials import Credentials

os.environ.update(GCP_PROJECT_ID="aidirac-503309", BIGQUERY_DATASET="finance_analytics_staging",
                  GCS_BUCKET_NAME="aidirac-503309-bills-voucher-documents", DEMO_FALLBACK="false", MEDALLION_ENABLED="true")
from app.config import get_settings
from app.db import BigQueryRepository
from app.services.documents import GCSObjectStore
from app.services.gst.medallion import Medallion, now
from app.services.gst.pipeline import land, silver
from app.services.gst.workbench import transition


def main():
    token = subprocess.check_output(["gcloud.cmd", "auth", "print-access-token"], text=True).strip()
    credentials = Credentials(token)
    bq = bigquery.Client(project="aidirac-503309", credentials=credentials)
    gcs = storage.Client(project="aidirac-503309", credentials=credentials)
    repo = object.__new__(BigQueryRepository)
    repo.client, repo.settings, repo.dataset = bq, get_settings(), "aidirac-503309.finance_analytics_staging"
    sql = Path("migrations/007_v5_medallion.sql").read_text().replace(".finance_analytics.", ".finance_analytics_staging.")
    bq.query(sql).result()
    print("PASS staging additive schema", flush=True)
    GCSObjectStore._bucket = lambda self: gcs.bucket(self.bucket)
    stores = []
    period = date.today().strftime("%Y-%m")
    for label in ("a", "b"):
        tenant = "v5-integration-" + label + "-" + uuid4().hex[:12]
        store = Medallion(repo, tenant, period)
        stores.append(store)
        stamp = now()
        store.upsert("gst_client_profile", {"client_id": tenant, "profile_id": tenant, "gstin": "", "legal_name": "Integration test " + label,
                     "business_nature": "passenger_transport", "effective_from": stamp, "created_at": stamp, "is_current": True}, ["client_id", "profile_id"])
        # Distinct invoice payload, same invoice number across tenants.
        payload = b"%PDF-1.4\n% Integration test " + label.encode() + b"\n%%EOF"
        doc = land(store, payload, "integration.pdf", "application/pdf", "integration-test")
        duplicate = land(store, payload, "integration.pdf", "application/pdf", "integration-test")
        assert duplicate["doc_id"] == doc["doc_id"] and duplicate["duplicate"]
        bucket, path = doc["gcs_uri"].removeprefix("gs://").split("/", 1)
        assert gcs.bucket(bucket).blob(path).exists()
        silver(store, doc, {"supplier_gstin": "27AAPFU0939F1ZV", "vendor_name": "Integration " + label, "invoice_number": "OVERLAP-001",
               "invoice_date": date.today().isoformat(), "subtotal": "1000", "total_amount": "1180", "igst": "180", "confidence": "1",
               "line_items": [{"description": "Passenger vehicle", "itc_category": "vehicle", "taxable_value": "1000", "igst": "180"}]}, engine="integration_review", actor="integration-test")
        workspace = store.workspace()
        assert workspace["counts"]["documents"] == 1 and workspace["counts"]["posted"] == 1
        assert all(row["client_id"] == tenant for row in workspace["documents"] + workspace["ledger"])
        assert len(workspace["ledger"]) == 1
        assert store.recompute()["run_id"] == workspace["summary"]["run_id"]
        print("PASS tenant " + label + " bronze/GCS/silver/gold/deduplication/idempotency", flush=True)
    actor = SimpleNamespace(role="tax_admin", email="integration-test@example.invalid")
    for state in ("validated", "json_generated", "filed", "locked"):
        transition(stores[0], actor, state, "A"*15 if state == "filed" else None, date.today().isoformat() if state == "filed" else None)
    assert stores[0].status()["state"] == "locked"
    assert stores[1].status()["state"] == "draft"
    print("PASS transactional filing and tenant isolation", flush=True)
    # Preserve a bounded staging audit for review; these synthetic tenants have no login/membership.
    print("PASS integration gate; synthetic rows are isolated in finance_analytics_staging", flush=True)


if __name__ == "__main__":
    main()
