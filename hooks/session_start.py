#!/usr/bin/env python3
"""Session start hook - shows agent/beads context without auto-registering."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except OSError:
        return 1, ""
    return proc.returncode, (proc.stdout or "").strip()


def _run_json(cmd: list[str]) -> list[dict]:
    code, out = _run(cmd)
    if code != 0 or not out:
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return []


def main() -> int:
    project = os.environ.get("PROJECT_DIR") or os.environ.get("AGENT_MAIL_PROJECT") or os.getcwd()

    print("")
    print("═══════════════════════════════════════════════════")
    print("🤝 Multi-Agent Coordination")
    print("═══════════════════════════════════════════════════")

    if not shutil.which("agent-mail"):
        print("")
        print("agent-mail CLI not found. Install/enable it to use coordination features.")
        print("")
        return 0

    agents = _run_json(["agent-mail", "list-agents", "--project", project, "--json"])

    if not agents:
        print("")
        print("No agents registered yet. To start coordinating:")
        print(f"  agent-mail register --task 'your task description' --project '{project}'")
        print("")
        return 0

    print("")
    print("👥 Agents with assigned work:")
    print("")

    _run(["agent-mail", "list-agents", "--project", project])
    print("")

    beads_available = shutil.which("bd") is not None and Path(project, ".beads").exists()

    for agent in agents[:8]:
        name = (agent.get("name") or "").strip()
        task = (agent.get("task_description") or "").strip()
        if not name:
            continue
        print(f"   {name}: {task}")
        if beads_available:
            rows = _run_json([
                "bd",
                "list",
                f"--assignee={name}",
                "--status=in_progress",
                "--json",
            ])
            for row in rows[:3]:
                issue_id = row.get("id")
                title = row.get("title")
                status = row.get("status")
                if issue_id and title and status:
                    print(f"   └─ {issue_id}: {title} [{status}]")

    print("")
    print("📋 Commands:")
    print("")
    print("  Resume as existing agent:")
    print(f"    agent-mail register --as <AgentName> --task 'continuing work' --project '{project}'")
    print("    bd list --assignee=<AgentName> --status=in_progress  # optional (Beads)")
    print("")
    print("  Register new agent (only if starting new coordinated work):")
    print(f"    agent-mail register --task 'description' --project '{project}'")
    print("    bd update <issue> --assignee=<YourAgentName> --status=in_progress  # optional (Beads)")
    print("")

    code, reservations = _run(["agent-mail", "file_reservations", "active", project])
    if code == 0 and reservations and "No active" not in reservations:
        print("📁 Active File Reservations:")
        for line in reservations.splitlines()[:10]:
            print(line)
        print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
