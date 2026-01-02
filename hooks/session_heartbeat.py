#!/usr/bin/env python3
"""Session heartbeat hook - keeps agent session alive during active work."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def _project_hash(project: str) -> str:
    import hashlib

    return hashlib.sha256(project.encode()).hexdigest()[:12]


def _get_ppid(pid: int) -> int:
    if not shutil.which("ps"):
        return 0
    try:
        proc = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(pid)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return 0
    if proc.returncode != 0:
        return 0
    try:
        return int(proc.stdout.strip())
    except ValueError:
        return 0


def _is_ancestor(candidate_pid: int, current_pid: int) -> bool:
    check_pid = current_pid
    while check_pid > 1:
        if check_pid == candidate_pid:
            return True
        check_pid = _get_ppid(check_pid)
        if check_pid == 0:
            return False
    return False


def main() -> int:
    project = os.environ.get("PROJECT_DIR") or os.environ.get("AGENT_MAIL_PROJECT") or os.getcwd()
    sessions_dir = Path.home() / ".config" / "agent-mail-cli" / "sessions"

    rate_limit_file = Path(f"/tmp/agent-mail-heartbeat-{os.getpid()}")
    try:
        if rate_limit_file.exists():
            last = int(rate_limit_file.read_text().strip() or "0")
            if int(time.time()) - last < 60:
                return 0
    except OSError:
        pass

    if not shutil.which("agent-mail"):
        return 0

    project_hash = _project_hash(project)
    project_sessions_dir = sessions_dir / project_hash
    if not project_sessions_dir.is_dir():
        return 0

    current_pid = os.getpid()
    agent_name = ""

    for session_file in sorted(project_sessions_dir.glob("*.json")):
        try:
            payload = json.loads(session_file.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        session_pid = int(payload.get("pid") or 0)
        if session_pid <= 0:
            continue
        if _is_ancestor(session_pid, current_pid):
            agent_name = session_file.stem
            break

    if not agent_name:
        return 0

    subprocess.run(
        ["agent-mail", "session", "heartbeat", agent_name, "--project", project, "--ttl", "300"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    try:
        rate_limit_file.write_text(str(int(time.time())))
    except OSError:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
