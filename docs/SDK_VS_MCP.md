# SDK vs MCP: Architectural Decision

## TL;DR

**For Claude Code and Python-capable agents:** Use the **SDK**, not MCP tools.

**Why:** MCP tool schemas bloat your context window with unused definitions. The SDK lets you discover operations at runtime using Python's introspection.

---

## The Context Bloat Problem

### MCP Approach (Context Heavy)
```
Your Context Window (200K tokens):
├─ System Prompt: 5K tokens
├─ MCP Tool Schemas: 15K tokens ⚠️ BLOAT
│  ├─ log_event(tool, summary, files?, success?, feature_id?, payload?, agent?)
│  ├─ get_active_feature(agent?)
│  ├─ set_active_feature(feature_id, collection?, agent?)
│  ├─ ... (schemas for each parameter, types, descriptions)
│  └─ ... (you may not even use these tools!)
├─ Conversation: 180K tokens
└─ Available: 0K tokens

Problem: Tool schemas consume tokens even if never used!
```

### SDK Approach (Context Efficient)
```
Your Context Window (200K tokens):
├─ System Prompt: 5K tokens
├─ MCP Tool Schemas: 0K tokens ✅ ZERO BLOAT
├─ Conversation: 195K tokens
└─ Available: Still have room!

Solution: Discover operations at runtime via Python introspection!
```

---

## How Runtime Discovery Works

### MCP: Predefined Tools (Static)
```python
# Agent must know about these 3 tools upfront (via schemas in context)
mcp_log_event(tool="Read", summary="...", files=[...])
mcp_get_active_feature(agent="claude")
mcp_set_active_feature(feature_id="feat-001")

# Limited to these 3 operations only
# Each requires ~5KB of schema definition in context
```

### SDK: Runtime Discovery (Dynamic)
```python
# Agent discovers operations as needed (no upfront schemas)
from htmlgraph import SDK
sdk = SDK(agent="claude")

# Explore what's available using Python introspection
dir(sdk)                    # See: features, bugs, chores, spikes, epics...
dir(sdk.features)           # See: create, get, edit, where, all, mark_done, assign...
help(sdk.features.where)    # Get method signature and docs

# Access ALL operations without any schema overhead
sdk.features.where(status="in-progress")
sdk.bugs.mark_done(["bug-001", "bug-002"])
sdk.chores.batch_update([...], {...})

# 100+ operations available, 0 bytes of schema in context!
```

---

## Comparison Matrix

| Aspect | MCP Tools | Python SDK |
|--------|-----------|------------|
| **Context Overhead** | ~15KB schemas per tool | 0 bytes (runtime discovery) |
| **Operations Available** | 3 tools only | 100+ methods across 9 collections |
| **Discovery** | Predefined schemas | Python introspection (`dir()`, `help()`) |
| **Type Safety** | JSON schemas | Python type hints |
| **Performance** | JSON-RPC overhead | Direct Python (faster) |
| **Flexibility** | Limited to tool params | Full programmatic access |
| **Auto-complete** | ❌ No | ✅ Yes (IDE support) |
| **Best For** | Non-Python agents | Claude Code, Python agents |

---

## When to Use Each

### Use SDK (Primary - Python Agents)
✅ **Claude Code** - Has Python, can import SDK directly
✅ **Custom Python agents** - Full programmatic control
✅ **Scripts & automation** - Batch operations, complex logic

**Benefits:**
- Zero context overhead
- Runtime discovery via introspection
- Type hints and auto-complete
- 3-16x faster than CLI
- Access to all 9 collections

### Use MCP (Fallback - Non-Python Agents)
⚠️ **Codex/GPT** - No Python import support
⚠️ **Gemini** - Different runtime environment
⚠️ **JavaScript agents** - Can't import Python

**Trade-offs:**
- Minimal 3 tools to reduce bloat
- Limited operations
- JSON-RPC overhead
- Still useful for event logging

### Use CLI (One-Off Commands)
⚠️ **Shell scripts** - Quick one-liners
⚠️ **Manual exploration** - Terminal-based discovery

**Trade-offs:**
- 400ms startup per command (slow)
- Good for pipes and shell integration

### Use HTTP API (Remote Access)
⚠️ **Web dashboards** - Browser-based UI
⚠️ **Remote monitoring** - Network-accessible
⚠️ **Microservices** - Language-agnostic REST

**Trade-offs:**
- Requires running server
- Network latency
- JSON serialization overhead

---

## Example: Context Usage Comparison

### Scenario: Query in-progress work across all collections

**MCP Approach:**
```
Context overhead:
- log_event schema: ~5KB
- get_active_feature schema: ~3KB
- set_active_feature schema: ~3KB
- Custom query not possible with these 3 tools!
- Would need separate MCP tool for each collection
- Total: ~40KB+ for 8 new tools

Agent code:
mcp_query_features(status="in-progress")
mcp_query_bugs(status="in-progress")
mcp_query_chores(status="in-progress")
...
```

**SDK Approach:**
```
Context overhead: 0KB (no schemas)

Agent code:
from htmlgraph import SDK
sdk = SDK(agent="claude")

in_progress = []
for coll_name in ['features', 'bugs', 'chores', 'spikes', 'epics']:
    coll = getattr(sdk, coll_name)
    in_progress.extend(coll.where(status='in-progress'))

# Discovered methods at runtime, no context overhead!
```

**Savings: 40KB+ of context preserved for conversation!**

---

## Implementation Strategy

### For HtmlGraph

1. ✅ **Provide SDK** - Primary interface for Python agents
2. ✅ **Minimal MCP** - Only 3 tools for non-Python agents
3. ✅ **Document SDK-first** - Emphasize context efficiency
4. ✅ **CLI/API as fallbacks** - For specific use cases

### For AI Agents (like Claude Code)

1. ✅ **Import SDK directly** - `from htmlgraph import SDK`
2. ✅ **Explore at runtime** - Use `dir()`, `help()`, type hints
3. ✅ **Skip MCP tools** - Don't load MCP schemas into context
4. ✅ **Use batch operations** - Efficient vectorized updates

---

## FAQ

**Q: Why not just make MCP comprehensive with all operations?**
A: That would require 100+ tool schemas consuming massive context. SDK gives you 100+ operations with 0 context overhead.

**Q: Can I use both SDK and MCP?**
A: Yes, but if you have Python (like Claude Code), just use SDK. MCP adds no value and wastes context.

**Q: What if I need remote access?**
A: Use HTTP API for remote access. SDK is for local Python execution.

**Q: How does the agent discover SDK methods?**
A: Python introspection (`dir()`, `help()`), type hints, and IDE auto-complete. AI agents understand Python's reflection capabilities.

**Q: Is this approach unique to HtmlGraph?**
A: No! This is a general principle: **Native language APIs > Protocol-defined tools** for context efficiency.

---

## Conclusion

**The SDK is architecturally superior to MCP for Python-capable agents.**

It provides:
- ✅ **Zero context overhead** (vs. MCP's ~15KB per tool)
- ✅ **Runtime discovery** (Python introspection)
- ✅ **Full access** (100+ operations vs. 3 MCP tools)
- ✅ **Better performance** (direct Python vs. JSON-RPC)

**Recommendation:** Claude Code and similar agents should use the SDK exclusively. MCP is only for agents that can't import Python modules.
