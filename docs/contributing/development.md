# Development Guide

Detailed guide for setting up a development environment.

## Prerequisites

- Python 3.10 or higher
- Git
- uv package manager
- Node.js (for JavaScript development, optional)

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/Shakes-tzd/htmlgraph.git
cd htmlgraph
```

### 2. Install Dependencies

```bash
# Install with all development dependencies
uv pip install -e ".[dev,test,docs]"
```

This installs:

- **dev**: Development tools (ruff, black, mypy)
- **test**: Testing tools (pytest, pytest-cov)
- **docs**: Documentation tools (mkdocs, mkdocstrings)

### 3. Verify Installation

```bash
# Run tests
uv run pytest

# Check version
python -c "import htmlgraph; print(htmlgraph.__version__)"
```

## Development Tools

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/python/htmlgraph --cov-report=html

# Run specific test file
uv run pytest tests/python/test_sdk.py

# Run specific test
uv run pytest tests/python/test_sdk.py::test_feature_creation

# Watch mode (requires pytest-watch)
uv run ptw
```

### Code Formatting

```bash
# Format all code
ruff format src/ tests/

# Check formatting without changes
ruff format --check src/ tests/
```

### Linting

```bash
# Lint all code
ruff check src/ tests/

# Fix auto-fixable issues
ruff check --fix src/ tests/

# Show rule details
ruff rule E501
```

### Type Checking

```bash
# Type check main code
mypy src/python/htmlgraph

# Type check tests too
mypy src/python/htmlgraph tests/python
```

### Documentation

#### MkDocs (Main Documentation)

```bash
# Serve docs locally (with live reload)
mkdocs serve

# Build docs to site/
mkdocs build

# Deploy docs to GitHub Pages
mkdocs gh-deploy
```

#### pdoc (API Documentation)

```bash
# Generate API docs locally
uv run pdoc htmlgraph --docformat google

# Save to file (uses config from pyproject.toml)
uv run pdoc htmlgraph -o docs/api-pdoc --docformat google

# Open in browser
uv run pdoc htmlgraph --docformat google

# Generate for specific module
uv run pdoc htmlgraph.sdk --docformat google
```

The pdoc configuration is in `pyproject.toml`:

```toml
[tool.pdoc]
output-directory = "docs/api-pdoc"
docformat = "google"
```

#### Documentation Workflow

1. **Docstrings**: Use Google-style docstrings in Python code
2. **MkDocs**: Write narrative documentation in `docs/`
3. **pdoc**: Auto-generates API reference from docstrings
4. **CI**: Both are verified on every push/PR

## Project Structure

### Python Package

```
src/python/htmlgraph/
├── __init__.py         # Package exports
├── sdk.py              # Main SDK interface
├── models.py           # Pydantic models
├── planning.py         # Spec and Plan models
├── graph.py            # Core graph operations
├── track_builder.py    # TrackBuilder API
├── agents.py           # Agent interface
├── server.py           # Dashboard server
├── cli.py              # CLI commands
└── dashboard.html      # Dashboard template
```

### Tests

```
tests/python/
├── conftest.py            # Pytest fixtures
├── test_sdk.py            # SDK tests
├── test_models.py         # Model tests
├── test_track_builder.py  # TrackBuilder tests
├── test_graph.py          # Graph tests
└── test_cli.py            # CLI tests
```

## Common Tasks

### Adding a New Feature

1. Write tests first (TDD):

```python
# tests/python/test_new_feature.py
def test_new_feature():
    sdk = SDK(agent="test")
    result = sdk.new_feature()
    assert result == expected
```

2. Implement feature:

```python
# src/python/htmlgraph/sdk.py
def new_feature(self):
    """New feature description.

    Returns:
        Expected return type.
    """
    # Implementation
    pass
```

3. Add documentation:

```markdown
<!-- docs/guide/new-feature.md -->
# New Feature

Description and examples...
```

4. Run tests:

```bash
uv run pytest tests/python/test_new_feature.py
```

### Fixing a Bug

1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify test passes
4. Add regression test

### Updating Documentation

1. Edit markdown files in `docs/`
2. Preview with `mkdocs serve`
3. Commit changes

## Running the Dashboard Locally

```bash
# Initialize a test graph
uv run htmlgraph init

# Create some test data
uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='dev')
sdk.features.create('Test Feature 1', priority='high')
sdk.features.create('Test Feature 2', priority='medium')
"

# Start server
uv run htmlgraph serve

# Open http://localhost:8080
```

## Debugging

### Using pdb

```python
import pdb; pdb.set_trace()
```

### Using pytest debugger

```bash
# Drop into debugger on failure
uv run pytest --pdb

# Drop into debugger on first failure
uv run pytest -x --pdb
```

### Verbose output

```bash
# Show print statements
uv run pytest -s

# More verbose
uv run pytest -vv
```

## Performance Profiling

```bash
# Profile tests
uv run pytest --profile

# Profile specific code
python -m cProfile -o profile.stats script.py

# View profile
python -m pstats profile.stats
```

## Pre-commit Hooks

Set up pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Next Steps

- [Contributing Guide](index.md) - General contribution guidelines
- [Publishing Guide](publishing.md) - How to publish releases
