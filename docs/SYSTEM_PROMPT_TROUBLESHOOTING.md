# Troubleshooting Guide: System Prompt & Delegation Issues

Comprehensive troubleshooting guide for system prompt persistence and delegation enforcement issues, with diagnostic workflows and solutions.

## Table of Contents
- [Common Issues](#common-issues)
- [Diagnostic Workflow](#diagnostic-workflow)
- [Debug Commands](#debug-commands)
- [Escalation Path](#escalation-path)

---

## Common Issues

### Issue 1: System Prompt Not Appearing in Context

**Symptoms:**
- System prompt missing from context at session start
- You don't see your custom guidance in the conversation
- /compact removes prompt and it doesn't return

**Root Causes:**
1. File doesn't exist or is empty
2. Hook not running (plugin not installed)
3. File has syntax errors or exceeds token limit
4. Permission denied reading file
5. .claude directory not found

**Diagnosis Steps:**

```bash
# Step 1: Verify file exists and has content
ls -lh .claude/system-prompt.md
# Expected: File exists, size >100 bytes

# If file doesn't exist
if [ ! -f .claude/system-prompt.md ]; then
    echo "ERROR: File doesn't exist"
    # Jump to Solution 1
fi

# Step 2: Check file content
wc -l .claude/system-prompt.md
# Expected: >5 lines

cat .claude/system-prompt.md | head -20
# Expected: Starts with markdown heading, readable content

# Step 3: Check for syntax errors
python3 -c "
import markdown
with open('.claude/system-prompt.md') as f:
    text = f.read()
    try:
        markdown.markdown(text)
        print('✓ Markdown syntax valid')
    except Exception as e:
        print(f'✗ Markdown error: {e}')
"

# Step 4: Check file permissions
stat .claude/system-prompt.md
# Expected: Readable by current user

# Step 5: Check token count
python3 -c "
with open('.claude/system-prompt.md') as f:
    text = f.read()
    tokens = len(text) // 4  # Rough estimate
    print(f'Approximate tokens: {tokens}')
    if tokens > 1000:
        print('⚠️  WARNING: Exceeds typical budget')
"

# Step 6: Check hook is running
claude --debug
# Look for "system-prompt" or "session-start" in output
# Expected: Hook should be listed as active
```

**Solutions:**

**Solution 1: File doesn't exist**
```bash
# Create the file
mkdir -p .claude
cat > .claude/system-prompt.md << 'EOF'
# System Prompt - My Project

## Model Selection
- **Haiku**: Quick tasks, file operations
- **Sonnet**: Complex reasoning
- **Opus**: Novel problems

## Delegation Pattern
Use Task() for work >30 minutes
EOF

# Start new session - hook should now inject it
```

**Solution 2: File exists but hook not running**
```bash
# Check if plugin is installed
claude plugin list | grep htmlgraph
# If not shown: Plugin missing

# Install plugin
claude plugin install htmlgraph@latest

# Verify installation
claude plugin list | grep htmlgraph
# Expected: htmlgraph with version number

# Start new session after installation
```

**Solution 3: File has syntax errors**
```bash
# Fix markdown syntax
# Common issues:
# - Missing heading markers (#)
# - Unclosed code blocks (```)
# - Invalid indentation

# Example fix:
cat > .claude/system-prompt.md << 'EOF'
# System Prompt - My Project

This is valid markdown.

## Section 1
Content here.

### Subsection
More content.
EOF

# Verify syntax
python3 -m markdown .claude/system-prompt.md > /dev/null && echo "✓ Valid"
```

**Solution 4: File too large (exceeds token budget)**
```bash
# Option 1: Truncate to essential content only
# Remove examples, verbose sections
# Keep: Model guidance, key rules, delegation patterns

# Option 2: Move details to README or CLAUDE.md
# System prompt: Core guidance only
# README.md: Detailed architecture
# CLAUDE.md: Project-specific notes

# Verify size
python3 -c "
with open('.claude/system-prompt.md') as f:
    tokens = len(f.read()) // 4
    print(f'Current: {tokens} tokens')
    print(f'Budget: 1000 tokens')
    print(f'Need to remove: {max(0, tokens - 1000)} tokens')
"
```

**Solution 5: Permission denied**
```bash
# Fix permissions
chmod 644 .claude/system-prompt.md

# Verify
ls -l .claude/system-prompt.md
# Expected: -rw-r--r-- (readable by all)
```

---

### Issue 2: Delegation Not Enforced Post-Compact

**Symptoms:**
- System prompt disappears after `/compact`
- Delegation patterns abandoned post-compact
- Orchestrator Skill not available after compact
- Environment variables don't persist

**Root Causes:**
1. SessionStart hook not re-running post-compact
2. Environment variables not persisting
3. File deleted between sessions
4. Backup system failed

**Diagnosis Steps:**

```bash
# Step 1: Before compact, check environment
echo "=== BEFORE COMPACT ==="
echo "CLAUDE_DELEGATION_ENABLED=$CLAUDE_DELEGATION_ENABLED"
echo "CLAUDE_ORCHESTRATOR_ACTIVE=$CLAUDE_ORCHESTRATOR_ACTIVE"
echo "CLAUDE_SESSION_ID=$CLAUDE_SESSION_ID"

# Step 2: Use /compact command
# (In Claude Code conversation)

# Step 3: After compact, check environment
echo "=== AFTER COMPACT ==="
echo "CLAUDE_DELEGATION_ENABLED=$CLAUDE_DELEGATION_ENABLED"
echo "CLAUDE_ORCHESTRATOR_ACTIVE=$CLAUDE_ORCHESTRATOR_ACTIVE"
echo "CLAUDE_SESSION_ID=$CLAUDE_SESSION_ID"

# If different: Environment not persisting
# If same: Environment persisted but hook didn't re-inject

# Step 4: Check if file still exists
ls -lh .claude/system-prompt.md
# Expected: File should still exist post-compact

# Step 5: Check hook execution post-compact
claude --debug
# Look for system-prompt injection attempt
# Expected: Hook runs even post-compact
```

**Solutions:**

**Solution 1: Hook not re-running post-compact**
```bash
# Verify hook is installed
ls -lh .claude/hooks/scripts/session-start.py
# Expected: File exists and is executable
chmod +x .claude/hooks/scripts/session-start.py

# Check hook content
grep -l "system.prompt" .claude/hooks/scripts/session-start.py
# Expected: File contains system-prompt logic

# Reinstall hook if needed
rm .claude/hooks/scripts/session-start.py
# Plugin will recreate on next session start

# Start new session to verify hook runs
```

**Solution 2: Environment not persisting**
```bash
# Ensure variables are exported (not just set)
export CLAUDE_DELEGATION_ENABLED=true
export CLAUDE_ORCHESTRATOR_ACTIVE=true

# Verify they're in environment
set | grep CLAUDE_DELEGATION
# Expected: CLAUDE_DELEGATION_ENABLED=true

# If variables clear after /compact:
# - Use file-based recovery (Layer 3)
# - Check backup exists: .htmlgraph/.system-prompt-backup.md
ls -lh .htmlgraph/.system-prompt-backup.md
```

**Solution 3: File deleted between sessions**
```bash
# Restore from git
git checkout .claude/system-prompt.md

# Or restore from backup
cp .htmlgraph/.system-prompt-backup.md .claude/system-prompt.md

# Or recreate from scratch
cat > .claude/system-prompt.md << 'EOF'
[Your system prompt content]
EOF

# Start new session
```

**Solution 4: Backup system failed**
```bash
# Check backup location
ls -lh .htmlgraph/.system-prompt-backup.md
# If missing: Backup wasn't created

# Manual backup creation
mkdir -p .htmlgraph
cp .claude/system-prompt.md .htmlgraph/.system-prompt-backup.md

# Start new session to verify it's used
```

---

### Issue 3: Orchestrator Skill Not Activating

**Symptoms:**
- `/orchestrator-directives` command fails
- Skill doesn't appear as available
- Cost-first delegation framework not mentioned
- Spawner routing not working

**Root Causes:**
1. Plugin not installed
2. Environment variable not set (`CLAUDE_ORCHESTRATOR_ACTIVE`)
3. Skill not found or disabled
4. Plugin needs update

**Diagnosis Steps:**

```bash
# Step 1: Check plugin installed
claude plugin list | grep htmlgraph
# Expected: htmlgraph listed with version

# Step 2: Check environment variable
echo $CLAUDE_ORCHESTRATOR_ACTIVE
# Expected: true

# Step 3: Try to invoke skill
/orchestrator-directives
# If fails: Skill not available or not loaded

# Step 4: Check Claude Code version
claude --version
# Expected: Latest version

# Step 5: Check if plugin needs update
claude plugin info htmlgraph
# Look for "Update available" message
```

**Solutions:**

**Solution 1: Plugin not installed**
```bash
# Install plugin
claude plugin install htmlgraph@latest

# Verify installation
claude plugin list | grep htmlgraph
# Expected: htmlgraph shown

# Start new session for plugin to activate
```

**Solution 2: Environment variable not set**
```bash
# Check if SessionStart hook is running
# (Hook should set this variable)

# Manual set as fallback
export CLAUDE_ORCHESTRATOR_ACTIVE=true

# Verify it's set
echo $CLAUDE_ORCHESTRATOR_ACTIVE
# Expected: true

# Start new session
```

**Solution 3: Plugin needs update**
```bash
# Check for updates
claude plugin update htmlgraph

# Or reinstall
claude plugin uninstall htmlgraph
claude plugin install htmlgraph@latest

# Verify new version
claude plugin info htmlgraph | grep version
```

---

### Issue 4: Agent Attribution Missing

**Symptoms:**
- Spikes created without `agent_assigned` field
- Can't track which agent did work
- Audit trail incomplete
- HtmlGraph dashboard shows "Unknown agent"

**Root Causes:**
1. SDK() called without `agent=` parameter
2. Agent attribution not passed to Task()
3. Subagent work not linked to parent

**Diagnosis Steps:**

```bash
# Step 1: Check SDK initialization
python3 << 'EOF'
from htmlgraph import SDK

# This is WRONG - no agent parameter
sdk = SDK()
spike = sdk.spikes.create("Task")

# Check agent field
print(f"Agent assigned: {spike.metadata.get('agent_assigned', 'MISSING')}")
EOF

# Step 2: Check Task() calls
# Look for: Task(prompt=..., subagent_type=...)
# Missing: agent parameter

# Step 3: Check spike in HtmlGraph
ls -lh .htmlgraph/spikes/
cat .htmlgraph/spikes/*.html | grep -i "agent_assigned"
```

**Solutions:**

**Solution 1: Add agent parameter to SDK**
```python
# BEFORE (missing agent)
from htmlgraph import SDK
sdk = SDK()
spike = sdk.spikes.create("Task")

# AFTER (with agent)
from htmlgraph import SDK
sdk = SDK(agent="claude")  # Add agent name
spike = sdk.spikes.create("Task")

# For specific team members
sdk = SDK(agent="alice")
sdk = SDK(agent="bot-name")
```

**Solution 2: Add agent to Task() calls**
```python
# BEFORE
Task(prompt="Do something", subagent_type="codex")

# AFTER
Task(
    prompt="Do something",
    subagent_type="codex",
    agent="claude"  # Or agent from environment
)
```

**Solution 3: Link subagent to parent**
```python
from htmlgraph import SDK
import os

# Parent session
parent_sdk = SDK(agent="orchestrator")

# Child session (subagent)
child_sdk = SDK(agent="claude")
child_sdk.set_parent_session(
    parent_session_id=os.getenv('CLAUDE_SESSION_ID')
)

# Now work in child is linked to parent
spike = child_sdk.spikes.create("Subagent work")
```

---

### Issue 5: Post-Compact Detection Failing

**Symptoms:**
- `is_post_compact` always returns false
- State not restored after compact
- Sessions not linked across compact boundary
- Duplicate session creation

**Root Causes:**
1. Session ID not changing between sessions
2. State file missing or corrupted
3. SessionStart hook not updating state
4. Session comparison logic broken

**Diagnosis Steps:**

```bash
# Step 1: Check session ID changes
echo "Session 1 ID:"
echo $CLAUDE_SESSION_ID

# Use /compact

echo "Session 2 ID:"
echo $CLAUDE_SESSION_ID

# They should be DIFFERENT if post-compact detected correctly

# Step 2: Check state file
ls -lh .htmlgraph/.session-state.json
# Expected: File exists and updated recently

cat .htmlgraph/.session-state.json
# Expected: Contains session IDs

# Step 3: Check is_post_compact detection
python3 << 'EOF'
from htmlgraph.session import SessionStateManager

manager = SessionStateManager()
is_post = manager.is_post_compact()
print(f"Is post-compact: {is_post}")

# Debug: Check current vs last session ID
current = manager._get_current_session_id()
last = manager._load_last_session_id()
print(f"Current session ID: {current}")
print(f"Last session ID: {last}")
print(f"Different: {current != last}")
EOF
```

**Solutions:**

**Solution 1: Session ID not changing**
```bash
# Check that SessionStart hook is setting new session ID
# Verify environment variable changes post-compact

# Manual check:
echo "Before:" && echo $CLAUDE_SESSION_ID
# Use /compact
echo "After:" && echo $CLAUDE_SESSION_ID
# Should be different

# If same: Hook not creating new ID
# Fix: Reinstall hook or update plugin
```

**Solution 2: State file missing**
```bash
# Create state directory
mkdir -p .htmlgraph

# Let hook create state file
# On next session start, hook should create .htmlgraph/.session-state.json

# Verify creation
ls -lh .htmlgraph/.session-state.json
# Expected: File should exist
```

**Solution 3: State file corrupted**
```bash
# Check state file validity
python3 -c "
import json
with open('.htmlgraph/.session-state.json') as f:
    try:
        data = json.load(f)
        print('✓ State file valid')
        print(f'Last session ID: {data.get(\"last_session_id\")}')
    except json.JSONDecodeError as e:
        print(f'✗ State file corrupted: {e}')
"

# If corrupted, delete and let hook recreate
rm .htmlgraph/.session-state.json
# Start new session - hook will recreate
```

---

## Diagnostic Workflow

### Quick Diagnostic (2 minutes)

```bash
#!/bin/bash
# Quick system prompt diagnostic

echo "=== SYSTEM PROMPT DIAGNOSTIC ==="

# 1. File check
echo -n "1. System prompt file: "
if [ -f .claude/system-prompt.md ]; then
    echo "✓ EXISTS"
else
    echo "✗ MISSING"
fi

# 2. Plugin check
echo -n "2. HtmlGraph plugin: "
if claude plugin list 2>/dev/null | grep -q htmlgraph; then
    echo "✓ INSTALLED"
else
    echo "✗ NOT INSTALLED"
fi

# 3. Environment variables
echo -n "3. Delegation enabled: "
[ "$CLAUDE_DELEGATION_ENABLED" = "true" ] && echo "✓ YES" || echo "✗ NO"

echo -n "4. Orchestrator active: "
[ "$CLAUDE_ORCHESTRATOR_ACTIVE" = "true" ] && echo "✓ YES" || echo "✗ NO"

# 4. Hook status
echo -n "5. SessionStart hook: "
if [ -x .claude/hooks/scripts/session-start.py ]; then
    echo "✓ INSTALLED"
else
    echo "✗ MISSING OR NOT EXECUTABLE"
fi

echo "=== END DIAGNOSTIC ==="
```

Run this before troubleshooting to identify problem area.

### Complete Diagnostic (10 minutes)

```bash
#!/bin/bash
# Complete system prompt diagnostic

mkdir -p /tmp/htmlgraph-diag

echo "=== COMPLETE DIAGNOSTIC REPORT ===" | tee /tmp/htmlgraph-diag/report.txt

# Environment
echo "" | tee -a /tmp/htmlgraph-diag/report.txt
echo "ENVIRONMENT VARIABLES:" | tee -a /tmp/htmlgraph-diag/report.txt
env | grep CLAUDE_ | tee -a /tmp/htmlgraph-diag/report.txt

# File system
echo "" | tee -a /tmp/htmlgraph-diag/report.txt
echo "FILE SYSTEM:" | tee -a /tmp/htmlgraph-diag/report.txt
ls -lh .claude/ 2>/dev/null | tee -a /tmp/htmlgraph-diag/report.txt
ls -lh .htmlgraph/ 2>/dev/null | tee -a /tmp/htmlgraph-diag/report.txt

# Plugin info
echo "" | tee -a /tmp/htmlgraph-diag/report.txt
echo "PLUGIN STATUS:" | tee -a /tmp/htmlgraph-diag/report.txt
claude plugin list 2>/dev/null | tee -a /tmp/htmlgraph-diag/report.txt
claude plugin info htmlgraph 2>/dev/null | tee -a /tmp/htmlgraph-diag/report.txt

# System prompt content
echo "" | tee -a /tmp/htmlgraph-diag/report.txt
echo "SYSTEM PROMPT CONTENT (first 50 lines):" | tee -a /tmp/htmlgraph-diag/report.txt
head -50 .claude/system-prompt.md 2>/dev/null | tee -a /tmp/htmlgraph-diag/report.txt

# Python diagnostics
echo "" | tee -a /tmp/htmlgraph-diag/report.txt
echo "PYTHON DIAGNOSTICS:" | tee -a /tmp/htmlgraph-diag/report.txt
python3 << 'PYEOF' | tee -a /tmp/htmlgraph-diag/report.txt
import os
import json
from pathlib import Path

# System prompt
sp_file = Path('.claude/system-prompt.md')
if sp_file.exists():
    content = sp_file.read_text()
    tokens = len(content) // 4
    print(f"System prompt: {len(content)} chars, ~{tokens} tokens")
else:
    print("System prompt: NOT FOUND")

# Environment variables
print(f"Delegation enabled: {os.getenv('CLAUDE_DELEGATION_ENABLED')}")
print(f"Orchestrator active: {os.getenv('CLAUDE_ORCHESTRATOR_ACTIVE')}")
print(f"Session ID: {os.getenv('CLAUDE_SESSION_ID')}")

# Session state
state_file = Path('.htmlgraph/.session-state.json')
if state_file.exists():
    try:
        state = json.loads(state_file.read_text())
        print(f"Session state: VALID")
    except:
        print(f"Session state: CORRUPTED")
else:
    print(f"Session state: NOT FOUND")

# Backup
backup_file = Path('.htmlgraph/.system-prompt-backup.md')
print(f"Backup exists: {backup_file.exists()}")

PYEOF

echo "" | tee -a /tmp/htmlgraph-diag/report.txt
echo "Report saved to: /tmp/htmlgraph-diag/report.txt"
```

---

## Debug Commands

### Check System Prompt Status

```bash
# Quick check
echo "System prompt status:"
echo "- File exists: $([ -f .claude/system-prompt.md ] && echo YES || echo NO)"
echo "- File size: $(wc -c < .claude/system-prompt.md 2>/dev/null || echo 0) bytes"
echo "- In environment: $([ -n "$CLAUDE_SYSTEM_PROMPT" ] && echo YES || echo NO)"
echo "- Backup exists: $([ -f .htmlgraph/.system-prompt-backup.md ] && echo YES || echo NO)"
```

### Check Hook Status

```bash
# Verify hook is installed
echo "SessionStart hook status:"
echo "- Installed: $([ -f .claude/hooks/scripts/session-start.py ] && echo YES || echo NO)"
echo "- Executable: $([ -x .claude/hooks/scripts/session-start.py ] && echo YES || echo NO)"
echo "- Size: $(wc -c < .claude/hooks/scripts/session-start.py 2>/dev/null || echo 0) bytes"

# Check hook contains system prompt logic
grep -c "system.prompt\|CLAUDE_DELEGATION" \
  .claude/hooks/scripts/session-start.py 2>/dev/null && echo "- Contains logic: YES" || echo "- Contains logic: NO"
```

### Check Delegation Status

```bash
# Verify delegation is enabled
echo "Delegation enforcement status:"
echo "- Enabled: $([ "$CLAUDE_DELEGATION_ENABLED" = "true" ] && echo YES || echo NO)"
echo "- Orchestrator active: $([ "$CLAUDE_ORCHESTRATOR_ACTIVE" = "true" ] && echo YES || echo NO)"
echo "- Session ID: $CLAUDE_SESSION_ID"
echo "- Is post-compact: $([ "$CLAUDE_IS_POST_COMPACT" = "true" ] && echo YES || echo NO)"
```

### Verify Hook Execution

```bash
# Run hook manually (for testing)
python3 .claude/hooks/scripts/session-start.py

# Check for errors
echo "Hook exit code: $?"

# Check environment after hook
echo "CLAUDE_DELEGATION_ENABLED=$CLAUDE_DELEGATION_ENABLED"
echo "CLAUDE_SYSTEM_PROMPT=${CLAUDE_SYSTEM_PROMPT:0:50}..."
```

---

## Escalation Path

### When to File an Issue

File an issue if:
1. All diagnostic steps complete
2. All solutions attempted without success
3. Problem is reproducible consistently
4. Affecting team productivity

### What Information to Include

When filing an issue, include:

```
1. ENVIRONMENT
   - Claude Code version: `claude --version`
   - HtmlGraph plugin version: `claude plugin info htmlgraph`
   - Operating system: macOS/Linux/Windows
   - Shell: bash/zsh/other

2. PROBLEM DESCRIPTION
   - What's happening
   - What you expected to happen
   - When it started

3. REPRODUCTION STEPS
   - Step-by-step to reproduce
   - Minimal example
   - Exact commands run

4. DIAGNOSTIC OUTPUT
   - Output from diagnostic script above
   - Relevant log files
   - System prompt content (sanitized if needed)

5. SOLUTIONS ATTEMPTED
   - Which solutions you tried
   - Results of each attempt
   - Errors encountered
```

### Example Issue Template

```markdown
## Title
System prompt not persisting post-compact on macOS

## Environment
- Claude Code: 0.45.0
- HtmlGraph plugin: 0.9.4
- OS: macOS 14.2
- Shell: zsh

## Problem
After using `/compact`, my system prompt disappears and doesn't reappear in the new session.

## Steps to Reproduce
1. Create .claude/system-prompt.md with content
2. Start Claude Code session
3. Verify system prompt appears in context
4. Run `/compact` command
5. System prompt is gone

## Diagnostic Output
[Paste complete diagnostic report]

## Solutions Attempted
1. ✗ Verified file exists
2. ✓ File permissions correct
3. ✗ Hook not running post-compact

## Expected Behavior
System prompt should persist and reappear in new session after compact.
```

### Support Resources

- **GitHub Issues**: https://github.com/Shakes-tzd/htmlgraph/issues
- **Documentation**: [System Prompt Architecture](SYSTEM_PROMPT_ARCHITECTURE.md)
- **Customization**: [System Prompt Customization Guide](SYSTEM_PROMPT_CUSTOMIZATION.md)
- **Admin Setup**: [Delegation Enforcement Guide](DELEGATION_ENFORCEMENT_ADMIN_GUIDE.md)

---

## Quick Reference Table

| Problem | Check | Solution |
|---------|-------|----------|
| Prompt missing from context | File exists + hook running | Create file, install plugin |
| Post-compact not persisting | Env vars set + backup exists | Restore from backup |
| Skill not activating | Plugin installed + env var set | Install/update plugin |
| Agent attribution missing | SDK(agent=...) used | Add agent parameter |
| Session not linking | Session IDs change | Check state file |

---

For detailed technical information, see [System Prompt Architecture](SYSTEM_PROMPT_ARCHITECTURE.md).

For setup and configuration, see [System Prompt Customization Guide](SYSTEM_PROMPT_CUSTOMIZATION.md) and [Delegation Enforcement Guide](DELEGATION_ENFORCEMENT_ADMIN_GUIDE.md).
