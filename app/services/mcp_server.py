"""Read-only MCP server backed only by BigQuery.
Run: python -m app.services.mcp_server
"""

from google.cloud import bigquery
from mcp.server.fastmcp import FastMCP

from ..db import get_repository
from .embeddings import EmbeddingService

mcp = FastMCP("bills-voucher-bigquery")


@mcp.tool()
def search_documents(query: str, client_id: str, top_k: int = 10) -> list[dict]:
    """Semantic search scoped to one client using BigQuery VECTOR_SEARCH."""
    return EmbeddingService(get_repository()).search(query, top_k, client_id)


@mcp.tool()
def validate_read_only_sql(sql: str) -> str:
    statement = sql.strip()
    if statement.endswith(";"):
        statement = statement[:-1].rstrip()
    if not statement or ";" in statement or not statement.lower().startswith(("select", "with")):
        raise ValueError("Only one SELECT/WITH query is allowed.")
    if __import__("re").search(r"\b(insert|update|delete|merge|create|alter|drop|truncate|call|execute)\b", statement, __import__("re").IGNORECASE):
        raise ValueError("Write and procedural SQL statements are not allowed.")
    return statement


def query_bigquery(sql: str, max_rows: int = 100) -> list[dict]:
    """Run a bounded read-only SELECT or WITH query against BigQuery."""
    rows = get_repository().query(validate_read_only_sql(sql))
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
