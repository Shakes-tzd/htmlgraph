# Git Hooks for Agent-Agnostic Tracking

HtmlGraph uses Git hooks as a universal continuity spine, enabling event tracking that works with ANY coding agent (Claude, Codex, Gemini, Cursor, vim, etc.) without requiring agent-specific integrations.

## Overview

**Philosophy**: Git is universal. Every developer uses it. By hooking into Git events, we get agent-agnostic tracking automatically.

**Current Hooks**:
- ✅ **post-commit** - Logs every commit with full metadata
- 🔜 **post-checkout** - Track branch switches
- 🔜 **post-merge** - Track merge events
- 🔜 **pre-push** - Track team boundaries

## Installation

### Quick Start

```bash
htmlgraph init --install-hooks
```

This will:
1. Create `.htmlgraph/hooks/post-commit.sh`
2. Install hook to `.git/hooks/post-commit`
3. Detect and chain existing hooks
4. Test the installation

### Manual Installation

If you prefer manual setup:

```bash
# 1. Ensure hooks directory exists
mkdir -p .htmlgraph/hooks

# 2. Copy hook script
cp path/to/post-commit.sh .htmlgraph/hooks/

# 3. Make executable
chmod +x .htmlgraph/hooks/post-commit.sh

# 4. Symlink to git hooks
ln -s $(pwd)/.htmlgraph/hooks/post-commit.sh .git/hooks/post-commit
```

### Existing Hooks

If you already have a `post-commit` hook, the installer will:
1. Backup your existing hook to `post-commit.existing`
2. Create a chaining hook that runs both
3. Ensure your hook runs first, HtmlGraph second
4. HtmlGraph hook never blocks on errors

## Post-Commit Hook

### What It Logs

```json
{
  "type": "GitCommit",
  "timestamp": "2025-12-17T06:45:00Z",
  "commit_hash": "dc86075abc123...",
  "commit_hash_short": "dc86075",
  "branch": "main",
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "commit_message": "feat: add new feature\n\nImplements: feature-xyz",
  "files_changed": ["src/file.py", "tests/test.py"],
  "insertions": 45,
  "deletions": 12,
  "features": ["feature-xyz"],
  "session_id": "session-abc-123"
}
```

### Feature Attribution

The hook automatically links commits to features using **three sources**:

1. **Active Features**: Features marked as "in-progress"
   ```bash
   htmlgraph feature start feature-xyz
   git commit -m "work on feature"
   # → Linked to feature-xyz
   ```

2. **Commit Message Parsing**: Looks for patterns
   ```
   Implements: feature-xyz
   Fixes: bug-abc
   Refs: feature-123
   ```

3. **Combined**: Merges both sources
   ```bash
   # Active: feature-auth
   git commit -m "feat: add OAuth\n\nImplements: feature-session"
   # → Linked to: feature-auth, feature-session
   ```

### Performance

- **Target**: <100ms overhead per commit
- **Actual**: ~10-50ms (async execution)
- **Method**: Background process, non-blocking
- **Errors**: Never block commits

### Error Handling

The hook is designed to **never fail**:

```bash
# If HtmlGraph not available
if ! command -v htmlgraph &> /dev/null; then
    # Fallback to Python module
    python3 -m htmlgraph.git_events commit &> /dev/null &
fi

# Always exit successfully
exit 0
```

Errors are logged to `.htmlgraph/git-hook-errors.log` for debugging.

## Event Storage

Events are appended to JSONL files:

```
.htmlgraph/
└── events/
    ├── session-abc-123.jsonl      # Active session's events
    └── git-events.jsonl            # Fallback if no session
```

**Format**: One JSON object per line (JSONL)
**Advantages**:
- Append-only (fast, safe)
- Streaming-friendly
- Human-readable
- Git-friendly diffs

## Hook Chaining

When existing hooks are detected:

```bash
#!/bin/bash
# Chained hook - runs existing hook then HtmlGraph hook

# Run existing hook (blocks on error)
if [ -f ".git/hooks/post-commit.existing" ]; then
    ".git/hooks/post-commit.existing" || exit $?
fi

# Run HtmlGraph hook (never blocks)
if [ -f ".htmlgraph/hooks/post-commit.sh" ]; then
    ".htmlgraph/hooks/post-commit.sh" || true
fi
```

**Key principle**: Existing hooks have priority, HtmlGraph never breaks your workflow.

## Testing

### Verify Installation

```bash
# 1. Check hook exists
ls -la .git/hooks/post-commit

# 2. Make a test commit
git commit -m "test: verify git hook" --allow-empty

# 3. Check events log
tail .htmlgraph/events/*.jsonl
```

### Expected Output

```json
{
  "type": "GitCommit",
  "commit_hash_short": "abc123d",
  "commit_message": "test: verify git hook",
  ...
}
```

## Debugging

### Hook Not Running

1. **Check hook is executable**:
   ```bash
   ls -la .git/hooks/post-commit
   # Should show: -rwxr-xr-x (executable)
   ```

2. **Run hook manually**:
   ```bash
   .git/hooks/post-commit
   ```

3. **Check error log**:
   ```bash
   cat .htmlgraph/git-hook-errors.log
   ```

### Events Not Logged

1. **Verify htmlgraph CLI works**:
   ```bash
   htmlgraph git-event commit
   ```

2. **Check session exists**:
   ```bash
   htmlgraph session list
   ```

3. **Manual test**:
   ```bash
   python3 -m htmlgraph.git_events commit
   ```

## Configuration

### Disable Hook

Temporarily:
```bash
git commit --no-verify -m "skip hooks"
```

Permanently:
```bash
rm .git/hooks/post-commit
```

### Custom Event File

Edit hook to specify custom location:
```bash
# In .htmlgraph/hooks/post-commit.sh
HTMLGRAPH_EVENT_FILE=".htmlgraph/events/custom.jsonl" \
  htmlgraph git-event commit
```

## Agent Compatibility

This hook works with ANY agent/tool:

| Agent/Tool | Works? | Notes |
|------------|--------|-------|
| Claude Code | ✅ | Rich integration via MCP |
| GitHub Codex | ✅ | Universal (just uses git) |
| Cursor | ✅ | Universal (just uses git) |
| Gemini Code Assist | ✅ | Universal (just uses git) |
| vim/emacs + git | ✅ | Universal (just uses git) |
| VSCode GitLens | ✅ | Universal (just uses git) |
| Command line | ✅ | Universal (just uses git) |

**Key advantage**: Works everywhere Git works, no agent-specific setup needed.

## Future Hooks

### post-checkout (Coming Soon)

Track branch switches for session continuity:

```json
{
  "type": "GitCheckout",
  "from_branch": "feature/auth",
  "to_branch": "main",
  "timestamp": "2025-12-17T06:50:00Z"
}
```

### post-merge (Coming Soon)

Track merge events for collaboration:

```json
{
  "type": "GitMerge",
  "merged_branch": "feature/auth",
  "into_branch": "main",
  "conflicts": false,
  "timestamp": "2025-12-17T06:55:00Z"
}
```

### pre-push (Coming Soon)

Track team boundaries (local → shared):

```json
{
  "type": "GitPush",
  "branch": "main",
  "remote": "origin",
  "commits_pushed": 3,
  "timestamp": "2025-12-17T07:00:00Z"
}
```

## Architecture

```
┌──────────────┐
│ Git Commit   │
└──────┬───────┘
       │
       ↓
┌──────────────────────────────────┐
│ .git/hooks/post-commit           │
│ (installed by init --install-hooks)│
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ .htmlgraph/hooks/post-commit.sh  │
│ - Checks for htmlgraph CLI       │
│ - Runs: htmlgraph git-event commit│
│ - Async, non-blocking            │
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ src/python/htmlgraph/git_events.py│
│ - log_git_commit()               │
│ - Get git metadata               │
│ - Link to active features        │
│ - Parse commit message           │
│ - Append to JSONL                │
└──────┬───────────────────────────┘
       │
       ↓
┌──────────────────────────────────┐
│ .htmlgraph/events/session-X.jsonl│
│ {"type":"GitCommit",...}         │
└──────────────────────────────────┘
```

## Best Practices

### For Developers

1. **Start features before coding**:
   ```bash
   htmlgraph feature start feature-xyz
   # Now all commits link automatically
   ```

2. **Use commit message patterns**:
   ```
   feat: add user auth

   Implements: feature-auth
   Refs: epic-security
   ```

3. **Check attribution**:
   ```bash
   htmlgraph session validate-attribution feature-xyz
   ```

### For Teams

1. **Version-control hooks**:
   ```bash
   git add .htmlgraph/hooks/
   git commit -m "chore: add git hooks"
   git push
   ```

2. **Document in README**:
   ```markdown
   ## Setup
   ```bash
   htmlgraph init --install-hooks
   ```
   ```

3. **CI/CD integration**:
   ```yaml
   # .github/workflows/ci.yml
   - name: Install HtmlGraph hooks
     run: htmlgraph init --install-hooks
   ```

## Comparison to Alternatives

### vs Claude Code Plugin Hooks

| Feature | Plugin Hooks | Git Hooks |
|---------|-------------|-----------|
| Agent support | Claude only | Universal |
| Setup | MCP required | Git only |
| Granularity | High (tool calls) | Medium (commits) |
| Overhead | ~5ms/call | ~10ms/commit |
| Offline | ❌ | ✅ |

**Recommendation**: Use both! Git hooks for universal coverage, plugin hooks for rich Claude integration.

### vs Filesystem Watcher

| Feature | Git Hooks | Filesystem Watcher |
|---------|-----------|-------------------|
| Granularity | Commit-level | File-level |
| Overhead | ~10ms/commit | Continuous |
| Setup | One command | Background daemon |
| Reliability | Very high | Medium |

**Recommendation**: Git hooks are the foundation. Add filesystem watcher for fine-grained activity if needed.

## Troubleshooting

### Hook runs but no events

**Cause**: No active session
**Fix**:
```bash
htmlgraph session start
```

### Hook slow (>100ms)

**Cause**: Synchronous execution
**Fix**: Hook should already be async (`&`). Check hook script.

### Events in wrong file

**Cause**: Multiple sessions active
**Fix**:
```bash
htmlgraph session dedupe
htmlgraph session list --status active
```

## Support

- GitHub Issues: https://github.com/Shakes-tzd/htmlgraph/issues
- Documentation: https://htmlgraph.dev/docs/git-hooks
- Examples: https://github.com/Shakes-tzd/htmlgraph/tree/main/examples

---

**Key Takeaway**: Git hooks make HtmlGraph work with ANY tool. Install once, track forever.
