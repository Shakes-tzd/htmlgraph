#!/usr/bin/env bash
# devcontainer-verify.sh — Full verification suite for the htmlgraph devcontainer.
#
# Runs the complete quality gate: build, vet, and the full Go test suite.
# Also exercises a minimal smoke test of the htmlgraph CLI to confirm the
# binary on PATH behaves correctly.
#
# Usage:
#   bash scripts/devcontainer-verify.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

export PATH="${HOME}/.local/bin:${PATH}"

section() {
    printf '\n==> %s\n' "$1"
}

section "go build ./..."
go build ./...

section "go vet ./..."
go vet ./...

section "go test ./... -count=1"
go test ./... -count=1

section "htmlgraph binary smoke test"
if ! command -v htmlgraph >/dev/null 2>&1; then
    echo "htmlgraph binary is not on PATH. Run ./plugin/build.sh first." >&2
    exit 1
fi
htmlgraph --version
htmlgraph help --compact | head -20 || true

section "htmlgraph serve smoke test"
htmlgraph serve --port 8081 >/tmp/htmlgraph-verify-serve.log 2>&1 &
SERVE_PID=$!
trap 'kill "${SERVE_PID}" 2>/dev/null || true' EXIT
sleep 1
if curl --silent --fail --max-time 3 http://127.0.0.1:8081/ >/dev/null; then
    echo "dashboard reachable on port 8081"
else
    echo "dashboard smoke test FAILED — see /tmp/htmlgraph-verify-serve.log" >&2
    cat /tmp/htmlgraph-verify-serve.log >&2 || true
    exit 1
fi
kill "${SERVE_PID}" 2>/dev/null || true
trap - EXIT

echo
echo "Devcontainer verification complete — all checks passed."
