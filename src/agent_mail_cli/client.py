"""HTTP client for mcp-agent-mail server."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

# Default config file locations
CONFIG_DIR = os.path.expanduser("~/.config/agent-mail-cli")
TOKEN_FILE = os.path.join(CONFIG_DIR, "token")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config")


def _read_token_file() -> str | None:
    """Read bearer token from config file."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE) as f:
                token = f.read().strip()
                if token:
                    return token
        except OSError:
            pass
    return None


def _read_config_file() -> dict[str, str]:
    """Read config file (simple key=value format)."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip()
        except OSError:
            pass
    return config


@dataclass
class AgentMailConfig:
    """Configuration for agent-mail server connection."""

    server_url: str = "http://127.0.0.1:8765/mcp/"
    timeout: float = 30.0
    bearer_token: str | None = None

    @classmethod
    def from_env(cls) -> "AgentMailConfig":
        """Load configuration from config files, falling back to environment variables.

        Config sources (in priority order):
        1. Environment variables (AGENT_MAIL_URL, AGENT_MAIL_TIMEOUT, AGENT_MAIL_TOKEN)
        2. Config files (~/.config/agent-mail-cli/token, ~/.config/agent-mail-cli/config)
        3. Default values
        """
        file_config = _read_config_file()
        file_token = _read_token_file()

        return cls(
            server_url=os.environ.get(
                "AGENT_MAIL_URL",
                file_config.get("url", "http://127.0.0.1:8765/mcp/")
            ),
            timeout=float(os.environ.get(
                "AGENT_MAIL_TIMEOUT",
                file_config.get("timeout", "30")
            )),
            bearer_token=os.environ.get("AGENT_MAIL_TOKEN") or file_token,
        )


class AgentMailError(Exception):
    """Error from agent-mail server."""

    def __init__(self, message: str, code: int | None = None, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data


class AgentMailClient:
    """Client for communicating with mcp-agent-mail server via JSON-RPC."""

    def __init__(self, config: AgentMailConfig | None = None):
        self.config = config or AgentMailConfig.from_env()
        self._request_id = 0

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for request."""
        headers = {"Content-Type": "application/json"}
        if self.config.bearer_token:
            headers["Authorization"] = f"Bearer {self.config.bearer_token}"
        return headers

    def _next_id(self) -> int:
        """Get next request ID."""
        self._request_id += 1
        return self._request_id

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call an MCP tool via JSON-RPC.

        Args:
            tool_name: Name of the tool (e.g., "send_message", "fetch_inbox")
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            AgentMailError: If the server returns an error
            httpx.HTTPError: If the HTTP request fails
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }

        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(
                self.config.server_url,
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

        if "error" in result:
            error = result["error"]
            raise AgentMailError(
                message=error.get("message", "Unknown error"),
                code=error.get("code"),
                data=error.get("data"),
            )

        # Extract actual data from MCP response wrapper
        mcp_result = result.get("result", {})
        if isinstance(mcp_result, dict):
            # Some MCP servers signal errors via `result.isError` + text content.
            if mcp_result.get("isError"):
                message = ""
                if "structuredContent" in mcp_result:
                    structured = mcp_result.get("structuredContent")
                    if isinstance(structured, dict):
                        message = str(structured.get("message") or structured.get("error") or "")
                if not message and mcp_result.get("content"):
                    try:
                        message = str(mcp_result["content"][0].get("text", "")).strip()
                    except Exception:
                        message = ""
                raise AgentMailError(
                    message=message or f"Tool '{tool_name}' failed",
                    data=mcp_result,
                )

            # Prefer structuredContent, fall back to parsing content[0].text
            if "structuredContent" in mcp_result:
                structured = mcp_result["structuredContent"]
                # Some responses wrap in "result", others don't
                if isinstance(structured, dict) and "result" in structured:
                    return structured["result"]
                return structured
            elif "content" in mcp_result and mcp_result["content"]:
                # Parse JSON from text content
                text = mcp_result["content"][0].get("text", "")
                if not text:
                    return {}
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    # Some tools return human-readable text; return it as-is.
                    return text
        return mcp_result

    # Convenience methods for common operations

    def ensure_project(self, human_key: str) -> dict[str, Any]:
        """Ensure a project exists."""
        return self.call_tool("ensure_project", {"human_key": human_key})

    def register_agent(
        self,
        project_key: str,
        program: str,
        model: str,
        name: str | None = None,
        task_description: str = "",
    ) -> dict[str, Any]:
        """Register an agent in a project."""
        args = {
            "project_key": project_key,
            "program": program,
            "model": model,
            "task_description": task_description,
        }
        if name:
            args["name"] = name
        return self.call_tool("register_agent", args)

    def start_session(
        self,
        human_key: str,
        program: str,
        model: str,
        agent_name: str | None = None,
        task_description: str = "",
        inbox_limit: int = 10,
    ) -> dict[str, Any]:
        """Start a session (ensure project, register agent, fetch inbox)."""
        args = {
            "human_key": human_key,
            "program": program,
            "model": model,
            "task_description": task_description,
            "inbox_limit": inbox_limit,
        }
        if agent_name:
            args["agent_name"] = agent_name
        return self.call_tool("macro_start_session", args)

    def fetch_inbox(
        self,
        project_key: str,
        agent_name: str,
        limit: int = 20,
        urgent_only: bool = False,
        since_ts: str | None = None,
        include_bodies: bool = False,
    ) -> list[dict[str, Any]]:
        """Fetch inbox messages."""
        args = {
            "project_key": project_key,
            "agent_name": agent_name,
            "limit": limit,
            "urgent_only": urgent_only,
            "include_bodies": include_bodies,
        }
        if since_ts:
            args["since_ts"] = since_ts
        return self.call_tool("fetch_inbox", args)

    def inbox_status(
        self,
        project_key: str,
        agent_name: str | None = None,
        *,
        since_ts: str | None = None,
        urgent_only: bool = False,
        recent_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Fetch lightweight inbox status (counts/timestamps only)."""
        args: dict[str, Any] = {
            "project_key": project_key,
            "urgent_only": urgent_only,
        }
        if agent_name:
            args["agent_name"] = agent_name
        if since_ts:
            args["since_ts"] = since_ts
        if recent_seconds is not None:
            args["recent_seconds"] = int(recent_seconds)
        return self.call_tool("inbox_status", args)

    def send_message(
        self,
        project_key: str,
        sender_name: str,
        to: list[str],
        subject: str,
        body_md: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        importance: str = "normal",
        ack_required: bool = False,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a message."""
        args = {
            "project_key": project_key,
            "sender_name": sender_name,
            "to": to,
            "subject": subject,
            "body_md": body_md,
            "importance": importance,
            "ack_required": ack_required,
        }
        if cc:
            args["cc"] = cc
        if bcc:
            args["bcc"] = bcc
        if thread_id:
            args["thread_id"] = thread_id
        return self.call_tool("send_message", args)

    def reply_message(
        self,
        project_key: str,
        message_id: int,
        sender_name: str,
        body_md: str,
        to: list[str] | None = None,
        cc: list[str] | None = None,
    ) -> dict[str, Any]:
        """Reply to a message."""
        args = {
            "project_key": project_key,
            "message_id": message_id,
            "sender_name": sender_name,
            "body_md": body_md,
        }
        if to:
            args["to"] = to
        if cc:
            args["cc"] = cc
        return self.call_tool("reply_message", args)

    def acknowledge_message(
        self, project_key: str, agent_name: str, message_id: int
    ) -> dict[str, Any]:
        """Acknowledge a message."""
        return self.call_tool(
            "acknowledge_message",
            {
                "project_key": project_key,
                "agent_name": agent_name,
                "message_id": message_id,
            },
        )

    def search_messages(
        self, project_key: str, query: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Search messages."""
        return self.call_tool(
            "search_messages",
            {"project_key": project_key, "query": query, "limit": limit},
        )

    def summarize_thread(
        self,
        project_key: str,
        thread_id: str,
        include_examples: bool = False,
        llm_mode: bool = True,
    ) -> dict[str, Any]:
        """Summarize a thread."""
        return self.call_tool(
            "summarize_thread",
            {
                "project_key": project_key,
                "thread_id": thread_id,
                "include_examples": include_examples,
                "llm_mode": llm_mode,
            },
        )

    def reserve_paths(
        self,
        project_key: str,
        agent_name: str,
        paths: list[str],
        ttl_seconds: int = 3600,
        exclusive: bool = True,
        reason: str = "",
    ) -> dict[str, Any]:
        """Reserve file paths."""
        return self.call_tool(
            "file_reservation_paths",
            {
                "project_key": project_key,
                "agent_name": agent_name,
                "paths": paths,
                "ttl_seconds": ttl_seconds,
                "exclusive": exclusive,
                "reason": reason,
            },
        )

    def release_reservations(
        self,
        project_key: str,
        agent_name: str,
        paths: list[str] | None = None,
    ) -> dict[str, Any]:
        """Release file reservations."""
        args = {"project_key": project_key, "agent_name": agent_name}
        if paths:
            args["paths"] = paths
        return self.call_tool("release_file_reservations", args)

    def renew_reservations(
        self,
        project_key: str,
        agent_name: str,
        extend_seconds: int = 1800,
    ) -> dict[str, Any]:
        """Renew file reservations."""
        return self.call_tool(
            "renew_file_reservations",
            {
                "project_key": project_key,
                "agent_name": agent_name,
                "extend_seconds": extend_seconds,
            },
        )

    def whois(
        self,
        project_key: str,
        agent_name: str,
        include_recent_commits: bool = True,
    ) -> dict[str, Any]:
        """Get agent info."""
        return self.call_tool(
            "whois",
            {
                "project_key": project_key,
                "agent_name": agent_name,
                "include_recent_commits": include_recent_commits,
            },
        )

    def list_contacts(self, project_key: str, agent_name: str) -> list[dict[str, Any]]:
        """List agent contacts."""
        return self.call_tool(
            "list_contacts",
            {"project_key": project_key, "agent_name": agent_name},
        )

    def health_check(self) -> dict[str, Any]:
        """Check server health."""
        return self.call_tool("health_check", {})

    # --- CLI parity helpers (avoid direct DB access) ---

    def list_projects(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.call_tool("list_projects", {"limit": limit})

    def list_agents(self, project_key: str, limit: int = 500) -> list[dict[str, Any]]:
        return self.call_tool("list_agents", {"project_key": project_key, "limit": limit})

    def list_file_reservations(
        self,
        project_key: str,
        *,
        active_only: bool = True,
        expiring_within_minutes: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        args: dict[str, Any] = {
            "project_key": project_key,
            "active_only": active_only,
            "limit": limit,
        }
        if expiring_within_minutes is not None:
            args["expiring_within_minutes"] = expiring_within_minutes
        return self.call_tool("list_file_reservations", args)

    def list_acks_pending(self, project_key: str, agent_name: str, limit: int = 20) -> list[dict[str, Any]]:
        return self.call_tool(
            "list_acks_pending",
            {"project_key": project_key, "agent_name": agent_name, "limit": limit},
        )

    def list_acks_overdue(
        self,
        project_key: str,
        agent_name: str,
        *,
        hours: int = 24,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return self.call_tool(
            "list_acks_overdue",
            {"project_key": project_key, "agent_name": agent_name, "hours": hours, "limit": limit},
        )

    def agent_dependencies(self, project_key: str, agent_name: str) -> dict[str, Any]:
        return self.call_tool("agent_dependencies", {"project_key": project_key, "agent_name": agent_name})

    def delete_agent(self, project_key: str, agent_name: str, *, force: bool = False, dry_run: bool = False) -> dict[str, Any]:
        return self.call_tool(
            "delete_agent",
            {"project_key": project_key, "agent_name": agent_name, "force": force, "dry_run": dry_run},
        )

    def purge_deleted_agents(self, project_key: str, *, dry_run: bool = False) -> dict[str, Any]:
        return self.call_tool(
            "purge_deleted_agents",
            {"project_key": project_key, "dry_run": dry_run},
        )
