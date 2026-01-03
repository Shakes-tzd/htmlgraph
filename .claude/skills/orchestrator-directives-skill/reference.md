# Orchestrator Directives - Complete Reference

This document contains the complete orchestration rules and patterns for HtmlGraph project.

**Source:** `packages/claude-plugin/rules/orchestration.md`

---

## Core Philosophy

**CRITICAL: When operating in orchestrator mode, you MUST delegate ALL operations except a minimal set of strategic activities.**

**You don't know the outcome before running a tool.** What looks like "one bash call" often becomes 2, 3, 4+ calls when handling failures, conflicts, hooks, or errors. Delegation preserves strategic context by isolating tactical execution in subagent threads.

## Operations You MUST Delegate

**ALL operations EXCEPT:**
- `Task()` - Delegation itself
- `AskUserQuestion()` - Clarifying requirements with user
- `TodoWrite()` - Tracking work items
- SDK operations - Creating features, spikes, bugs, analytics

**Everything else MUST be delegated**, including:

### 1. Git Operations - ALWAYS DELEGATE

- ❌ NEVER run git commands directly (add, commit, push, branch, merge)
- ✅ ALWAYS delegate to subagent with error handling

**Why?** Git operations cascade unpredictably:
- Commit hooks may fail (need fix + retry)
- Conflicts may occur (need resolution + retry)
- Push may fail (need pull + merge + retry)
- Tests may fail in hooks (need fix + retry)

**Context cost comparison:**
```
Direct execution: 7+ tool calls
  git add → commit fails (hook) → fix code → commit → push fails → pull → push

Delegation: 2 tool calls
  Task(delegate git workflow) → Read result
```

**Delegation pattern:**
```python
Task(
    prompt="""
    Commit and push changes:
    Files: CLAUDE.md, SKILL.md, git-commit-push.sh
    Message: "docs: enforce strict git delegation in orchestrator directives"

    Steps:
    1. git add [files]
    2. git commit -m "message"
    3. git push origin main
    4. Handle any errors (pre-commit hooks, conflicts, etc)

    🔴 CRITICAL - Report Results to HtmlGraph:
    [include SDK save pattern here]
    """,
    subagent_type="general-purpose"
)
```

### 2. Code Changes - DELEGATE Unless Trivial

- ❌ Multi-file edits
- ❌ Implementation requiring research
- ❌ Changes with testing requirements
- ✅ Single-line typo fixes (OK to do directly)

### 3. Research & Exploration - ALWAYS DELEGATE

- ❌ Large codebase searches (multiple Grep/Glob calls)
- ❌ Understanding unfamiliar systems
- ❌ Documentation research
- ✅ Single file quick lookup (OK to do directly)

### 4. Testing & Validation - ALWAYS DELEGATE

- ❌ Running test suites
- ❌ Debugging test failures
- ❌ Quality gate validation
- ✅ Checking test command exists (OK to do directly)

### 5. Build & Deployment - ALWAYS DELEGATE

- ❌ Build processes
- ❌ Package publishing
- ❌ Environment setup
- ✅ Checking deployment script exists (OK to do directly)

### 6. File Operations - DELEGATE Complex Operations

- ❌ Batch file operations (multiple files)
- ❌ Large file reading/writing
- ❌ Complex file transformations
- ✅ Reading single config file (OK to do directly)
- ✅ Writing single small file (OK to do directly)

### 7. Analysis & Computation - DELEGATE Heavy Work

- ❌ Performance profiling
- ❌ Large-scale analysis
- ❌ Complex calculations
- ✅ Simple status checks (OK to do directly)

## Why Strict Delegation Matters

### 1. Context Preservation

- Each tool call consumes tokens
- Failed operations consume MORE tokens
- Cascading failures consume MOST tokens
- Delegation isolates failure to subagent context

### 2. Parallel Efficiency

- Multiple subagents can work simultaneously
- Orchestrator stays available for decisions
- Higher throughput on independent tasks

### 3. Error Isolation

- Subagent handles retries and recovery
- Orchestrator receives clean success/failure
- No pollution of strategic context

### 4. Cognitive Clarity

- Orchestrator maintains high-level view
- Subagents handle tactical details
- Clear separation of concerns

## Decision Framework

Ask yourself:

1. **Will this likely be one tool call?**
   - If uncertain → DELEGATE
   - If certain → MAY do directly

2. **Does this require error handling?**
   - If yes → DELEGATE

3. **Could this cascade into multiple operations?**
   - If yes → DELEGATE

4. **Is this strategic (decisions) or tactical (execution)?**
   - Strategic → Do directly
   - Tactical → DELEGATE

## Orchestrator Reflection System

When orchestrator mode is enabled (strict), you'll receive reflections after direct tool execution:

```
ORCHESTRATOR REFLECTION: You executed code directly.

Ask yourself:
- Could this have been delegated to a subagent?
- Would parallel Task() calls have been faster?
- Is a work item tracking this effort?
- What if this operation fails - how many retries will consume context?
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
        "Research existing auth patterns (delegated to explorer)",
        "Implement OAuth flow (delegated to coder)",
        "Add tests (delegated to test-runner)",
        "Commit changes (delegated to general-purpose)"
    ]) \
    .save()

# Spawn subagents with tracked context
explorer = sdk.spawn_explorer(
    task="Find all auth-related code",
    scope="src/",
    questions=["What library is used?", "Where is validation?"]
)

Task(
    prompt=explorer["prompt"],
    description=explorer["description"],
    subagent_type=explorer["subagent_type"]
)
```

**See:** `packages/claude-plugin/skills/htmlgraph-orchestrator/SKILL.md` for complete orchestrator patterns

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

When operating as orchestrator, delegate ALL git operations:

```python
# ✅ CORRECT - Delegate git workflow to subagent
Task(
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
    subagent_type="general-purpose"
)

# Then read subagent result and continue orchestration
```

**Why delegate?** Git operations cascade unpredictably:
- Pre-commit hooks may fail → need code fix → retry commit
- Push may fail due to conflicts → need pull → merge → retry push
- Tests may fail in hooks → need debugging → fix → retry

**Context cost:**
- Direct execution: 5-10+ tool calls (with failures and retries)
- Delegation: 2 tool calls (Task + result review)

## Detailed Delegation Examples

### Example 1: Feature Implementation Workflow

```python
from htmlgraph import SDK
sdk = SDK(agent='orchestrator')

# 1. Create feature (orchestrator does this directly)
feature = sdk.features.create("Add user authentication") \
    .set_priority("high") \
    .add_steps([
        "Research existing auth patterns",
        "Implement OAuth flow",
        "Add tests",
        "Commit changes"
    ]) \
    .save()

# 2. Delegate research
research_id, research_prompt = delegate_with_id(
    "Research auth patterns",
    """
    Research existing authentication patterns:

    Questions to answer:
    - What library is currently used?
    - Where is validation implemented?
    - Are there existing tests?
    - What OAuth providers are supported?

    Document findings in HtmlGraph spike.
    """,
    "general-purpose"
)

Task(
    prompt=research_prompt,
    description=f"{research_id}: Research auth patterns",
    subagent_type="general-purpose"
)

# 3. Wait for research results
research_results = get_results_by_task_id(sdk, research_id, timeout=120)

# 4. Delegate implementation (based on research)
impl_id, impl_prompt = delegate_with_id(
    "Implement OAuth",
    f"""
    Implement OAuth flow based on research findings:

    Research results:
    {research_results['findings']}

    Requirements:
    - Add JWT auth to API endpoints
    - Create middleware for token validation
    - Support Google and GitHub OAuth

    Document implementation in HtmlGraph spike.
    """,
    "general-purpose"
)

Task(
    prompt=impl_prompt,
    description=f"{impl_id}: Implement OAuth",
    subagent_type="general-purpose"
)

# 5. Wait for implementation
impl_results = get_results_by_task_id(sdk, impl_id, timeout=300)

# 6. Delegate testing
test_id, test_prompt = delegate_with_id(
    "Test auth flow",
    """
    Write tests for authentication flow:

    - Unit tests for middleware
    - Integration tests for OAuth flow
    - End-to-end tests for user login

    Run tests and document results in spike.
    """,
    "general-purpose"
)

Task(
    prompt=test_prompt,
    description=f"{test_id}: Test auth flow",
    subagent_type="general-purpose"
)

# 7. Wait for testing
test_results = get_results_by_task_id(sdk, test_id, timeout=180)

# 8. Delegate git commit
git_id, git_prompt = delegate_with_id(
    "Commit auth feature",
    """
    Commit and push authentication feature:

    Message: "feat: add user authentication with OAuth support"

    Steps:
    1. Run ./scripts/git-commit-push.sh "feat: add user authentication with OAuth support" --no-confirm
    2. If script doesn't exist, use manual git workflow
    3. Handle any errors (hooks, conflicts, etc)

    Report final status.
    """,
    "general-purpose"
)

Task(
    prompt=git_prompt,
    description=f"{git_id}: Commit auth feature",
    subagent_type="general-purpose"
)

# 9. Update feature status (orchestrator does this directly)
feature.set_status("completed").save()
```

### Example 2: Bug Fix Workflow

```python
from htmlgraph import SDK
sdk = SDK(agent='orchestrator')

# 1. Create bug (orchestrator does this directly)
bug = sdk.bugs.create("Session timeout not working") \
    .set_priority("critical") \
    .add_description("Users report sessions timing out too early") \
    .save()

# 2. Delegate investigation
investigate_id, investigate_prompt = delegate_with_id(
    "Investigate session timeout",
    """
    Debug session timeout issue:

    Symptoms:
    - Users report sessions timing out too early
    - Expected: 30 min timeout
    - Observed: ~5 min timeout

    Tasks:
    1. Find session timeout configuration
    2. Check middleware implementation
    3. Review logs for timeout events
    4. Identify root cause

    Document findings in HtmlGraph spike.
    """,
    "general-purpose"
)

Task(
    prompt=investigate_prompt,
    description=f"{investigate_id}: Investigate session timeout",
    subagent_type="general-purpose"
)

# 3. Wait for investigation
investigate_results = get_results_by_task_id(sdk, investigate_id, timeout=180)

# 4. Delegate fix (based on investigation)
fix_id, fix_prompt = delegate_with_id(
    "Fix session timeout",
    f"""
    Fix session timeout based on investigation:

    Root cause:
    {investigate_results['findings']}

    Requirements:
    - Set timeout to 30 minutes
    - Add tests to prevent regression
    - Verify fix works

    Document fix in HtmlGraph spike.
    """,
    "general-purpose"
)

Task(
    prompt=fix_prompt,
    description=f"{fix_id}: Fix session timeout",
    subagent_type="general-purpose"
)

# 5. Wait for fix
fix_results = get_results_by_task_id(sdk, fix_id, timeout=240)

# 6. Delegate git commit
git_id, git_prompt = delegate_with_id(
    "Commit bug fix",
    """
    Commit and push session timeout fix:

    Message: "fix: correct session timeout to 30 minutes"

    Steps:
    1. Run ./scripts/git-commit-push.sh "fix: correct session timeout to 30 minutes" --no-confirm
    2. Handle any errors

    Report final status.
    """,
    "general-purpose"
)

Task(
    prompt=git_prompt,
    description=f"{git_id}: Commit bug fix",
    subagent_type="general-purpose"
)

# 7. Update bug status (orchestrator does this directly)
bug.set_status("resolved").save()
```

### Example 3: Parallel Task Coordination

```python
from htmlgraph import SDK
from htmlgraph.orchestration import delegate_with_id, get_results_by_task_id

sdk = SDK(agent='orchestrator')

# Create feature with parallel subtasks
feature = sdk.features.create("Refactor API layer") \
    .set_priority("medium") \
    .save()

# Spawn 3 parallel tasks
docs_id, docs_prompt = delegate_with_id(
    "Update API docs",
    "Update API documentation to reflect new endpoints",
    "general-purpose"
)

tests_id, tests_prompt = delegate_with_id(
    "Update API tests",
    "Update test suite for refactored API endpoints",
    "general-purpose"
)

migrate_id, migrate_prompt = delegate_with_id(
    "Create migration guide",
    "Create migration guide for API changes",
    "general-purpose"
)

# Delegate all in parallel (single message, multiple Task calls)
Task(prompt=docs_prompt, description=f"{docs_id}: Update API docs")
Task(prompt=tests_prompt, description=f"{tests_id}: Update API tests")
Task(prompt=migrate_prompt, description=f"{migrate_id}: Create migration guide")

# Retrieve results independently (order doesn't matter)
docs_results = get_results_by_task_id(sdk, docs_id, timeout=120)
tests_results = get_results_by_task_id(sdk, tests_id, timeout=180)
migrate_results = get_results_by_task_id(sdk, migrate_id, timeout=90)

# All tasks complete - commit everything
git_id, git_prompt = delegate_with_id(
    "Commit API refactor",
    """
    Commit all API refactoring changes:

    Message: "refactor: update API layer with improved endpoints"

    Changes include:
    - Updated documentation
    - Updated tests
    - Migration guide

    Commit and push all changes.
    """,
    "general-purpose"
)

Task(
    prompt=git_prompt,
    description=f"{git_id}: Commit API refactor",
    subagent_type="general-purpose"
)

# Update feature
feature.set_status("completed").save()
```

## Common Anti-Patterns to Avoid

### Anti-Pattern 1: Direct Git Execution

```python
# ❌ WRONG - Orchestrator executing git directly
Bash(command="git add .")
Bash(command="git commit -m 'feat: new feature'")
Bash(command="git push origin main")

# This will likely fail due to:
# - Pre-commit hooks
# - Merge conflicts
# - Remote changes
# Each failure consumes context and requires recovery
```

```python
# ✅ CORRECT - Delegate to subagent
Task(
    prompt="""
    Commit and push changes:
    Message: "feat: new feature"
    Handle all errors (hooks, conflicts, etc)
    """,
    subagent_type="general-purpose"
)
```

### Anti-Pattern 2: Sequential When Parallel is Possible

```python
# ❌ WRONG - Sequential delegation
Task(prompt="Update docs")
# Wait for result...
Task(prompt="Update tests")
# Wait for result...
Task(prompt="Update migration guide")

# Total time: T1 + T2 + T3
```

```python
# ✅ CORRECT - Parallel delegation
Task(prompt="Update docs")
Task(prompt="Update tests")
Task(prompt="Update migration guide")

# Total time: max(T1, T2, T3)
```

### Anti-Pattern 3: Not Using Task IDs

```python
# ❌ WRONG - No task IDs, can't distinguish results
Task(prompt="Research auth patterns")
Task(prompt="Research caching patterns")
Task(prompt="Research logging patterns")

# Which result is which?
```

```python
# ✅ CORRECT - Use task IDs
auth_id, auth_prompt = delegate_with_id("Research auth", "...", "general-purpose")
cache_id, cache_prompt = delegate_with_id("Research caching", "...", "general-purpose")
log_id, log_prompt = delegate_with_id("Research logging", "...", "general-purpose")

Task(prompt=auth_prompt, description=f"{auth_id}: Research auth")
Task(prompt=cache_prompt, description=f"{cache_id}: Research caching")
Task(prompt=log_prompt, description=f"{log_id}: Research logging")

# Retrieve results independently
auth_results = get_results_by_task_id(sdk, auth_id)
cache_results = get_results_by_task_id(sdk, cache_id)
log_results = get_results_by_task_id(sdk, log_id)
```

### Anti-Pattern 4: Not Tracking Work Items

```python
# ❌ WRONG - No feature/bug tracking
Task(prompt="Implement new feature")
# No record of what was planned or completed
```

```python
# ✅ CORRECT - Track with HtmlGraph SDK
feature = sdk.features.create("Implement new feature") \
    .set_priority("high") \
    .save()

Task(prompt="Implement new feature")

# Update status after completion
feature.set_status("completed").save()
```

## Summary

**Key Principles:**

1. **Delegate Everything** - Except Task(), AskUserQuestion(), TodoWrite(), and SDK operations
2. **Use Task IDs** - For parallel coordination and result tracking
3. **Track Work** - Use HtmlGraph SDK for all features, bugs, spikes
4. **Parallel > Sequential** - Delegate independently when possible
5. **Git = Always Delegate** - Never run git commands directly

**Benefits:**

- Context preservation (fewer tokens consumed)
- Parallel efficiency (faster completion)
- Error isolation (cleaner orchestration)
- Cognitive clarity (strategic focus)

**When in doubt, DELEGATE.**
