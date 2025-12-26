#!/bin/bash
# HtmlGraph Session Start Hook
# Installs dependencies and imports transcripts for Claude Code web sessions
set -euo pipefail

# Output async mode for non-blocking startup (5 min timeout)
echo '{"async": true, "asyncTimeout": 300000}'

# Only run on Claude Code web (remote) sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  echo "Not a remote session, skipping setup"
  exit 0
fi

echo "=== HtmlGraph Session Start ==="

# 1. Install uv if not present
if ! command -v uv &> /dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# 2. Install project dependencies
echo "Installing dependencies..."
cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"
uv sync --quiet

# 3. Set up PYTHONPATH for htmlgraph
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export PYTHONPATH="${CLAUDE_PROJECT_DIR}/src/python:${PYTHONPATH:-}"' >> "$CLAUDE_ENV_FILE"
fi

# 4. Auto-link transcripts by git branch
echo "Linking transcripts..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
uv run htmlgraph transcript auto-link --branch "$CURRENT_BRANCH" 2>/dev/null || echo "No transcripts to link"

# 5. List available transcripts for reference
echo "Available transcripts:"
uv run htmlgraph transcript list --limit 3 2>/dev/null || echo "None found"

# 6. Show session context
echo "Loading session context..."
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='claude')
info = sdk.get_session_start_info()
print(f\"Session: {info.get('session_id', 'new')}\")
if info.get('active_work'):
    work = info['active_work']
    print(f\"Active: {work.get('title', 'None')} ({work.get('status', '?')})\")
" 2>/dev/null || true

echo "=== HtmlGraph Ready ==="
