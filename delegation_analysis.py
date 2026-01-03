#!/usr/bin/env python3
"""Create delegation failure analysis spike."""

from htmlgraph import SDK

sdk = SDK(agent="copilot")
spike = sdk.spikes.create("Delegation Failure Analysis - GitHub Issues #19 and #20")
spike.set_findings("""# Delegation Failure Analysis

## Executive Summary

Analyzed two critical delegation failure issues (#19 and #20) from another project that expose fundamental weaknesses in orchestrator mode enforcement. These same vulnerabilities exist in HtmlGraph and require immediate fixes.

## Issues Analyzed

### Issue #19: Skills Bypass Delegation Enforcement
**Problem**: Orchestrator invoked Skill tool directly instead of delegating, bypassing all enforcement.

**What Happened**:
- Orchestrator called: Skill(skill="frontend-design:frontend-design")
- Skill executed in main context consuming ~6,000 tokens
- Should have delegated via Task() consuming ~200 tokens (30x savings)

**Root Cause**: Skills execute in main conversation context, providing escape hatch around delegation rules.

**Impact**:
- Defeats orchestrator mode purpose (context efficiency)
- Creates inconsistent behavior
- Easy to bypass accidentally

### Issue #20: Direct Bash Execution (Meta-Violation)
**Problem**: While submitting issue #19, orchestrator executed 8+ bash calls directly instead of delegating.

**What Happened**:
1. grep -r "github" .htmlgraph/
2. ls -la ~/.claude/plugins/cache/
3. cat plugin.json
4. find plugins
5. uv run htmlgraph --help | grep
6. gh issue create (failed - wrong repo)
7. gh issue create (failed - wrong labels)
8. gh issue create (succeeded)

**Context Cost**: ~500+ tokens vs ~50 tokens (single delegation)

**Root Cause**: Orchestrator directives say delegate "everything" but enforcement incomplete.

### Currently Allowed (Incorrectly):
- ✅ Task() - CORRECT
- ✅ AskUserQuestion() - CORRECT
- ✅ TodoWrite() - CORRECT
- ✅ SDK operations - CORRECT
- ❌ Bash commands - SHOULD BE DELEGATED
- ❌ File operations (Read, Write, Edit) - SHOULD BE DELEGATED
- ❌ Skills - SHOULD BE DELEGATED

## HtmlGraph Vulnerability Analysis

### 1. Skills Bypass (Issue #19 Pattern)

**HtmlGraph Status**: ✅ PARTIALLY PROTECTED

From src/python/htmlgraph/hooks/orchestrator.py:121-122:
```python
if tool in ["Task", "AskUserQuestion", "TodoWrite"]:
    return True, "", "orchestrator-core"
```

**Finding**: Skills are NOT in the always-allowed list, BUT there is no explicit blocking either.

**Test Required**:
```python
# Does HtmlGraph block this?
Skill(skill="code-quality:code-quality", args="...")
```

**Risk Level**: MEDIUM
- Skills not explicitly allowed
- But may slip through as "allowed-default" category (line 204)

### 2. Bash Command Bypass (Issue #20 Pattern)

**HtmlGraph Status**: ⚠️ VULNERABLE

From orchestrator.py:125-142:
```python
if tool == "Bash":
    # Allow SDK commands
    if command.startswith("uv run htmlgraph "):
        return True, "", "sdk-command"

    # Allow git read-only
    if command.startswith("git status"):
        return True, "", "git-readonly"

    # Allow SDK inline
    if "from htmlgraph import" in command:
        return True, "", "sdk-inline"
```

**Finding**: ONLY allows specific Bash patterns. Everything else goes to line 184-201 blocking patterns.

**BUT** - if command does not match blocked patterns (test/build), it falls through to:
```python
# Line 204: Default allow
return True, "Allowed but consider if delegation would be better", "allowed-default"
```

**Risk Level**: HIGH
- gh commands not explicitly blocked
- Generic bash commands may slip through
- "allowed-default" defeats strict mode purpose

### 3. Read/Grep/Glob Sequence Detection

**HtmlGraph Status**: ✅ GOOD APPROACH, ⚠️ INCOMPLETE

From orchestrator.py:145-160:
```python
if tool in ["Read", "Grep", "Glob"]:
    history = load_tool_history()
    recent_same_tool = sum(1 for h in history[-3:] if h["tool"] == tool)

    if recent_same_tool == 0:  # First use
        return True, "Single lookup allowed", "single-lookup"
    else:
        return False, "Multiple {tool} calls. Delegate to Explorer.", "multi-lookup-blocked"
```

**Finding**: Good pattern detection but ONLY blocks if SAME tool repeated.

**Vulnerability**: Alternating tools bypasses this:
```
Read → Grep → Read → Grep → Read (5 calls, none blocked!)
```

**Risk Level**: MEDIUM
- Detects same-tool sequences
- Misses mixed exploration patterns

## Proposed Solutions

### Solution 1: Strict Whitelist (RECOMMENDED)

**Implementation**:
```python
# In orchestrator.py enforce_orchestrator_mode()

if enforcement_level == "strict":
    # WHITELIST: Only these tools allowed
    ALLOWED_TOOLS = {
        "Task", "AskUserQuestion", "TodoWrite",
        # SDK operations detected via params
    }

    if tool not in ALLOWED_TOOLS:
        # Check if SDK operation
        if not is_sdk_operation(tool, params):
            # BLOCK with delegation suggestion
            return create_strict_block_response(tool, params)
```

**Changes Required**:
1. Remove "allowed-default" fallback in strict mode
2. Add is_sdk_operation() function for Bash SDK detection
3. Block ALL tools except whitelist + SDK operations

**Benefits**:
- Makes strict mode actually strict
- Clear behavioral boundary
- No escape hatches

### Solution 2: Auto-Delegation Wrapper

**Implementation**:
```python
# In hook PreToolUse handler

if enforcement_level == "strict" and tool not in ALLOWED_TOOLS:
    # Auto-wrap in Task delegation
    suggested_task = create_task_wrapper(tool, params)

    # Return modified tool call
    return {
        "hookSpecificOutput": {
            "permissionDecision": "allow",
            "modifiedToolCall": {
                "tool": "Task",
                "params": {
                    "prompt": suggested_task,
                    "subagent_type": "general-purpose"
                }
            }
        }
    }
```

**Benefits**:
- Transparent to user
- Impossible to bypass
- Automatic delegation

**Drawbacks**:
- May delegate when user wanted direct execution
- Harder to debug
- More complex implementation

### Solution 3: Escalating Enforcement (CURRENT HTMLGRAPH)

**Status**: PARTIALLY IMPLEMENTED

From orchestrator.py:416-437:
```python
if enforcement_level == "strict":
    mode = manager.increment_violation()
    violations = mode.violations

    if violations >= 3:
        error_message += "CIRCUIT BREAKER TRIGGERED"
```

**Finding**: Circuit breaker exists but violations accumulate TOO SLOWLY.

**Gap**: "allowed-default" tools do not increment violations, so circuit breaker never triggers!

### Solution 4: Context Budget Tracking

**New Feature Proposal**:
```python
class ContextBudgetTracker:
    def __init__(self, budget: int = 5000):
        self.budget = budget
        self.used = 0

    def charge(self, tool: str, estimate: int):
        self.used += estimate
        if self.used > self.budget:
            # Force strict delegation mode
            raise ContextBudgetExceeded()
```

**Benefits**:
- Shows REAL cost of violations
- Motivates delegation
- Educational

## Immediate Action Items

### 1. Fix "allowed-default" Escape Hatch (CRITICAL)
```python
# orchestrator.py:204 - REMOVE THIS IN STRICT MODE
# Line 204: Default allow
return True, "Allowed but consider...", "allowed-default"

# Replace with:
if enforcement_level == "strict":
    return False, "Not in allowed whitelist", "strict-blocked"
else:
    return True, "Allowed in guidance mode", "guidance-allowed"
```

### 2. Add Skill Blocking (HIGH)
```python
# orchestrator.py - Add after line 122
if tool == "Skill" and enforcement_level == "strict":
    return False, "Skills must be invoked via Task delegation", "skill-blocked"
```

### 3. Improve Multi-Tool Detection (MEDIUM)
```python
# Track TOTAL exploration tools in window, not just same-tool
exploration_count = sum(1 for h in history[-5:] if h["tool"] in ["Read", "Grep", "Glob"])
if exploration_count >= 3:
    return False, "Multiple exploration calls. Delegate to Explorer.", "exploration-blocked"
```

### 4. Add Bash Command Fallback Block (HIGH)
```python
# orchestrator.py:202 - Before "allowed-default"
if tool == "Bash" and enforcement_level == "strict":
    # If we got here, command not in whitelist
    return False, "Bash command not in allowed list. Delegate.", "bash-blocked"
```

## Testing Requirements

### Test Case 1: Skill Bypass
```python
# Should BLOCK in strict mode
Skill(skill="code-quality")
```

### Test Case 2: Generic Bash
```python
# Should BLOCK in strict mode
Bash(command="gh issue create")
Bash(command="curl https://api.github.com")
```

### Test Case 3: Mixed Exploration
```python
# Should BLOCK after 3 tools
Read("file1.py")  # Allowed
Grep("pattern")   # Allowed
Read("file2.py")  # BLOCKED (3rd exploration tool)
```

### Test Case 4: Circuit Breaker
```python
# Should trigger after 3 violations
Edit("file.py")  # Violation 1
Write("file2.py") # Violation 2
Edit("file3.py")  # Violation 3 → Circuit breaker
Edit("file4.py")  # HARD BLOCK
```

## Comparison: Issue Project vs HtmlGraph

| Aspect | Issue Project | HtmlGraph | Status |
|--------|---------------|-----------|--------|
| Skill blocking | ❌ No enforcement | ⚠️ Partial | NEEDS FIX |
| Bash blocking | ❌ Not blocked | ⚠️ Whitelist only | NEEDS FIX |
| Read/Grep blocking | ❌ Not blocked | ✅ Sequence detected | GOOD |
| Circuit breaker | ❌ No mechanism | ✅ Implemented | GOOD |
| Violation tracking | ❌ No tracking | ✅ Tracks violations | GOOD |
| Default fallback | ❌ Always allows | ⚠️ "allowed-default" | NEEDS FIX |

## Recommendations

### Priority 1: Close Escape Hatches
1. Remove "allowed-default" in strict mode
2. Block Skills in strict mode
3. Block non-whitelisted Bash commands

### Priority 2: Improve Detection
1. Track mixed exploration patterns
2. Charge violations for allowed-default hits
3. Add context budget tracking

### Priority 3: Testing & Validation
1. Add test suite for all bypass scenarios
2. Document expected behavior per enforcement level
3. Add usage analytics to measure effectiveness

## Success Metrics

- ✅ 0 bypass routes in strict mode
- ✅ 80%+ context savings (measured)
- ✅ Circuit breaker triggers reliably
- ✅ Clear error messages guide correct behavior

## Related Issues

- GH #19: Skills bypass delegation enforcement
- GH #20: Direct bash execution meta-violation
- HtmlGraph: orchestrator.py lines 204, 121-122 (vulnerabilities)
""")
saved_spike = spike.save()
print(f"Spike created: {saved_spike.id}")
print(saved_spike.findings[:500])
