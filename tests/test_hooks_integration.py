import os
import shutil
import subprocess

import pytest


def _has_agent_mail():
    return shutil.which("agent-mail") is not None


pytestmark = pytest.mark.integration


def test_check_inbox_integration():
    if not _has_agent_mail():
        pytest.skip("Requires agent-mail CLI on PATH")

    env = os.environ.copy()
    env.setdefault("AGENT_MAIL_URL", "http://127.0.0.1:8765/mcp/")
    env.setdefault("AGENT_MAIL_TIMEOUT", "2")

    # Skip quickly if the server isn't actually reachable.
    try:
        from agent_mail_cli.client import AgentMailClient, AgentMailConfig

        AgentMailClient(
            AgentMailConfig(
                server_url=env["AGENT_MAIL_URL"],
                timeout=float(env["AGENT_MAIL_TIMEOUT"]),
                bearer_token=env.get("AGENT_MAIL_TOKEN"),
            )
        ).health_check()
    except Exception as e:
        pytest.skip(f"agent-mail server not reachable/ready: {e}")

    # Minimal sanity: hook runs and exits cleanly
    env["PROJECT_DIR"] = os.getcwd()
    result = subprocess.run(
        ["uv", "run", "python", "hooks/check_inbox.py", "summary"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
