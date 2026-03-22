# Installation

## Requirements

HtmlGraph requires Python 3.10 or higher.

## Install from PyPI

The easiest way to install HtmlGraph is via pip:

```bash
pip install htmlgraph
```

Or using uv (recommended):

```bash
uv pip install htmlgraph
```

## Install from Source

Clone the repository and install in development mode:

```bash
git clone https://github.com/shakestzd/htmlgraph.git
cd htmlgraph
uv pip install -e .
```

## Verify Installation

Check that HtmlGraph is installed correctly:

```bash
python -c "import htmlgraph; print(htmlgraph.__version__)"
```

Or using the CLI:

```bash
htmlgraph --version
```

## Optional Dependencies

For development and testing:

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Install testing dependencies
uv pip install -e ".[test]"

# Install documentation dependencies
uv pip install -e ".[docs]"
```

## Agent Integration

### Claude Code Plugin

```bash
# Install the HtmlGraph plugin for Claude Code
claude plugin install htmlgraph

# Or from local marketplace
claude plugin marketplace add local-marketplace
claude plugin install htmlgraph
```

### Gemini CLI Extension

```bash
# Install the HtmlGraph extension for Gemini CLI
gemini extension install htmlgraph
```

### Codex CLI Skill

```bash
# Install the HtmlGraph skill for Codex CLI
codex skill install htmlgraph
```

## Next Steps

- [Quick Start Guide](quick-start.md) - Get started with your first graph
- [Core Concepts](concepts.md) - Understand HtmlGraph fundamentals
