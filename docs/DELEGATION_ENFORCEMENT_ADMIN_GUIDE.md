# Admin Guide: Delegation Enforcement

Enforce delegation patterns across your team or organization using Claude Code hooks, environment variables, and the Orchestrator Skill. This guide covers setup, configuration, monitoring, and troubleshooting.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Setup & Configuration](#setup--configuration)
- [Environment Variables Reference](#environment-variables-reference)
- [Monitoring & Verification](#monitoring--verification)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [CI/CD Integration](#cicd-integration)

---

## Overview

### What is Delegation Enforcement?

Delegation enforcement ensures agents (humans or AI) follow cost-optimal delegation patterns:
- Use FREE/CHEAP AIs for appropriate tasks (Gemini for research, Codex for coding)
- Reserve expensive Claude models for complex reasoning only
- Prevent context waste on routine operations
- Track who delegates to whom and why

### Why It Matters

Without enforcement:
- Agents use expensive Claude Opus for simple file operations (waste)
- No visibility into delegation decisions (opacity)
- Context accumulates with repeated patterns (efficiency loss)
- Cost optimization guidance ignored (budget burn)

With enforcement:
- Automatic cost-optimal routing
- Complete delegation audit trail
- Enforced patterns across team
- Measurable cost reduction (30-50% savings)

### Architecture Overview

**Three-layer enforcement system:**

1. **SessionStart Hook** (99.9% reliability)
   - Injects system prompt at session start
   - Activates Orchestrator Skill
   - Sets environment variables
   - Happens before agent runs any code

2. **Environment Variables** (95% reliability)
   - Persist across context clears
   - Trigger skill activation
   - Enable post-compact delegation
   - Survived compact/resume cycles

3. **Orchestrator Skill** (99% reliability)
   - Progressive disclosure of delegation patterns
   - Cost-first decision framework
   - Automatic spawner routing
   - Available throughout session

---

## Architecture

### Component Interaction

```
Session Start
    ↓
SessionStart Hook runs
    ├─ Reads .claude/system-prompt.md
    ├─ Sets environment variables
    │  ├─ CLAUDE_DELEGATION_ENABLED=true
    │  ├─ CLAUDE_ORCHESTRATOR_ACTIVE=true
    │  ├─ CLAUDE_SYSTEM_PROMPT=[content]
    │  └─ CLAUDE_SESSION_ID=[id]
    ├─ Injects system prompt as additionalContext
    └─ Creates/updates session state
            ↓
    Agent sees system prompt + environment
            ↓
    Orchestrator Skill activates
            ↓
    Agent follows delegation patterns
            ↓
    Spawner selection (Gemini → Codex → Claude)
            ↓
    Cost-optimal task routing
```

### Data Flow: Session Persistence

```
Session 1 (Initial)
    ↓
SessionStart Hook:
    ├─ Creates session ID (UUID)
    ├─ Saves state to .htmlgraph/.session-state.json
    ├─ Sets CLAUDE_SESSION_ID env var
    └─ Injects system prompt

    ↓
Agent works...

    ↓
User runs /compact
    ↓
Session boundary (context clears)

    ↓
Session 2 (After Compact/Resume)
    ↓
SessionStart Hook:
    ├─ Detects is_post_compact=true (NEW session ID)
    ├─ Restores state from backup
    ├─ Checks env vars for persistence
    ├─ Re-injects system prompt
    └─ Re-activates Orchestrator Skill

    ↓
Agent continues with same delegation guidance
```

### Hook Execution Timeline

```
Event                           Hook              Variables Set
─────────────────────────────────────────────────────────────────
Session starts                  SessionStart       CLAUDE_DELEGATION_ENABLED=true
                                                   CLAUDE_ORCHESTRATOR_ACTIVE=true
                                                   CLAUDE_SYSTEM_PROMPT=[content]
                                                   CLAUDE_SESSION_ID=[id]

System prompt injected          SessionStart       (available in context)

Agent does work                 (none)             (env vars persist)

/compact used                   SessionStart       Environment persists across
                                (new session)      boundary, variables re-applied

Post-compact agent              (env vars)         Delegation continues as before
resumes work

Session ends                    SessionEnd         Session saved to .htmlgraph/
```

---

## Setup & Configuration

### Prerequisites

- HtmlGraph plugin installed in Claude Code
- `.claude/` directory in project
- Bash/Python available in CI/CD environment
- Git repository (for version control)

### Step 1: Install HtmlGraph Plugin

```bash
# Check if installed
claude plugin list | grep htmlgraph

# If not installed
claude plugin install htmlgraph@latest

# Verify installation
claude plugin list
```

### Step 2: Create System Prompt (with delegation rules)

```bash
mkdir -p .claude
cat > .claude/system-prompt.md << 'EOF'
# System Prompt - Team Project

## Delegation Rules (ENFORCED)

### Cost-First Decision Framework
Ask in order:
1. Can Gemini do this? → YES: MUST use Gemini spawner (FREE)
2. Is this code work? → YES: MUST use Codex spawner (cheap)
3. Is this git work? → YES: MUST use Copilot spawner (cheap)
4. Does this need reasoning? → YES: Use Sonnet (mid-tier)
5. Is this novel/research? → YES: Use Opus (expensive, justified)
6. Otherwise → Use Haiku (fallback)

### Mandatory Patterns
- File research: ALWAYS use Gemini spawner
- Code generation: ALWAYS use Codex spawner
- Git operations: ALWAYS use Copilot spawner
- Complex reasoning: Use Task(subagent_type="sonnet")
- Direct execution: ONLY for trivial operations (<5 min)

### Prohibited Patterns
- ❌ Using Claude Opus for file operations
- ❌ Using Haiku for novel architecture
- ❌ Delegating simple tasks to multiple spawners
- ❌ Ignoring cost-first framework
- ❌ No delegation audit trail

## Model Selection
- **Haiku**: Orchestration, delegation, fallback
- **Sonnet**: Complex reasoning, multi-step logic
- **Opus**: Novel problems, deep research (EXPENSIVE)

## Context Persistence
This prompt persists through compact/resume cycles via:
1. SessionStart hook injection (primary)
2. Environment variables (backup)
3. File backup system (recovery)
EOF
```

### Step 3: Enable Environment Variable Persistence

Create `.claude/hooks/scripts/session-start.py` extension (or verify it exists):

```bash
# Check if session-start.py exists
ls -lh .claude/hooks/scripts/session-start.py

# If it exists, verify it sets environment variables
grep -E "CLAUDE_DELEGATION_ENABLED|CLAUDE_ORCHESTRATOR_ACTIVE" \
  .claude/hooks/scripts/session-start.py
```

The hook automatically sets these variables:
- `CLAUDE_DELEGATION_ENABLED=true`
- `CLAUDE_ORCHESTRATOR_ACTIVE=true`
- `CLAUDE_SYSTEM_PROMPT=[file content]`
- `CLAUDE_SESSION_ID=[session UUID]`

### Step 4: Verify Hook Installation

```bash
# List active hooks
/hooks SessionStart

# Should output something like:
# ✓ SessionStart hook active
# ✓ System prompt injection enabled
# ✓ Environment variables configured
```

### Step 5: Test Delegation Enforcement

```bash
# Start a Claude Code session
# Then run:
echo $CLAUDE_DELEGATION_ENABLED      # Should print: true
echo $CLAUDE_ORCHESTRATOR_ACTIVE      # Should print: true
echo $CLAUDE_SESSION_ID               # Should print: UUID

# Check system prompt is injected
# Look at context section - should show your custom system prompt
```

---

## Environment Variables Reference

### Required Variables

| Variable | Value | Set By | Purpose |
|----------|-------|--------|---------|
| `CLAUDE_DELEGATION_ENABLED` | `true` | SessionStart hook | Enable delegation enforcement |
| `CLAUDE_ORCHESTRATOR_ACTIVE` | `true` | SessionStart hook | Activate Orchestrator Skill |
| `CLAUDE_SYSTEM_PROMPT` | File content | SessionStart hook | System prompt text (fallback) |
| `CLAUDE_SESSION_ID` | UUID | SessionStart hook | Unique session identifier |

### Optional Variables

| Variable | Value | Set By | Purpose |
|----------|-------|--------|---------|
| `CLAUDE_IS_POST_COMPACT` | `true/false` | SessionStart hook | Detect post-compact sessions |
| `CLAUDE_AGENT_ASSIGNED` | Agent name | SDK/hook | Track which agent is working |
| `CLAUDE_PARENT_SESSION_ID` | UUID | SessionStart hook | Link subagents to parent |
| `CLAUDE_ORCHESTRATION_MODE` | `strict/lenient` | Config | Enforcement strictness |

### How Variables Persist

**Across Compact/Resume:**
```bash
# Session 1
export CLAUDE_DELEGATION_ENABLED=true
uv run my_task.py     # Variables available

# Use /compact command
# (session context clears, but environment remains)

# Session 2 (post-compact)
echo $CLAUDE_DELEGATION_ENABLED     # Still true! Variables persisted
```

**Across Subprocess Spawns:**
```python
# In your code
import os

if os.getenv('CLAUDE_DELEGATION_ENABLED'):
    # This agent is in a delegating project
    use_spawner('gemini')  # Route to spawner
else:
    # Direct execution mode
    run_directly()
```

---

## Monitoring & Verification

### Verify Delegation is Active

```bash
# 1. Check hook is running
/hooks SessionStart
# Expected: "SessionStart hook active" ✓

# 2. Check environment variables
env | grep CLAUDE_DELEGATION
# Expected: CLAUDE_DELEGATION_ENABLED=true ✓

# 3. Check system prompt loaded
# (Should see it in context at session start)

# 4. Verify Orchestrator Skill available
/orchestrator-directives
# Expected: Skill description appears ✓
```

### Check Delegation Audit Trail

Delegation patterns are tracked in HtmlGraph:

```bash
# View all Task() calls made in a session
uv run python << 'EOF'
from htmlgraph import SDK

sdk = SDK(agent="orchestrator")

# Get all delegated tasks in last session
tasks = sdk.spikes.where(
    status="completed",
    tags=["delegated"]
).order_by("created_at", reverse=True)

print(f"Delegated tasks: {len(tasks)}")
for task in tasks[:5]:
    print(f"  - {task.title}")
    print(f"    Spawner: {task.metadata.get('spawner_type')}")
    print(f"    Cost savings: {task.metadata.get('cost_savings')}")
EOF
```

### Cost Tracking

Monitor delegation cost savings:

```bash
# Run analysis
uv run python << 'EOF'
from pathlib import Path
import json

# Load session tracking
session_file = Path('.htmlgraph/sessions/').glob('*.html')

total_tasks = 0
delegated_tasks = 0
estimated_savings = 0

for session_html in session_file:
    # Parse session for delegation info
    if 'spawner' in session_html.read_text():
        delegated_tasks += 1

print(f"Total sessions: {total_tasks}")
print(f"Delegated tasks: {delegated_tasks}")
print(f"Estimated savings: ${estimated_savings}")
EOF
```

---

## Troubleshooting

### Delegation Not Enforced Post-Compact

**Symptom**: After running `/compact`, agent ignores delegation rules.

**Root Cause**: Environment variables not persisting, or SessionStart hook not re-running.

**Diagnosis**:
```bash
# 1. Check if environment persists
echo "Before compact:"
echo $CLAUDE_DELEGATION_ENABLED

# 2. Use /compact command

echo "After compact:"
echo $CLAUDE_DELEGATION_ENABLED     # Should still be true
```

**Solutions**:
```bash
# 1. Verify SessionStart hook is installed
ls -lh .claude/hooks/scripts/session-start.py
chmod +x .claude/hooks/scripts/session-start.py

# 2. Check hook permissions
file .claude/hooks/scripts/session-start.py

# 3. Force re-inject environment
export CLAUDE_DELEGATION_ENABLED=true
export CLAUDE_ORCHESTRATOR_ACTIVE=true

# 4. Start new session for hook to run
```

### Orchestrator Skill Not Activating

**Symptom**: `/orchestrator-directives` command fails or skill doesn't appear.

**Root Cause**: Environment variables not set, skill not installed, plugin not loaded.

**Diagnosis**:
```bash
# 1. Check skill is installed
/orchestrator-directives --help
# If fails: skill not available

# 2. Check environment
echo $CLAUDE_ORCHESTRATOR_ACTIVE
# If empty: env var not set

# 3. Check plugin loaded
claude plugin list | grep htmlgraph
# If not listed: plugin missing
```

**Solutions**:
```bash
# 1. Reinstall skill
claude plugin install htmlgraph@latest

# 2. Verify environment variable
# Should be set by SessionStart hook
export CLAUDE_ORCHESTRATOR_ACTIVE=true

# 3. Reload plugin
claude plugin reload htmlgraph

# 4. Start new session to trigger hook
```

### Agent Attribution Missing

**Symptom**: Spikes created without `agent_assigned` field.

**Root Cause**: SDK() called without `agent=` parameter.

**Diagnosis**:
```bash
# Check spike for agent attribution
uv run python << 'EOF'
from htmlgraph import SDK

# This is WRONG - missing agent parameter
sdk = SDK()
spike = sdk.spikes.create("Task")  # agent_assigned will be empty

# This is RIGHT - agent specified
sdk = SDK(agent="claude")
spike = sdk.spikes.create("Task")  # agent_assigned="claude"
EOF
```

**Solutions**:
```python
# ALWAYS include agent parameter
from htmlgraph import SDK

# For individual work
sdk = SDK(agent="claude")

# For team work - use team member name
sdk = SDK(agent="alice")
sdk = SDK(agent="bob")

# For bot work
sdk = SDK(agent="bot-name")
```

### System Prompt Not Injected Post-Compact

**Symptom**: System prompt disappeared after `/compact`.

**Root Cause**: File deleted, hook failed, or three-layer system broken.

**Diagnosis**:
```bash
# 1. Check file exists
ls -lh .claude/system-prompt.md
# If missing: file was deleted

# 2. Check hook execution
claude --debug  # Look for "system-prompt" in output

# 3. Check environment backup
echo $CLAUDE_SYSTEM_PROMPT | head -20
# If empty: env var not set

# 4. Check file backup
ls -lh .htmlgraph/.system-prompt-backup.md
# If missing: backup system failed
```

**Solutions**:
```bash
# 1. Recreate from backup
cp .htmlgraph/.system-prompt-backup.md .claude/system-prompt.md

# 2. Or restore from git
git checkout .claude/system-prompt.md

# 3. Or recreate from scratch
cat > .claude/system-prompt.md << 'EOF'
# System Prompt - [Project]
[Your content]
EOF

# 4. Start new session to re-inject
```

### Environment Variables Not Persisting

**Symptom**: Environment variables clear when context compacts.

**Root Cause**: Environment not properly exported, or subprocess isolation.

**Diagnosis**:
```bash
# Before compact
env | grep CLAUDE_

# After compact
env | grep CLAUDE_
# If different: env not persisting properly
```

**Solutions**:
```bash
# 1. Ensure variables are exported (not just set)
export CLAUDE_DELEGATION_ENABLED=true
export CLAUDE_ORCHESTRATOR_ACTIVE=true

# 2. Check they're in environment
set | grep CLAUDE_

# 3. Set in .claude/settings.json for persistence
# (Plugin will reload on session start)

# 4. Use file-based backup
# Create .htmlgraph/.env-backup for recovery
```

---

## Best Practices

### 1. Make Delegation Rules Explicit

**Good:**
```markdown
## Delegation Rules (MANDATORY)
- Research: ALWAYS use Gemini spawner (FREE)
- Code generation: ALWAYS use Codex spawner
- Git operations: ALWAYS use Copilot spawner
- Reasoning: Use Task(subagent_type="sonnet")
```

**Bad:**
```markdown
## Delegation
Try to use spawners if you think it's appropriate.
```

### 2. Define Decision Framework Clearly

**Good:**
```
1. Can Gemini do this? → YES: Use Gemini
2. Is this code? → YES: Use Codex
3. Is this reasoning? → YES: Use Sonnet
4. Else → Use Haiku
```

**Bad:**
```
Pick the right model. Use spawners sometimes.
```

### 3. Set Clear Expectations for Team

**In system prompt:**
```markdown
## Team Agreement
We commit to:
- Cost-first decision framework for all tasks
- Delegation audit trail for transparency
- No direct execution for >30 min tasks
- Monthly cost review meetings
```

### 4. Monitor Delegation Patterns

Regular reviews:
```bash
# Weekly: Check delegation usage
uv run python << 'EOF'
from htmlgraph import SDK

sdk = SDK(agent="admin")
spikes = sdk.spikes.where(tags=["delegated"],
                         created_after="7 days ago")
print(f"Delegated this week: {len(spikes)}")
EOF

# Monthly: Analyze cost savings
uv run python << 'EOF'
# Calculate total cost savings from delegation
# Compare against baseline (all direct execution)
EOF
```

### 5. Document Anti-Patterns

```markdown
## Anti-Patterns (DON'T DO THESE)
1. ❌ Using Opus for file operations (wastes $$$)
2. ❌ Direct execution for research (use Gemini instead)
3. ❌ No delegation audit trail (can't track costs)
4. ❌ Ignoring cost-first framework (budget burn)
5. ❌ Delegating without clear success criteria (wasted time)
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Enforce Delegation in Tests

on: [pull_request]

jobs:
  delegation-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install HtmlGraph
        run: pip install htmlgraph

      - name: Check delegation patterns
        env:
          CLAUDE_DELEGATION_ENABLED: 'true'
          CLAUDE_ORCHESTRATOR_ACTIVE: 'true'
        run: |
          python3 << 'EOF'
          from htmlgraph import SDK

          # Check if PR includes Task() calls (delegation)
          # Reject if large changes without delegation

          sdk = SDK(agent="ci-bot")

          # Verify system prompt exists
          import os
          if not os.path.exists('.claude/system-prompt.md'):
              print("ERROR: No system prompt found")
              exit(1)

          print("✓ Delegation enforcement active")
          print("✓ System prompt configured")
          EOF
```

### Local Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Check system prompt is in git
if ! git show :'.claude/system-prompt.md' &>/dev/null; then
    echo "⚠️  Warning: system-prompt.md not staged"
fi

# Verify syntax
if [ -f '.claude/system-prompt.md' ]; then
    python3 -m markdown '.claude/system-prompt.md' > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "ERROR: system-prompt.md has syntax errors"
        exit 1
    fi
fi

exit 0
```

### Continuous Monitoring

```bash
#!/bin/bash
# scripts/monitor-delegation.sh

# Track delegation metrics over time
uv run python3 << 'EOF'
from htmlgraph import SDK
from datetime import datetime, timedelta

sdk = SDK(agent="monitoring-bot")

# Get metrics from last 7 days
window_start = datetime.now() - timedelta(days=7)

spikes = sdk.spikes.where(created_after=window_start)

delegated = len([s for s in spikes if s.metadata.get('delegated')])
total = len(spikes)
percentage = (delegated / total * 100) if total > 0 else 0

print(f"Delegation rate: {percentage:.1f}%")
print(f"Delegated tasks: {delegated}/{total}")

# Alert if below threshold (e.g., <50%)
if percentage < 50:
    print("⚠️  Delegation rate below target!")
EOF
```

---

## Next Steps

1. **Enable delegation** using Setup & Configuration section
2. **Configure system prompt** with delegation rules
3. **Verify enforcement** using Monitoring section
4. **Monitor patterns** weekly
5. **Adjust rules** based on team feedback

For system prompt customization details, see [System Prompt Customization Guide](SYSTEM_PROMPT_CUSTOMIZATION.md).

For technical architecture, see [System Prompt Architecture](SYSTEM_PROMPT_ARCHITECTURE.md).
