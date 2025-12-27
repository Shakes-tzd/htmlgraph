# HtmlGraph Performance Benchmarks

Automated performance benchmarks to catch regressions.

## Running Benchmarks

```bash
# Run all benchmarks
pytest tests/benchmarks/ -v

# Run with detailed output (shows timing stats)
pytest tests/benchmarks/ -v -s

# Run specific benchmark class
pytest tests/benchmarks/bench_graph.py::TestLoadPerformance -v -s

# Run specific test
pytest tests/benchmarks/bench_graph.py::TestQueryPerformance::test_query_by_status -v -s
```

## Benchmark Categories

### Load Performance
- **test_load_small_graph**: Load 10 nodes (target: <500ms)
- **test_load_medium_graph**: Load 100 nodes (target: <1s)
- **test_load_large_graph**: Load 500 nodes (target: <5s)

### Query Performance
- **test_query_by_status**: Query by status attribute (target: <100ms)
- **test_query_by_type**: Query by type attribute (target: <100ms)
- **test_query_complex_selector**: Complex CSS selectors (target: <150ms)
- **test_query_with_cache**: Verify query caching effectiveness

### CRUD Performance
- **test_add_nodes**: Add 100 nodes (target: <2s)
- **test_update_nodes**: Update 10 nodes (target: <1s)
- **test_remove_nodes**: Remove 10 nodes (target: <500ms)
- **test_batch_delete**: Batch delete 20 nodes (target: <1s)

### Traversal Performance
- **test_ancestors**: Ancestor traversal (target: <500ms)
- **test_descendants**: Descendant traversal (target: <500ms)
- **test_shortest_path**: Shortest path calculation (target: <1s)

### Metrics
- **test_metrics_tracking**: Verify metrics collection works
- **test_save_baseline**: Save current performance as baseline
- **test_compare_to_baseline**: Compare to saved baseline

## Understanding Results

Each benchmark prints timing statistics:

```
Load 100 nodes:
  avg: 523.45ms     # Average time across runs
  min: 498.32ms     # Best (fastest) run
  max: 567.89ms     # Worst (slowest) run
  vs baseline: +5.2% # Percent change from baseline (if available)
```

## Baseline Comparison

1. **Save baseline** (first time or after optimization):
   ```bash
   pytest tests/benchmarks/bench_graph.py::TestBaselineComparison::test_save_baseline -v -s
   ```

2. **Compare to baseline** (after code changes):
   ```bash
   pytest tests/benchmarks/bench_graph.py::TestBaselineComparison::test_compare_to_baseline -v -s
   ```

The baseline is saved to `tests/benchmarks/baseline.json`.

**Note**: This file is excluded from git (via .gitignore) since baselines are environment-specific.
Each developer/CI environment should generate its own baseline.

## Performance Targets

Current performance targets (as of implementation):

| Operation | Graph Size | Target Time |
|-----------|------------|-------------|
| Load | 10 nodes | < 500ms |
| Load | 100 nodes | < 1s |
| Load | 500 nodes | < 5s |
| Query (simple) | 100 nodes | < 100ms |
| Query (complex) | 100 nodes | < 150ms |
| Add | 100 nodes | < 2s |
| Update | 10 nodes | < 1s |
| Remove | 10 nodes | < 500ms |
| Batch Delete | 20 nodes | < 1s |
| Traversal | 500 nodes | < 500ms |
| Shortest Path | 500 nodes | < 1s |

These targets are conservative and should pass on most modern hardware.
Adjust thresholds in `bench_graph.py` if needed for your environment.

## CI Integration

Add to CI pipeline to catch regressions:

```yaml
- name: Run performance benchmarks
  run: pytest tests/benchmarks/ -v
```

The tests will fail if performance degrades beyond thresholds.
