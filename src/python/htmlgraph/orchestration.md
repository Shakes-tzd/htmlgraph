# Orchestration Rules - Cost-First Delegation

**CRITICAL: When operating in orchestrator mode, you MUST delegate ALL operations except a minimal set of strategic activities.**

## Cost-First Delegation Priority

**IMPERATIVE: ALWAYS choose the cheapest/best approach for each task type.**

Use this decision tree IN ORDER (check each before falling back):

1. **Exploration/Research** → `Task(subagent_type="Explore")` (Uses Gemini FREE, 2M tokens)
2. **Git/GitHub Operations** → `Bash` tool with `gh` CLI (direct GitHub integration)
3. **Code Implementation** → `Task(subagent_type="general-purpose")` (Claude native)
4. **Simple Operations** → `Bash` tool (direct, for ls/pwd/cat/echo type commands)
5. **Deep Reasoning/Architecture** → Task() with Opus subagent ($$$$)
6. **Multi-Agent Coordination** → Task() with Sonnet subagent ($$$)
7. **FALLBACK ONLY** → Task() with Haiku subagent ($$, when above unavailable)

### Using Skills for Guidance

**Skills provide implementation guidance for common patterns:**

```
# Use /gemini skill for exploration guidance
Skill(skill="gemini")  # Shows how to use Explore agent effectively

# Use /codex skill for implementation patterns
Skill(skill="codex")   # Shows code generation best practices

# Use /copilot skill for Git/GitHub workflows
Skill(skill="copilot") # Shows gh CLI commands and patterns
```

### Task() for Claude Subagents

**Task() delegates work to Claude-based subagents:**

```python
# Exploration using Explore agent (uses Gemini FREE)
Task(
    subagent_type="Explore",
    prompt="Analyze codebase patterns for authentication"
)

# Code implementation using general-purpose agent
Task(
    subagent_type="general-purpose",
    prompt="Implement JWT authentication middleware with tests"
)

# Strategic planning using Opus
Task(
    subagent_type="general-purpose",
    model="opus",
    prompt="Design authentication architecture"
)
```

### Bash for Direct Operations

**Use Bash tool directly for Git/GitHub operations:**

```bash
# Git operations
git add . && git commit -m "feat: add auth"

# GitHub operations via gh CLI
gh pr create --title "Add auth" --body "Implements JWT middleware"

# Chained operations
git checkout -b feature/auth && git add . && gh pr create
```

### When to Use Each Approach

**Use Explore Agent (Task with subagent_type="Explore"):**
- ✅ Large codebase searches (FREE via Gemini)
- ✅ Understanding unfamiliar systems
- ✅ Documentation research
- ✅ Analysis requiring large context

**Use General-Purpose Agent (Task with subagent_type="general-purpose"):**
- ✅ Code generation and implementation
- ✅ Strategic coordination across models
- ✅ Multi-agent orchestration
- ✅ Architecture/design decisions

**Use Bash Tool:**
- ✅ Git operations (commit, push, branch)
- ✅ GitHub operations via gh CLI
- ✅ Simple file operations (ls, cat, echo)
- ✅ Build and deployment commands

**Cost Comparison**:
- Exploring 100 files: Explore agent (FREE via Gemini) vs general-purpose Task ($15-25) = 100% savings
- Git operations: Bash with gh CLI (minimal) vs Task ($5-10) = near 100% savings
- Code generation: Task ($10-15) = standard Claude rates

**Token Cache Consideration**:
Task() provides 5x cheaper prompt caching for RELATED sequential work within same conversation.

## Model Selection Reference

For detailed model selection logic, see:
- `/multi-ai-orchestration` skill (comprehensive guide)
- `src/python/htmlgraph/orchestration/model_selection.py` (decision matrix)
- `src/python/htmlgraph/orchestration/headless_spawner.py` (implementation)

## Core Philosophy

**You don't know the outcome before running a tool.** What looks like "one bash call" often becomes 2, 3, 4+ calls when handling failures, conflicts, hooks, or errors. Delegation preserves strategic context by isolating tactical execution in subagent threads.

## Operations You MUST Delegate

**ALL operations EXCEPT:**
- `Task()` - Delegation itself (use spawner subagent types when possible)
- `AskUserQuestion()` - Clarifying requirements with user
- `TodoWrite()` - Tracking work items
- SDK operations - Creating features, spikes, bugs, analytics

**Everything else MUST be delegated**, including:

### 1. Git Operations - ALWAYS use Copilot

**REQUIRED: MUST use Copilot spawner for all git/GitHub operations.**

- ❌ NEVER run git commands directly (add, commit, push, branch, merge)
- ❌ NEVER use generic Task() for git operations (expensive, not specialized)
- ✅ ALWAYS use Copilot spawner (cheaper, GitHub-specialized)

**Why Copilot?** Git operations cascade unpredictably + Copilot is specialized:
- Commit hooks may fail (need fix + retry)
- Conflicts may occur (need resolution + retry)
- Push may fail (need pull + merge + retry)
- Tests may fail in hooks (need fix + retry)
- Copilot has native GitHub integration

**Cost comparison:**
```
Task() for git: $5-10 per workflow
Copilot for git: $2-3 per workflow (60% savings + better results)
Direct execution: 7+ tool calls (context pollution)
```

**IMPERATIVE Delegation pattern:**
```
# ✅ CORRECT - Use Bash tool with gh CLI for git operations
Bash("""
gh pr create --title "Add feature" --body "Description" || \
git add CLAUDE.md SKILL.md git-commit-push.sh && \
git commit -m 'docs: enforce strict git delegation in orchestrator directives' && \
git push origin main
""")

# See /copilot skill for more gh CLI workflows

# ❌ INCORRECT - Don't run git commands in multiple separate Bash calls
Bash("git add file.py")
Bash("git commit -m 'message'")
Bash("git push")
```

### 2. Code Changes - Delegate to General-Purpose Agent

**REQUIRED: MUST delegate code implementation (unless trivial).**

- ❌ NEVER execute code changes directly (expensive, loses strategic context)
- ❌ Multi-file edits → MUST delegate to general-purpose agent
- ❌ Implementation requiring research → MUST delegate
- ❌ Changes with testing requirements → MUST delegate
- ✅ Single-line typo fixes (OK to do directly)

**IMPERATIVE Delegation pattern:**
```
# ✅ CORRECT - Use Task() for code implementation
Task(
    subagent_type="general-purpose",
    prompt="Implement authentication middleware with JWT..."
)

# See /codex skill for implementation patterns

# ❌ INCORRECT - Don't execute code changes directly
Edit(file_path="...", old_string="...", new_string="...")
Write(file_path="...", content="...")
```

### 3. Research & Exploration - Use Explore Agent (FREE!)

**REQUIRED: MUST use Explore agent for exploration (FREE via Gemini!).**

- ❌ NEVER use general-purpose Task() for exploration (expensive)
- ❌ Large codebase searches → MUST use Explore agent (FREE)
- ❌ Understanding unfamiliar systems → MUST use Explore agent (FREE)
- ❌ Documentation research → MUST use Explore agent (FREE)
- ✅ Single file quick lookup (OK to do directly)

**IMPERATIVE Delegation pattern:**
```
# ✅ CORRECT - Use Explore agent (leverages Gemini FREE tier)
Task(
    subagent_type="Explore",
    prompt="Analyze all authentication patterns in codebase"
)

# See /gemini skill for exploration guidance

# ❌ INCORRECT - Don't use general-purpose Task() (costs $15-25 vs FREE)
Task(subagent_type="general-purpose", prompt="Explore codebase...")
```

### 4. Testing & Validation - MUST DELEGATE

**REQUIRED: MUST delegate testing operations.**

- ❌ Running test suites → MUST delegate to general-purpose agent
- ❌ Debugging test failures → MUST delegate
- ❌ Quality gate validation → MUST delegate
- ✅ Checking test command exists (OK to do directly)

**Delegation pattern:**
```
# ✅ CORRECT - Delegate testing to general-purpose agent
Task(
    subagent_type="general-purpose",
    prompt="Run pytest suite and fix any failures"
)

# Or use Bash for simple test runs (no fixes)
Bash("uv run pytest")
```

### 5. Build & Deployment - MUST DELEGATE
- ❌ Build processes → MUST delegate
- ❌ Package publishing → MUST delegate
- ❌ Environment setup → MUST delegate
- ✅ Checking deployment script exists (OK to do directly)

### 6. File Operations - DELEGATE Complex Operations
- ❌ Batch file operations (multiple files) → MUST delegate
- ❌ Large file reading/writing → MUST delegate
- ❌ Complex file transformations → MUST delegate
- ✅ Reading single config file (OK to do directly)
- ✅ Writing single small file (OK to do directly)

### 7. Analysis & Computation - ALWAYS use Gemini

**REQUIRED: MUST use Gemini spawner for analysis (FREE!).**

- ❌ Performance profiling → MUST use Gemini spawner (FREE)
- ❌ Large-scale analysis → MUST use Gemini spawner (FREE)
- ❌ Complex calculations → MUST delegate
- ✅ Simple status checks (OK to do directly)

## Why Strict Delegation Matters

**1. Cost Optimization (NEW - MOST IMPORTANT)**
- Gemini is FREE for exploration (vs $15-25 with Task)
- Codex is 70% cheaper for code (vs Task)
- Copilot is 60% cheaper for git (vs Task)
- Choosing the right model saves 60-100% per operation

**2. Context Preservation**
- Each tool call consumes tokens
- Failed operations consume MORE tokens
- Cascading failures consume MOST tokens
- Delegation isolates failure to subagent context

**3. Parallel Efficiency**
- Multiple subagents can work simultaneously
- Orchestrator stays available for decisions
- Higher throughput on independent tasks

**4. Error Isolation**
- Subagent handles retries and recovery
- Orchestrator receives clean success/failure
- No pollution of strategic context

**5. Cognitive Clarity**
- Orchestrator maintains high-level view
- Subagents handle tactical details
- Clear separation of concerns

## Decision Framework

Ask yourself IN ORDER:
1. **Is this exploration/research?**
   - If yes → MUST use Gemini spawner (FREE)

2. **Is this code implementation?**
   - If yes → MUST use Codex spawner (cheaper, specialized)

3. **Is this git/GitHub operation?**
   - If yes → MUST use Copilot spawner (cheaper, specialized)

4. **Is this strategic coordination?**
   - If yes → MAY use generic Task() with Opus/Sonnet

5. **Is this a trivial single tool call?**
   - If yes AND certain → MAY do directly
   - If uncertain → MUST delegate to appropriate spawner

## Orchestrator Reflection System

When orchestrator mode is enabled (strict), you'll receive reflections after direct tool execution:

```
ORCHESTRATOR REFLECTION: You executed code directly.

Ask yourself:
- Could this have been delegated to Gemini spawner (FREE)?
- Could this have been delegated to Codex spawner (70% cheaper)?
- Could this have been delegated to Copilot spawner (60% cheaper)?
- What if this operation fails - how many retries will consume context?
- Would parallel spawner Task() calls have been faster?
```

Use these reflections to adjust your delegation habits.

## Integration with HtmlGraph SDK

Always use SDK to track orchestration activities:

```python
from htmlgraph import SDK

sdk = SDK(agent='orchestrator')

# Track what you delegate
feature = sdk.features.create("Implement authentication") \
    .set_priority("high") \
    .add_steps([
        "Research existing auth patterns (delegated to Gemini FREE)",
        "Implement OAuth flow (delegated to Codex)",
        "Add tests (delegated to Codex)",
        "Commit changes (delegated to Copilot)"
    ]) \
    .save()
```

Then delegate using Skill tool to invoke spawner skills:

```
# Research (FREE!)
Skill(
    skill=".claude-plugin:gemini-spawner",
    args="Find all auth-related code and analyze patterns"
)

# Implementation
Skill(
    skill=".claude-plugin:codex-spawner",
    args="Implement OAuth flow based on research findings"
)

# Git operations
Skill(
    skill=".claude-plugin:copilot-spawner",
    args="Commit changes with message: 'feat: add OAuth'"
)
```

**See:** `packages/claude-plugin/skills/multi-ai-orchestration-skill/SKILL.md` for complete model selection patterns

## Task ID Pattern for Parallel Coordination

**Problem:** Timestamp-based lookup cannot distinguish parallel task results.

**Solution:** Generate unique task ID for each delegation.

### Helper Functions

HtmlGraph provides orchestration helpers in `htmlgraph.orchestration`:

```python
from htmlgraph.orchestration import delegate_with_id, get_results_by_task_id

# Generate task ID and enhanced prompt
task_id, prompt = delegate_with_id(
    "Implement authentication",
    "Add JWT auth to API endpoints...",
    "general-purpose"
)

# Delegate (orchestrator calls Task tool)
Task(
    prompt=prompt,
    description=f"{task_id}: Implement authentication",
    subagent_type="general-purpose"
)

# Retrieve results by task ID
results = get_results_by_task_id(sdk, task_id, timeout=120)
if results["success"]:
    print(results["findings"])
```

### Parallel Task Coordination

```python
from htmlgraph.orchestration import delegate_with_id, get_results_by_task_id

# Spawn 3 parallel tasks
auth_id, auth_prompt = delegate_with_id("Implement auth", "...", "general-purpose")
test_id, test_prompt = delegate_with_id("Write tests", "...", "general-purpose")
docs_id, docs_prompt = delegate_with_id("Update docs", "...", "general-purpose")

# Delegate all in parallel (single message, multiple Task calls)
Task(prompt=auth_prompt, description=f"{auth_id}: Implement auth")
Task(prompt=test_prompt, description=f"{test_id}: Write tests")
Task(prompt=docs_prompt, description=f"{docs_id}: Update docs")

# Retrieve results independently (order doesn't matter)
auth_results = get_results_by_task_id(sdk, auth_id)
test_results = get_results_by_task_id(sdk, test_id)
docs_results = get_results_by_task_id(sdk, docs_id)
```

**Benefits:**
- Works with parallel delegations
- Full traceability (Task → task_id → spike → findings)
- Timeout handling with polling
- Independent result retrieval

## Git Workflow Patterns

### Orchestrator Pattern (REQUIRED)

When operating as orchestrator, ALWAYS use Copilot spawner skill for git operations:

```
# ✅ CORRECT - Use Skill to invoke Copilot spawner for git workflow
Skill(
    skill=".claude-plugin:copilot-spawner",
    args="""Commit and push changes to git:

    Files to commit: [list files or use 'all changes']
    Commit message: "chore: update session tracking"

    Steps:
    1. Run ./scripts/git-commit-push.sh "chore: update session tracking" --no-confirm
    2. If that script doesn't exist, use manual git workflow:
       - git add [files]
       - git commit -m "message"
       - git push origin main
    3. Handle any errors (pre-commit hooks, conflicts, push failures)
    4. Retry with fixes if needed

    Report final status: success or failure with details.

    🔴 CRITICAL - Track in HtmlGraph:
    After successful commit, update the active feature/spike with completion status."""
)

# ❌ INCORRECT - Don't use Task() for spawners (spawns Claude subagent)
Task(
    prompt="commit changes...",
    subagent_type="general-purpose"
)
```

**Why Copilot?** Git operations cascade unpredictably + cost savings:
- Pre-commit hooks may fail → need code fix → retry commit
- Push may fail due to conflicts → need pull → merge → retry push
- Tests may fail in hooks → need debugging → fix → retry
- Copilot is 60% cheaper than Task() for git operations

**Cost:**
- Direct execution: 5-10+ tool calls (with failures and retries)
- Task() delegation: $5-10 per workflow
- Copilot delegation: $2-3 per workflow (60% savings)

## Troubleshooting Spawner Issues

### "Spawner 'gemini' requires 'gemini' CLI"

**Meaning:** The Gemini CLI is not installed on the system.

**Solution 1: Install the CLI**
```bash
# Install Gemini CLI
# See: https://ai.google.dev/gemini-api/docs/cli

# Verify installation
which gemini
```

**Solution 2: Use different spawner**
```
# Try Codex instead
Skill(skill=".claude-plugin:codex-spawner", args="Same task")

# Or fallback to Claude subagent
Task(subagent_type="haiku", prompt="Same task")
```

### Spawner Execution Timeout

**Meaning:** The spawner took longer than expected to complete.

**Solution:**
```
# Break into smaller subtasks
Skill(skill=".claude-plugin:gemini-spawner", args="Analyze first 50 files")
Skill(skill=".claude-plugin:gemini-spawner", args="Analyze next 50 files")
```

### "Operation cannot proceed without required CLI"

**Meaning:** The CLI is genuinely not installed, not a transient error.

**This is TRANSPARENT - not a silent fallback:**
- Orchestrator receives explicit error
- You decide: install, use different spawner, or fallback to Claude
- Do NOT silently fallback

**Example:**
```python
# This fails explicitly if CLI missing (no silent fallback)
try:
    result = Skill(skill=".claude-plugin:gemini-spawner", args="...")
except CLINotFound as e:
    # Orchestrator handles explicitly
    if ask_user("Install Gemini CLI?"):
        install_gemini()
        result = Skill(skill=".claude-plugin:gemini-spawner", args="...")
    else:
        # Explicit fallback to Claude subagent
        result = Task(subagent_type="haiku", prompt="...")
```

### Spawner Returns Empty/Malformed Results

**Solution:**
```
# Request explicit output format
Skill(
    skill=".claude-plugin:gemini-spawner",
    args="""Find all API endpoints and return as JSON:
    {
        "endpoints": [
            {"path": "/api/users", "method": "GET", "file": "src/api/users.py"}
        ]
    }"""
)
```

### Spawner Cost Higher Than Expected

**Solution:**
```
# Use cheaper spawner for exploration
Skill(skill=".claude-plugin:gemini-spawner", args="Quick analysis")  # FREE

# Use Codex for code (cheaper than Claude)
Skill(skill=".claude-plugin:codex-spawner", args="Code generation")  # 70% cheaper

# Use Copilot for git (cheaper than Claude)
Skill(skill=".claude-plugin:copilot-spawner", args="Git operations")  # 60% cheaper

# Only use Claude subagents for strategic reasoning
Task(subagent_type="sonnet", prompt="Architecture analysis")  # Necessary cost
```
