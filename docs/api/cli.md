# Command Line Interface

HtmlGraph provides command-line tools for managing sessions, features, and the dashboard.

## Quick Reference

### Serve Dashboard
```bash
uv run htmlgraph serve
# Visit http://localhost:8000
```

### Check Status
```bash
uv run htmlgraph status
```

### List Features
```bash
uv run htmlgraph feature list
```

### Get Feature Details
```bash
uv run htmlgraph feature show <feature-id>
```

### List Sessions
```bash
uv run htmlgraph session list
```

### View Session Details
```bash
uv run htmlgraph session show <session-id>
```

## Full Reference

For complete CLI documentation, see:
- [API Reference](reference.md) - Full API overview
- [SDK Reference](sdk.md) - Python SDK documentation
- [Guide: Dashboard](../guide/dashboard.md) - Using the dashboard

## Environment Variables

Set these to control HtmlGraph behavior:

```bash
# Data storage location
export HTMLGRAPH_HOME=~/.htmlgraph

# Server configuration
export HTMLGRAPH_HOST=localhost
export HTMLGRAPH_PORT=8000

# Logging
export HTMLGRAPH_LOG_LEVEL=INFO
```
