"""Read-only billing adapters. Connection policy comes from trusted server storage.

No arbitrary URL, SQL, tool selection, or inbound application token forwarding.
Live activation additionally requires an approved egress and credential policy.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from app.gst.intake import MAX_BYTES, MAX_ROWS, preview


class ConnectorError(ValueError):
    """Safe diagnostic; never includes credentials or remote response bodies."""


@dataclass(frozen=True)
class Connection:
    client_id: str
    source_system: str
    endpoint: str
    approved_endpoint: str
    mode: str
    enabled: bool = False
    approved_tool: str = "list_invoices"

    def authorize(self, selected_client: str):
        parsed = urlsplit(self.endpoint)
        if not self.enabled or self.client_id != selected_client:
            raise ConnectorError("Connection is disabled or not authorized for this business.")
        if (
            self.endpoint != self.approved_endpoint
            or parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ConnectorError("An approved HTTPS resource endpoint is required.")
        if self.mode not in {"rest", "mcp"} or self.source_system not in {"vendor", "customer", "driver"}:
            raise ConnectorError("Unsupported connection type or source.")
        if self.approved_tool != "list_invoices":
            raise ConnectorError("Only the approved read-only billing tool is supported.")


@dataclass(frozen=True)
class ResourceCredential:
    """Issued by the server credential broker after issuer/signature verification.

    This is not a JWT verifier or a browser request schema.
    """

    resource: str
    expires_at: datetime
    scopes: frozenset[str]
    token: str = field(repr=False)

    def header(self, endpoint: str):
        if (
            self.resource != endpoint
            or self.expires_at.tzinfo is None
            or self.expires_at <= datetime.now(timezone.utc)
            or "invoices:read" not in self.scopes
            or not self.token
            or "\r" in self.token
            or "\n" in self.token
        ):
            raise ConnectorError("A current resource-bound read credential is required.")
        return {"Authorization": "Bearer " + self.token}


async def retrieve(
    connection: Connection,
    selected_client: str,
    credential: ResourceCredential,
    transport: httpx.AsyncBaseTransport,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Retrieve one bounded page. Caller persists cursor only after staging commits.

    Transport is injected by the approved gateway; there is deliberately no
    default unrestricted network client. Synthetic tests use MockTransport.
    """
    connection.authorize(selected_client)
    headers = credential.header(connection.endpoint)
    if cursor is not None and (not isinstance(cursor, str) or len(cursor) > 1000):
        raise ConnectorError("Invalid synchronization cursor.")
    request_id = str(uuid4())
    kwargs: dict[str, Any] = {}
    if connection.mode == "mcp":
        headers.update(
            {
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2026-07-28",
                "Mcp-Method": "tools/call",
                "Mcp-Name": connection.approved_tool,
            }
        )
        metadata = {
            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientCapabilities": {},
            "io.modelcontextprotocol/clientInfo": {"name": "gst-easy", "version": "3"},
        }
        kwargs["json"] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": connection.approved_tool,
                "arguments": {"cursor": cursor, "limit": 1000},
                "_meta": metadata,
            },
        }
        method = "POST"
    else:
        headers["Accept"] = "application/json"
        kwargs["params"] = {"limit": 1000, **({"cursor": cursor} if cursor else {})}
        method = "GET"
    payload: Any
    try:
        async with httpx.AsyncClient(
            transport=transport, timeout=15, follow_redirects=False, trust_env=False
        ) as client:
            async with client.stream(method, connection.endpoint, headers=headers, **kwargs) as response:
                if response.status_code == 429:
                    raise ConnectorError("Source rate limit reached. Retry later without advancing the cursor.")
                if response.status_code != 200:
                    raise ConnectorError("Source request failed. Previous records and cursor are preserved.")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > MAX_BYTES:
                        raise ConnectorError("Source response exceeds the supported size.")
                    body.extend(chunk)
                content_type = response.headers.get("content-type", "").split(";")[0]
                if content_type == "text/event-stream" and connection.mode == "mcp":
                    messages = []
                    for event in body.decode().replace("\r\n", "\n").split("\n\n"):
                        data = "\n".join(line[5:].lstrip() for line in event.splitlines() if line.startswith("data:"))
                        if data:
                            message = json.loads(data)
                            if not isinstance(message, dict):
                                raise ConnectorError("Invalid MCP event response.")
                            messages.append(message)
                    finals = [m for m in messages if m.get("id") == request_id]
                    if len(finals) != 1:
                        raise ConnectorError("Source did not return one complete response.")
                    payload = finals[0]
                elif content_type == "application/json":
                    payload = json.loads(body)
                else:
                    raise ConnectorError("Unsupported source response format.")
    except (httpx.HTTPError, UnicodeError, json.JSONDecodeError):
        raise ConnectorError("Source is unavailable or returned invalid data. Retry safely.") from None
    if connection.mode == "mcp":
        if (
            not isinstance(payload, dict)
            or payload.get("jsonrpc") != "2.0"
            or payload.get("id") != request_id
            or "error" in payload
        ):
            raise ConnectorError("Invalid MCP response.")
        result = payload.get("result", {})
        if not isinstance(result, dict) or result.get("resultType", "complete") != "complete" or result.get("isError"):
            raise ConnectorError("MCP tool did not complete successfully.")
        payload = result.get("structuredContent")
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("records"), list)
        or len(payload["records"]) > MAX_ROWS
    ):
        raise ConnectorError("Source must return a bounded records array.")
    next_cursor = payload.get("next_cursor")
    if next_cursor is not None and (not isinstance(next_cursor, str) or len(next_cursor) > 1000):
        raise ConnectorError("Source returned an invalid cursor.")
    if next_cursor is not None and (not next_cursor or next_cursor == cursor):
        raise ConnectorError("Source cursor did not advance. Previous records and cursor are preserved.")
    normalized = preview(connection.source_system, payload["records"])
    return {
        **normalized,
        "next_cursor": next_cursor,
        "source_system": connection.source_system,
        "client_id": selected_client,
    }
