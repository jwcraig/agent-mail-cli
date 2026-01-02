import json
from types import SimpleNamespace

import pytest

from agent_mail_cli.client import AgentMailClient, AgentMailConfig, AgentMailError

pytestmark = pytest.mark.unit


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP error")

    def json(self):
        return self._payload


class DummyClient:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        return DummyResponse(self._payload)


def test_call_tool_structured_content(monkeypatch):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "structuredContent": {"result": {"ok": True, "value": 123}}
        },
    }

    monkeypatch.setattr("agent_mail_cli.client.httpx.Client", lambda *args, **kwargs: DummyClient(payload))

    client = AgentMailClient(AgentMailConfig(server_url="http://example", timeout=1))
    result = client.call_tool("health_check", {})
    assert result == {"ok": True, "value": 123}


def test_call_tool_content_text(monkeypatch):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [{"text": json.dumps({"ok": True, "value": 456})}]
        },
    }

    monkeypatch.setattr("agent_mail_cli.client.httpx.Client", lambda *args, **kwargs: DummyClient(payload))

    client = AgentMailClient(AgentMailConfig(server_url="http://example", timeout=1))
    result = client.call_tool("health_check", {})
    assert result == {"ok": True, "value": 456}


def test_call_tool_error(monkeypatch):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"message": "boom", "code": 123, "data": {"x": 1}},
    }

    monkeypatch.setattr("agent_mail_cli.client.httpx.Client", lambda *args, **kwargs: DummyClient(payload))

    client = AgentMailClient(AgentMailConfig(server_url="http://example", timeout=1))
    with pytest.raises(AgentMailError) as exc:
        client.call_tool("health_check", {})

    assert exc.value.code == 123
    assert exc.value.data == {"x": 1}


def test_call_tool_is_error_content_text(monkeypatch):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "isError": True,
            "content": [{"type": "text", "text": "Error calling tool 'x': boom"}],
        },
    }

    monkeypatch.setattr("agent_mail_cli.client.httpx.Client", lambda *args, **kwargs: DummyClient(payload))

    client = AgentMailClient(AgentMailConfig(server_url="http://example", timeout=1))
    with pytest.raises(AgentMailError) as exc:
        client.call_tool("send_message", {})

    assert "boom" in str(exc.value).lower()


def test_call_tool_content_text_non_json(monkeypatch):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [{"type": "text", "text": "plain text response"}],
        },
    }

    monkeypatch.setattr("agent_mail_cli.client.httpx.Client", lambda *args, **kwargs: DummyClient(payload))

    client = AgentMailClient(AgentMailConfig(server_url="http://example", timeout=1))
    result = client.call_tool("health_check", {})
    assert result == "plain text response"
