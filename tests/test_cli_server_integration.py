import json
import os
import time
import uuid

import pytest
from typer.testing import CliRunner

from agent_mail_cli import cli
from agent_mail_cli.client import AgentMailClient, AgentMailConfig

pytestmark = pytest.mark.integration

runner = CliRunner()


def _integration_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("AGENT_MAIL_URL", "http://127.0.0.1:8765/mcp/")
    env.setdefault("AGENT_MAIL_TIMEOUT", "2")
    if os.environ.get("AGENT_MAIL_TOKEN"):
        env.setdefault("AGENT_MAIL_TOKEN", os.environ["AGENT_MAIL_TOKEN"])
    return env


def _skip_unless_server_ready(env: dict[str, str]) -> None:
    cfg = AgentMailConfig(
        server_url=env["AGENT_MAIL_URL"],
        timeout=float(env.get("AGENT_MAIL_TIMEOUT", "2")),
        bearer_token=env.get("AGENT_MAIL_TOKEN"),
    )
    client = AgentMailClient(cfg)
    try:
        client.health_check()
    except Exception as e:
        pytest.skip(f"agent-mail server not reachable/ready: {e}")


def _parse_json(result) -> object:
    assert result.stdout, f"expected stdout, got: {result.stderr}"
    return json.loads(result.stdout)


def test_cli_health_integration(monkeypatch, tmp_path):
    env = _integration_env()
    _skip_unless_server_ready(env)

    result = runner.invoke(cli.app, ["health", "--json"], env=env)
    assert result.exit_code == 0, result.stdout + result.stderr

    payload = _parse_json(result)
    assert isinstance(payload, dict)
    assert payload.get("status") in {"ok", "healthy"}


def test_cli_send_ack_and_reservations_integration(monkeypatch, tmp_path):
    env = _integration_env()
    _skip_unless_server_ready(env)

    # Keep session tracking hermetic.
    monkeypatch.setattr(cli, "SESSIONS_DIR", tmp_path / "sessions")

    project = str(tmp_path / "proj")
    run_id = uuid.uuid4().hex[:8]

    subject = f"pytest integration {run_id}"

    # Register both agents (also ensures the project exists server-side).
    res_a = runner.invoke(
        cli.app,
        ["register", "--task", "pytest integration", "--ttl", "60", "--project", project, "--json"],
        env=env,
    )
    assert res_a.exit_code == 0, res_a.stdout + res_a.stderr
    agent_a = _parse_json(res_a)["name"]

    res_b = runner.invoke(
        cli.app,
        ["register", "--task", "pytest integration", "--ttl", "60", "--project", project, "--json"],
        env=env,
    )
    assert res_b.exit_code == 0, res_b.stdout + res_b.stderr
    agent_b = _parse_json(res_b)["name"]

    # Send an ack-required message from A to B.
    send_res = runner.invoke(
        cli.app,
        [
            "send",
            "--to",
            agent_b,
            "--subject",
            subject,
            "--body",
            f"hello from {agent_a}",
            "--from",
            agent_a,
            "--ack",
            "--project",
            project,
            "--json",
        ],
        env=env,
    )
    assert send_res.exit_code == 0, send_res.stdout + send_res.stderr

    # Poll inbox briefly (some servers may process asynchronously).
    inbox_msgs: list[dict] = []
    for _ in range(6):
        inbox_res = runner.invoke(
            cli.app,
            ["inbox", agent_b, "--project", project, "--json"],
            env=env,
        )
        assert inbox_res.exit_code == 0, inbox_res.stdout + inbox_res.stderr
        inbox_msgs = _parse_json(inbox_res)
        assert isinstance(inbox_msgs, list)
        if any(m.get("subject") == subject for m in inbox_msgs):
            break
        time.sleep(0.2)

    msg = next((m for m in inbox_msgs if m.get("subject") == subject), None)
    assert msg is not None, f"message not found in inbox: {inbox_msgs!r}"
    msg_id = int(msg["id"])

    # Verify it appears in pending acks.
    pending_res = runner.invoke(
        cli.app,
        ["acks", "pending", project, agent_b, "--json"],
        env=env,
    )
    assert pending_res.exit_code == 0, pending_res.stdout + pending_res.stderr
    pending = _parse_json(pending_res)
    assert isinstance(pending, list)
    assert any(int(p["id"]) == msg_id for p in pending)

    # Ack it.
    ack_res = runner.invoke(
        cli.app,
        ["ack", str(msg_id), "--agent", agent_b, "--project", project, "--json"],
        env=env,
    )
    assert ack_res.exit_code == 0, ack_res.stdout + ack_res.stderr

    # Pending should no longer include this message.
    pending_res_2 = runner.invoke(
        cli.app,
        ["acks", "pending", project, agent_b, "--json"],
        env=env,
    )
    assert pending_res_2.exit_code == 0, pending_res_2.stdout + pending_res_2.stderr
    pending_2 = _parse_json(pending_res_2)
    assert isinstance(pending_2, list)
    assert not any(int(p["id"]) == msg_id for p in pending_2)

    # Exercise reservations: reserve, list active, then release.
    reserve_res = runner.invoke(
        cli.app,
        ["reserve", "src/agent_mail_cli/cli.py", "--agent", agent_a, "--project", project, "--json"],
        env=env,
    )
    assert reserve_res.exit_code == 0, reserve_res.stdout + reserve_res.stderr

    active_res = runner.invoke(
        cli.app,
        ["file_reservations", "active", project, "--json"],
        env=env,
    )
    assert active_res.exit_code == 0, active_res.stdout + active_res.stderr
    active = _parse_json(active_res)
    assert isinstance(active, list)
    assert any(r.get("agent") == agent_a for r in active)

    release_res = runner.invoke(
        cli.app,
        ["release", "--agent", agent_a, "--project", project, "--json"],
        env=env,
    )
    assert release_res.exit_code == 0, release_res.stdout + release_res.stderr
