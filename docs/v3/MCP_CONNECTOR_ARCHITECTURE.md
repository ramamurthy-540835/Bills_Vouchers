# Read-only REST / MCP billing adapters

`app/gst/connectors.py` implements bounded REST and MCP retrieval into the shared
normalizer. Server-owned policy binds client, source, exact HTTPS endpoint and
the approved list_invoices tool. Redirects and arbitrary SQL/tools are excluded.
Credentials are never included in dataclass representations or error messages.
The supplied credential must be unexpired, resource-bound and invoices:read.

The credential object is a broker contract, not a JWT signature verifier. No
browser endpoint accepts it. There is deliberately no unrestricted default
network transport. Production connection activation needs an approved egress
policy, issuer/signature validation and Secret Manager credential broker.

MCP adapter targets the [2026-07-28 protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/index).
It sends per-request version/capabilities, matching method/name headers and
supports JSON and bounded SSE responses under the
[HTTP binding](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http).
It does not implement unrestricted elicitation, sampling, legacy protocol
negotiation or arbitrary tool discovery. The synthetic contract has no custom
parameter-header annotations.

Local MockTransport tests exercise three sources, REST/MCP, SSE, expired/wrong
audience credentials, revocation, tenant mismatch and provider errors.
These are not live MCP interoperability or OAuth certification tests.

Remaining: connection-management UI, persisted consent/revocation and sync
cursor, OAuth discovery/PKCE broker, signed issuer verification, secure egress,
scheduled jobs, retry history and actual customer integration. A cursor must
advance only after authorized staging commits; failures preserve previous data.
No inbound application/MCP token may be forwarded to an unrelated downstream API.
