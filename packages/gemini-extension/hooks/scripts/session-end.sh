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

export HTMLGRAPH_AGENT=gemini

# Get active session ID
SESSION_ID=$($HTMLGRAPH_CMD session list 2>/dev/null | grep -o 'session-[a-z0-9-]*' | head -1)

if [ -z "$SESSION_ID" ]; then
  exit 0  # No active session
fi

# Optional handoff prompt (interactive shells only)
HANDOFF_NOTES="${HTMLGRAPH_HANDOFF_NOTES:-}"
HANDOFF_RECOMMEND="${HTMLGRAPH_HANDOFF_RECOMMEND:-}"
HANDOFF_BLOCKERS_RAW="${HTMLGRAPH_HANDOFF_BLOCKERS:-}"

if [ -t 0 ]; then
  if [ -z "$HANDOFF_NOTES" ]; then
    read -r -p "Handoff notes (optional): " HANDOFF_NOTES
  fi
  if [ -z "$HANDOFF_RECOMMEND" ]; then
    read -r -p "Recommended next steps (optional): " HANDOFF_RECOMMEND
  fi
  if [ -z "$HANDOFF_BLOCKERS_RAW" ]; then
    read -r -p "Blockers (comma-separated, optional): " HANDOFF_BLOCKERS_RAW
  fi
fi

# Build session end command with handoff context
cmd=($HTMLGRAPH_CMD session end "$SESSION_ID")
if [ -n "$HANDOFF_NOTES" ]; then
  cmd+=("--notes" "$HANDOFF_NOTES")
fi
if [ -n "$HANDOFF_RECOMMEND" ]; then
  cmd+=("--recommend" "$HANDOFF_RECOMMEND")
fi
if [ -n "$HANDOFF_BLOCKERS_RAW" ]; then
  IFS=',' read -r -a blockers <<< "$HANDOFF_BLOCKERS_RAW"
  for blocker in "${blockers[@]}"; do
    trimmed="$(echo "$blocker" | xargs)"
    if [ -n "$trimmed" ]; then
      cmd+=("--blocker" "$trimmed")
    fi
  done
fi

# End the session
"${cmd[@]}" &> /dev/null

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
