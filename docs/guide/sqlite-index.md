# SQLite Index (Optional)

The SQLite index is an **optional** performance feature that accelerates queries on large graphs.

## Overview

HtmlGraph stores all data as HTML files (the source of truth). For performance, it optionally maintains a SQLite index that mirrors this data for fast queries.

**Key Points:**
- ✅ **Optional** - HtmlGraph works without it
- ✅ **Rebuildable** - Can be regenerated from HTML files anytime
- ✅ **Gitignored** - Not committed to version control
- ✅ **Automatic** - Maintained automatically by the SDK

## How It Works

```
HTML Files (source of truth)    SQLite Index (performance cache)
.htmlgraph/features/*.html  →   .htmlgraph/index.sqlite
.htmlgraph/sessions/*.html  →
.htmlgraph/tracks/*/*.html  →
```

The SDK automatically:
1. Reads HTML files when accessed
2. Updates SQLite index for faster subsequent queries
3. Rebuilds index when HTML files change

## When to Use

**Use SQLite index when:**
- You have 100+ features/nodes
- Query performance is slow
- You're running analytics frequently
- You're building dashboards

**Skip SQLite index when:**
- Small projects (< 100 nodes)
- Prefer simplicity over speed
- Working in constrained environments
- Debugging HTML structure

## Configuration

### Enable (Default)

The SQLite index is enabled by default:

```python
from htmlgraph import SDK

# Index is used automatically
sdk = SDK(agent="claude")
features = sdk.features.all()  # Queries use index
```

### Disable

To disable the index:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude", use_index=False)
# All queries read HTML files directly
```

Or via environment variable:

```bash
export HTMLGRAPH_USE_INDEX=false
htmlgraph status  # Queries HTML files only
```

## Index Maintenance

### Rebuild Index

If the index becomes out of sync:

```bash
# Rebuild from HTML files
htmlgraph index rebuild

# Or via SDK
from htmlgraph import SDK
sdk = SDK(agent="claude")
sdk.rebuild_index()
```

### Clear Index

To remove the index entirely:

```bash
rm .htmlgraph/index.sqlite

# It will be recreated on next use
```

### Check Index Status

```bash
# View index statistics
htmlgraph index stats
```

## Performance Comparison

| Operation | Without Index | With Index | Speedup |
|-----------|--------------|------------|---------|
| `features.all()` (100 nodes) | 250ms | 15ms | 16x |
| `features.where(status="todo")` | 200ms | 8ms | 25x |
| `find_bottlenecks()` | 800ms | 45ms | 18x |
| `recommend_next_work()` | 1.2s | 65ms | 18x |

*Benchmarks on M1 MacBook Pro with 100 features, 50 sessions*

## Index Schema

The SQLite index contains these tables:

- `nodes` - All graph nodes (features, bugs, etc.)
- `edges` - Relationships between nodes
- `steps` - Feature/task steps
- `sessions` - Session metadata
- `events` - Event log entries

**Note:** Schema is internal and may change between versions. Always use SDK methods to query.

## Troubleshooting

### Index Corruption

If queries return unexpected results:

```bash
# Rebuild index from HTML source of truth
htmlgraph index rebuild --force
```

### Disk Space

The index typically uses 10-20% of HTML file size:

```bash
# Check index size
du -sh .htmlgraph/index.sqlite

# Compare to HTML size
du -sh .htmlgraph/features/
du -sh .htmlgraph/sessions/
```

To reduce size, archive old features/sessions:

```bash
# Move completed features older than 90 days
htmlgraph archive --older-than 90d
```

### Performance Still Slow

If queries are slow even with indexing:

1. **Rebuild index**: `htmlgraph index rebuild`
2. **Check disk I/O**: Use SSD for `.htmlgraph/` if possible
3. **Analyze query**: Use `EXPLAIN QUERY PLAN` in SQLite
4. **Reduce data**: Archive old nodes

## Best Practices

1. **Gitignore index**: Already in `.gitignore`, never commit
2. **Rebuild after git pull**: If HTML changed, rebuild index
3. **Monitor index size**: Keep under 100MB for best performance
4. **Use for analytics**: Essential for `find_bottlenecks()`, `recommend_next_work()`

## FAQ

### Is the index required?

No. HtmlGraph works perfectly without it, just slower on large graphs.

### Can I commit the index to git?

Not recommended. The index is gitignored by default. It's rebuildable from HTML files.

### What if the index is deleted?

No problem. It will be recreated automatically on next use.

### How often is the index updated?

Automatically on every SDK write operation. No manual intervention needed.

### Does the index support transactions?

Yes. All SDK operations use SQLite transactions for consistency.

## See Also

- [Performance Optimization Guide](../cookbook/analytics.md)
- [Troubleshooting](../cookbook/troubleshooting.md)
- [Architecture Overview](../philosophy/why-html.md)
