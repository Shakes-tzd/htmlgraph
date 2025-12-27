"""Test query compilation functionality."""

import tempfile
from pathlib import Path

from htmlgraph.graph import CompiledQuery, HtmlGraph
from htmlgraph.models import Node


def test_compile_query_basic():
    """Test that compile_query creates a CompiledQuery object."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        # Add some test nodes
        graph.add(Node(id="feat-001", title="Feature 1", status="todo", priority="high"))
        graph.add(Node(id="feat-002", title="Feature 2", status="blocked", priority="high"))
        graph.add(Node(id="feat-003", title="Feature 3", status="done", priority="low"))

        # Compile a query
        compiled = graph.compile_query("[data-status='blocked']")

        # Verify it's a CompiledQuery
        assert isinstance(compiled, CompiledQuery)
        assert compiled.selector == "[data-status='blocked']"


def test_query_compiled_returns_correct_results():
    """Test that query_compiled returns the same results as regular query."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        # Add test nodes
        graph.add(Node(id="feat-001", title="Feature 1", status="todo", priority="high"))
        graph.add(Node(id="feat-002", title="Feature 2", status="blocked", priority="high"))
        graph.add(Node(id="feat-003", title="Feature 3", status="blocked", priority="low"))
        graph.add(Node(id="feat-004", title="Feature 4", status="done", priority="high"))

        # Compile query
        compiled = graph.compile_query("[data-status='blocked']")

        # Execute compiled query
        results = graph.query_compiled(compiled)

        # Compare with regular query
        regular_results = graph.query("[data-status='blocked']")

        # Should have same number of results
        assert len(results) == len(regular_results)
        assert len(results) == 2

        # Should contain same IDs
        result_ids = {n.id for n in results}
        regular_ids = {n.id for n in regular_results}
        assert result_ids == regular_ids
        assert result_ids == {"feat-002", "feat-003"}


def test_compile_query_caching():
    """Test that compiling the same query twice returns cached instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        # Compile same query twice
        compiled1 = graph.compile_query("[data-status='blocked']")
        compiled2 = graph.compile_query("[data-status='blocked']")

        # Should return same instance
        assert compiled1 is compiled2

        # Check metrics
        metrics = graph.metrics
        assert metrics["compiled_queries"] == 1
        assert metrics["compiled_query_hits"] == 1


def test_compiled_query_uses_query_cache():
    """Test that compiled queries use the same cache as regular queries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        # Add test node
        graph.add(Node(id="feat-001", title="Feature 1", status="blocked", priority="high"))

        # Reset metrics
        graph.reset_metrics()

        # First query with regular query
        results1 = graph.query("[data-status='blocked']")
        assert len(results1) == 1

        # Check it was a cache miss
        metrics = graph.metrics
        assert metrics["cache_misses"] == 1
        assert metrics["cache_hits"] == 0

        # Now use compiled query with same selector
        compiled = graph.compile_query("[data-status='blocked']")
        results2 = graph.query_compiled(compiled)
        assert len(results2) == 1

        # Should be a cache hit (from regular query cache)
        metrics = graph.metrics
        assert metrics["cache_hits"] == 1
        assert metrics["cache_misses"] == 1


def test_compiled_query_lru_eviction():
    """Test that compiled query cache has LRU eviction."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        # Set small cache size for testing
        graph._compiled_query_max_size = 3

        # Add test node
        graph.add(Node(id="feat-001", title="Feature 1", status="blocked", priority="high"))

        # Compile 4 different queries (exceeds cache size)
        compiled1 = graph.compile_query("[data-status='blocked']")
        compiled2 = graph.compile_query("[data-status='todo']")
        compiled3 = graph.compile_query("[data-status='done']")
        compiled4 = graph.compile_query("[data-priority='high']")

        # Cache should only hold 3 queries
        assert len(graph._compiled_queries) == 3

        # First query should have been evicted
        assert "[data-status='blocked']" not in graph._compiled_queries

        # Other queries should still be there
        assert "[data-status='todo']" in graph._compiled_queries
        assert "[data-status='done']" in graph._compiled_queries
        assert "[data-priority='high']" in graph._compiled_queries


def test_metrics_include_compilation_stats():
    """Test that metrics include compilation statistics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        # Add test node
        graph.add(Node(id="feat-001", title="Feature 1", status="blocked", priority="high"))

        # Reset metrics
        graph.reset_metrics()

        # Compile query
        compiled = graph.compile_query("[data-status='blocked']")
        graph.query_compiled(compiled)

        # Get metrics
        metrics = graph.metrics

        # Check compilation metrics exist
        assert "compiled_queries" in metrics
        assert "compiled_query_hits" in metrics
        assert "compiled_queries_cached" in metrics
        assert "compilation_hit_rate" in metrics

        # Check values
        assert metrics["compiled_queries"] == 1
        assert metrics["compiled_query_hits"] == 0
        assert metrics["compiled_queries_cached"] == 1


def test_cache_invalidation_clears_compiled_queries():
    """Test that cache invalidation also clears compiled queries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        # Add test node
        graph.add(Node(id="feat-001", title="Feature 1", status="blocked", priority="high"))

        # Compile query
        compiled = graph.compile_query("[data-status='blocked']")
        assert len(graph._compiled_queries) == 1

        # Add another node (triggers cache invalidation)
        graph.add(Node(id="feat-002", title="Feature 2", status="todo", priority="low"))

        # Compiled query cache should be cleared
        assert len(graph._compiled_queries) == 0


if __name__ == "__main__":
    test_compile_query_basic()
    test_query_compiled_returns_correct_results()
    test_compile_query_caching()
    test_compiled_query_uses_query_cache()
    test_compiled_query_lru_eviction()
    test_metrics_include_compilation_stats()
    test_cache_invalidation_clears_compiled_queries()
    print("✅ All tests passed!")
