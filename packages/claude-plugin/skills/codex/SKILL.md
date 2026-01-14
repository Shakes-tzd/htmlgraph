---
name: codex
description: CodexSpawner with full event tracking for code generation and implementation
when_to_use:
  - Code generation with full HtmlGraph tracking
  - Sandboxed execution environments with event hierarchy
  - Structured JSON outputs with subprocess recording
  - Code generation integrating with other spawners
  - AI-powered implementation with observability
skill_type: executable
---

# CodexSpawner - Code Generation with Full Event Tracking

⚠️ **IMPORTANT: This skill teaches TWO EXECUTION PATTERNS**

1. **Task(subagent_type="general-purpose")** - Built-in Claude code generation (simplest, recommended)
2. **CodexSpawner** - Direct OpenAI Codex CLI with full HtmlGraph parent event tracking

Choose based on your needs. See "EXECUTION PATTERNS" below.

## Quick Summary

| Pattern | Use Case | Tracking | Complexity |
|---------|----------|----------|-----------|
| **Task(general-purpose)** | Code generation, implementation, debugging | ✅ Yes (via Task) | Low (1-2 lines) |
| **CodexSpawner** | Need precise Codex control + full subprocess tracking | ✅ Yes (full parent context) | Medium (setup required) |

---

## 🚀 CodexSpawner Pattern: Full Event Tracking

### What is CodexSpawner?

CodexSpawner is the HtmlGraph-integrated way to invoke OpenAI Codex CLI with **full parent event context and subprocess tracking**.

**Key distinction**: CodexSpawner is invoked directly via Python SDK - NOT wrapped in Task(). Task() is only for Claude subagents (Haiku, Sonnet, Opus).

CodexSpawner:
- ✅ Invokes external Codex CLI directly
- ✅ Creates parent event context in database
- ✅ Links to parent Task delegation event
- ✅ Records subprocess invocations as child events
- ✅ Tracks all activities in HtmlGraph event hierarchy
- ✅ Provides full observability of Codex execution

### When to Use CodexSpawner vs Task(general-purpose)

**Use Task(general-purpose) (simple, recommended):**
```python
# Delegate to Claude for code generation
Task(subagent_type="general-purpose",
     prompt="Implement JWT authentication middleware with tests")
# Task() delegates to Claude - handles everything automatically
```

**Use CodexSpawner (direct Python invocation - advanced):**
```python
# Direct Codex CLI invocation with full tracking
spawner = CodexSpawner()
result = spawner.spawn(
    prompt="Generate auth middleware",
    sandbox="workspace-write",
    output_json=True,
    track_in_htmlgraph=True,
    tracker=tracker,
    parent_event_id=parent_event_id
)
# NOT Task(CodexSpawner) - invoke directly!
```

### How to Use CodexSpawner

```python
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import uuid

# Add plugin agents directory to path
PLUGIN_AGENTS_DIR = Path("/path/to/htmlgraph/packages/claude-plugin/.claude-plugin/agents")
sys.path.insert(0, str(PLUGIN_AGENTS_DIR))

from htmlgraph import SDK
from htmlgraph.orchestration.spawners import CodexSpawner
from htmlgraph.db.schema import HtmlGraphDB
from htmlgraph.config import get_database_path
from spawner_event_tracker import SpawnerEventTracker

# Initialize
sdk = SDK(agent='claude')
db = HtmlGraphDB(str(get_database_path()))
session_id = f"sess-{uuid.uuid4().hex[:8]}"
db._ensure_session_exists(session_id, "claude")

# Create parent event context (like PreToolUse hook does)
user_query_event_id = f"event-query-{uuid.uuid4().hex[:8]}"
parent_event_id = f"event-{uuid.uuid4().hex[:8]}"
start_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

# Insert UserQuery event
db.connection.cursor().execute(
    """INSERT INTO agent_events
       (event_id, agent_id, event_type, session_id, tool_name, input_summary, status, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
    (user_query_event_id, "claude-code", "tool_call", session_id, "UserPromptSubmit",
     "Generate spawner usage documentation", "completed", start_time)
)

# Insert Task delegation event
db.connection.cursor().execute(
    """INSERT INTO agent_events
       (event_id, agent_id, event_type, session_id, tool_name, input_summary,
        context, parent_event_id, subagent_type, status, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (parent_event_id, "claude-code", "task_delegation", session_id, "Task",
     "Generate documentation code examples", '{"subagent_type":"general-purpose"}',
     user_query_event_id, "general-purpose", "started", start_time)
)
db.connection.commit()

# Export parent context (like PreToolUse hook does)
os.environ["HTMLGRAPH_PARENT_EVENT"] = parent_event_id
os.environ["HTMLGRAPH_PARENT_SESSION"] = session_id
os.environ["HTMLGRAPH_SESSION_ID"] = session_id

# Create tracker with parent context
tracker = SpawnerEventTracker(
    delegation_event_id=parent_event_id,
    parent_agent="claude",
    spawner_type="codex",
    session_id=session_id
)
tracker.db = db

# Invoke CodexSpawner with FULL tracking
spawner = CodexSpawner()
result = spawner.spawn(
    prompt="Generate Python code example for using CopilotSpawner",
    sandbox="workspace-write",
    output_json=True,
    full_auto=True,
    track_in_htmlgraph=True,      # Enable SDK activity tracking
    tracker=tracker,               # Enable subprocess event tracking
    parent_event_id=parent_event_id,  # Link to parent event
    timeout=120
)

# Check results
print(f"Success: {result.success}")
print(f"Response: {result.response}")
if result.tracked_events:
    print(f"Tracked {len(result.tracked_events)} events in HtmlGraph")
```

### Key Parameters for CodexSpawner.spawn()

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | str | ✅ | Code generation task for Codex |
| `sandbox` | str | ❌ | Sandbox mode: "workspace-write", "workspace-read", etc. |
| `output_json` | bool | ❌ | Return structured JSON output (default: False) |
| `full_auto` | bool | ❌ | Enable full-auto headless mode (default: False) |
| `track_in_htmlgraph` | bool | ❌ | Enable SDK activity tracking (default: True) |
| `tracker` | SpawnerEventTracker | ❌ | Tracker instance for subprocess events |
| `parent_event_id` | str | ❌ | Parent event ID for event hierarchy |
| `timeout` | int | ❌ | Max seconds to wait (default: 120) |

### Real Example: Generate Code Documentation

```python
# See above code example + this prompt:
result = spawner.spawn(
    prompt="""Generate a Python code example showing how to:
1. Create a CopilotSpawner instance
2. Set up parent event context in database
3. Invoke it with parent event linking
4. Track the execution with SpawnerEventTracker
5. Handle the AIResult

Use real example from HtmlGraph project and show best practices.
    """,
    sandbox="workspace-write",
    output_json=True,
    full_auto=True,
    track_in_htmlgraph=True,
    tracker=tracker,
    parent_event_id=parent_event_id,
    timeout=120
)

# Result: Full tracking with Codex-generated code examples
# All subprocess invocations recorded in HtmlGraph
```

### Fallback & Error Handling Pattern

**CRITICAL: If external spawner fails, delegate to Claude sub-agent (NOT direct execution).**

```python
# Try external spawner first
try:
    spawner = CodexSpawner()
    result = spawner.spawn(
        prompt="Your code generation task",
        sandbox="workspace-write",
        output_json=True,
        track_in_htmlgraph=True,
        tracker=tracker,
        parent_event_id=parent_event_id,
        timeout=120
    )

    if result.success:
        return result  # Success, use spawner result
    else:
        # Spawner returned error result
        raise Exception(f"Spawner failed: {result.error}")

except Exception as e:
    # External spawner failed (CLI not installed, API issues, sandbox restrictions, etc.)
    # FALLBACK to Claude sub-agent - do NOT attempt direct execution
    print(f"⚠️ CodexSpawner failed: {e}")
    print("📌 Falling back to Claude code generation agent...")

    return Task(
        subagent_type="general-purpose",
        prompt="Your code generation task here"
    )
    # Task(general-purpose) guarantees execution via Claude
```

**Why fallback to Task()?**
- ✅ Codex CLI may not be installed on user's system
- ✅ OpenAI API credentials/quota issues may affect external tool
- ✅ Claude sub-agent provides guaranteed code generation fallback
- ✅ Never attempt direct execution as fallback (violates orchestration principles)
- ✅ Task() handles all retries, error recovery, and parent context automatically

**Pattern Summary:**
1. Try external spawner first (Codex CLI)
2. If spawner succeeds → return result
3. If spawner fails → delegate to Claude sub-agent via Task(subagent_type="general-purpose")
4. Never try direct execution as fallback

---

<python>
import subprocess
import sys
from htmlgraph.orchestration.headless_spawner import HeadlessSpawner

# Get the task prompt from skill arguments
task_prompt = skill_args if 'skill_args' in dir() else ""

if not task_prompt:
    print("❌ ERROR: No task prompt provided")
    print("Usage: Skill(skill='.claude-plugin:codex', args='Generate API endpoint with tests')")
    sys.exit(1)

# Check if codex CLI is available
cli_check = subprocess.run(
    ["which", "codex"],
    capture_output=True,
    text=True
)

if cli_check.returncode != 0:
    print("⚠️ Codex CLI not found on system")
    print("Install from: https://github.com/openai/codex")
    print("\nFallback: Use Task(subagent_type='general-purpose', prompt='...')")
    print("Claude can generate code directly without the Codex CLI.")
    sys.exit(1)

# Codex CLI is available - use spawner to execute
print("✅ Codex CLI found, executing spawner...")
print(f"\nTask: {task_prompt[:100]}...")

try:
    spawner = HeadlessSpawner()
    result = spawner.spawn_codex(
        prompt=task_prompt,
        output_json=True,
        sandbox="workspace-write",
        full_auto=True,
        track_in_htmlgraph=True,
        timeout=120
    )

    if result.success:
        print("\n✅ Codex execution successful")
        if result.tokens_used:
            print(f"📊 Tokens used: {result.tokens_used}")
        print("\n" + "="*60)
        print("RESPONSE:")
        print("="*60)
        print(result.response)
        if result.tracked_events:
            print(f"\n📈 Tracked {len(result.tracked_events)} events in HtmlGraph")
    else:
        print(f"\n❌ Codex execution failed: {result.error}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Error executing spawner: {type(e).__name__}: {e}")
    sys.exit(1)
</python>

Use OpenAI Codex (GPT-4 Turbo) for code generation and implementation in sandboxed environments.

## Skill vs Execution Model

**CRITICAL DISTINCTION:**

| What | Description |
|------|-------------|
| **This Skill** | Documentation teaching HOW to use CodexSpawner |
| **CodexSpawner** | Direct Codex CLI invocation with full tracking (advanced) |
| **Task() Tool** | Delegation to Claude subagents ONLY (Haiku, Sonnet, Opus) |
| **Bash Tool** | Direct CLI invocation without HtmlGraph tracking |

**Workflow:**
1. Read this skill to understand CodexSpawner pattern
2. For **simple code generation**: Use `Task(subagent_type="general-purpose")` (recommended)
3. For **advanced control + full tracking**: Use CodexSpawner directly with parent event context
4. OR use **Bash** if you have codex CLI and don't need HtmlGraph tracking

## EXECUTION - Real Commands for Code Generation

**⚠️ To actually generate code, use these approaches:**

### PRIMARY: Task() Delegation (Recommended)
```python
# Use Claude for code generation (native approach)
Task(
    subagent_type="general-purpose",
    prompt="Generate API endpoint for user authentication with JWT tokens and full tests"
)

# For complex implementations
Task(
    subagent_type="general-purpose",
    model="sonnet",  # or "opus" for complex work
    prompt="Refactor authentication system to support multi-tenancy across 15+ files"
)
```

### ALTERNATIVE: Direct CLI (if codex CLI installed)
```bash
# If you have codex CLI installed on your system
Bash("codex generate 'Create FastAPI endpoint with authentication'")

# Or use the SDK spawner
uv run python -c "
from htmlgraph.orchestration.headless_spawner import HeadlessSpawner
spawner = HeadlessSpawner()
result = spawner.spawn_codex(
    prompt='Generate auth endpoint',
    sandbox='workspace-write',
    track_in_htmlgraph=True
)
print(result.response)
"
```

## When to Use

- **Code Generation** - Generate production-quality code
- **Sandboxed Execution** - Run code in isolated environments
- **Structured Outputs** - Generate JSON adhering to schemas
- **Alternative Model** - Compare GPT-4 vs Claude capabilities
- **Tool Restrictions** - Fine-grained control over allowed operations

## Requirements

The `codex` CLI must be installed:

```bash
# Install Codex CLI
npm install -g @openai/codex-cli

# Or via pip
pip install openai-codex-cli

# Verify installation
codex --version
```

## How to Invoke

**PRIMARY: Use Skill() to invoke (tries external CLI first):**

```python
# Recommended approach - uses external codex CLI via agent spawner
Skill(skill=".claude-plugin:codex", args="Generate API endpoint for user authentication with full tests")
```

**What happens internally:**
1. Check if `codex` CLI is installed on your system
2. If **YES** → Use agent spawner SDK to execute: `codex generate "API endpoint with tests"`
3. If **NO** → Automatically fallback to: `Task(subagent_type="general-purpose", prompt="Generate API endpoint")`

**FALLBACK: Direct Task() invocation (when Skill unavailable):**

```python
# Manual fallback - uses Claude's general-purpose agent
Task(
    subagent_type="general-purpose",
    prompt="Generate API endpoint for user authentication with full tests",
    model="haiku"  # Optional: specify model
)
```

**Note:** Direct Codex spawning requires the CLI. If unavailable, Claude can implement the code directly.

## Sandbox Modes

Codex provides three security levels:

### 1. Read-Only (Safest)
```python
# Analysis without modifications
Task(
    subagent_type="general-purpose",
    prompt="Analyze code structure without making changes"
)
```

### 2. Workspace-Write (Recommended)
```python
# Generate and write code to workspace
Task(
    subagent_type="general-purpose",
    prompt="Generate new feature implementation with tests"
)
```

### 3. Full-Access (Use with Caution)
```python
# System-wide operations (dangerous)
Task(
    subagent_type="general-purpose",
    prompt="System configuration changes (requires full access)"
)
```

## Example Use Cases

### 1. API Endpoint Generation

```python
Task(
    subagent_type="general-purpose",
    prompt="""
    Generate FastAPI endpoint for user authentication:
    - POST /auth/login
    - JWT token generation
    - Input validation with Pydantic
    - Error handling
    - Unit tests with pytest
    """
)
```

### 2. Structured Data Extraction

```python
# Generate JSON matching a schema
Task(
    subagent_type="general-purpose",
    prompt="""
    Extract all functions and classes from src/:

    Output format:
    {
      "functions": [{"name": "...", "file": "...", "line": ...}],
      "classes": [{"name": "...", "file": "...", "methods": [...]}]
    }
    """
)
```

### 3. Batch Code Review

```python
# Analyze multiple files
Task(
    subagent_type="general-purpose",
    prompt="Review all Python files in src/ for code quality issues and security vulnerabilities"
)
```

### 4. Test Generation

```python
# Generate comprehensive tests
Task(
    subagent_type="general-purpose",
    prompt="""
    Generate pytest tests for UserService class:
    - Test all public methods
    - Include edge cases
    - Mock external dependencies
    - Aim for 90%+ coverage
    """
)
```

## When to Use Codex vs Claude

**Use Codex when:**
- Need to compare GPT-4 vs Claude capabilities
- OpenAI-specific features required
- Structured JSON outputs mandatory
- Evaluation/benchmarking required

**Use Claude when:**
- Complex reasoning needed
- Integration with HtmlGraph workflows required
- Claude Code native tools preferred
- Production code generation

## Error Handling

### CLI Not Found

If you see this error:
```
ERROR: codex CLI not found
Install from: npm install -g @openai/codex-cli
```

**Options:**
1. Install the CLI and retry
2. Use Claude directly for implementation
3. Switch to a different subagent

### Common Issues

**Timeout Errors:**
```
Error: Timed out after 120 seconds
Solution: Split into smaller tasks or increase timeout
```

**Approval Failures:**
```
Error: Command requires approval
Solution: Adjust approval settings or sandbox mode
```

**Sandbox Restrictions:**
```
Error: Operation not allowed in sandbox
Solution: Upgrade sandbox level or redesign approach
```

## Advanced Features

### Full Auto Mode
```python
# Auto-execute generated code
Task(
    subagent_type="general-purpose",
    prompt="Fix linting errors and run tests automatically"
)
```

### Multimodal Inputs
```python
# Include images for context
Task(
    subagent_type="general-purpose",
    prompt="Convert this UI mockup to React code (see attached image)"
)
```

## Integration with HtmlGraph

Track code generation in features:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Create feature for implementation
feature = sdk.features.create(
    title="User Authentication API",
    description="""
    Generated via Codex:
    - API endpoints
    - Input validation
    - JWT tokens
    - Unit tests

    Model: GPT-4 Turbo
    Sandbox: workspace-write
    """
).save()
```

## When NOT to Use

Avoid Codex for:
- Exploratory research (use Gemini skill)
- GitHub operations (use GitHub CLI skill)
- Simple tasks (use Claude Haiku)

## Fallback Strategy

The skill implements a multi-level fallback strategy:

### Level 1: External CLI (Preferred)
```python
Skill(skill=".claude-plugin:codex", args="Generate authentication API")
# Attempts to use external codex CLI via agent spawner SDK
```

### Level 2: Claude General-Purpose Agent (Automatic Fallback)
```python
# If codex CLI not found, automatically falls back to:
Task(subagent_type="general-purpose", prompt="Generate authentication API")
# Uses Claude for code generation
```

### Level 3: Error Handling (Final Fallback)
```python
# If Task() fails:
# - Returns error message to orchestrator
# - Orchestrator can retry with different approach
# - Or escalate to user for guidance
```

**Error Handling:**
- Transparent fallback (no silent failures)
- Clear error messages at each level
- Automatic retry with Claude if CLI unavailable
- Timeout protection (120s default)

## Tips for Best Results

1. **Be specific** - Detailed requirements get better code
2. **Include tests** - Request unit tests in the prompt
3. **Specify frameworks** - Mention libraries to use
4. **Request documentation** - Ask for docstrings and comments
5. **Validate output** - Always review generated code

## Related Skills

- `/gemini` - For exploration before implementation
- `/copilot` - For GitHub integration after generation
- `/code-quality` - For validating generated code
- `/debugging-workflow` - For fixing issues in generated code
