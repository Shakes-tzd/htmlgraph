# Contributing

Welcome! We're glad you're interested in contributing to HtmlGraph.

## Ways to Contribute

- **Report bugs**: Open an issue with reproduction steps
- **Suggest features**: Describe use cases and requirements
- **Improve docs**: Fix typos, add examples, clarify explanations
- **Write code**: Fix bugs, implement features, optimize performance
- **Share examples**: Show how you're using HtmlGraph
- **Spread the word**: Blog posts, tweets, talks

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/htmlgraph.git
cd htmlgraph
```

### 2. Set Up Development Environment

```bash
# Install with development dependencies
uv pip install -e ".[dev,test,docs]"

# Run tests
uv run pytest

# Build docs
mkdocs serve
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/python/htmlgraph

# Run specific test
uv run pytest tests/python/test_sdk.py::test_feature_creation
```

### Code Style

We use:

- **ruff** for linting
- **black** for formatting
- **mypy** for type checking

```bash
# Format code
ruff format src/

# Lint code
ruff check src/

# Type check
mypy src/python/htmlgraph
```

### Documentation

Build and preview docs locally:

```bash
# Serve docs locally
mkdocs serve

# Build docs
mkdocs build
```

## Pull Request Process

### 1. Make Your Changes

- Write clear, focused commits
- Add tests for new features
- Update documentation
- Follow code style

### 2. Test Thoroughly

```bash
# Run full test suite
uv run pytest

# Check types
mypy src/python/htmlgraph

# Lint
ruff check src/
```

### 3. Submit Pull Request

- Push to your fork
- Open pull request on main repo
- Describe what changed and why
- Link related issues

### 4. Code Review

- Respond to feedback
- Make requested changes
- Be patient and respectful

## Guidelines

### Commit Messages

Follow conventional commits:

```
feat: add TrackBuilder fluent API
fix: correct drift detection algorithm
docs: add TrackBuilder examples
test: add tests for session management
```

### Code Quality

- Write tests for new code
- Maintain test coverage >90%
- Add docstrings (Google style)
- Use type hints
- Keep functions focused and small

### Documentation

- Update relevant docs when changing features
- Add examples for new features
- Keep API reference in sync with code
- Write clear, concise explanations

## Project Structure

```
htmlgraph/
├── src/
│   ├── python/htmlgraph/     # Python SDK
│   └── js/                   # JavaScript library
├── docs/                     # Documentation
├── examples/                 # Example projects
├── tests/                    # Test suite
├── packages/                 # Agent integrations
│   ├── claude-plugin/       # Claude Code plugin
│   ├── gemini-extension/    # Gemini CLI extension
│   └── codex-skill/         # Codex CLI skill
└── .htmlgraph/              # Development graph
```

## Development Setup

See [Development Guide](development.md) for detailed setup instructions.

## Questions?

- [GitHub Discussions](https://github.com/shakestzd/htmlgraph/discussions)
- [GitHub Issues](https://github.com/shakestzd/htmlgraph/issues)
- Email: [shakes@example.com](mailto:shakes@example.com)

## Next Steps

- [Development Guide](development.md) - Detailed development setup
- [Publishing Guide](publishing.md) - How to publish releases
