# Migration Guide: Git-Based Continuity Spine

## Overview

This guide helps you migrate from older HtmlGraph tracking approaches to the new Git-based continuity spine architecture. The migration is designed to be **non-breaking** - both systems can run in parallel during transition.

## What's Changing

### Before: Plugin-Only Tracking

**Old Architecture**:
- Session tracking via Claude Code plugin hooks only
- Events logged via plugin hook system
- Agent-specific (Claude Code only)
- Session boundaries strict (lost on crash)

**Limitations**:
- Only works with Claude Code
- Can't track work from other agents (Codex, Cursor, etc.)
- Session data lost if plugin crashes
- No cross-agent collaboration tracking
- Limited offline support

### After: Git-Based Continuity Spine

**New Architecture**:
- Git commits as universal continuity points
- Git hooks log commit/checkout/merge/push events
- Agent-agnostic (works with any coding agent)
- Session continuity survives crashes (reconstructable from commits)

**Benefits**:
- ✅ Works with ANY agent (Claude, Codex, Cursor, vim)
- ✅ Survives session crashes (Git history is durable)
- ✅ Cross-agent collaboration tracking
- ✅ Offline-first (Git is local)
- ✅ Team-friendly (merge/push tracking)

## Migration Phases

### Phase 1: Parallel Run (Recommended)

Run both systems side-by-side to validate the Git spine before fully switching:

**Duration**: 1-2 weeks
**Goal**: Validate Git spine completeness

**Steps**:

1. **Install Git hooks alongside existing plugin**:
   ```bash
   cd /path/to/project
   htmlgraph install-hooks
   ```

2. **Verify both systems are logging**:
   ```bash
   # Check plugin events
   ls .htmlgraph/sessions/*.jsonl

   # Check git events
   ls .htmlgraph/events/*.jsonl

   # Make a commit to test
   git commit -m "test: validate git hooks"

   # Check for git event
   tail .htmlgraph/events/git.jsonl
   ```

3. **Compare outputs daily**:
   ```python
   from htmlgraph import SDK
   sdk = SDK(agent="claude")

   # Get events from last 24 hours
   plugin_events = sdk.get_recent_events(hours=24, source="plugin")
   git_events = sdk.get_recent_events(hours=24, source="git")

   print(f"Plugin events: {len(plugin_events)}")
   print(f"Git events: {len(git_events)}")
   ```

4. **Monitor for gaps**:
   - Are git hooks firing for all commits?
   - Are feature attributions correct?
   - Are session continuations working?

**Validation Checklist**:
- [ ] Git hooks fire on every commit
- [ ] Events show correct feature attribution
- [ ] Session continuity works across commits
- [ ] No duplicate events
- [ ] Both event sources align

### Phase 2: Git-Primary (Transition)

Make Git hooks the primary source of truth while keeping plugin hooks as fallback:

**Duration**: 1-2 weeks
**Goal**: Prove Git spine reliability

**Steps**:

1. **Update configuration to prefer Git events**:
   ```json
   // .htmlgraph/config.json
   {
     "tracking": {
       "primary_source": "git",
       "fallback_source": "plugin"
     }
   }
   ```

2. **Dashboard shows both sources**:
   ```python
   summary = sdk.summary(include_sources=True)
   # Output shows which events came from git vs plugin
   ```

3. **Monitor for missing events**:
   ```bash
   # Run analytics to find gaps
   uv run htmlgraph analytics validate-tracking --days 7
   ```

4. **Fix any gaps**:
   - Add missing file patterns to features
   - Improve commit message conventions
   - Add explicit feature references

**Validation Checklist**:
- [ ] Git events cover 95%+ of activity
- [ ] Plugin events only fill small gaps
- [ ] No critical events missed
- [ ] Team members can read git-based history
- [ ] Cross-agent tracking works

### Phase 3: Plugin-Optional (Final State)

Git spine is proven reliable, plugin hooks become optional for rich context:

**Duration**: Ongoing
**Goal**: Git-first, plugin-enhanced

**Steps**:

1. **Document the tradeoffs**:
   - Git hooks: Universal, minimal context
   - Plugin hooks: Rich context, Claude-only

2. **Make plugin hooks optional**:
   ```bash
   # Users can choose to disable plugin hooks
   claude plugin disable htmlgraph-hooks
   ```

3. **Update documentation**:
   - Git hooks are primary (recommended for all)
   - Plugin hooks are enhancement (optional for Claude users)

4. **Preserve user choice**:
   - Both systems continue to work
   - Users can enable/disable either or both
   - No forced migration

## Detailed Migration Instructions

### For Existing Projects

If you have an existing HtmlGraph project with plugin-based tracking:

**Step 1: Backup existing data**
```bash
# Backup sessions and events
tar -czf htmlgraph-backup-$(date +%Y%m%d).tar.gz .htmlgraph/
```

**Step 2: Install git hooks**
```bash
htmlgraph install-hooks --dry-run  # Preview what will happen
htmlgraph install-hooks            # Actually install
```

**Step 3: Verify installation**
```bash
htmlgraph install-hooks --list

# Expected output:
# ✅ pre-commit (installed)
# ✅ post-commit (installed)
# ✅ post-checkout (installed)
# ✅ post-merge (installed)
# ✅ pre-push (installed)
```

**Step 4: Test git hooks**
```bash
# Make a test commit
echo "# Test" > test.md
git add test.md
git commit -m "test: validate git hooks (feature-test-001)"

# Check event was logged
tail .htmlgraph/events/git.jsonl
# Should see GitCommit event with feature-test-001
```

**Step 5: Compare tracking coverage**
```python
from htmlgraph import SDK
sdk = SDK(agent="claude")

# Run for 1 week in parallel
# Then check coverage
stats = sdk.tracking_coverage_stats(days=7)
print(stats)

# Example output:
# {
#   "total_events": 1234,
#   "git_events": 1180,
#   "plugin_events": 1234,
#   "git_coverage_pct": 95.6,
#   "missing_from_git": ["Read", "Grep"]  # Fine-grained events
# }
```

**Step 6: Gradually transition**
- Week 1: Both systems run
- Week 2: Monitor coverage
- Week 3: Make git primary
- Week 4: Declare plugin optional

### For New Projects

If you're starting a new HtmlGraph project:

**Step 1: Initialize with git hooks**
```bash
cd /path/to/new/project
htmlgraph init --install-hooks

# This creates:
# .htmlgraph/
# ├── config.json (with git-primary tracking)
# ├── hooks/ (git hook templates)
# ├── events/ (event log directory)
# ├── sessions/ (session directory)
# └── features/ (feature directory)
```

**Step 2: Optionally enable plugin hooks**
```bash
# If using Claude Code and want rich context
claude plugin install htmlgraph
```

**Step 3: Start working**
```bash
# Create a feature
uv run htmlgraph feature create "Add user auth" --priority high

# Work on it
# ... edit files ...

# Commit (git hook will track automatically)
git commit -m "feat: add login endpoint (feature-auth-001)"

# Check tracking
uv run htmlgraph feature show feature-auth-001
```

## Migrating Session Data

### Option A: Keep Existing Sessions (Recommended)

Existing session HTML files remain valid. No migration needed.

**How it works**:
- Old sessions: Have events from plugin hooks
- New sessions: Have events from git hooks
- Both work together seamlessly
- Analytics queries work across both

**Example**:
```python
# Get all sessions (old and new)
all_sessions = sdk.sessions.all()

# Old session (plugin-tracked)
old = all_sessions[0]
print(f"Events: {old.event_count} (from plugin)")

# New session (git-tracked)
new = all_sessions[-1]
print(f"Events: {new.event_count} (from git)")

# Analytics work across both
timeline = sdk.get_feature_timeline("feature-xyz")
# Combines events from old (plugin) and new (git) sessions
```

### Option B: Backfill Git Events (Optional)

If you want uniform event sources, backfill git commits as events:

```python
from htmlgraph.git_events import backfill_commits

# Backfill last 100 commits
backfill_commits(
    graph_dir=".htmlgraph",
    limit=100,
    attribution_strategy="message_parsing"  # Parse feature refs from messages
)
```

**Backfill Strategy**:
1. Walk git log backwards
2. For each commit, create GitCommit event
3. Attribute to features via commit message parsing
4. Link to existing sessions where possible

**Limitations**:
- Can't reconstruct fine-grained events (Read, Edit, Grep)
- Best-effort feature attribution
- No session context for old commits

## Updating Code and Workflows

### SDK Changes (None Required)

**Good news**: SDK is backwards compatible. No code changes needed.

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# All existing code works unchanged
feature = sdk.features.create("New Feature").save()
sdk.sessions.start()
sdk.track_activity("Edit", "src/file.py")
```

**Enhanced queries** (optional):
```python
# New: Query by commit hash
events = sdk.get_events_for_commit("abc123")

# New: Get session chain (via continued_from)
chain = sdk.get_session_chain("session-xyz")

# New: Cross-agent attribution
agents = sdk.get_agents_for_feature("feature-auth")
# → ["claude", "codex", "cursor"]
```

### CLI Changes (None Required)

All existing CLI commands work unchanged:
```bash
# No changes needed
htmlgraph feature create "New Feature"
htmlgraph session start
htmlgraph track "Edit src/file.py"
```

**New commands** (optional):
```bash
# Validate tracking coverage
htmlgraph analytics validate-tracking

# Show git events
htmlgraph events --source git

# Show commit attribution
htmlgraph commit-info abc123
```

### Workflow Changes

**Commit Message Convention** (recommended):

Include feature references in commit messages for better attribution:

```bash
# Good (explicit feature reference)
git commit -m "feat: add login endpoint (feature-auth-001)"

# Better (structured format)
git commit -m "feat: add login endpoint

Implements: feature-auth-001
Related: feature-session-002
"

# Best (with context)
git commit -m "feat: add login endpoint

Implements: feature-auth-001
Related: feature-session-002

- JWT authentication
- Password hashing with bcrypt
- Rate limiting
"
```

**Feature File Patterns** (recommended):

Add file patterns to features for better commit attribution:

```python
feature = sdk.features.create("User Authentication") \
    .set_file_patterns([
        "src/auth/**/*.py",
        "tests/auth/**/*.py",
        "docs/auth.md"
    ]) \
    .save()

# Now commits touching these files auto-attribute to this feature
```

## Troubleshooting

### Git Hooks Not Firing

**Problem**: Commits don't create events

**Diagnosis**:
```bash
# Check if hooks are installed
ls -la .git/hooks/post-commit

# Check permissions
ls -la .git/hooks/post-commit
# Should be executable: -rwxr-xr-x

# Check content
cat .git/hooks/post-commit
# Should call htmlgraph.git_events
```

**Solutions**:
```bash
# Reinstall hooks
htmlgraph install-hooks --force

# Fix permissions
chmod +x .git/hooks/post-commit

# Test manually
.git/hooks/post-commit
tail .htmlgraph/events/git.jsonl
```

### Duplicate Events

**Problem**: Same event appears twice

**Diagnosis**:
```bash
# Check for duplicate hook calls
cat .git/hooks/post-commit
# Look for multiple calls to htmlgraph.git_events
```

**Solution**:
```bash
# Reinstall hooks cleanly
htmlgraph install-hooks --uninstall post-commit
htmlgraph install-hooks
```

### Missing Feature Attribution

**Problem**: Commits not attributed to correct feature

**Diagnosis**:
```python
from htmlgraph import SDK
sdk = SDK()

# Check active features
active = sdk.features.where(status="in-progress")
print(f"Active features: {[f.id for f in active]}")

# Check commit message parsing
from htmlgraph.git_events import parse_feature_refs
message = "your commit message here"
refs = parse_feature_refs(message)
print(f"Parsed refs: {refs}")
```

**Solutions**:

1. **Use explicit feature references** in commit messages:
   ```bash
   git commit -m "feat: add feature (feature-auth-001)"
   ```

2. **Set file patterns** on features:
   ```python
   with sdk.features.edit("feature-auth-001") as f:
       f.file_patterns = ["src/auth/**/*.py"]
   ```

3. **Mark feature as in-progress**:
   ```python
   with sdk.features.edit("feature-auth-001") as f:
       f.status = "in-progress"
   ```

### Plugin vs Git Event Conflicts

**Problem**: Same activity logged twice (once by plugin, once by git)

**Expected Behavior**: This is normal during parallel run phase.

**Mitigation**:
```python
# Analytics automatically deduplicate by event_id
sdk.get_unique_events(session_id="session-xyz")

# Or filter by source
sdk.get_events(session_id="session-xyz", source="git")
sdk.get_events(session_id="session-xyz", source="plugin")
```

## Rollback Procedure

If you need to rollback to plugin-only tracking:

**Step 1: Disable git hooks**
```bash
# Uninstall all git hooks
for hook in pre-commit post-commit post-checkout post-merge pre-push; do
    htmlgraph install-hooks --uninstall $hook
done
```

**Step 2: Update configuration**
```json
// .htmlgraph/config.json
{
  "tracking": {
    "primary_source": "plugin"
  }
}
```

**Step 3: Verify plugin hooks still work**
```python
from htmlgraph import SDK
sdk = SDK(agent="claude")

# Start a session
session = sdk.sessions.start(title="Test plugin tracking")

# Make some edits
# ...

# Check events
events = sdk.get_session_events(session.id)
print(f"Events: {len(events)}")
```

**Step 4: Optionally remove git events**
```bash
# Remove git event log
rm -f .htmlgraph/events/git.jsonl

# Keep session events (from plugin)
# Don't touch .htmlgraph/sessions/
```

## Best Practices Post-Migration

### 1. Commit Message Conventions

**Recommended format**:
```
<type>: <short description> (<feature-ref>)

<detailed description>

Implements: <feature-id>
Related: <feature-id>, <feature-id>
```

**Example**:
```bash
git commit -m "feat: add JWT authentication (feature-auth-001)

Implement JWT token generation and validation for user authentication.

Implements: feature-auth-001
Related: feature-session-002, feature-api-003

- Generate tokens with configurable expiry
- Validate tokens on protected routes
- Refresh token rotation
"
```

### 2. Feature File Patterns

Always set file patterns on features for automatic attribution:

```python
feature = sdk.features.create("User Authentication") \
    .set_file_patterns([
        "src/auth/**/*.py",
        "src/middleware/auth.py",
        "tests/auth/**/*.py",
        "tests/integration/test_auth*.py",
        "docs/auth/**/*.md"
    ]) \
    .save()
```

### 3. Active Feature Management

Keep active features list clean:

```python
# At end of session, complete finished features
sdk.features.mark_done(["feature-auth-001"])

# Or if blocked, mark as todo
with sdk.features.edit("feature-db-002") as f:
    f.status = "blocked"
    f.blocked_reason = "Waiting for DB schema review"
```

### 4. Cross-Agent Handoffs

When handing off to another agent, use handoff notes:

```python
# End session with handoff notes
sdk.sessions.end(
    handoff_notes="""
    Completed login endpoint implementation.
    Next: Add password reset flow.
    Note: Tests are passing but need integration test coverage.
    """,
    recommended_next="feature-auth-002"
)
```

### 5. Periodic Validation

Run validation weekly:

```bash
# Validate tracking coverage
uv run htmlgraph analytics validate-tracking --days 7

# Check for orphaned features
uv run htmlgraph analytics find-orphans

# Verify continuity links
uv run htmlgraph analytics validate-continuity
```

## FAQ

### Q: Do I have to migrate?

**A**: No. Both systems continue to work. Migration is optional but recommended for:
- Multi-agent projects
- Team collaboration
- Improved offline support
- Agent-agnostic tracking

### Q: Will my existing data still work?

**A**: Yes. All existing session HTML files, feature files, and event logs remain fully compatible. Analytics queries work across old (plugin) and new (git) data.

### Q: Can I run both systems permanently?

**A**: Yes. Both systems can run in parallel indefinitely. Git provides universal coverage, plugin provides rich context for Claude Code users.

### Q: What if git hooks break?

**A**: Git hooks are non-blocking (except pre-commit). If a hook fails, Git operation succeeds. Errors are logged to `.htmlgraph/git-hook-errors.log`. Plugin hooks serve as fallback.

### Q: How do I know migration is complete?

**A**: Run coverage validation:
```bash
uv run htmlgraph analytics validate-tracking --days 30
```
Target: 95%+ coverage from git events alone.

### Q: Can I customize git hooks?

**A**: Yes. Edit `.htmlgraph/hooks/*.sh` files. If using symlinks, switch to copies first:
```bash
htmlgraph install-hooks --use-copy
# Now edit .htmlgraph/hooks/*.sh
```

### Q: What about CI/CD?

**A**: Git hooks work in CI/CD. Consider:
- Disable in CI: `git config htmlgraph.hooks false`
- Or run with readonly mode for analytics
- Team pushes still tracked via pre-push hook

## Support and Resources

### Documentation

- [Git Continuity Architecture](./GIT_CONTINUITY_ARCHITECTURE.md) - Technical deep-dive
- [Git Hooks Guide](./GIT_HOOKS.md) - Hook installation and configuration
- [Event Log Reference](./EVENT_LOG.md) - Event schema and querying
- [Session Management](./SESSION_MANAGEMENT.md) - Session lifecycle

### Getting Help

**Common issues**:
- Check [Troubleshooting](#troubleshooting) section above
- Review error log: `.htmlgraph/git-hook-errors.log`
- Run diagnostics: `htmlgraph doctor`

**Community support**:
- GitHub Issues: [github.com/Shakes-tzd/htmlgraph/issues](https://github.com/Shakes-tzd/htmlgraph/issues)
- Discussions: [github.com/Shakes-tzd/htmlgraph/discussions](https://github.com/Shakes-tzd/htmlgraph/discussions)

### Feedback

Help us improve this migration guide:
- What was confusing?
- What worked well?
- What's missing?

Submit feedback via GitHub issues with label `migration-guide`.

---

*Last updated: 2025-01-02*
