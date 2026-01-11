---
name: copilot
description: Spawn GitHub Copilot for GitHub-integrated workflows and git operations
usage: /copilot "Your git/GitHub prompt here"
examples:
  - /copilot "Commit all changes with message: feat: add authentication"
  - /copilot "Create a pull request for the current branch"
  - /copilot "Review the diff and suggest improvements"
cost: Subscription (GitHub Copilot)
capabilities:
  - github_integration
  - git_operations
  - pr_handling
context_window: 100K tokens
---

# Copilot Spawner Skill

**CRITICAL: You MUST use Bash to invoke the copilot-spawner.py executable. DO NOT do any work yourself.**

## Usage

When the user invokes `/copilot "prompt"` or when you need to delegate git/GitHub operations to Copilot:

1. **Use Bash to invoke the spawner:**

```bash
uv run python "${CLAUDE_PLUGIN_ROOT}/agents/copilot-spawner.py" \
  -p "User's git/GitHub prompt" \
  --allow-all-tools \
  --timeout 120
```

2. **Parse the JSON response:**
   - Success: `{"success": true, "response": "...", "tokens": 0, "agent": "github-copilot"}`
   - Failure: `{"success": false, "error": "...", "agent": "github-copilot"}`

3. **Return the response to the user**

## Tool Permissions

- `--allow-all-tools` - Auto-approve all tools (recommended for git operations)
- `--allow-tool shell` - Only allow shell commands
- `--allow-tool git` - Only allow git commands

## Environment Variables (Automatic)

The spawner executable automatically reads:
- `HTMLGRAPH_PARENT_SESSION` - Current session ID
- `HTMLGRAPH_PARENT_EVENT` - Parent event ID (from Bash tool call)
- `HTMLGRAPH_PARENT_QUERY_EVENT` - UserQuery event ID
- `HTMLGRAPH_PARENT_AGENT` - Orchestrator agent name

## Event Tracking (Automatic)

The spawner creates a 4-level event hierarchy:
```
UserQuery (level 0)
└─ Bash: copilot-spawner.py (level 1)
   └─ Task → copilot (level 2)
      └─ HeadlessSpawner.initialize (level 3)
         └─ HeadlessSpawner.setup_auth (level 4)
            └─ copilot-cli (level 5)
               └─ subprocess.copilot (level 6)
```

## Cost

**Subscription** - Included with GitHub Copilot subscription. 60% cheaper than using Claude for git operations.

Use this for:
- Git operations (commit, push, pull, branch, merge)
- GitHub workflows (PR creation, issue management)
- Code review (diff analysis, suggestions)
- Repository management

## Example Implementation

```python
import json
import subprocess
import os

# Invoke spawner via Bash
result = subprocess.run([
    "uv", "run", "python",
    f"{os.environ['CLAUDE_PLUGIN_ROOT']}/agents/copilot-spawner.py",
    "-p", user_prompt,
    "--allow-all-tools",
    "--timeout", "120"
], capture_output=True, text=True)

# Parse JSON response
response = json.loads(result.stdout)

if response["success"]:
    print(response["response"])
else:
    print(f"Error: {response['error']}")
```

**Remember: Just invoke via Bash. The spawner handles all tracking automatically.**
