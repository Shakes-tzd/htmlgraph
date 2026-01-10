# Version Synchronization Rules

**CRITICAL: Python package version MUST always equal plugin version.**

## Why This Matters

When hooks run in Claude Code, they use `--with htmlgraph>=VERSION` which pulls from PyPI.
If plugin version differs from PyPI version, hooks won't work correctly.

## Version Files (Must All Match)

```
pyproject.toml:                           version = "X.Y.Z"
src/python/htmlgraph/__init__.py:         __version__ = "X.Y.Z"
packages/claude-plugin/.claude-plugin/plugin.json:    "version": "X.Y.Z"
packages/gemini-extension/gemini-extension.json:      "version": "X.Y.Z"
```

## For Claude: Always Check PyPI

Before referencing version numbers, check PyPI for the ACTUAL current version:

```bash
# Find current PyPI version
curl -s https://pypi.org/pypi/htmlgraph/json | python3 -c "import sys, json; print(json.load(sys.stdin)['info']['version'])"

# Or check locally
grep "version = " pyproject.toml
grep "__version__" src/python/htmlgraph/__init__.py
```

## Publishing Requirements

**Before running `./scripts/deploy-all.sh VERSION`:**

1. ✅ Verify all version files match target version
2. ✅ Run: `./scripts/verify-versions.sh X.Y.Z`
3. ✅ Confirm all files were updated

**The publishing script will:**
- ✅ FAIL if versions are inconsistent
- ✅ FAIL if hook shebangs reference wrong version
- ✅ Automatically sync all version files (in future)

## Hook Shebang Format

```python
#!/usr/bin/env -S uv run --with htmlgraph>=X.Y.Z
```

This ensures:
- Hooks pull specific minimum version from PyPI
- Users get compatible version automatically
- Updates don't break existing hooks

## Version Update Workflow

When deploying new version:

```bash
# 1. Update all 4 version files to same version
# 2. Update hook shebangs to match
# 3. Run verification
./scripts/verify-versions.sh 0.25.0

# 4. Deploy
./scripts/deploy-all.sh 0.25.0 --no-confirm
```

## Emergency: Version Mismatch Detection

If versions become out of sync:

```bash
# Check what's published vs local
echo "PyPI:" && curl -s https://pypi.org/pypi/htmlgraph/json | python3 -c "import sys, json; print(json.load(sys.stdin)['info']['version'])"
echo "Local:" && grep "version = " pyproject.toml

# Fix by updating all 4 files, then:
./scripts/verify-versions.sh
./scripts/deploy-all.sh <new-version> --no-confirm
```

## For AI Agents

**DIRECTIVE**: When discussing version numbers:
1. ALWAYS check PyPI first: `curl -s https://pypi.org/pypi/htmlgraph/json`
2. Reference ACTUAL version from PyPI, not local assumptions
3. Mention all 4 version files that must match
4. Warn if versions are inconsistent
5. Recommend running `./scripts/verify-versions.sh` before deployment
