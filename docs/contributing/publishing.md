# Publishing Guide

How to publish new releases of HtmlGraph.

## Quick Start: Automated Deployment

HtmlGraph includes a flexible deployment system that automates the entire release process. **This is the recommended way to publish releases.**

### First Time Setup

1. Create deployment configuration:

```bash
htmlgraph deploy init
```

2. Edit `htmlgraph-deploy.toml` to customize your deployment (already set up for HtmlGraph).

3. Set up PyPI credentials in `.env`:

```bash
PyPI_API_TOKEN=pypi-YOUR_TOKEN_HERE
```

### Deploy a Release

```bash
# Full deployment (recommended)
htmlgraph deploy run

# Dry run (preview what will happen)
htmlgraph deploy run --dry-run

# Flexible options
htmlgraph deploy run --skip-pypi        # Build and install locally only
htmlgraph deploy run --docs-only        # Just commit and push to git
htmlgraph deploy run --build-only       # Just build the package
```

The deployment system will:

1. ✅ Push changes to git
2. ✅ Build package distributions
3. ✅ Publish to PyPI
4. ✅ Install locally to verify
5. ✅ Update Claude plugin (and other configured plugins)

All with proper error handling, color-coded output, and dry-run support.

### Manual Process

If you prefer manual control or need to troubleshoot, follow the manual process below.

## Version Numbering

HtmlGraph uses [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes (e.g., 1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (e.g., 1.1.0 → 1.2.0)
- **PATCH**: Bug fixes, backward compatible (e.g., 1.1.0 → 1.1.1)

## Files to Update

When bumping version, update **all four** of these files:

1. `pyproject.toml` - Python package version
2. `src/python/htmlgraph/__init__.py` - `__version__ = "X.Y.Z"`
3. `packages/claude-plugin/.claude-plugin/plugin.json` - Claude plugin version
4. `packages/gemini-extension/gemini-extension.json` - Gemini extension version

## Publishing Checklist

### Pre-Release

- [ ] All tests pass: `uv run pytest`
- [ ] Code is formatted: `ruff format src/`
- [ ] Code is linted: `ruff check src/`
- [ ] Type checks pass: `mypy src/python/htmlgraph`
- [ ] Documentation is up to date
- [ ] Changelog is updated
- [ ] Version bumped in all 4 files
- [ ] Changes committed to git

### Build

```bash
# Clean previous builds
rm -rf dist/

# Build distributions
uv build
```

This creates:

- `dist/htmlgraph-X.Y.Z.tar.gz` (source distribution)
- `dist/htmlgraph-X.Y.Z-py3-none-any.whl` (wheel)

### Publish to PyPI

```bash
# Ensure credentials are set
source .env

# Publish to PyPI
uv publish dist/htmlgraph-X.Y.Z* --token "$PyPI_API_TOKEN"
```

### Post-Release

- [ ] Create git tag: `git tag vX.Y.Z`
- [ ] Push tag: `git push origin vX.Y.Z`
- [ ] Create GitHub release
- [ ] Update plugin installations
- [ ] Announce release

## PyPI Credentials Setup

### Option 1: API Token in .env (Recommended)

Create `.env` file:

```bash
PyPI_API_TOKEN=pypi-YOUR_TOKEN_HERE
```

Then source it before publishing:

```bash
source .env
uv publish dist/htmlgraph-X.Y.Z* --token "$PyPI_API_TOKEN"
```

### Option 2: Environment Variable

```bash
export PYPI_TOKEN=pypi-YOUR_TOKEN_HERE
uv publish dist/htmlgraph-X.Y.Z* --token "$PYPI_TOKEN"
```

### Option 3: CLI Arguments

```bash
uv publish dist/htmlgraph-X.Y.Z* --token pypi-YOUR_TOKEN_HERE
```

## Complete Publishing Commands

```bash
# 1. Update version in all 4 files
# (Manual step - edit files)

# 2. Update changelog
# (Manual step - edit docs/changelog.md)

# 3. Commit version bump
git add .
git commit -m "chore: bump version to X.Y.Z"

# 4. Build distributions
rm -rf dist/
uv build

# 5. Publish to PyPI
source .env
uv publish dist/htmlgraph-X.Y.Z* --token "$PyPI_API_TOKEN"

# 6. Create and push git tag
git tag vX.Y.Z
git push origin vX.Y.Z

# 7. Create GitHub release
gh release create vX.Y.Z --title "vX.Y.Z" --notes "Release notes here"

# 8. Verify publication
open https://pypi.org/project/htmlgraph/
pip install htmlgraph==X.Y.Z
```

## Automation Script

Save as `scripts/release.sh`:

```bash
#!/bin/bash
set -e

# Check for version argument
if [ -z "$1" ]; then
    echo "Usage: ./release.sh X.Y.Z"
    exit 1
fi

VERSION=$1

echo "Releasing version $VERSION..."

# Update versions (requires manual editing first)
echo "⚠️  Ensure versions are updated in all 4 files!"
read -p "Press enter to continue..."

# Run tests
echo "Running tests..."
uv run pytest

# Build
echo "Building distributions..."
rm -rf dist/
uv build

# Publish
echo "Publishing to PyPI..."
source .env
uv publish dist/htmlgraph-$VERSION* --token "$PyPI_API_TOKEN"

# Git tag
echo "Creating git tag..."
git tag v$VERSION
git push origin v$VERSION

# GitHub release
echo "Creating GitHub release..."
gh release create v$VERSION --title "v$VERSION" --generate-notes

echo "✅ Release $VERSION complete!"
echo "   PyPI: https://pypi.org/project/htmlgraph/$VERSION/"
echo "   GitHub: https://github.com/Shakes-tzd/htmlgraph/releases/tag/v$VERSION"
```

Usage:

```bash
chmod +x scripts/release.sh
./scripts/release.sh 0.3.0
```

## Post-Release Updates

### Update Claude Plugin

```bash
claude plugin update htmlgraph
```

### Update Gemini Extension

```bash
gemini extension update htmlgraph
```

### Update Codex Skill

```bash
codex skill update htmlgraph
```

## Verify Publication

```bash
# Check PyPI page
open https://pypi.org/project/htmlgraph/

# Install from PyPI to test
pip install htmlgraph==X.Y.Z

# Verify version
python -c "import htmlgraph; print(htmlgraph.__version__)"
```

## Safety & Rollback

### Safety

⚠️ **PyPI uploads are permanent!** You cannot:

- Delete a published version
- Re-upload the same version
- Modify published files

Always test in a staging environment first.

### Rollback

If a release has issues:

```bash
# Yank the bad version (hides from pip install)
uv publish --yank htmlgraph==X.Y.Z

# Publish a fixed version
# Increment version to X.Y.Z+1
uv build && uv publish dist/*
```

## Version History

- **0.3.0** (2024-12-22): TrackBuilder API, multi-agent support
- **0.2.2** (2024-12-20): Drift detection, session improvements
- **0.2.0** (2024-12-18): Track creation, specs and plans
- **0.1.x** (2024-12-15): Initial release, basic features

See [Changelog](../changelog.md) for details.

## Using HtmlGraph Deployment in Your Projects

The HtmlGraph deployment system is designed to be **generic** and can be used by any Python project, not just HtmlGraph itself.

### Installation

```bash
pip install htmlgraph
```

### Setup for Your Project

1. Initialize deployment config:

```bash
cd your-project/
htmlgraph deploy init
```

2. Edit `htmlgraph-deploy.toml`:

```toml
[project]
name = "your-project"
pypi_package = "your-package-name"

[deployment]
steps = [
    "git-push",
    "build",
    "pypi-publish",
    "local-install",
    "update-plugins"  # Optional
]

[deployment.git]
branch = "main"
remote = "origin"

[deployment.build]
command = "uv build"  # or "python -m build"

[deployment.pypi]
token_env_var = "PyPI_API_TOKEN"

[deployment.plugins]
# Add your plugin update commands (optional)
# claude = "claude plugin update {package}"

[deployment.hooks]
# Custom commands at each stage
pre_build = ["pytest"]  # Run tests before build
post_build = []
pre_publish = []
post_publish = ["./scripts/notify_release.sh {version}"]
```

3. Deploy your project:

```bash
htmlgraph deploy run
```

### Configuration Options

- **steps**: List of deployment steps to run (in order)
  - `git-push`: Push commits and tags to git remote
  - `build`: Build package distributions
  - `pypi-publish`: Publish to PyPI
  - `local-install`: Install package locally
  - `update-plugins`: Run configured plugin update commands

- **hooks**: Custom commands at each stage
  - `pre_build`: Run before building (e.g., tests, linting)
  - `post_build`: Run after building (e.g., validation)
  - `pre_publish`: Run before publishing (e.g., sanity checks)
  - `post_publish`: Run after publishing (e.g., notifications)

- **plugins**: Plugin update commands
  - Use `{package}` placeholder for package name
  - Use `{version}` placeholder for version number

### Examples

**Skip PyPI and only build locally:**
```bash
htmlgraph deploy run --skip-pypi
```

**Deploy only docs changes (no build):**
```bash
htmlgraph deploy run --docs-only
```

**Test deployment without making changes:**
```bash
htmlgraph deploy run --dry-run
```

## Next Steps

- [Development Guide](development.md) - Development setup
- [Contributing Guide](index.md) - General guidelines
