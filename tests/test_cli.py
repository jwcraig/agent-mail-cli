import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_mail_cli import cli
from agent_mail_cli.client import AgentMailError


class DummyClient:
    def __init__(self):
        self.projects = [{"id": 1, "slug": "proj", "human_key": "/tmp/proj"}]

    def list_projects(self, limit=500):
        return self.projects

    def inbox_status(self, **kwargs):
        return {"scope": "project", "recent_message_count": 0}

    def fetch_inbox(self, **kwargs):
        return []

    def whois(self, **kwargs):
        return {"name": kwargs.get("agent_name")}

    def list_agents(self, project_key, limit=500):
        return [{"name": "BlueLake", "last_active_ts": "2026-01-01T00:00:00Z", "task_description": ""}]


pytestmark = pytest.mark.unit

runner = CliRunner()


def test_inbox_status_project_not_found(monkeypatch, tmp_path):
    dummy = DummyClient()
    dummy.projects = []

    monkeypatch.setattr(cli, "get_client", lambda: dummy)

    result = runner.invoke(cli.app, ["inbox-status", "--project", str(tmp_path), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["error"] == "project_not_found"


def test_inbox_requires_agent(monkeypatch, tmp_path):
    dummy = DummyClient()
    dummy.projects = []
    dummy.list_agents = lambda project_key, limit=500: []
    monkeypatch.setattr(cli, "get_client", lambda: dummy)

    result = runner.invoke(cli.app, ["inbox", "--project", str(tmp_path)])
    assert result.exit_code == 1
    assert "Agent name is required" in result.stdout or "Agent name is required" in result.stderr


def test_whoami_autodetect_from_env(monkeypatch, tmp_path):
    dummy = DummyClient()
    monkeypatch.setattr(cli, "get_client", lambda: dummy)

    env = os.environ.copy()
    env["AGENT_NAME"] = "BlueLake"

    result = runner.invoke(cli.app, ["whoami", "--project", str(tmp_path), "--json"], env=env)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "BlueLake"


def test_init_writes_config_and_token(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    monkeypatch.setattr(cli, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cli, "TOKEN_PATH", config_dir / "token")
    monkeypatch.setattr(cli, "CONFIG_PATH", config_dir / "config")

    result = runner.invoke(
        cli.app,
        [
            "init",
            "--token",
            "TEST_TOKEN",
            "--url",
            "http://127.0.0.1:8765/mcp/",
            "--timeout",
            "5",
        ],
    )

    assert result.exit_code == 0
    assert (config_dir / "token").read_text().strip() == "TEST_TOKEN"
    config_text = (config_dir / "config").read_text()
    assert "url=http://127.0.0.1:8765/mcp/" in config_text
    assert "timeout=5" in config_text
