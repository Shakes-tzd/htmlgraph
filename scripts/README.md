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

## Deployment Script (`deploy-all.sh`)

**Purpose**: Automate the complete deployment workflow from git push to PyPI publish to plugin updates.

**8 Automated Steps**:
0. **Update version numbers** in all files (NEW!)
1. Push to git (with tags)
2. Build Python package
3. Publish to PyPI
4. Install locally
5. Update Claude plugin
6. Update Gemini extension
7. Update Codex skill (if present)

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
