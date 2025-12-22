#!/bin/bash
#
# HtmlGraph SessionEnd Hook for Gemini CLI
# Finalizes session and ensures proper tracking
#

set +e

# Find project root
PROJECT_ROOT="$(pwd)"

# Check if .htmlgraph exists
if [ ! -d "$PROJECT_ROOT/.htmlgraph" ]; then
  exit 0  # Not an HtmlGraph project
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

# Get active session ID
SESSION_ID=$($HTMLGRAPH_CMD session list 2>/dev/null | grep -o 'session-[a-z0-9-]*' | head -1)

if [ -z "$SESSION_ID" ]; then
  exit 0  # No active session
fi

# End the session
$HTMLGRAPH_CMD session end "$SESSION_ID" &> /dev/null

# Provide feedback
echo ""
echo "---"
echo ""
echo "## HtmlGraph Session Ended"
echo ""
echo "**Session:** $SESSION_ID"
echo ""
echo "All activities have been tracked. View the session report:"
echo "\`\`\`bash"
echo "uv run htmlgraph serve"
echo "# Navigate to Sessions view"
echo "\`\`\`"
echo ""
echo "---"
echo ""

exit 0
