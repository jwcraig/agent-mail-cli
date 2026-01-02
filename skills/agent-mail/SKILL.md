---
name: agent-mail
description: Multi-agent coordination via agent-mail CLI. Use when communicating with other agents, coordinating file access, sending/receiving messages, checking inbox, or reserving files. Triggers on "send message to agent", "check inbox", "reserve files", "coordinate with other agents", multi-agent workflows, file reservations, acknowledgements, "list agents", "delete agent", "clean up agents", "purge agents".
---

# Agent Mail CLI

Fast CLI for multi-agent coordination. Uses the server-backed MCP HTTP endpoints (no direct SQLite access).

## Quick Reference

```bash
agent-mail --help              # All commands
agent-mail <cmd> --help        # Command details
agent-mail init                # Create config directory and files
```

## Core Commands

### Messaging (HTTP API)
```bash
agent-mail send --to Agent --from Me --subject "..." --body "..."
agent-mail reply MESSAGE_ID --from Me --body "..."
agent-mail inbox AGENT [--limit N] [--urgent] [--bodies]
agent-mail ack MESSAGE_ID --agent AGENT
agent-mail search "query" [--limit N]
agent-mail thread THREAD_ID [--summarize]
```

### File Reservations
```bash
# Server-backed (HTTP API via MCP server)
agent-mail reserve "path/*.js" --agent AGENT [--ttl 3600]
agent-mail renew --agent AGENT [--extend 1800]
agent-mail release --agent AGENT [paths...]

# Queries
agent-mail file_reservations active PROJECT
agent-mail file_reservations soon PROJECT [--minutes 30]
agent-mail file_reservations list PROJECT [--all]
```

### Acknowledgements
```bash
agent-mail acks pending PROJECT AGENT
agent-mail acks overdue PROJECT AGENT [--hours 24]
agent-mail list-acks --project PROJECT --agent AGENT
```

### Agent/Project Management
```bash
# Registration
agent-mail register --task "..."              # First time (name auto-assigned)
agent-mail register --resume --task "..."     # Resume most recent agent
agent-mail register --as AGENT --task "..."   # Resume specific agent

# Quick orientation
agent-mail whoami                             # Auto-detects agent when possible
agent-mail context AGENT                      # Resume context summary

# Context & info
agent-mail context AGENT                      # Full context for resuming work
agent-mail whoami AGENT                       # Agent profile + recent commits
agent-mail list-agents                        # All agents in project
agent-mail contacts list AGENT
agent-mail list-projects
agent-mail health

# Cleanup (HTTP API)
agent-mail delete AGENT [--force]             # Soft-delete (renames to Deleted-*)
agent-mail purge [--dry-run]                  # Hard-delete all soft-deleted agents
```

### Session Management (Local)
```bash
# Sessions prevent two agents using the same identity concurrently
agent-mail session status [AGENT]            # Check session status (all or specific)
agent-mail session heartbeat AGENT [--ttl N] # Extend session TTL (default 300s)
agent-mail session end AGENT                 # Release session lock

# Register with session control
agent-mail register --as AGENT --force       # Override existing session
agent-mail register --as AGENT --ttl 600     # Set custom session TTL
```

## Notes

- Project auto-detected from `$PWD`; override with `--project /path`
- Agent names are adjective+noun (BlueLake, GreenCastle, RedStone)
- Messages support Markdown
- All commands talk to the server over HTTP; this CLI does not read the server DB directly
- Sessions are stored locally in `~/.config/agent-mail-cli/sessions/`
- Heartbeat runs automatically via PostToolUse hook (every 60s during active work)
- Initialize config with `agent-mail init --token ... --url ...`
- Optional (Claude Code): install hooks with `agent-mail hooks add` (uses `uv run python`)
