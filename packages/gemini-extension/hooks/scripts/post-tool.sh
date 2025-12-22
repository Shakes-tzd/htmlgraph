#!/bin/bash
#
# HtmlGraph AfterTool Hook for Gemini CLI
# Tracks tool usage for activity attribution
#

set +e

# Find project root
PROJECT_ROOT="$(pwd)"

# Check if .htmlgraph exists
if [ ! -d "$PROJECT_ROOT/.htmlgraph" ]; then
  exit 0  # Not an HtmlGraph project
fi

# Read hook input from stdin (Gemini passes JSON)
INPUT=$(cat)

# Extract tool name from JSON (basic parsing)
TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOOL_NAME" ]; then
  exit 0  # No tool name, skip
fi

# Check if htmlgraph is installed
if ! command -v htmlgraph &> /dev/null; then
  if ! command -v uv &> /dev/null; then
    exit 0
  fi
  HTMLGRAPH_CMD="uv run htmlgraph"
else
  HTMLGRAPH_CMD="htmlgraph"
fi

# Track the tool usage event
# This is a simplified version - just log to events
$HTMLGRAPH_CMD session track-activity \
  --type tool_use \
  --tool "$TOOL_NAME" \
  --timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  &> /dev/null &

exit 0
