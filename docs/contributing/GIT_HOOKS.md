# Git Hooks - Automatic Tracking

HtmlGraph provides Git hooks that automatically track development events, ensuring continuity across sessions and agents. These hooks log commits, checkouts, merges, and pushes without requiring manual intervention.

## Overview

Git hooks are scripts that run automatically at specific points in the Git workflow. HtmlGraph uses them to:

- **Track commits** - Record what was done and when
- **Track branch switches** - Maintain context across branches
- **Track merges** - Log integration events
- **Track pushes** - Capture team collaboration boundaries
- **Enforce SDK usage** - Block direct edits to `.htmlgraph/` files (AI agents must use SDK)
- **Remind about features** - Suggest creating features for non-trivial work

## Available Hooks

### 1. `pre-commit` (Blocking)

**Purpose**: Enforces HtmlGraph best practices before committing.

**What it does**:
1. **BLOCKS** direct edits to `.htmlgraph/` HTML files
   - AI agents must use SDK, not file manipulation
   - Prevents accidental corruption of graph data
   - Can bypass with `git commit --no-verify` (not recommended)

2. **REMINDS** about feature tracking (non-blocking)
   - Shows active features if any exist
   - Suggests creating a feature for non-trivial work
   - Can disable with: `git config htmlgraph.precommit false`

**Example output**:
```
❌ BLOCKED: Direct edits to .htmlgraph/ files
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Modified files:
  - .htmlgraph/features/feat-abc123.html

AI agents must use SDK, not direct file edits.

Use SDK instead:
  from htmlgraph import SDK
  sdk = SDK()
  sdk.features.complete('feat-abc123')

Or CLI:
  uv run htmlgraph feature complete feat-abc123
```

### 2. `post-commit` (Non-blocking)

**Purpose**: Logs commit events for continuity tracking.

**What it does**:
- Runs in background (non-blocking)
- Logs commit hash, message, timestamp
- Records files changed
- Enables session reconstruction

**Logged data**:
```json
{
  "event": "git:commit",
  "timestamp": "2024-12-26T10:30:00Z",
  "commit": "abc123...",
  "message": "feat: add new feature",
  "files_changed": 5
}
```

### 3. `post-checkout` (Non-blocking)

**Purpose**: Tracks branch switches and checkouts.

**What it does**:
- Logs branch name changes
- Records old and new HEAD
- Helps agents understand context switches
- Runs in background

**Use cases**:
- Multi-feature development
- Agent handoffs across branches
- Understanding work context

### 4. `post-merge` (Non-blocking)

**Purpose**: Logs successful merges.

**What it does**:
- Records merge events
- Logs source and target branches
- Tracks integration points
- Runs in background

**Use cases**:
- Team collaboration tracking
- Integration milestones
- Conflict resolution history

### 5. `pre-push` (Non-blocking)

**Purpose**: Logs push events before remote update.

**What it does**:
- Records what's being pushed
- Logs remote name and URL
- Tracks team boundaries
- Runs in background

**Use cases**:
- Handoff events
- Team collaboration
- Release tracking

## Installation

### Quick Install (Recommended)

Install all hooks with default settings:

```bash
# During initialization (interactive)
htmlgraph init --interactive
# Answer "Y" to "Install git hooks?"

# Or non-interactive
htmlgraph init --install-hooks

# Or standalone installation
htmlgraph install-hooks
```

### Manual Installation

```bash
# Install all hooks
htmlgraph install-hooks

# Dry-run to see what would happen
htmlgraph install-hooks --dry-run

# Force installation (overwrite existing)
htmlgraph install-hooks --force

# Use file copies instead of symlinks
htmlgraph install-hooks --use-copy
```

### List Hook Status

```bash
htmlgraph install-hooks --list
```

**Example output**:
```
Git Hooks Installation Status
============================================================

🟢 pre-commit (✓ installed)
  Enabled in config: True
  Versioned (.htmlgraph/hooks/): True
  Installed (.git/hooks/): True
  Type: Symlink (✓ ours)
  Target: /project/.htmlgraph/hooks/pre-commit.sh

🟢 post-commit (✓ installed)
  Enabled in config: True
  Versioned (.htmlgraph/hooks/): True
  Installed (.git/hooks/): True
  Type: Symlink (✓ ours)

🔴 post-checkout (✗ installed)
  Enabled in config: False
  Versioned (.htmlgraph/hooks/): True
  Installed (.git/hooks/): False
```

## Configuration

### Configuration File

Hooks are configured via `.htmlgraph/hooks-config.json`:

```json
{
  "enabled_hooks": [
    "pre-commit",
    "post-commit",
    "post-checkout",
    "post-merge",
    "pre-push"
  ],
  "use_symlinks": true,
  "backup_existing": true,
  "chain_existing": true
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled_hooks` | array | all hooks | List of hooks to install |
| `use_symlinks` | boolean | `true` | Use symlinks instead of copies |
| `backup_existing` | boolean | `true` | Backup existing hooks |
| `chain_existing` | boolean | `true` | Chain with existing hooks |

### Enable/Disable Hooks

```bash
# Enable a hook
htmlgraph install-hooks --enable post-checkout

# Disable a hook
htmlgraph install-hooks --disable post-checkout

# Re-run installation after config changes
htmlgraph install-hooks
```

## Uninstallation

```bash
# Uninstall a specific hook
htmlgraph install-hooks --uninstall pre-commit

# Uninstall all hooks (run for each)
htmlgraph install-hooks --uninstall pre-commit
htmlgraph install-hooks --uninstall post-commit
htmlgraph install-hooks --uninstall post-checkout
htmlgraph install-hooks --uninstall post-merge
htmlgraph install-hooks --uninstall pre-push
```

## Advanced Usage

### Chaining with Existing Hooks

If you already have Git hooks installed, HtmlGraph will:

1. **Backup** existing hook to `.git/hooks/<hook>.backup`
2. **Create wrapper** that runs both hooks in sequence
3. **Exit on failure** if existing hook fails

Example chained hook:
```bash
#!/bin/bash
# Chained hook - runs existing hook then HtmlGraph hook

# Run existing hook
if [ -f ".git/hooks/pre-commit.backup" ]; then
  ".git/hooks/pre-commit.backup" || exit $?
fi

# Run HtmlGraph hook
if [ -f ".htmlgraph/hooks/pre-commit.sh" ]; then
  ".htmlgraph/hooks/pre-commit.sh" || true
fi
```

### Symlinks vs Copies

**Symlinks (default)**:
- ✅ Automatic updates when HtmlGraph is updated
- ✅ Single source of truth
- ❌ May not work on all systems (Windows)

**Copies**:
- ✅ Works everywhere
- ❌ Manual update required
- ❌ Divergence possible

Use copies on Windows or constrained environments:
```bash
htmlgraph install-hooks --use-copy
```

### Disabling Specific Checks

**Disable feature reminder** (keep blocking check):
```bash
git config htmlgraph.precommit false
```

**Bypass pre-commit entirely** (one-time):
```bash
git commit --no-verify
```

⚠️ **Warning**: `--no-verify` bypasses ALL checks including the SDK enforcement. Use sparingly.

### Troubleshooting

**Hooks not running?**

1. Check permissions:
   ```bash
   ls -la .git/hooks/
   chmod +x .git/hooks/pre-commit  # Should be executable
   ```

2. Verify installation:
   ```bash
   htmlgraph install-hooks --list
   ```

3. Check hook content:
   ```bash
   cat .git/hooks/pre-commit
   ```

**Pre-commit blocking legitimate changes?**

If you need to commit `.htmlgraph/` files (e.g., during development):
```bash
# One-time bypass (not recommended)
git commit --no-verify

# Or temporarily disable
git config htmlgraph.precommit false
# ... make commits ...
git config --unset htmlgraph.precommit
```

**Hook errors?**

Check the error log:
```bash
cat .htmlgraph/git-hook-errors.log
```

## Best Practices

### For AI Agents

1. **Never use `--no-verify`** unless explicitly instructed
2. **Always use SDK** for `.htmlgraph/` changes
3. **Create features** for non-trivial work (>30 min, 3+ files)
4. **Review hook output** to understand tracking

### For Developers

1. **Install hooks early** - Run `htmlgraph init --install-hooks` at project start
2. **Don't bypass checks** - If pre-commit blocks you, use the SDK
3. **Keep hooks updated** - Use symlinks for auto-updates
4. **Review hook logs** - Understand what's being tracked

### For Teams

1. **Standardize configuration** - Commit `.htmlgraph/hooks-config.json`
2. **Document exceptions** - If disabling hooks, explain why
3. **Use chaining** - Integrate with existing tooling
4. **Monitor compliance** - Review hook bypass frequency

## File Structure

```
project/
├── .git/
│   └── hooks/
│       ├── pre-commit          # Symlink or copy
│       ├── post-commit         # Symlink or copy
│       ├── post-checkout       # Symlink or copy
│       ├── post-merge          # Symlink or copy
│       └── pre-push            # Symlink or copy
│
├── .htmlgraph/
│   ├── hooks/
│   │   ├── pre-commit.sh       # Versioned template
│   │   ├── post-commit.sh      # Versioned template
│   │   ├── post-checkout.sh    # Versioned template
│   │   ├── post-merge.sh       # Versioned template
│   │   └── pre-push.sh         # Versioned template
│   │
│   ├── hooks-config.json       # Configuration
│   └── git-hook-errors.log     # Error log (gitignored)
```

## CLI Reference

### `htmlgraph install-hooks`

Install Git hooks for automatic tracking.

**Options**:
```
--project-dir, -d DIR    Project directory (default: current)
--force, -f              Force installation even if hooks exist
--dry-run                Show what would be done without doing it
--list, -l               List hook installation status
--uninstall, -u HOOK     Uninstall a specific hook
--enable HOOK            Enable a hook in configuration
--disable HOOK           Disable a hook in configuration
--use-copy               Use file copy instead of symlinks
```

**Examples**:
```bash
# Install all hooks
htmlgraph install-hooks

# Dry-run
htmlgraph install-hooks --dry-run

# List status
htmlgraph install-hooks --list

# Enable/disable hooks
htmlgraph install-hooks --enable post-checkout
htmlgraph install-hooks --disable pre-push

# Uninstall a hook
htmlgraph install-hooks --uninstall pre-commit

# Force reinstall with copies
htmlgraph install-hooks --force --use-copy
```

## See Also

- [AGENTS.md](../AGENTS.md) - SDK usage for AI agents
- [Session Management](./SESSIONS.md) - Session tracking details
- [Git Events](./GIT_EVENTS.md) - Event logging reference
- [SDK Reference](./SDK_REFERENCE.md) - Python SDK documentation

## FAQ

**Q: Do hooks slow down Git operations?**
A: No. All tracking hooks run in the background (asynchronous). Only pre-commit runs synchronously, and it's optimized to be fast (<100ms).

**Q: Can I use HtmlGraph without hooks?**
A: Yes! Hooks are optional. You can track manually via SDK or CLI.

**Q: What if I already have Git hooks?**
A: HtmlGraph will chain them. Your existing hooks run first, then ours.

**Q: Are hooks versioned?**
A: Yes! Templates are in `.htmlgraph/hooks/` (tracked). Installed hooks in `.git/hooks/` are not tracked (standard Git behavior).

**Q: Can I customize hooks?**
A: Yes! Edit `.htmlgraph/hooks/*.sh` files. Use copies (not symlinks) to prevent overwrites.

**Q: Do hooks work on Windows?**
A: Yes, but use `--use-copy` instead of symlinks.

**Q: How do I update hooks?**
A: If using symlinks (default), hooks auto-update when HtmlGraph is updated. If using copies, re-run `htmlgraph install-hooks --force`.

---

*Last updated: 2024-12-26*
