"""Read-only MCP server backed only by BigQuery.
Run: python -m app.services.mcp_server
"""

from google.cloud import bigquery
from mcp.server.fastmcp import FastMCP  # type: ignore[attr-defined]

from ..db import get_repository
from .embeddings import EmbeddingService

mcp = FastMCP("bills-voucher-bigquery")


@mcp.tool()
def search_documents(query: str, top_k: int = 10) -> list[dict]:
    """Semantic search over GST bills and vouchers using BigQuery VECTOR_SEARCH."""
    return EmbeddingService(get_repository()).search(query, top_k)


@mcp.tool()
def query_bigquery(sql: str, max_rows: int = 100) -> list[dict]:
    """Run a bounded read-only SELECT or WITH query against BigQuery."""
    if not sql.lstrip().lower().startswith(("select", "with")):
        raise ValueError("Only SELECT/WITH queries are allowed.")
    rows = get_repository().query(sql)
    return [dict(r.items()) for r in rows[: max(1, min(max_rows, 1000))]]


@mcp.tool()
def powerbi_dashboard_data(client_id: str = "client_demo_001") -> list[dict]:
    """Return Power BI-ready monthly income and expense data from the BigQuery analytics view."""
    repo = get_repository()
    rows = repo.query(
        f"""SELECT month,category,income,expense FROM `{repo.table("powerbi_finance_dashboard")}` WHERE client_id=@client ORDER BY month,category""",
        [bigquery.ScalarQueryParameter("client", "STRING", client_id)],
    )
    return [dict(r.items()) for r in rows]


if __name__ == "__main__":
    mcp.run(transport="stdio")
