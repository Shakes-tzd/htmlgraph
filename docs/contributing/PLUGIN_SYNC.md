# Claude Plugin Sync Strategy

## Source of Truth: `packages/claude-plugin/`

The HtmlGraph project maintains **a single source of truth** for Claude Code plugin configuration to enable proper dogfooding and ensure consistency between development and distribution.

## Why Sync?

**Dogfooding Principle**: We use exactly what we ship.

- `.claude/` directory = local development environment
- `packages/claude-plugin/` = distributed plugin package
- Both MUST have identical capabilities (hooks, skills, configs)

## Directory Structure

```
packages/claude-plugin/          # SOURCE OF TRUTH (distributed to users)
├── hooks/
│   ├── hooks.json              # Plugin hook configuration
│   └── scripts/
│       ├── session-start.py
│       ├── session-end.py
│       ├── user-prompt-submit.py
│       ├── track-event.py
│       ├── validate-work.py
│       ├── orchestrator-reflect.py
│       └── link-activities.py
├── skills/
│   ├── htmlgraph-tracker/
│   ├── htmlgraph-coder/
│   ├── htmlgraph-explorer/
│   ├── htmlgraph-orchestrator/
│   ├── parallel-orchestrator/
│   └── strategic-planning/
└── config/
    ├── validation-config.json
    ├── drift-config.json
    └── classification-prompt.md

.claude/                         # SYNCED FROM PLUGIN (local dev)
├── hooks/
│   ├── hooks.json              # Synced from plugin
│   ├── session-start.sh        # Local wrapper (preserved)
│   ├── protect-htmlgraph.sh    # Local wrapper (preserved)
│   └── scripts/                # Synced from plugin
├── skills/                     # Synced from plugin
├── config/                     # Synced from plugin
└── settings.json               # Local settings with synced hook references
```

## Sync Tool Usage

### Check Sync Status

```bash
# Check if files are in sync
uv run python scripts/sync_plugin_to_local.py --check

# Exit code 0 = in sync
# Exit code 1 = out of sync
```

### Preview Sync Changes

```bash
# Dry run (show what would change)
uv run python scripts/sync_plugin_to_local.py --dry-run
```

### Perform Sync

```bash
# Sync plugin → .claude
uv run python scripts/sync_plugin_to_local.py
```

## What Gets Synced

**✅ Synced from Plugin:**
- All hook scripts (`hooks/scripts/*.py`)
- Hook configuration (`hooks/hooks.json`)
- All skills (`skills/*/SKILL.md`)
- All config files (`config/*.json`, `config/*.md`)

**⚠️ Preserved in .claude (Local Only):**
- `.claude/settings.json` - Local settings with project-specific paths
- `.claude/hooks/session-start.sh` - Shell wrapper for session start
- `.claude/hooks/protect-htmlgraph.sh` - Local protection hook

**❌ Excluded:**
- `__pycache__` directories
- `.pyc` files

## Workflow Integration

### Before Committing Plugin Changes

```bash
# 1. Make changes in packages/claude-plugin/
vim packages/claude-plugin/hooks/scripts/session-start.py

# 2. Sync to local for testing
uv run python scripts/sync_plugin_to_local.py

# 3. Test locally with .claude/ configuration
# (hooks will run from .claude/ during development)

# 4. Commit both plugin and synced .claude changes
git add packages/claude-plugin/ .claude/
git commit -m "feat: enhance session tracking"
```

### Before Deployment

```bash
# Verify sync before publishing plugin
uv run python scripts/sync_plugin_to_local.py --check

# Should show "✅ All files are in sync!"
```

### CI/CD Integration

Add to GitHub Actions or pre-commit hooks:

```yaml
# .github/workflows/test.yml
- name: Check Plugin Sync
  run: |
    uv run python scripts/sync_plugin_to_local.py --check
    if [ $? -ne 0 ]; then
      echo "❌ Plugin and .claude are out of sync!"
      echo "Run: uv run python scripts/sync_plugin_to_local.py"
      exit 1
    fi
```

## Path Translation

The sync tool automatically translates paths between plugin and local contexts:

**Plugin (`hooks/hooks.json`):**
```json
{
  "command": "uv run \"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-start.py\""
}
```

**Local (`.claude/settings.json`):**
```json
{
  "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/scripts/session-start.py"
}
```

The synced files remain unchanged; only `.claude/settings.json` uses project-specific paths.

## Making Changes

### To Add/Modify a Hook Script

1. Edit in `packages/claude-plugin/hooks/scripts/`
2. Run `uv run python scripts/sync_plugin_to_local.py`
3. Test locally
4. Commit both directories

### To Add a New Skill

1. Create in `packages/claude-plugin/skills/new-skill/SKILL.md`
2. Run `uv run python scripts/sync_plugin_to_local.py`
3. Test with `/skill new-skill`
4. Commit both directories

### To Update Config

1. Edit in `packages/claude-plugin/config/`
2. Run `uv run python scripts/sync_plugin_to_local.py`
3. Test functionality
4. Commit both directories

## Troubleshooting

### Sync Shows Changes After Fresh Sync

**Problem**: Running sync twice shows changes on second run.

**Solution**: Check for file permission issues or encoding differences.

```bash
# Compare specific files
diff -u .claude/hooks/scripts/session-start.py \
        packages/claude-plugin/hooks/scripts/session-start.py
```

### Local Changes Getting Overwritten

**Problem**: Made changes in `.claude/` and sync overwrote them.

**Solution**: `.claude/` is NOT the source of truth. Make changes in `packages/claude-plugin/` instead.

```bash
# DON'T: Edit in .claude
vim .claude/hooks/scripts/session-start.py  # ❌ Will be overwritten

# DO: Edit in plugin
vim packages/claude-plugin/hooks/scripts/session-start.py  # ✅ Source of truth
uv run python scripts/sync_plugin_to_local.py
```

### Sync Fails During CI

**Problem**: CI shows sync failure but local works.

**Solution**: Ensure both directories are committed to git.

```bash
# Verify git status
git status

# Both should be clean or have matching changes
git add packages/claude-plugin/ .claude/
git commit -m "sync: update plugin and local config"
```

## Key Principles

1. **`packages/claude-plugin/` is the source of truth** - Always edit here first
2. **Sync before testing** - Ensure `.claude/` matches plugin for accurate testing
3. **Sync before deployment** - Verify consistency before publishing
4. **Commit both** - Always commit plugin and synced .claude together
5. **Test locally** - Use `.claude/` to dogfood exactly what users will get

## Related Documentation

- [Plugin README](../packages/claude-plugin/README.md) - Plugin installation and usage
- [Deploy Script](../scripts/deploy-all.sh) - Deployment automation
- [CLAUDE.md](../CLAUDE.md) - Project documentation
