---
name: error-analysis
description: Systematically capture, analyze, and track errors with HtmlGraph spike-based investigation workflow
args:
  - name: error_context
    description: Brief description of the error or error message
    required: false
---

# /htmlgraph:error-analysis

Systematically capture, analyze, and track errors with HtmlGraph spike-based investigation workflow.

## Usage

```
/htmlgraph:error-analysis [error_context]
```

## Parameters

- `error_context` (optional): Brief description of the error or error message


## Examples

```bash
/htmlgraph:error-analysis "PreToolUse hook failing with 'No such file'"
```
Capture and analyze a hook error with HtmlGraph tracking

```bash
/htmlgraph:error-analysis
```
Interactive error capture workflow


## Instructions for Claude

**CRITICAL: This command implements systematic error investigation using HtmlGraph spikes.**

This command follows the research-first debugging methodology from `.claude/rules/debugging.md`. It ensures errors are properly documented, investigated systematically, and tracked in HtmlGraph.

### Implementation:

```python
**DO THIS:**

1. **Capture error details:**
   - If error_context provided, use it as starting point
   - Otherwise, use AskUserQuestion to gather:
     - Exact error message
     - When did it occur (what operation)
     - What changed recently (code, config, plugins)
     - Can it be reproduced consistently?
     - Expected vs actual behavior

2. **Categorize the error:**
   Identify error type:
   - **Hook Error** - PreToolUse, PostToolUse, SessionStart failures
   - **API Error** - Network, authentication, rate limits
   - **Build Error** - Compilation, linting, type checking
   - **Runtime Error** - Exceptions, crashes, unexpected behavior
   - **Configuration Error** - Plugin, settings, environment issues
   - **Integration Error** - External services, databases, APIs

3. **Gather relevant context:**
   Collect diagnostic information based on error type:

   For Hook Errors:
   ```bash
   /hooks                    # List all active hooks
   /hooks PreToolUse        # Show specific hook type
   claude --debug <command> # Verbose output
   ```

   For Build Errors:
   ```bash
   uv run ruff check        # Linting errors
   uv run mypy src/         # Type errors
   uv run pytest -v         # Test failures
   ```

   For Runtime Errors:
   - Recent file changes (git diff)
   - Environment variables
   - Dependency versions
   - Stack traces

4. **Create HtmlGraph spike for investigation:**
   ```python
   from htmlgraph import SDK
   sdk = SDK(agent='claude-code')

   # Extract keywords from error message
   def extract_keywords(error_msg: str) -> list[str]:
       """Extract key terms from error message."""
       import re
       # Remove stack traces and focus on error message
       error_text = error_msg.split('\n')[0]  # First line
       # Extract error type and key words
       keywords = re.findall(r'\b\w{4,}\b', error_text.lower())
       return keywords

   error_keywords = extract_keywords(error_message)

   # Search for similar errors in past spikes
   spikes = sdk.spikes.all()
   similar = []

   def calculate_similarity(spike_title: str, keywords: list[str]) -> float:
       """Calculate similarity score."""
       title_words = set(spike_title.lower().split())
       keyword_set = set(keywords)
       intersection = len(title_words & keyword_set)
       union = len(title_words | keyword_set)
       return intersection / union if union > 0 else 0

   for spike in spikes:
       similarity_score = calculate_similarity(spike.title, error_keywords)

       if similarity_score > 0.4:  # 40% similarity threshold
           similar.append({
               "id": spike.id,
               "title": spike.title,
               "similarity": similarity_score,
               "resolution": spike.properties.get("resolution", "N/A"),
               "created": spike.created,
           })

   # Sort by similarity and recency
   similar.sort(key=lambda x: (x['similarity'], x['created']), reverse=True)

   if similar:
       print(f"\n### 📚 Similar Past Issues")
       print(f"\nFound {len(similar)} similar issues from history:")
       for s in similar[:3]:
           print(f"\n**{s['title']}** ({s['id']})")
           print(f"Similarity: {s['similarity']:.0%}")
           print(f"Resolution: {s['resolution']}")
           print(f"View: `/htmlgraph:spike {s['id']}`")

       print(f"\nThese past issues may provide insights for resolution.")
   else:
       print(f"\nNo similar errors found in history.")
       print(f"This appears to be a new type of error.")

   # Determine spike title based on error category
   title = f"Error Investigation: {error_category} - {brief_description}"

   spike = sdk.start_planning_spike(
       title=title,
       context=f"""
       ## Error Details
       **Type:** {error_category}
       **Message:** {error_message}
       **Occurred:** {when_occurred}
       **Reproducible:** {is_reproducible}

       ## Context
       {relevant_context}

       ## Expected Behavior
       {expected_behavior}

       ## Actual Behavior
       {actual_behavior}

       ## Recent Changes
       {recent_changes}

       ## Similar Past Issues
       {similar}
       """,
       timebox_hours=2.0  # Default 2-hour investigation timebox
   )
   ```

5. **Provide systematic investigation prompts:**
   Based on error category, guide investigation:

   **Hook Errors:**
   - [ ] Research hook documentation (use /htmlgraph:research or claude-code-guide)
   - [ ] Check for duplicate hooks across sources
   - [ ] Verify hook file paths and permissions
   - [ ] Test with --debug flag for verbose output
   - [ ] Check plugin versions and compatibility

   **API Errors:**
   - [ ] Verify authentication credentials
   - [ ] Check rate limits and quotas
   - [ ] Test with curl/requests directly
   - [ ] Review API documentation for changes
   - [ ] Check network connectivity

   **Build Errors:**
   - [ ] Run linters: `uv run ruff check --fix`
   - [ ] Check types: `uv run mypy src/`
   - [ ] Run tests: `uv run pytest -v`
   - [ ] Review recent code changes
   - [ ] Check dependency versions

   **Runtime Errors:**
   - [ ] Reproduce error with minimal test case
   - [ ] Check stack trace for root cause
   - [ ] Verify input data and edge cases
   - [ ] Review recent code changes
   - [ ] Test in isolation (unit test)

   **Configuration Errors:**
   - [ ] Validate configuration files (JSON, YAML)
   - [ ] Check environment variables
   - [ ] Verify file paths and permissions
   - [ ] Review plugin settings
   - [ ] Compare with working configuration

6. **Offer debugging agent integration:**
   Based on investigation needs:

   ```
   ## Debugging Resources Available

   **DELEGATION**: Use `Task(subagent_type="htmlgraph:researcher")` for researching documentation and prior art.
   Use `Task(subagent_type="htmlgraph:debugger")` for systematic error investigation.
   Use `Task(subagent_type="htmlgraph:test-runner")` to validate fixes.

   ### Researcher Agent (htmlgraph:researcher)
   Use when you need to understand unfamiliar concepts or APIs:
   - Research Claude Code hook behavior
   - Look up library documentation
   - Find best practices for error handling

   ### Debugger Agent (htmlgraph:debugger)
   Use for systematic error analysis:
   - Reproduce errors consistently
   - Isolate root causes
   - Test hypotheses systematically

   ### Test Runner Agent (htmlgraph:test-runner)
   Use to validate fixes:
   - Run quality gates (lint, type, test)
   - Verify error is resolved
   - Prevent regression
   ```

7. **Document investigation workflow:**
   ```python
   # Add investigation steps to spike
   investigation_steps = [
       "Gather diagnostic information",
       "Research root cause (if unfamiliar)",
       "Form hypothesis about cause",
       "Test hypothesis systematically",
       "Implement minimal fix",
       "Validate fix resolves error",
       "Document learning"
   ]

   with sdk.spikes.edit(spike.id) as s:
       for step in investigation_steps:
           s.add_step(step)
   ```

8. **Output structured investigation plan:**
   Show spike details and next steps
```

### Output Format:

```
## Error Investigation Spike Created

**Spike ID:** {spike.id}
**Title:** {spike.title}
**Category:** {error_category}
**Timebox:** 2 hours

### Error Summary
{formatted_error_details}

### Investigation Checklist
{category_specific_checklist}

### Debugging Tools Available
- `/hooks` - List active hooks
- `claude --debug <command>` - Verbose output
- `/doctor` - System diagnostics
- Quality gates: `uv run ruff check && uv run mypy src/ && uv run pytest`

### Next Steps
1. Complete investigation checklist items
2. Document findings in spike: `/htmlgraph:spike {spike.id}`
3. Delegate to specialized agents:
   - `Task(subagent_type="htmlgraph:researcher")` for unfamiliar concepts
   - `Task(subagent_type="htmlgraph:debugger")` for systematic debugging
   - `Task(subagent_type="htmlgraph:test-runner")` to validate fixes

### Start Investigation
Use these commands to begin:
```bash
# View spike in dashboard
uv run htmlgraph serve
# Open: http://localhost:8080

# Research if needed (unfamiliar error)
/htmlgraph:research "{error topic}"

# Document findings as you investigate
# Findings are auto-tracked in the spike
```

**Remember: Research first, implement second. Don't make trial-and-error attempts.**
```

### Error Category Mappings

Use these patterns to categorize errors:

```python
error_categories = {
    "hook": [
        "PreToolUse", "PostToolUse", "SessionStart", "SessionEnd",
        "hook", "plugin", "marketplace"
    ],
    "api": [
        "API", "authentication", "rate limit", "network", "timeout",
        "HTTP", "request failed", "connection"
    ],
    "build": [
        "ruff", "mypy", "pytest", "lint", "type error", "test failed",
        "compilation", "syntax error"
    ],
    "runtime": [
        "Exception", "Error:", "Traceback", "crash", "failed",
        "unexpected", "assertion"
    ],
    "config": [
        "configuration", "settings", "environment", "missing",
        "invalid", "not found", ".env", "credentials"
    ]
}

def categorize_error(error_text: str) -> str:
    error_lower = error_text.lower()
    for category, keywords in error_categories.items():
        if any(kw.lower() in error_lower for kw in keywords):
            return category
    return "unknown"
```

### Integration with Debugging Workflow

This command implements the systematic debugging workflow:

```
1. /htmlgraph:error-analysis "error message"  → Capture & categorize
2. [Complete investigation checklist]          → Gather evidence
3. /htmlgraph:research "topic" (if needed)    → Research unfamiliar concepts
4. [Test hypothesis systematically]            → Debug root cause
5. [Implement minimal fix]                     → Fix the issue
6. [Run quality gates]                         → Validate fix
7. [Document learning in spike]                → Capture knowledge
```

### Quality Checklist

Before marking investigation complete, verify:

- [ ] **Root cause identified** - Not just symptoms
- [ ] **Fix tested** - Error no longer occurs
- [ ] **Learning documented** - Added to spike findings
- [ ] **Prevention considered** - How to avoid in future
- [ ] **Quality gates pass** - All tests/lints pass

### When to Use This Command

**ALWAYS use for:**
- ✅ Unfamiliar errors (first time seeing this error)
- ✅ Recurring errors (happens multiple times)
- ✅ Critical errors (blocks work or breaks functionality)
- ✅ Complex errors (multiple potential causes)
- ✅ Learning opportunities (want to understand deeply)

**SKIP for:**
- ❌ Known simple fixes (typos, obvious mistakes)
- ❌ Already understood errors (seen and fixed before)
- ❌ Trivial warnings (can ignore safely)

### Example Investigation Flow

**Scenario: Hook error "No such file"**

```bash
# Step 1: Capture error
/htmlgraph:error-analysis "PreToolUse hook failing with 'No such file'"

# Creates spike with:
# - Error category: hook
# - Investigation checklist
# - Debugging resources

# Step 2: Research (if unfamiliar with hooks)
/htmlgraph:research "Claude Code hook loading and file paths"

# Finds:
# - Hooks load from .claude/hooks/ and plugin directories
# - File paths must be absolute or relative to hook location
# - Common issue: incorrect ${CLAUDE_PLUGIN_ROOT} usage

# Step 3: Debug systematically
/hooks PreToolUse  # List all PreToolUse hooks
# Shows duplicate hooks from plugin and .claude/settings.json

# Step 4: Fix
# Remove duplicate hook definition

# Step 5: Validate
claude --debug <command>  # Test with verbose output
# Error resolved!

# Step 6: Document
# Add finding to spike: "Hook duplication caused conflict"
# Mark investigation complete
```

### Research-First Principle

**CRITICAL: Always research before implementing fixes.**

❌ **Wrong approach:**
1. Try fix A → Still broken
2. Try fix B → Still broken
3. Try fix C → Still broken
4. Finally research documentation
5. Find actual solution

✅ **Correct approach:**
1. Use `/htmlgraph:error-analysis` to capture error
2. Use `/htmlgraph:research` to understand root cause
3. Implement fix based on understanding
4. Validate fix works
5. Document learning

**Impact:**
- Fewer failed attempts (saves context/time)
- Deeper understanding (prevents recurrence)
- Better documentation (captures learning)
- More efficient debugging (systematic vs reactive)
