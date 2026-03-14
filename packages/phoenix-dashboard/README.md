# HtmlGraph Phoenix Dashboard

**Exploration: Phoenix LiveView dashboard for HtmlGraph activity feed.**

This is an exploratory implementation of a real-time activity feed dashboard
built with Phoenix LiveView, replacing the static HTML dashboard with live
WebSocket-driven updates.

## Architecture

```
                    ┌─────────────────────────┐
                    │   Phoenix LiveView App   │
                    │                          │
┌──────────┐       │  ┌───────────────────┐   │       ┌──────────┐
│  Claude   │──────▶│  │   EventPoller     │   │◀──────│  Browser  │
│  Hooks    │       │  │   (GenServer)     │   │  WS   │  Client   │
│ (Python)  │       │  └────────┬──────────┘   │       └──────────┘
└──────────┘       │           │ PubSub        │
      │             │  ┌────────▼──────────┐   │
      │             │  │ ActivityFeedLive   │   │
      ▼             │  │   (LiveView)      │   │
┌──────────┐       │  └───────────────────┘   │
│  SQLite   │◀──────│                          │
│  .htmlgraph/     │  exqlite (read-only)     │
│  htmlgraph.db    └─────────────────────────┘
└──────────┘
```

## Key Features

- **Multi-level nesting**: Session → UserQuery → Tool Events → Subagent Events (up to 4 levels)
- **Badges**: Color-coded tool types, models, subagent types, error states, feature links
- **Descending order**: Most recent events first at every level
- **Live updates**: 1-second polling with PubSub broadcast, new events flash green
- **Expand/collapse**: Per-turn and per-event toggle with tree connectors

## Event Hierarchy

```
Session (collapsible group)
└── UserQuery "Fix the database schema"     [15 tools] [2.3s] [Opus 4.6]
    ├── Read src/schema.py                  [0.1s]
    ├── Edit src/schema.py                  [0.2s]
    ├── Task → researcher-agent             [Haiku 4.5] (3)
    │   ├── Read docs/api.md
    │   ├── Grep "schema"
    │   └── WebSearch "SQLite migrations"
    ├── Bash "uv run pytest"                [1.2s]
    └── Write src/migration.py              [0.1s]
```

## Running (once dependencies are available)

```bash
cd packages/phoenix-dashboard
mix deps.get
mix phx.server
# Visit http://localhost:4000
```

## Environment Variables

- `HTMLGRAPH_DB_PATH` — Path to the HtmlGraph SQLite database (default: `../../.htmlgraph/htmlgraph.db`)
- `SECRET_KEY_BASE` — Required in production
- `PORT` — HTTP port (default: 4000)

## Future: Pythonx Integration

When Pythonx is added, the dashboard can call HtmlGraph's Python SDK directly:

```elixir
# Instead of raw SQL queries, call the Python SDK
{:ok, result} = Pythonx.eval("""
from htmlgraph import SDK
sdk = SDK(agent="phoenix-dashboard")
return sdk.analytics.recommend_next_work()
""")
```

This enables using all existing Python analytics without porting them to Elixir.
