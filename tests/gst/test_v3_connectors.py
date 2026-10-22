import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.gst.connectors import Connection, ConnectorError, ResourceCredential, retrieve


def fixture(mode='rest', source='vendor'):
    endpoint = 'https://billing.example.test/' + mode
    connection = Connection('tenant-a', source, endpoint, endpoint, mode, True)
    credential = ResourceCredential(endpoint, datetime.now(timezone.utc) + timedelta(minutes=5),
                                    frozenset({'invoices:read'}), 'synthetic-test-token')
    return connection, credential


@pytest.mark.parametrize('mode', ['rest', 'mcp'])
@pytest.mark.parametrize('source', ['vendor', 'customer', 'driver'])
def test_synthetic_sources(mode, source):
    connection, credential = fixture(mode, source)
    def respond(request):
        assert request.headers['authorization'] == 'Bearer synthetic-test-token'
        records = {'records': [{'source_record_id': 'test-1', 'event_type': 'trip' if source == 'driver' else 'invoice',
                                'invoice_total': '118.00'}], 'next_cursor': 'page-2'}
        if mode == 'mcp':
            body = json.loads(request.content)
            assert body['params']['name'] == 'list_invoices'
            assert body['params']['_meta']['io.modelcontextprotocol/protocolVersion'] == '2026-07-28'
            records = {'jsonrpc': '2.0', 'id': body['id'],
                       'result': {'resultType': 'complete', 'structuredContent': records}}
        return httpx.Response(200, json=records)
    result = asyncio.run(retrieve(connection, 'tenant-a', credential, httpx.MockTransport(respond)))
    assert result['financial_records_created'] == 0
    assert len(result['accepted']) == 1
    assert result['next_cursor'] == 'page-2'


def test_cross_tenant_rejected_before_network():
    connection, credential = fixture()
    def forbidden(request):
        pytest.fail('Unauthorized connection made a request')
    with pytest.raises(ConnectorError):
        asyncio.run(retrieve(connection, 'tenant-b', credential, httpx.MockTransport(forbidden)))


@pytest.mark.parametrize('status', [302, 401, 403, 429, 500])
def test_provider_failure_preserves_cursor(status):
    connection, credential = fixture()
    with pytest.raises(ConnectorError):
        asyncio.run(retrieve(connection, 'tenant-a', credential,
                              httpx.MockTransport(lambda request: httpx.Response(status)), 'saved-cursor'))


def test_wrong_audience_expiry_and_revocation():
    connection, credential = fixture()
    for resource, expiry in [('https://other.example.test', credential.expires_at),
                             (connection.endpoint, datetime.now(timezone.utc) - timedelta(seconds=1))]:
        bad = ResourceCredential(resource, expiry, credential.scopes, credential.token)
        with pytest.raises(ConnectorError):
            bad.header(connection.endpoint)
    with pytest.raises(ConnectorError):
        Connection('tenant-a', 'vendor', connection.endpoint, connection.endpoint, 'rest').authorize('tenant-a')
    assert credential.token not in repr(credential)


def test_mcp_sse():
    connection, credential = fixture('mcp')
    def respond(request):
        request_id = json.loads(request.content)['id']
        body = {'jsonrpc': '2.0', 'id': request_id, 'result': {
            'resultType': 'complete', 'structuredContent': {'records': []}}}
        return httpx.Response(200, headers={'content-type': 'text/event-stream'},
                              text=': keepalive\n\ndata: '+json.dumps(body)+'\n\n')
    assert asyncio.run(retrieve(connection, 'tenant-a', credential,
                                httpx.MockTransport(respond)))['accepted'] == []


@pytest.mark.parametrize('event', ['[]', 'null', '42', '"private-provider-text"'])
def test_malformed_sse_is_safe_error_not_unhandled_exception(event):
    connection, credential = fixture('mcp')
    with pytest.raises(ConnectorError, match='Invalid MCP event response') as error:
        asyncio.run(retrieve(connection, 'tenant-a', credential, httpx.MockTransport(
            lambda request: httpx.Response(200, headers={'content-type': 'text/event-stream'},
                                           text='data: '+event+'\n\n'))))
    assert 'private-provider-text' not in str(error.value)


@pytest.mark.parametrize('next_cursor', ['', 'saved-cursor'])
def test_source_cannot_create_nonadvancing_sync_loop(next_cursor):
    connection, credential = fixture()
    with pytest.raises(ConnectorError, match='did not advance'):
        asyncio.run(retrieve(connection, 'tenant-a', credential, httpx.MockTransport(
            lambda request: httpx.Response(200, json={'records': [], 'next_cursor': next_cursor})),
            'saved-cursor'))


def test_oversized_source_response_is_rejected(monkeypatch):
    monkeypatch.setattr('app.gst.connectors.MAX_BYTES', 10)
    connection, credential = fixture()
    with pytest.raises(ConnectorError, match='supported size'):
        asyncio.run(retrieve(connection, 'tenant-a', credential, httpx.MockTransport(
            lambda request: httpx.Response(200, json={'records': []}))))
