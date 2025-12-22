# Minimal MCP Server

HtmlGraph includes a tiny MCP (Model Context Protocol) server intended as a **workflow conduit** for agents that don't have native hooks or Python support (e.g., Codex/Gemini).

## Strategic Goal: Prefer SDK Over MCP

**For Python-capable agents (like Claude Code):** Use the **Python SDK directly** instead of MCP. This avoids tool schema bloat in your context window while providing more powerful, type-safe operations.

```python
# ✅ PREFERRED: Use SDK (no tool schemas in context)
from htmlgraph import SDK
sdk = SDK(agent="claude")
sdk.features.where(status="in-progress")  # Discover methods at runtime

# ❌ AVOID: MCP tools (adds unused schemas to context)
# log_event(...), get_active_feature(...), set_active_feature(...)
```

**Why SDK is better than MCP:**
- ✅ **No context bloat** - No MCP tool schemas consuming tokens
- ✅ **Runtime discovery** - Explore operations via Python introspection
- ✅ **Type hints** - AI can see all available methods
- ✅ **More powerful** - Full programmatic access, not limited to 3 tools
- ✅ **Faster** - Direct Python, no JSON-RPC overhead

## MCP Server Goals (for non-Python agents)

- Expose only **3 minimal tools** to avoid context/tool-schema bloat
- Route all state into HtmlGraph's existing filesystem-first tracking (`.htmlgraph/events/*.jsonl`)
- Encourage agents to use the **Python SDK** first, CLI second, HTTP API third

## Run

```bash
htmlgraph mcp serve
```

Use `--graph-dir` to point at a specific HtmlGraph directory:

```bash
htmlgraph mcp serve -g .htmlgraph
```

## Tools

- `log_event(tool, summary, files?, success?, feature_id?, payload?, agent?)`
- `get_active_feature(agent?)`
- `set_active_feature(feature_id, collection?, agent?)`

## Notes

- The server runs over **stdio** (JSON-RPC style messages).
- The event stream is append-only under `.htmlgraph/events/`; the analytics DB is rebuildable (`htmlgraph index rebuild`).
- `get_active_feature` and `set_active_feature` **auto-log** lightweight MCP events by default (throttled). Disable with `HTMLGRAPH_MCP_AUTOLOG=0`.

## How Agents Should Use It

MCP is intentionally minimal. For anything beyond "what am I working on?" and "log what I did", use:

### 1) **Python SDK (RECOMMENDED - Fastest & Most Powerful)**

The SDK is 3-16x faster than CLI and provides type-safe, programmatic access:

```python
from htmlgraph import SDK

sdk = SDK(agent="your-agent-name")

# Work with any collection
sdk.features.where(status="in-progress")
sdk.bugs.mark_done(["bug-001", "bug-002"])
sdk.chores.batch_update(["chore-1"], {"status": "done"})

# Edit with auto-save
with sdk.features.edit("feat-001") as f:
    f.status = "in-progress"
    f.steps[0].completed = True

# Cross-collection queries
in_progress = []
for coll_name in ['features', 'bugs', 'chores', 'spikes', 'epics']:
    coll = getattr(sdk, coll_name)
    in_progress.extend(coll.where(status='in-progress'))
```

**Why SDK:**
- ✅ 3-16x faster than CLI (no process startup)
- ✅ Type-safe with auto-complete
- ✅ Batch operations (vectorized)
- ✅ Context managers (auto-save)
- ✅ All collections supported (features, bugs, chores, spikes, epics, phases, sessions, tracks)

### 2) **CLI for One-Off Commands**

⚠️ CLI is slower (400ms startup per command) but convenient for quick queries:

```bash
htmlgraph --help
htmlgraph status
htmlgraph feature list --status in-progress
htmlgraph query "[data-status='in-progress']"
```

### 3) **HTTP API for Remote Access**

⚠️ Requires server + network overhead. Use only for remote access or web integrations:

Run the server:

```bash
htmlgraph serve
```

Common endpoints:

- `GET /api/collections` → list collections
- `GET /api/status` → WIP + primary overview
- `GET /api/<collection>` / `GET /api/<collection>/<id>` → list/get nodes
- `PATCH /api/<collection>/<id>` → update node fields

## Recommended Pattern

**For Python-based agents:**
1. Use **SDK** for all work (fastest, most powerful)
2. Call `log_event(...)` to record significant actions for cross-session analytics

**For non-Python agents:**
1. Use **CLI** for operations
2. Call `log_event(...)` to record actions in event stream

**For remote/web access:**
1. Use **HTTP API**
2. Event logging happens server-side
