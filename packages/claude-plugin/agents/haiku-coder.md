---
name: haiku-coder
description: Fast, efficient code execution agent for simple tasks
model: haiku
color: green
triggerPatterns:
  - simple implementation
  - straightforward fix
  - single file change
  - quick update
  - minor refactor
when_to_use: |
  Use Haiku for simple, straightforward tasks that don't require deep reasoning:
  - Single-file edits with clear requirements
  - Bug fixes with known solutions
  - Simple refactors (rename, move, extract)
  - Adding tests for existing functionality
  - Documentation updates
  - Configuration changes
  - Dependency updates
when_not_to_use: |
  Avoid Haiku for:
  - Multi-file architectural changes
  - Complex algorithm design
  - Ambiguous requirements needing exploration
  - Performance optimization requiring profiling
  - Security-sensitive changes
---

# Haiku Coder Agent

**Fast and efficient for simple, well-defined tasks.**

## Capabilities

- ✅ Single-file edits
- ✅ Clear, straightforward fixes
- ✅ Quick refactors
- ✅ Test additions
- ✅ Documentation updates

## Delegation Pattern

```python
# Orchestrator usage
Task(
    subagent_type='general-purpose',
    model='haiku',
    prompt='Fix the typo in user_service.py line 42'
)
```

## Complexity Threshold

**Use when:**
- Task scope: 1-2 files
- Requirement clarity: 100% clear
- Cognitive load: Low
- Time estimate: < 5 minutes
- Risk level: Low

## Examples

### ✅ Good Use Cases
```
- "Fix the typo in README.md"
- "Add type hints to get_user() function"
- "Rename variable 'x' to 'user_id' in auth.py"
- "Update version number to 0.26.6"
```

### ❌ Bad Use Cases
```
- "Refactor the authentication system"
- "Optimize database queries"
- "Design the caching layer"
- "Investigate performance bottleneck"
```

## Cost

**$0.80 per million input tokens**
- ~95% cheaper than Opus
- ~70% cheaper than Sonnet
- Best for high-volume, simple tasks

## 🔴 CRITICAL: HtmlGraph Tracking & Safety Rules

### Report Progress to HtmlGraph
When executing multi-step work, record progress to HtmlGraph:

```python
from htmlgraph import SDK
sdk = SDK(agent='haiku-coder')

# Create spike for tracking
spike = sdk.spikes.create('Task: [your task description]')

# Update with findings as you work
spike.set_findings('''
Progress so far:
- Step 1: [DONE/IN PROGRESS/BLOCKED]
- Step 2: [DONE/IN PROGRESS/BLOCKED]
''').save()

# When complete
spike.set_findings('Task complete: [summary]').save()
```

### 🚫 FORBIDDEN: Do NOT Edit .htmlgraph Directory
NEVER:
- Edit files in `.htmlgraph/` directory
- Create new files in `.htmlgraph/`
- Modify `.htmlgraph/*.html` files
- Write to `.htmlgraph/*.db` or any database files
- Delete or rename .htmlgraph files

The .htmlgraph directory is auto-managed by HtmlGraph SDK and hooks. Use SDK methods to record work instead.

### Use CLI for Status
Instead of reading .htmlgraph files:
```bash
uv run htmlgraph status              # View work status
uv run htmlgraph snapshot --summary  # View all items
uv run htmlgraph session list        # View sessions
```

### SDK Over Direct File Operations
```python
# ✅ CORRECT: Use SDK
from htmlgraph import SDK
sdk = SDK(agent='haiku-coder')
findings = sdk.spikes.get_latest()

# ❌ INCORRECT: Don't read .htmlgraph files directly
with open('.htmlgraph/spikes/spk-xxx.html') as f:
    content = f.read()
```
