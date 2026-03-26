#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../go"
echo "Building htmlgraph-hooks..."
go build -o ../go-plugin/hooks/bin/htmlgraph-hooks ./cmd/htmlgraph/
chmod +x ../go-plugin/hooks/bin/htmlgraph-hooks
echo "Built: packages/go-plugin/hooks/bin/htmlgraph-hooks"
ls -la ../go-plugin/hooks/bin/htmlgraph-hooks
