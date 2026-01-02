#!/usr/bin/env python3
"""Multi-agent workflow guidance."""

print(
    r"""

## Multi-Agent Workflow Notes

Multiple agents may be working in this repo concurrently.

**First-time setup:**
- `agent-mail init --token <TOKEN> --url <URL>` (writes config files)
- `agent-mail hooks add` (installs Claude hooks for inbox/session help)

**Understanding the two commit streams:**

| Stream | Branch | What goes there | Tool |
|--------|--------|-----------------|------|
| Code | working branch | Your code changes | `git commit` |
| Beads | beads-sync branch | Issue tracking data | `bd sync` |

**bd sync is always safe:**
- Operates in its **own worktree** (completely separate from your working tree)
- Commits to `beads-sync` branch, never touches your working branch, except to update the local .beads/issues.jsonl (expected)
- Only syncs YOUR issue changes, automatically merges others' changes
- Backed by `.beads/issues.jsonl` - run freely without conflicts

**Git commits (your working branch):**
- `git status` shows ALL working tree changes including other agents' files
- **Only stage files YOU modified** - use `git add <specific-files>` not `git add .`
- If unsure what you changed, review your tool call history or ask via agent-mail
- `.beads/issues.jsonl` CAN be committed to working branch as `chore(beads): sync`
  - Useful as a backup snapshot on your feature branch
  - Helps recover from corruption by comparing with beads-sync branch

**File reservations:**
- Check before editing shared files: `agent-mail file_reservations active`
- Reserve files you're working on: `agent-mail reserve <paths> --agent <your-name>`

**Useful quick context:**
- `agent-mail whoami` (uses session/env if available)
- `agent-mail context <your-name>` to summarize inbox + reservations
"""
)
