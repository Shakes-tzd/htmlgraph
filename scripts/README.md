# Deployment Automation

This directory contains deployment scripts and tools for HtmlGraph and can be adapted for any Python project.

## Quick Start

### Option 1: Shell Script (Default)

```bash
# Full deployment (all steps)
./scripts/deploy-all.sh 0.8.0

# Just commit and push
./scripts/deploy-all.sh --docs-only

# Build package only
./scripts/deploy-all.sh --build-only

# Preview without changes (dry-run)
./scripts/deploy-all.sh --dry-run
```

### Option 2: Python Entry Point (After Installation)

```bash
# Full deployment
htmlgraph-deploy 0.8.0

# Just commit and push
htmlgraph-deploy --docs-only

# Build package only
htmlgraph-deploy --build-only

# Preview without changes
htmlgraph-deploy --dry-run
```

### Option 3: Invoke Tasks (For Developers)

```bash
# Install dev dependencies first
uv sync --group dev

# See available tasks
uv run invoke --list

# Deploy with Invoke
uv run invoke deploy --version=0.8.0

# Just build package
uv run invoke build-package

# Just publish
uv run invoke publish-pypi --version=0.8.0
```

## Available Flags

### `--docs-only`

Only commit and push to git (skip build/publish/install).

```bash
./scripts/deploy-all.sh --docs-only
```

### `--build-only`

Only build package distribution (skip git/publish/install).

```bash
./scripts/deploy-all.sh --build-only
```

### `--skip-pypi`

Skip PyPI publishing step (still builds and installs locally).

```bash
./scripts/deploy-all.sh 0.8.0 --skip-pypi
```

### `--skip-plugins`

Skip Claude, Gemini, and Codex plugin/extension updates.

```bash
./scripts/deploy-all.sh 0.8.0 --skip-plugins
```

### `--dry-run`

Show what would happen without actually executing anything.

```bash
./scripts/deploy-all.sh --dry-run
./scripts/deploy-all.sh 0.8.0 --dry-run --skip-pypi
```

### `--help`

Show help message with all options and examples.

```bash
./scripts/deploy-all.sh --help
```

## Configuration

The deployment script is configurable via the **CONFIGURATION SECTION** at the top of `deploy-all.sh`.

## Environment Setup

### PyPI Authentication

Create a `.env` file in project root:

```bash
PyPI_API_TOKEN=pypi-YOUR_TOKEN_HERE
```

Or set environment variable:

```bash
export PyPI_API_TOKEN="pypi-YOUR_TOKEN_HERE"
```

## Deployment Steps

The script performs up to 7 steps:

1. **Git Push** - Push to remote
2. **Build Package** - Create distributions
3. **Publish to PyPI** - Upload to PyPI
4. **Install Locally** - Install latest version
5. **Update Claude Plugin** - Update Claude plugin
6. **Update Gemini Extension** - Update Gemini extension
7. **Update Codex Skill** - Update Codex skill

## Workflow Examples

### Release New Version

```bash
./scripts/deploy-all.sh 0.8.0
```

### Documentation Update

```bash
./scripts/deploy-all.sh --docs-only
```

### Test Build Process

```bash
./scripts/deploy-all.sh --build-only
```

### Pre-Release Testing

```bash
./scripts/deploy-all.sh 0.8.0 --dry-run
```

## Using Deploy Script in Your Project

### Step 1: Copy the Template

```bash
cp scripts/templates/deploy-template.sh scripts/deploy.sh
chmod +x scripts/deploy.sh
```

### Step 2: Customize Configuration

Edit `scripts/deploy.sh` and customize the CONFIGURATION SECTION.

### Step 3: Test It

```bash
./scripts/deploy.sh --dry-run
```

### Step 4: Use in Your Workflow

```bash
./scripts/deploy.sh 1.0.0
```

## Python Entry Point

After installation, use the `htmlgraph-deploy` command:

```bash
htmlgraph-deploy 0.8.0
htmlgraph-deploy --dry-run
htmlgraph-deploy --help
```

## Invoke Tasks

Use Python tasks for deployment:

```bash
# List tasks
uv run invoke --list

# Deploy
uv run invoke deploy --version=0.8.0

# Individual tasks
uv run invoke push-git
uv run invoke build-package
uv run invoke publish-pypi --version=0.8.0
```

## Troubleshooting

### PyPI Token Not Found

Set environment variable:

```bash
export PyPI_API_TOKEN="pypi-YOUR_TOKEN_HERE"
```

### Build Fails

Check dependencies:

```bash
uv sync
```

### Git Push Fails

Commit changes first:

```bash
git add -A
git commit -m "..."
```

## Best Practices

1. Always use `--dry-run` first
2. Update version in pyproject.toml
3. Commit before deploying
4. Keep tokens secure
5. Test locally first
6. Use git tags for version tracking

## License

MIT - See LICENSE file for details
