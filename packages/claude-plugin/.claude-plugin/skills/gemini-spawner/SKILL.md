---
name: gemini
description: Spawn Google Gemini 2.0-Flash for FREE exploratory research and batch analysis
usage: /gemini "Your exploration prompt here"
examples:
  - /gemini "Analyze all authentication patterns in the codebase"
  - /gemini "Find all API endpoints and document them"
  - /gemini "Review the test coverage and suggest improvements"
cost: FREE
capabilities:
  - exploration
  - analysis
  - batch_processing
context_window: 2M tokens
---

# Gemini Spawner Skill

**CRITICAL: You MUST use Bash to invoke the gemini-spawner.py executable. DO NOT do any work yourself.**

## Usage

When the user invokes `/gemini "prompt"` or when you need to delegate exploration work to Gemini:

1. **Use Bash to invoke the spawner:**

```bash
uv run python "${CLAUDE_PLUGIN_ROOT}/agents/gemini-spawner.py" \
  -p "User's exploration prompt" \
  --model gemini-2.0-flash \
  --timeout 120
```

2. **Parse the JSON response:**
   - Success: `{"success": true, "response": "...", "tokens": 123, "agent": "gemini-2.0-flash"}`
   - Failure: `{"success": false, "error": "...", "agent": "gemini-2.0-flash"}`

3. **Return the response to the user**

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
└─ Bash: gemini-spawner.py (level 1)
   └─ Task → gemini (level 2)
      └─ HeadlessSpawner.initialize (level 3)
         └─ gemini-cli (level 4)
            └─ subprocess.gemini (level 5)
```

## Cost

**FREE** - Google Gemini 2.0-Flash is completely free with 2M token context window.

Use this for:
- Exploratory research (searching large codebases)
- Batch analysis (processing many files)
- Documentation review
- Pattern discovery
- Any task that benefits from large context and FREE cost

## Example Implementation

```python
import json
import subprocess
import os

# Invoke spawner via Bash
result = subprocess.run([
    "uv", "run", "python",
    f"{os.environ['CLAUDE_PLUGIN_ROOT']}/agents/gemini-spawner.py",
    "-p", user_prompt,
    "--model", "gemini-2.0-flash",
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
