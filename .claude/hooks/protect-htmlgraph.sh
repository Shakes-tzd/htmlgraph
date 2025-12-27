#!/bin/bash
# Pre-tool-use hook to prevent direct editing of .htmlgraph directory
# Use the SDK instead: sdk.features.create(), sdk.tracks.edit(), etc.

# Read the tool input from stdin
INPUT=$(cat)

# Extract the file_path from the tool input
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Check if the file path is in .htmlgraph directory
if [[ "$FILE_PATH" == *".htmlgraph/"* ]] || [[ "$FILE_PATH" == *"/.htmlgraph/"* ]]; then
    # Block the operation
    cat << 'EOF'
{
  "decision": "block",
  "reason": "Direct editing of .htmlgraph/ files is not allowed. Use the SDK instead:\n\n  from htmlgraph.sdk import SDK\n  sdk = SDK(agent='claude')\n  \n  # For features:\n  sdk.features.create('Title').save()\n  with sdk.features.edit(id) as f: f.status = 'done'\n  \n  # For tracks:\n  with sdk.tracks.edit(id) as t: t.status = 'done'\n  \n  # For other collections:\n  sdk.bugs, sdk.spikes, sdk.sessions, etc."
}
EOF
    exit 0
fi

# Allow all other operations
echo '{"decision": "allow"}'
