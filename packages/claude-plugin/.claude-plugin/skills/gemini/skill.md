---
name: gemini
description: Use Google Gemini for exploration and large-context research
when_to_use:
  - Large codebase exploration and analysis
  - Research tasks requiring extensive context
  - Large-context workflows
  - Multimodal tasks (images, PDFs, documents)
skill_type: executable
---

# Gemini - Exploration & Research

⚠️ **IMPORTANT: This skill is DOCUMENTATION/COORDINATION ONLY - it does NOT directly execute exploration.**

This skill provides embedded Python code that checks for the external Gemini CLI and executes it if available. If the CLI is not installed, it shows you HOW to use Task() delegation for exploration work.

**The embedded Python code is for INTERNAL coordination - not the primary execution path for users.**

<python>
import subprocess
import sys
from htmlgraph.orchestration.headless_spawner import HeadlessSpawner

# Get the task prompt from skill arguments
task_prompt = skill_args if 'skill_args' in dir() else ""

if not task_prompt:
    print("❌ ERROR: No task prompt provided")
    print("Usage: Skill(skill='.claude-plugin:gemini', args='Your exploration task')")
    sys.exit(1)

# Check if gemini CLI is available
cli_check = subprocess.run(
    ["which", "gemini"],
    capture_output=True,
    text=True
)

if cli_check.returncode != 0:
    print("⚠️ Gemini CLI not found on system")
    print("Install from: https://github.com/google/gemini-cli")
    print("\nFallback: Use Task(subagent_type='Explore', prompt='...')")
    print("The Claude Explore agent integrates with Gemini automatically.")
    sys.exit(1)

# Gemini CLI is available - use spawner to execute
print("✅ Gemini CLI found, executing spawner...")
print(f"\nTask: {task_prompt[:100]}...")

try:
    spawner = HeadlessSpawner()
    result = spawner.spawn_gemini(
        prompt=task_prompt,
        output_format="stream-json",
        track_in_htmlgraph=True,
        timeout=120
    )

    if result.success:
        print("\n✅ Gemini execution successful")
        if result.tokens_used:
            print(f"📊 Tokens used: {result.tokens_used}")
        print("\n" + "="*60)
        print("RESPONSE:")
        print("="*60)
        print(result.response)
        if result.tracked_events:
            print(f"\n📈 Tracked {len(result.tracked_events)} events in HtmlGraph")
    else:
        print(f"\n❌ Gemini execution failed: {result.error}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Error executing spawner: {type(e).__name__}: {e}")
    sys.exit(1)
</python>

Use Google Gemini 2.0-Flash for exploration and research tasks via the HeadlessSpawner SDK.

## Skill vs Execution Model

**CRITICAL DISTINCTION:**

| What | Description |
|------|-------------|
| **This Skill** | Documentation + embedded coordination logic |
| **Embedded Python** | Internal check for gemini CLI → spawns if available |
| **Task() Tool** | PRIMARY execution path for exploration work |
| **Bash Tool** | ALTERNATIVE for direct CLI invocation (if you have gemini CLI) |

**Workflow:**
1. Read this skill to understand Gemini capabilities
2. Use **Task(subagent_type="Explore")** for actual exploration (PRIMARY)
3. OR use **Bash** if you have gemini CLI installed (ALTERNATIVE)

## EXECUTION - Real Commands for Exploration

**⚠️ To actually perform exploration, use these approaches:**

### PRIMARY: Task() Delegation (Recommended)
```python
# Use Claude's Explore agent (automatically uses appropriate model)
Task(
    subagent_type="Explore",
    prompt="Analyze all authentication patterns in the codebase and document findings"
)

# For large-context research
Task(
    subagent_type="Explore",
    prompt="Review entire API documentation and extract deprecated endpoints"
)
```

### ALTERNATIVE: Direct CLI (if gemini CLI installed)
```bash
# If you have gemini CLI installed on your system
Bash("gemini analyze 'Find all authentication patterns'")

# Or use the SDK spawner
uv run python -c "
from htmlgraph.orchestration.headless_spawner import HeadlessSpawner
spawner = HeadlessSpawner()
result = spawner.spawn_gemini(
    prompt='Analyze auth patterns',
    track_in_htmlgraph=True
)
print(result.response)
"
```

## When to Use

- **Large Context** - 2M token context window for large codebases
- **Multimodal** - Process images, PDFs, and documents
- **Batch Operations** - Analyze many files efficiently
- **Fast Inference** - Quick turnaround for exploratory work

## How to Invoke

**PRIMARY: Use Skill() to invoke (tries external CLI first):**

```python
# Recommended approach - uses external gemini CLI via agent spawner
Skill(skill=".claude-plugin:gemini", args="Analyze authentication patterns in the codebase")
```

**What happens internally:**
1. Check if `gemini` CLI is installed on your system
2. If **YES** → Use agent spawner SDK to execute: `gemini analyze "auth patterns"`
3. If **NO** → Automatically fallback to: `Task(subagent_type="Explore", prompt="Analyze auth patterns")`

**FALLBACK: Direct Task() invocation (when Skill unavailable):**

```python
# Manual fallback - uses Claude's built-in Explore agent
Task(
    subagent_type="Explore",
    prompt="Analyze authentication patterns in the codebase",
    model="haiku"  # Optional: specify model
)
```

The Explore agent automatically uses Gemini for large-context work.

## Capabilities

- **Context Window**: 2M tokens (large-context support)
- **Multimodal**: Process images, PDFs, audio, documents
- **Fast Inference**: Sub-second latency
- **Best For**: Exploration, research, understanding systems

## Example Use Cases

### 1. Codebase Exploration

```python
Task(
    subagent_type="Explore",
    prompt="""
    Search codebase for all authentication patterns:
    1. Where auth is implemented
    2. What auth methods are used
    3. Where auth is validated
    4. Recommendations for adding OAuth 2.0
    """
)
```

### 2. Batch File Analysis

```python
# Analyze multiple files for security issues
Task(
    subagent_type="Explore",
    prompt="Review all API endpoints in src/ for security vulnerabilities"
)
```

### 3. Multimodal Processing

```python
# Extract information from diagrams or images
Task(
    subagent_type="Explore",
    prompt="Extract all text and tables from architecture diagrams in docs/"
)
```

### 4. Large Documentation Review

```python
# Process extensive documentation
Task(
    subagent_type="Explore",
    prompt="Summarize all API documentation and find deprecated endpoints"
)
```

## When to Use Gemini vs Claude

**Use Gemini for:**
- Large-context exploration
- Multimodal document analysis
- Tasks not requiring complex reasoning
- Exploration phase before implementation

**Use Claude for:**
- Precise code generation
- Complex reasoning tasks
- Production code writing
- Critical decision-making

## Fallback Strategy

The skill implements a multi-level fallback strategy:

### Level 1: External CLI (Preferred)
```python
Skill(skill=".claude-plugin:gemini", args="Your exploration task")
# Attempts to use external gemini CLI via agent spawner SDK
```

### Level 2: Claude Explore Agent (Automatic Fallback)
```python
# If gemini CLI not found, automatically falls back to:
Task(subagent_type="Explore", prompt="Your exploration task")
# Uses Claude's built-in Explore agent
```

### Level 3: Claude Models (Final Fallback)
```python
# If alternative unavailable, uses Claude models for exploration
# Maintains full functionality with different inference model
```

**Error Handling:**
- Transparent fallback (no silent failures)
- Clear error messages if all methods fail
- Automatic retry with different methods

## Integration with HtmlGraph

Track exploration work in spikes:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Create spike for research findings
spike = sdk.spikes.create(
    title="Auth Pattern Analysis via Gemini",
    findings="""
    ## Research Question
    Where and how is authentication implemented?

    ## Findings
    [Results from Gemini exploration]

    ## Recommendations
    [Next steps based on research]
    """
).save()
```

## When NOT to Use

Avoid Gemini for:
- Precise code generation (use Claude Sonnet)
- Critical production code (use Claude with tests)
- Tasks requiring Claude's reasoning (use Sonnet/Opus)
- Small context tasks (overhead not needed)

## Tips for Best Results

1. **Be specific** - Clear prompts get better results
2. **Use for exploration first** - Research before implementing
3. **Leverage large context** - Include entire codebases
4. **Batch operations** - Process many files at once
5. **Document findings** - Save results in HtmlGraph spikes

## Related Skills

- `/codex` - For code implementation after exploration
- `/copilot` - For GitHub integration and git operations
- `/debugging-workflow` - Research-first debugging methodology
