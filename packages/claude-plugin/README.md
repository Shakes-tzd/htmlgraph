# HtmlGraph Claude Code Plugin

This plugin tracks Claude Code activity into your project's `.htmlgraph/` so you can get cross-session continuity analytics and spot repeated workflows to automate.

## Prerequisites

**Always use `uv` for running htmlgraph commands:**

```bash
# Install htmlgraph
uv pip install htmlgraph

# Upgrade to latest version
uv pip install --upgrade htmlgraph
```

## Install (local dev marketplace)

1. Start Claude Code from the repository root (the folder that contains `.claude-plugin/marketplace.json`).
2. Add the marketplace:
   - `/plugin marketplace add .`
3. Install the plugin:
   - `/plugin install htmlgraph@htmlgraph-dev`
4. Restart Claude Code.

## What gets written

- `.htmlgraph/events/*.jsonl` is the **Git-friendly source of truth** (append-only).
- `.htmlgraph/index.sqlite` is a **rebuildable cache** for the dashboard (gitignored).
- `.htmlgraph/sessions/*.html` are human-readable session summaries (should stay small; run `uv run htmlgraph session dedupe` if you have legacy explosion).

## Dashboard

```bash
uv run htmlgraph serve
# Open http://localhost:8080
```

The Analytics tab uses the SQLite index.

## Version Check

The plugin automatically checks for htmlgraph updates at session start. If a newer version is available on PyPI, you'll see a warning with upgrade instructions.

## Notes

- Headless drift auto-classification is disabled by default to avoid recursively spawning `claude` from inside hooks.
