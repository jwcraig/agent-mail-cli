#!/usr/bin/env bash
set -euo pipefail

# Agent Mail CLI installer
# - Installs uv if missing
# - Installs this CLI as a uv tool
#
# Usage:
#   ./scripts/install.sh --yes
#   ./scripts/install.sh --dir "$HOME/agent-mail-cli" --yes
#   curl -fsSL https://raw.githubusercontent.com/jwcraig/agent-mail-cli/main/scripts/install.sh | bash -s -- --yes

REPO_URL="https://github.com/jwcraig/agent-mail-cli"
REPO_NAME="agent-mail-cli"
BRANCH="main"
DEFAULT_CLONE_DIR="$PWD/${REPO_NAME}"
CLONE_DIR=""
YES=0

usage() {
  cat <<USAGE_EOF
Agent Mail CLI installer

Options:
  --dir DIR         Clone/use repo at DIR (default: ./agent-mail-cli)
  --branch NAME     Git branch to clone (default: main)
  -y, --yes         Non-interactive; assume Yes where applicable
  -h, --help        Show help

Examples:
  ./scripts/install.sh --yes
  ./scripts/install.sh --dir "$HOME/agent-mail-cli" --yes
  curl -fsSL https://raw.githubusercontent.com/jwcraig/agent-mail-cli/main/scripts/install.sh | bash -s -- --yes
USAGE_EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) shift; CLONE_DIR="${1:-}" ;;
    --dir=*) CLONE_DIR="${1#*=}" ;;
    --branch) shift; BRANCH="${1:-}" ;;
    --branch=*) BRANCH="${1#*=}" ;;
    -y|--yes) YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
  shift || true
done

info() { printf "\033[1;36m[INFO]\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m[ OK ]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[ERR ]\033[0m %s\n" "$*"; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || return 1; }

ensure_uv() {
  if need_cmd uv; then
    ok "uv already installed"
    return 0
  fi
  if [[ $YES -eq 0 ]]; then
    echo "uv not found. Install uv now? [y/N]"
    read -r answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
      err "uv is required"
      exit 1
    fi
  fi
  info "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
}

ensure_repo() {
  local target_dir
  if [[ -n "$CLONE_DIR" ]]; then
    target_dir="$CLONE_DIR"
  else
    target_dir="$DEFAULT_CLONE_DIR"
  fi

  if [[ -d "$target_dir/.git" ]]; then
    ok "Using existing repo at $target_dir"
  else
    if [[ $YES -eq 0 ]]; then
      echo "Clone $REPO_URL into $target_dir? [y/N]"
      read -r answer
      if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        err "Aborted"
        exit 1
      fi
    fi
    info "Cloning repo"
    git clone --branch "$BRANCH" "$REPO_URL" "$target_dir"
  fi
  echo "$target_dir"
}

main() {
  ensure_uv
  if ! need_cmd git; then
    err "git is required"
    exit 1
  fi

  repo_dir=$(ensure_repo)
  cd "$repo_dir"

  info "Installing agent-mail-cli as a uv tool"
  uv tool install .

  ok "Installed agent-mail CLI"
  echo ""
  echo "Next steps:"
  echo "  agent-mail init --token <TOKEN> --url <URL>"
  echo "  Start the mcp_agent_mail server (this installer does not install it)"
  echo "  agent-mail --help"
}

main
