# Orchestrator Directives Skill

Use this skill when operating in orchestrator mode to understand delegation patterns and decision frameworks.

**Trigger keywords:** orchestrator, delegation, subagent, task coordination, parallel execution

---

## Overview

When operating in orchestrator mode, you MUST delegate ALL operations except a minimal set of strategic activities. This skill provides the patterns and decision framework for effective delegation.

## Core Philosophy

**You don't know the outcome before running a tool.** What looks like "one bash call" often becomes 2, 3, 4+ calls when handling failures, conflicts, hooks, or errors. Delegation preserves strategic context by isolating tactical execution in subagent threads.

## Quick Reference: What to Delegate

### Operations You CAN Execute Directly

- `Task()` - Delegation itself
- `AskUserQuestion()` - Clarifying requirements with user
- `TodoWrite()` - Tracking work items
- SDK operations - Creating features, spikes, bugs, analytics
- Single file quick lookup (simple Read)
- Single small file write (simple Write)
- Simple status checks

### Operations You MUST Delegate

**1. Git Operations - ALWAYS DELEGATE**
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

**2. Code Changes - DELEGATE Unless Trivial**
- ❌ Multi-file edits
- ❌ Implementation requiring research
- ❌ Changes with testing requirements
- ✅ Single-line typo fixes (OK to do directly)

**3. Research & Exploration - ALWAYS DELEGATE**
- ❌ Large codebase searches (multiple Grep/Glob calls)
- ❌ Understanding unfamiliar systems
- ❌ Documentation research

**4. Testing & Validation - ALWAYS DELEGATE**
- ❌ Running test suites
- ❌ Debugging test failures
- ❌ Quality gate validation

**5. Build & Deployment - ALWAYS DELEGATE**
- ❌ Build processes
- ❌ Package publishing
- ❌ Environment setup

**6. File Operations - DELEGATE Complex Operations**
- ❌ Batch file operations (multiple files)
- ❌ Large file reading/writing
- ❌ Complex file transformations

**7. Analysis & Computation - DELEGATE Heavy Work**
- ❌ Performance profiling
- ❌ Large-scale analysis
- ❌ Complex calculations

## Decision Framework

Ask yourself these questions:

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

## Common Delegation Patterns

### Git Operations (CRITICAL - ALWAYS DELEGATE)

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

### Code Implementation

```python
# Delegate implementation work
Task(
    prompt="""
    Implement authentication feature:

    Requirements:
    - Add JWT auth to API endpoints
    - Create middleware for token validation
    - Add tests for auth flow

    🔴 CRITICAL - Report Results:
    After implementation, create spike with findings using HtmlGraph SDK.
    """,
    subagent_type="general-purpose"
)
```

### Research & Exploration

```python
# Delegate research work
Task(
    prompt="""
    Research existing authentication patterns:

    Questions to answer:
    - What library is currently used?
    - Where is validation implemented?
    - Are there existing tests?

    🔴 CRITICAL - Report Results:
    Document findings in HtmlGraph spike with all discovered patterns.
    """,
    subagent_type="general-purpose"
)
```

## Why Strict Delegation Matters

**1. Context Preservation**
- Each tool call consumes tokens
- Failed operations consume MORE tokens
- Cascading failures consume MOST tokens
- Delegation isolates failure to subagent context

**2. Parallel Efficiency**
- Multiple subagents can work simultaneously
- Orchestrator stays available for decisions
- Higher throughput on independent tasks

**3. Error Isolation**
- Subagent handles retries and recovery
- Orchestrator receives clean success/failure
- No pollution of strategic context

**4. Cognitive Clarity**
- Orchestrator maintains high-level view
- Subagents handle tactical details
- Clear separation of concerns

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
```

## Parallel Task Coordination

Use task IDs for parallel delegation:

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

## See Also

- **reference.md** - Complete orchestration patterns and detailed examples
- **packages/claude-plugin/skills/htmlgraph-orchestrator/SKILL.md** - Full orchestrator skill
- **.claude/rules/orchestration.md** - Source orchestration rules

## Usage Examples

### Example 1: Feature Implementation

```python
# Orchestrator creates feature
feature = sdk.features.create("Add user authentication") \
    .set_priority("high") \
    .save()

# Delegate research
Task(
    prompt="Research existing auth patterns and document in spike",
    subagent_type="general-purpose"
)

# Delegate implementation (after research completes)
Task(
    prompt="Implement OAuth flow based on research findings",
    subagent_type="general-purpose"
)

# Delegate testing
Task(
    prompt="Write tests for auth flow and validate",
    subagent_type="general-purpose"
)

# Delegate git operations
Task(
    prompt="Commit changes with message 'feat: add user authentication'",
    subagent_type="general-purpose"
)
```

### Example 2: Bug Fix

```python
# Orchestrator creates bug
bug = sdk.bugs.create("Session timeout not working") \
    .set_priority("critical") \
    .save()

# Delegate investigation
Task(
    prompt="Debug session timeout issue and document findings in spike",
    subagent_type="general-purpose"
)

# Delegate fix (after investigation)
Task(
    prompt="Fix session timeout based on investigation findings",
    subagent_type="general-purpose"
)

# Delegate verification
Task(
    prompt="Verify fix works and update bug status",
    subagent_type="general-purpose"
)
```

---

**Remember:** When in doubt, DELEGATE. Orchestrators make decisions, subagents execute tasks.
