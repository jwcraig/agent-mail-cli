#!/usr/bin/env python3
"""Periodic reminder to check inbox (rate-limited)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _sha8(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def _run_agent_mail(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["agent-mail", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _parse_status_fields(payload: dict[str, Any]) -> tuple[str, int, str]:
    scope = (payload.get("scope") or "").strip()
    if scope == "agent":
        count = int(payload.get("unread_count") or 0)
        latest = (payload.get("latest_unread_ts") or "").strip()
    else:
        count = int(payload.get("recent_message_count") or 0)
        latest = (payload.get("latest_recent_ts") or "").strip()
    return scope, count, latest


def _load_json(text: str) -> dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "summary"

    project = os.environ.get("PROJECT_DIR") or os.environ.get("AGENT_MAIL_PROJECT") or os.getcwd()
    project_hash = _sha8(project)

    agent = os.environ.get("AGENT_MAIL_AGENT") or os.environ.get("AGENT_NAME") or ""

    if not shutil.which("agent-mail"):
        return 0

    state_file = ""
    json_text = ""
    json_urgent_text = ""

    if mode == "urgent":
        if not agent:
            return 0
        agent_hash = _sha8(agent)
        state_file = f"/tmp/agent-mail-inbox-urgent-state-{project_hash}-{agent_hash}"
        json_text = _run_agent_mail([
            "inbox-status",
            "--project",
            project,
            "--agent",
            agent,
            "--urgent",
            "--json",
        ])
    else:
        if agent:
            agent_hash = _sha8(agent)
            state_file = f"/tmp/agent-mail-inbox-summary-state-{project_hash}-{agent_hash}"
            json_text = _run_agent_mail([
                "inbox-status",
                "--project",
                project,
                "--agent",
                agent,
                "--json",
            ])
            json_urgent_text = _run_agent_mail([
                "inbox-status",
                "--project",
                project,
                "--agent",
                agent,
                "--urgent",
                "--json",
            ])
        else:
            state_file = f"/tmp/agent-mail-inbox-summary-state-{project_hash}"
            json_text = _run_agent_mail([
                "inbox-status",
                "--project",
                project,
                "--recent-minutes",
                "60",
                "--json",
            ])

    if not json_text:
        return 0

    status = _load_json(json_text)
    scope, count, latest = _parse_status_fields(status)

    urgent_count = 0
    if scope == "agent" and json_urgent_text:
        urgent = _load_json(json_urgent_text)
        _, urgent_count, _ = _parse_status_fields(urgent)

    if not scope or count <= 0:
        return 0

    current_key = f"{mode}|{count}|{latest}|{urgent_count}"
    try:
        if state_file and Path(state_file).exists():
            last_key = Path(state_file).read_text().strip()
            if last_key == current_key:
                return 0
        if state_file:
            Path(state_file).write_text(current_key)
    except OSError:
        pass

    print("")
    if mode == "urgent":
        print(f"🚨 Urgent unread mail: {count} message(s).")
        print(f"   Review: agent-mail inbox {agent} --project {project} --urgent")
        print("")
        return 0

    if scope == "agent":
        if urgent_count > 0:
            print(f"📬 Unread mail: {count} (urgent: {urgent_count}).")
        else:
            print(f"📬 Unread mail: {count}.")
        print(f"   Tip: run: agent-mail inbox {agent} --project {project}")
    else:
        print(f"📬 Recent project mail: {count} message(s) (last hour).")
        print(f"   Tip: run: agent-mail inbox <your-agent-name> --project {project}")
    print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
