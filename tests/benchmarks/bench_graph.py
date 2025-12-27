"""
Performance benchmarks for HtmlGraph operations.

Tracks timing for:
- Graph loading (reload)
- Query operations (CSS selectors)
- CRUD operations (add/update/remove)
- Graph traversal (ancestors, descendants, paths)

Use these benchmarks to catch performance regressions.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from htmlgraph.graph import HtmlGraph
from htmlgraph.models import Edge, Node


class BenchmarkResult:
    """Helper for tracking benchmark results."""

    def __init__(self, name: str):
        self.name = name
        self.times = []
        self.baseline = None

    def record(self, elapsed: float):
        """Record a timing (in seconds)."""
        self.times.append(elapsed)

    def avg_ms(self) -> float:
        """Get average time in milliseconds."""
        return (sum(self.times) / len(self.times)) * 1000 if self.times else 0.0

    def min_ms(self) -> float:
        """Get minimum time in milliseconds."""
        return min(self.times) * 1000 if self.times else 0.0

    def max_ms(self) -> float:
        """Get maximum time in milliseconds."""
        return max(self.times) * 1000 if self.times else 0.0

    def report(self) -> str:
        """Generate report string."""
        report = (
            f"{self.name}:\n"
            f"  avg: {self.avg_ms():.2f}ms\n"
            f"  min: {self.min_ms():.2f}ms\n"
            f"  max: {self.max_ms():.2f}ms"
        )
        if self.baseline:
            pct = ((self.avg_ms() - self.baseline) / self.baseline) * 100
            sign = "+" if pct > 0 else ""
            report += f"\n  vs baseline: {sign}{pct:.1f}%"
        return report


class TestLoadPerformance:
    """Benchmark graph loading operations."""

    def test_load_small_graph(self, small_graph):
        """Benchmark loading small graph (10 nodes)."""
        result = BenchmarkResult("Load 10 nodes")

        # Force reload to test loading performance
        for _ in range(5):
            small_graph._nodes.clear()
            small_graph._invalidate_cache()

            start = time.perf_counter()
            count = small_graph.reload()
            elapsed = time.perf_counter() - start

            result.record(elapsed)
            assert count == 10

        print(f"\n{result.report()}")
        # Should load quickly
        assert result.avg_ms() < 500, f"Load too slow: {result.avg_ms():.2f}ms"

    def test_load_medium_graph(self, medium_graph):
        """Benchmark loading medium graph (100 nodes)."""
        result = BenchmarkResult("Load 100 nodes")

        for _ in range(3):
            medium_graph._nodes.clear()
            medium_graph._invalidate_cache()

            start = time.perf_counter()
            count = medium_graph.reload()
            elapsed = time.perf_counter() - start

            result.record(elapsed)
            assert count == 100

        print(f"\n{result.report()}")
        # Target: <1s for 100 nodes
        assert result.avg_ms() < 1000, f"Load too slow: {result.avg_ms():.2f}ms"

    def test_load_large_graph(self, large_graph):
        """Benchmark loading large graph (500 nodes)."""
        result = BenchmarkResult("Load 500 nodes")

        for _ in range(2):
            large_graph._nodes.clear()
            large_graph._invalidate_cache()

            start = time.perf_counter()
            count = large_graph.reload()
            elapsed = time.perf_counter() - start

            result.record(elapsed)
            assert count == 500

        print(f"\n{result.report()}")
        # Target: <5s for 500 nodes
        assert result.avg_ms() < 5000, f"Load too slow: {result.avg_ms():.2f}ms"


class TestQueryPerformance:
    """Benchmark query operations."""

    def test_query_by_status(self, medium_graph):
        """Benchmark status queries."""
        medium_graph.reload()
        result = BenchmarkResult("Query by status (100 nodes)")

        # Run multiple queries
        for _ in range(10):
            start = time.perf_counter()
            nodes = medium_graph.query("[data-status='todo']")
            elapsed = time.perf_counter() - start

            result.record(elapsed)
            assert len(nodes) > 0

        print(f"\n{result.report()}")
        # Should query quickly
        assert result.avg_ms() < 100, f"Query too slow: {result.avg_ms():.2f}ms"

    def test_query_by_type(self, medium_graph):
        """Benchmark type queries."""
        medium_graph.reload()
        result = BenchmarkResult("Query by type (100 nodes)")

        for _ in range(10):
            start = time.perf_counter()
            nodes = medium_graph.query("[data-type='feature']")
            elapsed = time.perf_counter() - start

            result.record(elapsed)
            assert len(nodes) > 0

        print(f"\n{result.report()}")
        assert result.avg_ms() < 100, f"Query too slow: {result.avg_ms():.2f}ms"

    def test_query_complex_selector(self, medium_graph):
        """Benchmark complex CSS selector queries."""
        medium_graph.reload()
        result = BenchmarkResult("Complex query (100 nodes)")

        for _ in range(10):
            start = time.perf_counter()
            nodes = medium_graph.query("[data-status='todo'][data-priority='high']")
            elapsed = time.perf_counter() - start

            result.record(elapsed)

        print(f"\n{result.report()}")
        assert result.avg_ms() < 150, f"Query too slow: {result.avg_ms():.2f}ms"

    def test_query_with_cache(self, medium_graph):
        """Benchmark query caching effectiveness."""
        medium_graph.reload()

        # First query (cache miss)
        start = time.perf_counter()
        nodes1 = medium_graph.query("[data-status='in-progress']")
        first_time = time.perf_counter() - start

        # Second query (cache hit)
        start = time.perf_counter()
        nodes2 = medium_graph.query("[data-status='in-progress']")
        cached_time = time.perf_counter() - start

        print(f"\nQuery caching:")
        print(f"  first (miss): {first_time*1000:.2f}ms")
        print(f"  cached (hit): {cached_time*1000:.2f}ms")
        print(f"  speedup: {first_time/cached_time if cached_time > 0 else float('inf'):.1f}x")

        assert nodes1 == nodes2
        # Cached should be faster (or at least not slower)
        assert cached_time <= first_time * 1.5  # Allow some variance


class TestCrudPerformance:
    """Benchmark CRUD operations."""

    def test_add_nodes(self):
        """Benchmark adding nodes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)
            result = BenchmarkResult("Add 100 nodes")

            start = time.perf_counter()
            for i in range(100):
                node = Node(
                    id=f"test-{i:03d}",
                    title=f"Test Node {i}",
                    type="feature",
                    status="todo",
                )
                graph.add(node)
            elapsed = time.perf_counter() - start

            result.record(elapsed)
            print(f"\n{result.report()}")

            # Target: <2s for 100 nodes
            assert result.avg_ms() < 2000, f"Add too slow: {result.avg_ms():.2f}ms"

    def test_update_nodes(self, medium_graph):
        """Benchmark updating nodes."""
        medium_graph.reload()
        nodes = list(medium_graph.nodes.values())[:10]
        result = BenchmarkResult("Update 10 nodes")

        start = time.perf_counter()
        for node in nodes:
            node.status = "done"
            medium_graph.update(node)
        elapsed = time.perf_counter() - start

        result.record(elapsed)
        print(f"\n{result.report()}")

        # Target: <1s for 10 updates
        assert result.avg_ms() < 1000, f"Update too slow: {result.avg_ms():.2f}ms"

    def test_remove_nodes(self, medium_graph):
        """Benchmark removing nodes."""
        medium_graph.reload()
        node_ids = list(medium_graph.nodes.keys())[:10]
        result = BenchmarkResult("Remove 10 nodes")

        start = time.perf_counter()
        for node_id in node_ids:
            medium_graph.remove(node_id)
        elapsed = time.perf_counter() - start

        result.record(elapsed)
        print(f"\n{result.report()}")

        # Target: <500ms for 10 removals
        assert result.avg_ms() < 500, f"Remove too slow: {result.avg_ms():.2f}ms"

    def test_batch_delete(self, medium_graph):
        """Benchmark batch delete operations."""
        medium_graph.reload()
        node_ids = list(medium_graph.nodes.keys())[:20]
        result = BenchmarkResult("Batch delete 20 nodes")

        start = time.perf_counter()
        deleted = medium_graph.batch_delete(node_ids)
        elapsed = time.perf_counter() - start

        result.record(elapsed)
        print(f"\n{result.report()}")

        assert deleted == 20
        # Should be faster than individual deletes
        assert result.avg_ms() < 1000, f"Batch delete too slow: {result.avg_ms():.2f}ms"


class TestTraversalPerformance:
    """Benchmark graph traversal operations."""

    def test_ancestors(self, large_graph):
        """Benchmark ancestor traversal."""
        large_graph.reload()

        # Find a node with dependencies
        nodes_with_deps = [
            n for n in large_graph.nodes.values()
            if n.edges.get("blocked_by")
        ]
        if not nodes_with_deps:
            pytest.skip("No nodes with dependencies")

        result = BenchmarkResult("Ancestors traversal")

        for _ in range(5):
            start = time.perf_counter()
            for node in nodes_with_deps[:10]:
                ancestors = large_graph.ancestors(node.id)
            elapsed = time.perf_counter() - start

            result.record(elapsed)

        print(f"\n{result.report()}")
        assert result.avg_ms() < 500, f"Ancestors too slow: {result.avg_ms():.2f}ms"

    def test_descendants(self, large_graph):
        """Benchmark descendant traversal."""
        large_graph.reload()

        # Find nodes that block others
        blocking_nodes = []
        for node in large_graph.nodes.values():
            for edge_list in node.edges.values():
                for edge in edge_list:
                    if edge.relationship == "blocked_by":
                        if edge.target_id not in blocking_nodes:
                            blocking_nodes.append(edge.target_id)

        if not blocking_nodes:
            pytest.skip("No blocking nodes")

        result = BenchmarkResult("Descendants traversal")

        for _ in range(5):
            start = time.perf_counter()
            for node_id in blocking_nodes[:10]:
                descendants = large_graph.descendants(node_id)
            elapsed = time.perf_counter() - start

            result.record(elapsed)

        print(f"\n{result.report()}")
        assert result.avg_ms() < 500, f"Descendants too slow: {result.avg_ms():.2f}ms"

    def test_shortest_path(self, large_graph):
        """Benchmark shortest path calculation."""
        large_graph.reload()

        # Find connected nodes
        nodes_with_edges = [
            n for n in large_graph.nodes.values()
            if any(n.edges.values())
        ]
        if len(nodes_with_edges) < 2:
            pytest.skip("Not enough connected nodes")

        result = BenchmarkResult("Shortest path")

        for _ in range(5):
            start = time.perf_counter()
            for i in range(min(10, len(nodes_with_edges) - 1)):
                source = nodes_with_edges[i].id
                target = nodes_with_edges[i + 1].id
                path = large_graph.shortest_path(source, target)
            elapsed = time.perf_counter() - start

            result.record(elapsed)

        print(f"\n{result.report()}")
        assert result.avg_ms() < 1000, f"Shortest path too slow: {result.avg_ms():.2f}ms"


class TestMetricsCollection:
    """Test that performance metrics are collected correctly."""

    def test_metrics_tracking(self, small_graph):
        """Verify that graph tracks performance metrics."""
        small_graph.reload()

        # Reset metrics
        small_graph._metrics["query_count"] = 0
        small_graph._metrics["cache_hits"] = 0
        small_graph._metrics["cache_misses"] = 0

        # Run some queries
        small_graph.query("[data-status='todo']")
        small_graph.query("[data-status='todo']")  # Cache hit
        small_graph.query("[data-status='done']")

        # Check metrics were collected
        assert small_graph._metrics["query_count"] > 0
        assert small_graph._metrics["cache_hits"] > 0
        assert small_graph._metrics["cache_misses"] > 0

        print("\nMetrics collected:")
        print(f"  Query count: {small_graph._metrics['query_count']}")
        print(f"  Cache hits: {small_graph._metrics['cache_hits']}")
        print(f"  Cache misses: {small_graph._metrics['cache_misses']}")
        print(f"  Hit rate: {small_graph._metrics['cache_hits'] / small_graph._metrics['query_count'] * 100:.1f}%")


class TestBaselineComparison:
    """Compare current performance against baseline if available."""

    def test_save_baseline(self, small_graph, medium_graph):
        """Save current performance as baseline."""
        baseline = {}

        # Run representative benchmarks
        small_graph.reload()
        start = time.perf_counter()
        small_graph.query("[data-status='todo']")
        baseline["query_small"] = time.perf_counter() - start

        medium_graph.reload()
        start = time.perf_counter()
        medium_graph.query("[data-status='todo']")
        baseline["query_medium"] = time.perf_counter() - start

        # Save to file (optional, can be committed)
        baseline_file = Path("tests/benchmarks/baseline.json")
        with open(baseline_file, "w") as f:
            json.dump(baseline, f, indent=2)

        print(f"\nBaseline saved to {baseline_file}")
        print(f"  query_small: {baseline['query_small']*1000:.2f}ms")
        print(f"  query_medium: {baseline['query_medium']*1000:.2f}ms")

    def test_compare_to_baseline(self, small_graph, benchmark_baseline):
        """Compare current performance to baseline."""
        if not benchmark_baseline:
            pytest.skip("No baseline available")

        small_graph.reload()

        # Run current benchmark
        start = time.perf_counter()
        small_graph.query("[data-status='todo']")
        current = time.perf_counter() - start

        # Compare
        baseline_time = benchmark_baseline.get("query_small", 0)
        if baseline_time > 0:
            pct_change = ((current - baseline_time) / baseline_time) * 100
            print(f"\nPerformance vs baseline:")
            print(f"  baseline: {baseline_time*1000:.2f}ms")
            print(f"  current: {current*1000:.2f}ms")
            print(f"  change: {pct_change:+.1f}%")

            # Warn if significantly slower (>50% regression)
            if pct_change > 50:
                pytest.fail(f"Performance regression: {pct_change:+.1f}% slower than baseline")
