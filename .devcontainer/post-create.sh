#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

export PATH="${HOME}/.local/bin:${PATH}"

echo "==> Installing AI agent CLIs..."
npm install -g --no-fund --no-audit \
    @anthropic-ai/claude-code \
    @google/gemini-cli \
    @openai/codex

echo "==> Building htmlgraph from source..."
./plugin/build.sh

echo "==> Running quality gates..."
go build ./...
go vet ./...

echo
echo "==> Installed tool versions:"
go version
node --version
npm --version
claude --version || true
codex --version || true
gemini --version || true
htmlgraph --version || true

cat <<'EOF'

Devcontainer bootstrap complete.

This is a source-development environment — every change you make to
cmd/, internal/, or plugin/ can be rebuilt with `htmlgraph build`.

Next steps:
- Authenticate the CLIs once (stored in persistent volumes):
    claude           # OAuth browser login (or API key)
    codex
    gemini
- Launch Claude Code in dev mode so it loads the plugin from source:
    htmlgraph claude --dev
- Start the dashboard:
    htmlgraph serve
    # http://localhost:8080
- Run the full test suite on demand:
    bash scripts/devcontainer-verify.sh

Persistent volumes mounted:
  /home/vscode/.claude         — Claude Code credentials
  /home/vscode/.codex          — Codex credentials
  /home/vscode/.gemini         — Gemini credentials
  /home/vscode/.local          — htmlgraph binary + version metadata
  <workspace>/.htmlgraph       — devcontainer-only work item state
                                 (isolated from your host .htmlgraph/)
EOF
