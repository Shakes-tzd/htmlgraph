# Deployment & Release Rules

**CRITICAL: Use `./scripts/deploy-all.sh` for all deployment operations.**

## Using the Deployment Script (FLEXIBLE OPTIONS)

**IMPORTANT PRE-DEPLOYMENT CHECKLIST:**
1. ✅ **MUST be in project root directory** - Script will fail if run from subdirectories like `dist/`
2. ~~✅ **Commit all changes first**~~ - **AUTOMATED!** Script auto-commits version changes in Step 0
3. ~~✅ **Verify version numbers**~~ - **AUTOMATED!** Script auto-updates all version numbers in Step 0
4. ✅ **Run tests** - `uv run pytest` must pass before deployment

**NEW STREAMLINED WORKFLOW (v0.9.4+):**
```bash
# 1. Run tests
uv run pytest

# 2. Deploy (one command, fully automated!)
./scripts/deploy-all.sh 0.9.4 --no-confirm

# That's it! The script now handles:
# ✅ Dashboard file sync (index.html ← dashboard.html)
# ✅ Version updates in all files (Step 0)
# ✅ Auto-commit of version changes
# ✅ Git push with tags
# ✅ Build, publish, install
# ✅ Plugin updates
# ✅ No interactive prompts with --no-confirm
```

**Session Tracking Files Excluded:**
```
.gitignore now excludes regenerable session tracking:
- .htmlgraph/sessions/*.jsonl
- .htmlgraph/events/*.jsonl
- .htmlgraph/parent-activity.json

This eliminates the multi-commit cycle problem.
```

**Quick Usage:**
```bash
# Full release (non-interactive, recommended)
./scripts/deploy-all.sh 0.9.4 --no-confirm

# Full release (with confirmations)
./scripts/deploy-all.sh 0.9.4

# Documentation changes only (commit + push)
./scripts/deploy-all.sh --docs-only

# Build package only (test builds)
./scripts/deploy-all.sh --build-only

# Skip PyPI publishing (build + install only)
./scripts/deploy-all.sh 0.9.4 --skip-pypi

# Preview what would happen (dry-run)
./scripts/deploy-all.sh --dry-run

# Show all options
./scripts/deploy-all.sh --help
```

**Available Flags:**
- `--no-confirm` - Skip all confirmation prompts (non-interactive mode)
- `--docs-only` - Only commit and push to git (skip build/publish)
- `--build-only` - Only build package (skip git/publish/install)
- `--skip-pypi` - Skip PyPI publishing step
- `--skip-plugins` - Skip plugin update steps
- `--dry-run` - Show what would happen without executing

**What the Script Does (9 Steps):**
- **Pre-flight: Dashboard Sync** - Sync `src/python/htmlgraph/dashboard.html` → `index.html`
- **Pre-flight: Code Quality** - Run linters (ruff, mypy) and tests
- **Pre-flight: Plugin Sync** - Verify packages/claude-plugin and .claude are synced
0. **Update & Commit Versions** - Auto-update version numbers in all files and commit
1. **Git Push** - Push commits and tags to origin/main
2. **Build Package** - Create wheel and source distributions
3. **Publish to PyPI** - Upload package to PyPI
4. **Local Install** - Install latest version locally
5. **Update Claude Plugin** - Run `claude plugin update htmlgraph`
6. **Update Gemini Extension** - Update version in gemini-extension.json
7. **Update Codex Skill** - Check for Codex and update if present
8. **Create GitHub Release** - Create release with distribution files

**See:** `scripts/README.md` for complete documentation

## Version Numbering

HtmlGraph follows [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 0.3.0)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

**Version Files to Update:**
1. `pyproject.toml` - Package version
2. `src/python/htmlgraph/__init__.py` - `__version__` variable
3. `packages/claude-plugin/.claude-plugin/plugin.json` - Claude plugin version
4. `packages/gemini-extension/gemini-extension.json` - Gemini extension version

## Publishing Checklist

**Pre-Release:**
- [ ] All tests pass: `uv run pytest`
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if exists)
- [ ] Version bumped in all files
- [ ] Changes committed to git
- [ ] Create git tag: `git tag v0.3.0`

**Build & Publish:**
```bash
# 1. Update versions (example for 0.3.0)
# Edit: pyproject.toml, __init__.py, plugin.json, gemini-extension.json

# 2. Commit version bump
git add pyproject.toml src/python/htmlgraph/__init__.py \
  packages/claude-plugin/.claude-plugin/plugin.json \
  packages/gemini-extension/gemini-extension.json
git commit -m "chore: bump version to 0.3.0"

# 3. Create git tag
git tag v0.3.0
git push origin main --tags

# 4. Build distributions
uv build
# Creates: dist/htmlgraph-0.3.0-py3-none-any.whl
#          dist/htmlgraph-0.3.0.tar.gz

# 5. Publish to PyPI
source .env  # Load PyPI_API_TOKEN
uv publish dist/htmlgraph-0.3.0* --token "$PyPI_API_TOKEN"

# Alternative: Set token as environment variable
export UV_PUBLISH_TOKEN="pypi-YOUR_TOKEN_HERE"
uv publish dist/htmlgraph-0.3.0*

# 6. Verify publication
open https://pypi.org/project/htmlgraph/
```

## PyPI Credentials Setup

**Option 1: API Token (Recommended)**
1. Create token at: https://pypi.org/manage/account/token/
2. Add to `.env` file:
   ```bash
   PyPI_API_TOKEN=pypi-YOUR_TOKEN_HERE
   ```
3. Use with: `source .env && uv publish dist/* --token "$PyPI_API_TOKEN"`

**Option 2: Environment Variable**
```bash
export UV_PUBLISH_TOKEN="pypi-YOUR_TOKEN_HERE"
uv publish dist/*
```

**Option 3: Command-line Arguments**
```bash
uv publish dist/* --username YOUR_USERNAME --password YOUR_PASSWORD
```

## Post-Release

**Update Claude Plugin:**
```bash
# Users update with:
claude plugin update htmlgraph

# Or fresh install:
claude plugin install htmlgraph@0.3.0
```

**Update Gemini Extension:**
```bash
# Distribution mechanism TBD
# Users may need to manually update or use extension marketplace
```

**Verify Installation:**
```bash
# Test PyPI package
pip install htmlgraph==0.3.0
python -c "import htmlgraph; print(htmlgraph.__version__)"

# Check PyPI page
curl -s https://pypi.org/pypi/htmlgraph/json | \
  python -c "import sys, json; print(json.load(sys.stdin)['info']['version'])"
```

## Common Release Commands

**Full Release Workflow:**
```bash
#!/bin/bash
# release.sh - Complete release workflow

VERSION="0.3.0"

# Update versions
sed -i '' "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
sed -i '' "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" src/python/htmlgraph/__init__.py
sed -i '' "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" packages/claude-plugin/.claude-plugin/plugin.json
sed -i '' "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" packages/gemini-extension/gemini-extension.json

# Commit and tag
git add pyproject.toml src/python/htmlgraph/__init__.py \
  packages/claude-plugin/.claude-plugin/plugin.json \
  packages/gemini-extension/gemini-extension.json
git commit -m "chore: bump version to $VERSION"
git tag "v$VERSION"
git push origin main --tags

# Build and publish
uv build
source .env
uv publish dist/htmlgraph-$VERSION* --token "$PyPI_API_TOKEN"

echo "✅ Published htmlgraph $VERSION to PyPI"
echo "📦 https://pypi.org/project/htmlgraph/$VERSION/"
```

## Rollback / Unpublish

**⚠️ WARNING: PyPI does NOT allow unpublishing or replacing versions.**

Once published, a version is permanent. If you need to fix an issue:

1. **Patch Release:** Bump to next patch version (e.g., 0.3.0 → 0.3.1)
2. **Yank Release:** Mark as unavailable (doesn't delete):
   ```bash
   # Use twine to yank (uv doesn't support this yet)
   pip install twine
   twine yank htmlgraph 0.3.0 -r pypi
   ```
3. **Publish Fix:** Release corrected version

## Version History

Track major releases and their features:

- **0.3.0** (2025-12-22) - TrackBuilder fluent API, multi-pattern glob support
- **0.2.2** (2025-12-21) - Enhanced session tracking, drift detection
- **0.2.0** (2025-12-21) - Initial public release with SDK
- **0.1.x** - Development versions

## Memory File Synchronization

**CRITICAL: Use `htmlgraph sync-docs` to maintain documentation consistency.**

HtmlGraph uses a centralized documentation pattern:
- **AGENTS.md** - Single source of truth (SDK, API, CLI, workflows)
- **CLAUDE.md** - Platform-specific notes + references AGENTS.md
- **GEMINI.md** - Platform-specific notes + references AGENTS.md

**Quick Usage:**
```bash
# Check if files are synchronized
htmlgraph sync-docs --check

# Generate platform-specific file
htmlgraph sync-docs --generate gemini
htmlgraph sync-docs --generate claude

# Synchronize all files (default)
htmlgraph sync-docs
```

**Why This Matters:**
- ✅ Single source of truth in AGENTS.md
- ✅ Platform-specific notes in separate files
- ✅ Easy maintenance (update once, not 3+ times)
- ✅ Consistency across all platforms

## Dashboard File Synchronization

**AUTOMATIC: Dashboard sync happens automatically during deployment.**

HtmlGraph maintains two versions of the dashboard HTML file:
- **Source of Truth**: `src/python/htmlgraph/dashboard.html` (packaged with Python library)
- **Project Root**: `index.html` (for easy viewing in development)

**Automatic Sync Behavior:**
- ✅ **During Deployment**: `deploy-all.sh` automatically syncs dashboard files in pre-flight
- ✅ **Auto-Commit**: If changes detected, automatically commits with message "chore: sync index.html with dashboard.html"
- ✅ **Idempotent**: Safe to run multiple times, only commits when out of sync
- ✅ **Dry-Run Support**: `--dry-run` flag shows what would be synced without executing

**Manual Sync (if needed):**
```bash
# Sync manually (rare - deployment handles this)
cp src/python/htmlgraph/dashboard.html index.html

# Check if files are in sync
git diff --quiet index.html && echo "In sync" || echo "Out of sync"
```

**Why This Matters:**
- ✅ Ensures packaged dashboard matches development version
- ✅ Eliminates manual copy-paste errors
- ✅ Prevents deployment with stale dashboard
- ✅ Maintains consistency automatically
