# HtmlGraph for Codex

## Start Here

Read [AGENTS.md](./AGENTS.md) first for the canonical SDK/API/CLI patterns and guardrails.

## Architecture Snapshot

HtmlGraph is document-first, but not document-only:

- HTML files in `.htmlgraph/*/*.html` are the primary graph documents for work-item CRUD.
- JSONL files in `.htmlgraph/events/` are append-only event history.
- SQLite supports observability and analytics:
  - `.htmlgraph/htmlgraph.db` for dashboard/API and hook-driven event tables
  - `.htmlgraph/index.sqlite` as a rebuildable analytics cache from JSONL events

This is closer to a browser-style model: document artifacts plus indexed/queryable databases.

## Non-Negotiables

- Never edit `.htmlgraph/` HTML files directly.
- Use SDK, CLI, or API for all graph updates.
- Prefer `uv run htmlgraph ...` commands in this repo.

## Codex Quick Workflow

```bash
# orient
uv run htmlgraph status
uv run htmlgraph feature list

# claim/start work
uv run htmlgraph feature start <feature-id>

# complete work
uv run htmlgraph feature complete <feature-id>
```

## Server Commands

```bash
# dashboard/API server (default port 8080)
uv run htmlgraph serve

# fastapi observability server (default port 8000)
uv run htmlgraph serve-api
```

## Codex Automation / Headless

For CI and scripted runs, see [docs/codex_headless.md](./docs/codex_headless.md).

## Codex Skill

Codex skill assets live in [packages/codex-skill](./packages/codex-skill/).
