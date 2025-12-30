# HtmlGraph Scripts

Collection of utility scripts for common development workflows.

## Quick Reference

```bash
# Install git hooks (run after cloning)
./scripts/install-hooks.sh

# Git workflow (3 commands → 1)
./scripts/git-commit-push.sh "commit message"

# Deployment (7 steps automated)
./scripts/deploy-all.sh 0.9.1

# All support --dry-run and --help
```

---

## Install Git Hooks (`install-hooks.sh`)

**Purpose**: Install pre-commit hooks for code quality checks.

**Run after cloning**:
```bash
./scripts/install-hooks.sh
```

**What it installs**:
- `pre-commit` hook that runs before every commit:
  - `ruff check` - linting
  - `ruff format --check` - formatting
  - `mypy` - type checking

Commits will be blocked if any check fails.

---

## Git Commit and Push (`git-commit-push.sh`)

**Purpose**: Systematize the common git workflow of staging, committing, and pushing.

**Reduces**:
```bash
# From this (3 bash calls):
git add -A
git commit -m "message"
git push origin main

# To this (1 bash call):
./scripts/git-commit-push.sh "message"
```

### Usage

```bash
# Basic usage
./scripts/git-commit-push.sh "chore: update session tracking"

# Skip confirmation prompt
./scripts/git-commit-push.sh "fix: deployment issues" --no-confirm

# Preview without executing
./scripts/git-commit-push.sh "feat: new feature" --dry-run

# Show help
./scripts/git-commit-push.sh --help
```

### Features

- ✅ Shows files to be committed before proceeding
- ✅ Confirms action (unless \`--no-confirm\`)
- ✅ Stages all changes (\`git add -A\`)
- ✅ Commits with provided message
- ✅ Pushes to origin/main
- ✅ Supports \`--dry-run\` for preview

### Flags

- \`--dry-run\` - Show what would happen without executing
- \`--no-confirm\` - Skip confirmation prompt
- \`--help\` - Show help message

---

## Plugin Sync Tool (`sync_plugin_to_local.py`)

**Purpose**: Maintain single source of truth by syncing `packages/claude-plugin/` → `.claude/` for dogfooding.

**What it syncs**:
- Hook scripts (`hooks/scripts/*.py`)
- Hook configuration (`hooks/hooks.json`)
- Skills (`skills/*/SKILL.md`)
- Config files (`config/*.json`, `config/*.md`)

### Usage

```bash
# Check sync status
uv run python scripts/sync_plugin_to_local.py --check

# Preview changes
uv run python scripts/sync_plugin_to_local.py --dry-run

# Perform sync
uv run python scripts/sync_plugin_to_local.py
```

### When to Use

**Before committing plugin changes**:
```bash
# 1. Edit plugin files
vim packages/claude-plugin/hooks/scripts/session-start.py

# 2. Sync to .claude for testing
uv run python scripts/sync_plugin_to_local.py

# 3. Test locally, then commit both
git add packages/claude-plugin/ .claude/
git commit -m "feat: enhance session tracking"
```

**Before deployment**: The deploy script automatically checks sync status and fails if out of sync.

### Features

- ✅ Ensures `.claude/` matches distributed plugin exactly
- ✅ Enables proper dogfooding (use what we ship)
- ✅ Integrated into deployment workflow
- ✅ Preserves local-only files (session-start.sh, protect-htmlgraph.sh)

See [Plugin Sync Documentation](../docs/PLUGIN_SYNC.md) for details.

---

## Deployment Script (`deploy-all.sh`)

**Purpose**: Automate the complete deployment workflow from git push to PyPI publish to plugin updates.

**10 Automated Steps**:
0. **Pre-flight check** - Verify plugin sync
1. **Update version numbers** - Auto-update and commit all version files
2. **Push to git** - With automatic tag creation
3. **Build Python package** - Create wheel and source distribution
4. **Publish to PyPI** - Upload to package index
5. **Install locally** - Install and verify latest version
6. **Update Claude plugin** - Sync plugin files
7. **Update Gemini extension** - Update version metadata
8. **Update Codex skill** - If applicable
9. **Create GitHub release** - With distribution files and release notes

### Usage

```bash
# Full release
./scripts/deploy-all.sh 0.9.1

# Full release (non-interactive, no prompts)
./scripts/deploy-all.sh 0.9.1 --no-confirm

# Documentation changes only (skip build/publish)
./scripts/deploy-all.sh --docs-only

# Build package only (skip git/publish/install)
./scripts/deploy-all.sh --build-only

# Skip PyPI publishing
./scripts/deploy-all.sh 0.9.1 --skip-pypi

# Preview what would happen
./scripts/deploy-all.sh --dry-run
```

### Pre-Deployment Checklist

**CRITICAL - Do these first:**

1. ✅ **MUST be in project root directory** - Script fails from subdirectories
2. ~~✅ **Commit all changes first**~~ - **AUTOMATED!** Script auto-commits version changes
3. ~~✅ **Verify version numbers**~~ - **AUTOMATED!** Script auto-updates and commits versions
4. ✅ **Run tests** - `uv run pytest` must pass before deployment

**What's Automated Now (v0.9.4+):**
- ✅ Version number updates (Step 0)
- ✅ Auto-commit of version files
- ✅ Session tracking files excluded from git (via .gitignore)
- ✅ Non-interactive mode with `--no-confirm` flag

**New Workflow:**
```bash
# 1. Run tests
uv run pytest

# 2. Deploy (one command, fully automated!)
./scripts/deploy-all.sh 0.9.4 --no-confirm

# That's it! Script handles:
# - Version updates in all files
# - Auto-commit version changes
# - Git push with tags
# - Build, publish, install
# - Plugin updates
```

---

## Common Workflows

### Quick Commit and Push

```bash
./scripts/git-commit-push.sh "chore: update docs" --no-confirm
```

### Full Release

```bash
# 1. Pre-deployment checks
cd /Users/shakes/DevProjects/htmlgraph
uv run pytest
git status

# 2. Deploy
./scripts/deploy-all.sh 0.9.1
```

### Development Notes

**CRITICAL**: All scripts use \`uv run python\` instead of bare \`python\` to comply with project standards.

---

## Troubleshooting

### "No such file or directory"
**Solution**: Always run from project root
```bash
cd /Users/shakes/DevProjects/htmlgraph
./scripts/git-commit-push.sh "message"
```

### "Uncommitted changes detected"
**Solution**: Commit changes first
```bash
./scripts/git-commit-push.sh "chore: commit" --no-confirm
./scripts/deploy-all.sh 0.9.1
```

### Pre-Deployment Checklist

**CRITICAL - Do these first:**

1. ✅ **MUST be in project root directory** - Script fails from subdirectories
2. ✅ **Commit all changes first** - Script checks for uncommitted changes
3. ~~✅ **Verify version numbers**~~ - **AUTOMATED!** Script now updates all version numbers automatically
4. ✅ **Run tests** - `uv run pytest` must pass before deployment

---

### Version Management (AUTOMATED!)

**NEW:** The script now automatically updates version numbers in all files!

Just provide the version number and the script handles the rest:

```bash
./scripts/deploy-all.sh 0.9.3
```

**Files Updated Automatically:**
- ✅ `pyproject.toml` - Python package version
- ✅ `src/python/htmlgraph/__init__.py` - `__version__` variable
- ✅ `packages/claude-plugin/.claude-plugin/plugin.json` - Claude plugin version
- ✅ `packages/gemini-extension/gemini-extension.json` - Gemini extension version

**How it works:**
1. Script detects version from command line argument
2. Updates all 4 files before git push (Step 0)
3. Commits include correct version numbers
4. Build uses updated version numbers
5. No more manual version updates needed!

**Example workflow:**
```bash
# Old way (manual):
# 1. Edit pyproject.toml version
# 2. Edit __init__.py version
# 3. Edit plugin.json versions
# 4. Commit version changes
# 5. Run deployment

# New way (automatic):
./scripts/deploy-all.sh 0.9.3  # That's it!
```

---

### Environment Variables

Required for PyPI publishing:
```bash
# In .env file:
PyPI_API_TOKEN=pypi-YOUR_TOKEN_HERE

# Or as environment variable:
export UV_PUBLISH_TOKEN="pypi-YOUR_TOKEN_HERE"
```
