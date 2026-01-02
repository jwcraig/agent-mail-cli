# Agent Mail CLI

CLI wrapper for `mcp_agent_mail` server with progressive disclosure for token efficiency.

## Why?

MCP servers load **all tool definitions** at session start, regardless of usage. The `mcp-agent-mail` server has 28 tools with verbose descriptions.

This CLI replaces those 28 MCP tools with a single `Bash(agent-mail:*)` permission, reducing context overhead to ~50 tokens. Agents discover commands via `--help` only when needed.

## Credits / Upstream

The original server project is by **Dicklesworthstone**:

```text
https://github.com/Dicklesworthstone/mcp_agent_mail
```

This CLI targets the `jwcraig/mcp_agent_mail` fork of `https://github.com/Dicklesworthstone/mcp_agent_mail`
because it requires MCP tool endpoints that aren’t available in upstream.

```text
https://github.com/jwcraig/mcp_agent_mail
```

This client expects the server to expose MCP tools with these names (grouped roughly by feature):

- Project / agents: `ensure_project`, `register_agent`, `list_projects`, `list_agents`, `whois`, `agent_dependencies`, `delete_agent`, `purge_deleted_agents`
- Sessions / inbox: `macro_start_session`, `fetch_inbox`, `inbox_status`
- Messaging: `send_message`, `reply_message`, `search_messages`, `summarize_thread`, `acknowledge_message`
- File reservations: `file_reservation_paths`, `list_file_reservations`, `renew_file_reservations`, `release_file_reservations`
- Misc: `health_check`, `list_contacts`

## Why not use the server CLI?

The `mcp_agent_mail` repo ships a powerful CLI for **server administration** (setup, config,
exports/archives, guard install, DB inspection). This repo exists for a different use case:

- **Thin client** for agent workflows (send/reply, inbox, reservations, contacts)
- **LLM-friendly surface area** that minimizes tool loading and permissions
- **No server admin commands**, so agents can’t accidentally modify server state

If you’re running the server, use the server CLI. If you’re just coordinating agents against a
running server, use this CLI.

## Requirements

- Python 3.11+
- uv (recommended for installation)

## Installation

```bash
# Local clone (from the repo root)
uv tool install .

# Or from a specific path
REPO_PATH="${REPO_PATH:-$PWD}"
uv tool install "$REPO_PATH"

# Or with uv pip
uv pip install "$REPO_PATH"
```

One-line installer (downloads and installs with uv):

```bash
curl -fsSL "https://raw.githubusercontent.com/jwcraig/agent-mail-cli/main/scripts/install.sh" | bash -s -- --yes
```

Note: this installer only installs the CLI. You must install and run the server
`mcp_agent_mail` server separately.

Server installer (fork):

```bash
curl -fsSL "https://raw.githubusercontent.com/jwcraig/mcp_agent_mail/main/scripts/install.sh" | bash -s -- --yes
```

Upstream server (for reference):

```text
https://github.com/Dicklesworthstone/mcp_agent_mail
```

If `agent-mail` is not found, make sure your PATH includes the uv tool bin directory
(often `~/.local/bin`) and verify with:

```bash
command -v agent-mail
```

## Configuration

Config is stored in `~/.config/agent-mail-cli/`. Initialize it with:

```bash
agent-mail init --token "YOUR_TOKEN_HERE" --url "http://127.0.0.1:8765/mcp/" --timeout 30
```

Manual equivalent:

```bash
# Store bearer token (required when server uses auth)
mkdir -p ~/.config/agent-mail-cli
echo "YOUR_TOKEN_HERE" > ~/.config/agent-mail-cli/token

# Optional: additional settings in config file
echo "url=http://127.0.0.1:8765/mcp/" > ~/.config/agent-mail-cli/config
echo "timeout=30" >> ~/.config/agent-mail-cli/config
```

Environment variables override config files when set:

| Variable             | Default                                 | Description                |
| -------------------- | --------------------------------------- | -------------------------- |
| `AGENT_MAIL_URL`     | `http://127.0.0.1:8765/mcp/`            | Server URL                 |
| `AGENT_MAIL_TOKEN`   | _(from ~/.config/agent-mail-cli/token)_ | Bearer token               |
| `AGENT_MAIL_TIMEOUT` | `30`                                    | Request timeout in seconds |

Quick env-only setup:

```bash
export AGENT_MAIL_URL="http://127.0.0.1:8765/mcp/"
export AGENT_MAIL_TOKEN="YOUR_TOKEN_HERE"
```

You can also copy `.env.example` and edit as needed:

```bash
cp .env.example .env
```

If you want to load it explicitly:

```bash
set -a
source .env
set +a
```

## Server Assumptions

This CLI is a thin HTTP client. It assumes:

- A running MCP Agent Mail HTTP server is reachable at `AGENT_MAIL_URL`
- MCP JSON-RPC tool names and semantics match the server (e.g., `macro_start_session`, `send_message`, `fetch_inbox`)
- Optional bearer auth via `Authorization: Bearer <token>`
- MCP responses include `result.structuredContent` or JSON in `result.content[0].text`

This CLI does **not** read the server’s SQLite database directly; all operations go through server endpoints.

This CLI does not start the server. It expects the server to be available when commands are run, and that
server storage persists across restarts for inboxes and reservations.

## Usage

### Discovery

```bash
agent-mail --help              # List all commands
agent-mail send --help         # Detailed usage for send
agent-mail session --help      # Session management commands
```

### Session Bootstrap

```bash
# Start a session (auto-registers agent, fetches inbox)
agent-mail session start

# With custom agent name
agent-mail session start --name "BlueLake" --task "Working on auth"
```

### Messaging

```bash
# Send a message
agent-mail send --to GreenCastle --from BlueLake \
  --subject "Plan review" --body "Please check the API changes"

# Reply to a message
agent-mail reply 123 --from BlueLake --body "Looks good, approved!"

# Fetch inbox
agent-mail inbox BlueLake
agent-mail inbox BlueLake --limit 5 --urgent --bodies

# Acknowledge a message
agent-mail ack 123 --agent BlueLake

# Search messages
agent-mail search "authentication"

# View/summarize thread
agent-mail thread TKT-123 --summarize
```

### File Reservations

```bash
# Reserve files
agent-mail reserve "api/src/*.js" --agent BlueLake --ttl 7200

# Release reservations
agent-mail release --agent BlueLake

# Renew reservations
agent-mail renew --agent BlueLake --extend 3600
```

### Agent Management

```bash
# Register agent
agent-mail register --name BlueLake --task "Refactoring auth"

# Get agent info
agent-mail whoami BlueLake

# List contacts
agent-mail contacts list BlueLake
```

### Health Check

```bash
agent-mail health
```

## Testing

```bash
uv run pytest
```

Unit vs integration:

```bash
uv run pytest -m unit
uv run pytest -m integration
```

## Troubleshooting

- `agent-mail: command not found` -> ensure your PATH includes the uv tool bin directory
- `401 Unauthorized` -> token mismatch; update `~/.config/agent-mail-cli/token` or `AGENT_MAIL_TOKEN`
- `Connection refused` -> server is not running or `AGENT_MAIL_URL` is wrong

## OS Notes

This README uses bash examples by default. If you're on Windows, use the PowerShell equivalents below.

Config path differences:

- macOS/Linux: `~/.config/agent-mail-cli/`
- Windows (PowerShell): `$Env:APPDATA\\agent-mail-cli\\`

PowerShell equivalents:

```powershell
# Set environment variables
$Env:AGENT_MAIL_URL = "http://127.0.0.1:8765/mcp/"
$Env:AGENT_MAIL_TOKEN = "YOUR_TOKEN_HERE"

# Write token file
$configDir = Join-Path $Env:APPDATA "agent-mail-cli"
New-Item -ItemType Directory -Force -Path $configDir | Out-Null
Set-Content -Path (Join-Path $configDir "token") -Value "YOUR_TOKEN_HERE"
```

Token generation alternatives (cross-platform):

```bash
# Python (macOS/Linux/Windows with python on PATH)
python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
```

Docker Desktop on Windows notes:

- Use WSL2-based Docker Desktop
- Host paths in `docker run -v` may need Windows-style paths or `//c/Users/...` in WSL

## JSON Output

Add `--json` to any command for machine-readable output:

```bash
agent-mail inbox BlueLake --json
agent-mail search "error" --json | jq '.[] | .subject'
```

## Skills (agent-mail)

This repo includes a Codex/Claude skill to help agents use the CLI consistently:

- Path: `skills/agent-mail/SKILL.md`
- Purpose: messaging, file reservations, acknowledgements, and agent cleanup flows
- Uses server-backed MCP HTTP endpoints (no direct SQLite access from this CLI)

Install into the current project:

```bash
agent-mail skill add
```

Install globally (per-user):

```bash
agent-mail skill add --global
```

## Optional Hooks (Claude Code / Gemini)

This repo includes optional hook scripts to make multi-agent coordination smoother.

- Supported: **Claude Code** (template provided via `.claude/settings.local.json`)
- Supported (with wiring on your side): **Gemini CLI** (no template included; hook config differs)
- Not supported: **Codex CLI** (Codex does not currently have hooks — use the skill instead)

Hooks are safe to publish and do not require Beads, but some output is enhanced when Beads (`bd`) is installed.

Hooks live in `hooks/` (Python scripts):

- `check_inbox.py`: rate-limited inbox reminders (supports `urgent` mode)
- `session_start.py`: shows active agents and hints on how to register/resume
- `session_heartbeat.py`: keeps local agent sessions alive during active work
- `post_send.py`: reminder to check acknowledgements
- `multi_agent_guidance.py`: prints a short workflow guide (mentions Beads as optional)

Project path resolution:

- Uses `PROJECT_DIR` or `AGENT_MAIL_PROJECT` if set
- Falls back to `$PWD`

Dependencies:

- Required: `agent-mail` CLI
- Required for hooks: `uv` (uses `uv run python`)
- Optional: `jq`, `bd` (Beads), `ubs` (if you add your own on-save scanner)

Agent-friendly tips:

- Many commands auto-detect the agent from the local session or `AGENT_NAME`
- `agent-mail whoami` and `agent-mail context` are quick ways to reorient

Beads coupling:

- Beads is _not required_ for agent-mail to work.
- When installed, Beads output is shown in `session_start.py` and `multi_agent_guidance.py`.

### Sample Claude Settings

This repo includes a generic Claude settings file with the hooks wired up:

- Path: `.claude/settings.local.json`

To use it in a project:

```bash
agent-mail hooks add
```

The sample uses `$PWD` to resolve the project path and relies on the `hooks/` folder in this repo.
Customize matchers or hook commands as needed.

## Claude Code Integration

1. **Remove MCP server** from `~/.claude/settings.json` (delete `mcp-agent-mail` from `mcpServers`)

2. **Add CLI permission**:

   ```json
   {
     "permissions": {
       "allow": ["Bash(agent-mail:*)"]
     }
   }
   ```

3. **Update CLAUDE.md** (optional):

   ```markdown
   ## Agent Mail CLI

   Multi-agent coordination: `agent-mail --help`
   ```

## Server Setup (Server Repo)

The CLI connects to an `mcp-agent-mail` server. This was built to work well with a
long-running MCP server in Docker.

Note: the following Docker example builds directly from the **server**
`mcp_agent_mail` repository (where the Dockerfile lives), not this CLI repo.

```bash
# Generate a token (save it for the CLI config)
TOKEN=$(openssl rand -hex 32)
echo "$TOKEN" > ~/.config/agent-mail-cli/token

# Build from the server repo (Dockerfile is there)
docker build -t mcp-agent-mail https://github.com/jwcraig/mcp_agent_mail.git#main

# Run with token auth (recommended)
docker run -d --name agent-mail \
  --restart unless-stopped \
  -p 8765:8765 \
  -e HTTP_BEARER_TOKEN="$TOKEN" \
  -e HTTP_RBAC_ENABLED=false \
  -v ~/.config/agent-mail-cli/data:/data/mailbox \
  mcp-agent-mail
```

## Server Overview

The `mcp_agent_mail` project provides the MCP HTTP server. It is a long-running service that:

- Exposes MCP tools/resources over HTTP (default `/mcp/`)
- Stores mailboxes in a Git-backed archive and indexes them in SQLite
- Ships its own admin/developer CLI for server setup, maintenance, and data export

## Keeping the Server Fork Updated

If you run the server from the `jwcraig/mcp_agent_mail` fork, keep it in sync with upstream:

```bash
git remote add upstream https://github.com/Dicklesworthstone/mcp_agent_mail.git
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

If you prefer rebase:

```bash
git fetch upstream
git checkout main
git rebase upstream/main
git push --force-with-lease origin main
```

## Uninstall

```bash
uv tool uninstall agent-mail-cli
```

## License

MIT
