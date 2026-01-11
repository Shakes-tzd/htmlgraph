---
name: codex
description: Spawn OpenAI Codex for code generation and implementation with sandbox execution
usage: /codex "Your code implementation prompt here"
examples:
  - /codex "Implement JWT authentication middleware"
  - /codex "Add REST API endpoints for user management"
  - /codex "Refactor the database layer to use SQLAlchemy"
cost: Paid (OpenAI)
capabilities:
  - code_generation
  - implementation
  - file_operations
context_window: 128K tokens
---

# Codex Spawner Skill

**CRITICAL: You MUST use Bash to invoke the codex-spawner.py executable. DO NOT do any work yourself.**

## Usage

When the user invokes `/codex "prompt"` or when you need to delegate code implementation to Codex:

1. **Use Bash to invoke the spawner:**

```bash
uv run python "${CLAUDE_PLUGIN_ROOT}/agents/codex-spawner.py" \
  -p "User's implementation prompt" \
  --model gpt-4-turbo \
  --sandbox workspace-write \
  --timeout 180
```

2. **Parse the JSON response:**
   - Success: `{"success": true, "response": "...", "tokens": 123, "agent": "gpt-4"}`
   - Failure: `{"success": false, "error": "...", "agent": "gpt-4"}`

3. **Return the response to the user**

## Sandbox Modes

- `read-only` - Can read files but not modify
- `workspace-write` - Can modify files in workspace (recommended)

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
└─ Bash: codex-spawner.py (level 1)
   └─ Task → codex (level 2)
      └─ HeadlessSpawner.initialize (level 3)
         └─ HeadlessSpawner.setup_sandbox (level 4)
            └─ codex-cli (level 5)
               └─ subprocess.codex (level 6)
```

## Cost

**Paid** - OpenAI charges for Codex/GPT-4 usage. 70% cheaper than using Claude for code generation.

Use this for:
- Code implementation (writing new features)
- File operations (reading, modifying, creating files)
- Refactoring (improving existing code)
- Code generation (scaffolding, boilerplate)

## Example Implementation

```python
import json
import subprocess
import os

# Invoke spawner via Bash
result = subprocess.run([
    "uv", "run", "python",
    f"{os.environ['CLAUDE_PLUGIN_ROOT']}/agents/codex-spawner.py",
    "-p", user_prompt,
    "--model", "gpt-4-turbo",
    "--sandbox", "workspace-write",
    "--timeout", "180"
], capture_output=True, text=True)

# Parse JSON response
response = json.loads(result.stdout)

if response["success"]:
    print(response["response"])
else:
    print(f"Error: {response['error']}")
```

**Remember: Just invoke via Bash. The spawner handles all tracking automatically.**
