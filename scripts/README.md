# HtmlGraph Scripts

Collection of utility scripts for common development workflows.

## Quick Reference

```bash
# Git workflow (3 commands → 1)
./scripts/git-commit-push.sh "commit message"

# Deployment (7 steps automated)
./scripts/deploy-all.sh 0.9.1

# Both support --dry-run and --help
```

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
2. ✅ **Commit all changes first** - Script checks for uncommitted changes
3. ✅ **Verify version numbers** - Ensure consistency across all files
4. ✅ **Run tests** - \`uv run pytest\` must pass before deployment

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
