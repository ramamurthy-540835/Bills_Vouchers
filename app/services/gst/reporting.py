"""BigQuery-backed export helpers for GST purchase and outward registers."""

from datetime import date
from typing import Any


def gstr_rows(repo: Any, client_id: str, start: date | None = None, end: date | None = None) -> list[dict[str, Any]]:
    from google.cloud import bigquery

    clauses = ["d.client_id=@client", "d.status='approved'"]
    params = [bigquery.ScalarQueryParameter("client", "STRING", client_id)]
    if start:
        clauses.append("e.invoice_date>=@start")
        params.append(bigquery.ScalarQueryParameter("start", "DATE", start))
    if end:
        clauses.append("e.invoice_date<=@end")
        params.append(bigquery.ScalarQueryParameter("end", "DATE", end))
    sql = f"""SELECT COALESCE(e.supplier_gstin,e.gstin) supplier_gstin, e.invoice_number, e.invoice_date,
        e.subtotal taxable_value, e.cgst, e.sgst, e.igst, e.total_amount,
        e.classification, e.reverse_charge, e.irn
        FROM `{repo.table('document_extractions')}` e
        JOIN `{repo.table('documents')}` d ON d.id=e.document_id
        WHERE {' AND '.join(clauses)} ORDER BY e.invoice_date,e.invoice_number"""
    return [dict(row.items()) for row in repo.query(sql, params)]
