import os
from pathlib import Path

import pytest

import importlib.util


def _load_hook(name: str):
    path = Path(__file__).resolve().parents[1] / "hooks" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


check_inbox = _load_hook("check_inbox")
session_heartbeat = _load_hook("session_heartbeat")

pytestmark = pytest.mark.unit


def test_check_inbox_no_agent_mail(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(check_inbox.shutil, "which", lambda _: None)

    assert check_inbox.main() == 0


def test_check_inbox_parses_status(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("AGENT_NAME", "BlueLake")
    monkeypatch.setattr(check_inbox.shutil, "which", lambda _: "/usr/bin/agent-mail")

    def fake_run(args):
        return '{"scope":"agent","unread_count":2,"latest_unread_ts":"2026-01-02T00:00:00Z"}'

    monkeypatch.setattr(check_inbox, "_run_agent_mail", lambda args: fake_run(args))

    assert check_inbox.main() == 0


def test_session_heartbeat_rate_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(session_heartbeat.shutil, "which", lambda _: "/usr/bin/agent-mail")

    # Avoid touching real home directory.
    monkeypatch.setattr(session_heartbeat.Path, "home", lambda: tmp_path)

    # Keep the test hermetic: don't depend on ps ancestry walking.
    monkeypatch.setattr(session_heartbeat, "_is_ancestor", lambda *_: True)

    calls: list[list[str]] = []

    class DummyProc:
        def __init__(self):
            self.returncode = 0
            self.stdout = ""
            self.stderr = ""

    monkeypatch.setattr(
        session_heartbeat.subprocess,
        "run",
        lambda args, **kwargs: (calls.append(list(args)) or DummyProc()),
    )

    # Build a minimal session file so the hook finds an agent name to heartbeat.
    sessions_dir = tmp_path / ".config" / "agent-mail-cli" / "sessions"
    project_hash = session_heartbeat._project_hash(str(tmp_path))
    project_dir = sessions_dir / project_hash
    project_dir.mkdir(parents=True, exist_ok=True)

    session_file = project_dir / "BlueLake.json"
    session_file.write_text('{"pid": %d}' % os.getpid())

    # First call should invoke the heartbeat command.
    assert session_heartbeat.main() == 0
    assert calls
    assert calls[-1][:4] == ["agent-mail", "session", "heartbeat", "BlueLake"]

    # Second call should be rate-limited (no additional subprocess calls).
    call_count = len(calls)
    assert session_heartbeat.main() == 0
    assert len(calls) == call_count
