---
name: codex
description: Use OpenAI Codex for sandboxed code generation and implementation
when_to_use:
  - Code generation requiring GPT-4 reasoning
  - Sandboxed execution environments needed
  - Structured JSON outputs required
  - Prefer OpenAI models over Anthropic
skill_type: executable
---

# Codex - Sandboxed Code Generation

⚠️ **IMPORTANT: This skill is DOCUMENTATION/COORDINATION ONLY - it does NOT directly execute code generation.**

This skill provides embedded Python code that checks for the external Codex CLI and executes it if available. If the CLI is not installed, it shows you HOW to use Task() delegation for code generation work.

**The embedded Python code is for INTERNAL coordination - not the primary execution path for users.**

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
| **This Skill** | Documentation + embedded coordination logic |
| **Embedded Python** | Internal check for codex CLI → spawns if available |
| **Task() Tool** | PRIMARY execution path for code generation |
| **Bash Tool** | ALTERNATIVE for direct CLI invocation (if you have codex CLI) |

**Workflow:**
1. Read this skill to understand Codex capabilities
2. Use **Task(subagent_type="general-purpose")** for actual code generation (PRIMARY)
3. OR use **Bash** if you have codex CLI installed (ALTERNATIVE)

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
