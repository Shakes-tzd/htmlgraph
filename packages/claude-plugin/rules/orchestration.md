# Orchestration Rules - Cost-First Multi-AI Delegation

**CRITICAL: When operating in orchestrator mode, you MUST delegate ALL operations except a minimal set of strategic activities.**

## Cost-First Delegation Priority

**IMPERATIVE: ALWAYS choose the cheapest/best model for each task type.**

Use this decision tree IN ORDER (check each before falling back):

1. **Exploration/Research** → `spawn_gemini()` (FREE, 2M tokens/min)
2. **Code Implementation** → `spawn_codex()` ($, specialized for code)
3. **Git/GitHub Operations** → `spawn_copilot()` ($, GitHub integration)
4. **Deep Reasoning/Architecture** → Claude Opus ($$$$, via Task)
5. **Multi-Agent Coordination** → Claude Sonnet ($$$, via Task)
6. **FALLBACK ONLY** → Task() with Haiku ($$, when above unavailable)

### Using HeadlessSpawner

**REQUIRED: Import and use HeadlessSpawner for multi-AI delegation.**

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# Exploration (FREE!)
result = spawner.spawn_gemini(
    prompt="Analyze codebase patterns for authentication...",
    model="gemini-2.0-flash-exp"
)

# Code implementation (cheaper than Claude)
result = spawner.spawn_codex(
    prompt="Implement JWT authentication middleware...",
    model="gpt-4"
)

# Git operations (specialized for GitHub)
result = spawner.spawn_copilot(
    prompt="Commit changes with message: 'feat: add auth'",
    allow_all_tools=True
)
```

### Why Not Task()?

Task() is ONLY for Claude-specific work:
- ❌ NOT for exploration (use Gemini FREE instead)
- ❌ NOT for code implementation (use Codex, specialized)
- ❌ NOT for git/GitHub operations (use Copilot)
- ✅ YES for strategic coordination across models
- ✅ YES for multi-agent orchestration
- ✅ YES for architecture/design decisions
- ✅ YES when other models unavailable

**Cost Example**:
- Exploring 100 files: Task($15-25) vs Gemini(FREE) = 100% savings
- Code generation: Task($10) vs Codex($3) = 70% savings
- Git operations: Task($5) vs Copilot($2) = 60% savings

**Token Cache Consideration**:
Task() provides 5x cheaper prompt caching for RELATED sequential work within same conversation. However, for independent tasks or when other models are better suited, HeadlessSpawner saves more overall.

## Model Selection Reference

For detailed model selection logic, see:
- `/multi-ai-orchestration` skill (comprehensive guide)
- `src/python/htmlgraph/orchestration/model_selection.py` (decision matrix)
- `src/python/htmlgraph/orchestration/headless_spawner.py` (implementation)

## Core Philosophy

**You don't know the outcome before running a tool.** What looks like "one bash call" often becomes 2, 3, 4+ calls when handling failures, conflicts, hooks, or errors. Delegation preserves strategic context by isolating tactical execution in subagent threads.

## Operations You MUST Delegate

**ALL operations EXCEPT:**
- `Task()` - Delegation itself (but prefer HeadlessSpawner when possible)
- `AskUserQuestion()` - Clarifying requirements with user
- `TodoWrite()` - Tracking work items
- SDK operations - Creating features, spikes, bugs, analytics

**Everything else MUST be delegated**, including:

### 1. Git Operations - ALWAYS use Copilot

**REQUIRED: MUST use spawn_copilot() for all git/GitHub operations.**

- ❌ NEVER run git commands directly (add, commit, push, branch, merge)
- ❌ NEVER use Task() for git operations (expensive, not specialized)
- ✅ ALWAYS use spawn_copilot() (cheaper, GitHub-specialized)

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
```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# ✅ CORRECT - Use Copilot for git
result = spawner.spawn_copilot(
    prompt="""
    Commit and push changes to git:

    Files: CLAUDE.md, SKILL.md, git-commit-push.sh
    Message: "docs: enforce strict git delegation in orchestrator directives"

    Steps:
    1. Run ./scripts/git-commit-push.sh "docs: enforce..." --no-confirm
    2. If script doesn't exist, use manual git workflow:
       - git add [files]
       - git commit -m "message"
       - git push origin main
    3. Handle any errors (pre-commit hooks, conflicts, push failures)
    4. Retry with fixes if needed

    Report final status: success or failure with details.
    """,
    allow_all_tools=True
)

# ❌ INCORRECT - Don't use Task() for git
Task(prompt="commit changes...", subagent_type="general-purpose")
```

### 2. Code Changes - ALWAYS use Codex

**REQUIRED: MUST use spawn_codex() for code implementation (unless trivial).**

- ❌ NEVER use Task() for code generation (expensive, not specialized)
- ❌ Multi-file edits → MUST use Codex
- ❌ Implementation requiring research → MUST use Codex
- ❌ Changes with testing requirements → MUST use Codex
- ✅ Single-line typo fixes (OK to do directly)

**IMPERATIVE Delegation pattern:**
```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# ✅ CORRECT - Use Codex for code
result = spawner.spawn_codex(
    prompt="Implement authentication middleware with JWT...",
    model="gpt-4"
)

# ❌ INCORRECT - Don't use Task() for code
Task(prompt="implement feature...", subagent_type="general-purpose")
```

### 3. Research & Exploration - ALWAYS use Gemini

**REQUIRED: MUST use spawn_gemini() for exploration (FREE!).**

- ❌ NEVER use Task() for exploration (expensive)
- ❌ Large codebase searches → MUST use Gemini (FREE)
- ❌ Understanding unfamiliar systems → MUST use Gemini (FREE)
- ❌ Documentation research → MUST use Gemini (FREE)
- ✅ Single file quick lookup (OK to do directly)

**IMPERATIVE Delegation pattern:**
```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# ✅ CORRECT - Use Gemini for exploration (FREE!)
result = spawner.spawn_gemini(
    prompt="Analyze all authentication patterns in codebase...",
    model="gemini-2.0-flash-exp"
)

# ❌ INCORRECT - Don't use Task() for exploration (costs $15-25)
Task(prompt="analyze codebase...", subagent_type="explorer")
```

### 4. Testing & Validation - MUST DELEGATE

**REQUIRED: MUST delegate testing operations.**

- ❌ Running test suites → MUST delegate (prefer Codex for specialized testing)
- ❌ Debugging test failures → MUST delegate
- ❌ Quality gate validation → MUST delegate
- ✅ Checking test command exists (OK to do directly)

**Delegation pattern:**
```python
# Use Codex for testing (specialized) or Task as fallback
result = spawner.spawn_codex(
    prompt="Run pytest suite and fix any failures...",
    model="gpt-4"
)
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

**REQUIRED: MUST use spawn_gemini() for analysis (FREE!).**

- ❌ Performance profiling → MUST use Gemini (FREE)
- ❌ Large-scale analysis → MUST use Gemini (FREE)
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
   - If yes → MUST use spawn_gemini() (FREE)

2. **Is this code implementation?**
   - If yes → MUST use spawn_codex() (cheaper, specialized)

3. **Is this git/GitHub operation?**
   - If yes → MUST use spawn_copilot() (cheaper, specialized)

4. **Is this strategic coordination?**
   - If yes → MAY use Task() with Opus/Sonnet

5. **Is this a trivial single tool call?**
   - If yes AND certain → MAY do directly
   - If uncertain → MUST delegate to appropriate model

## Orchestrator Reflection System

When orchestrator mode is enabled (strict), you'll receive reflections after direct tool execution:

```
ORCHESTRATOR REFLECTION: You executed code directly.

Ask yourself:
- Could this have been delegated to Gemini (FREE)?
- Could this have been delegated to Codex (70% cheaper)?
- Could this have been delegated to Copilot (60% cheaper)?
- What if this operation fails - how many retries will consume context?
- Would parallel HeadlessSpawner calls have been faster?
```

Use these reflections to adjust your delegation habits.

## Integration with HtmlGraph SDK

Always use SDK to track orchestration activities:

```python
from htmlgraph import SDK
from htmlgraph.orchestration import HeadlessSpawner

sdk = SDK(agent='orchestrator')
spawner = HeadlessSpawner()

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

# Spawn subagents with appropriate models
research_result = spawner.spawn_gemini(
    prompt="Find all auth-related code and analyze patterns",
    model="gemini-2.0-flash-exp"
)

code_result = spawner.spawn_codex(
    prompt="Implement OAuth flow based on research findings",
    model="gpt-4"
)

git_result = spawner.spawn_copilot(
    prompt="Commit changes with message: 'feat: add OAuth'",
    allow_all_tools=True
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

When operating as orchestrator, ALWAYS use Copilot for git operations:

```python
from htmlgraph.orchestration import HeadlessSpawner

spawner = HeadlessSpawner()

# ✅ CORRECT - Use Copilot for git workflow
result = spawner.spawn_copilot(
    prompt="""
    Commit and push changes to git:

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
    After successful commit, update the active feature/spike with completion status.
    """,
    allow_all_tools=True
)

# ❌ INCORRECT - Don't use Task() for git (expensive)
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
