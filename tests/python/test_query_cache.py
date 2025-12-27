"""
Tests for query result caching with automatic invalidation.

Verifies that:
- Query results are cached
- Cache is invalidated on mutations (add, update, delete)
- Cache is invalidated on reload
- Cache returns copies to prevent mutation issues
"""

import tempfile
from pathlib import Path

import pytest

from htmlgraph import HtmlGraph
from htmlgraph.models import Node


@pytest.fixture
def temp_graph():
    """Create a temporary graph for testing."""
    tmpdir = tempfile.mkdtemp()
    graph = HtmlGraph(tmpdir, auto_load=False)
    yield graph
    import shutil

    shutil.rmtree(tmpdir)


class TestQueryCacheBasic:
    """Test basic caching functionality."""

    def test_cache_initialized(self, temp_graph):
        """Cache should be initialized on graph creation."""
        assert hasattr(temp_graph, "_query_cache")
        assert isinstance(temp_graph._query_cache, dict)
        assert temp_graph._cache_enabled is True

    def test_cache_stats_initial(self, temp_graph):
        """Cache stats should report zero cached queries initially."""
        stats = temp_graph.cache_stats
        assert stats["cached_queries"] == 0
        assert stats["cache_enabled"] is True

    def test_query_caches_result(self, temp_graph):
        """First query should cache the result."""
        node = Node(id="test-001", title="Test", type="feature", status="todo")
        temp_graph.add(node)

        # First query
        result1 = temp_graph.query('[data-status="todo"]')
        assert len(result1) == 1

        # Check cache
        stats = temp_graph.cache_stats
        assert stats["cached_queries"] == 1
        assert '[data-status="todo"]' in temp_graph._query_cache

    def test_second_query_uses_cache(self, temp_graph):
        """Second identical query should use cached result."""
        node = Node(id="test-001", title="Test", type="feature", status="todo")
        temp_graph.add(node)

        # First query (caches)
        temp_graph.query('[data-status="todo"]')

        # Second query (should use cache)
        result2 = temp_graph.query('[data-status="todo"]')
        assert len(result2) == 1

        # Cache should still have 1 entry
        stats = temp_graph.cache_stats
        assert stats["cached_queries"] == 1

    def test_different_queries_cache_separately(self, temp_graph):
        """Different queries should be cached separately."""
        node1 = Node(id="test-001", title="Test 1", type="feature", status="todo")
        node2 = Node(id="test-002", title="Test 2", type="feature", status="done")
        temp_graph.add(node1)
        temp_graph.add(node2)

        # Two different queries
        temp_graph.query('[data-status="todo"]')
        temp_graph.query('[data-status="done"]')

        # Should have 2 cached queries
        stats = temp_graph.cache_stats
        assert stats["cached_queries"] == 2


class TestCacheInvalidation:
    """Test cache invalidation on mutations."""

    def test_add_invalidates_cache(self, temp_graph):
        """Adding a node should invalidate the cache."""
        node1 = Node(id="test-001", title="Test 1", type="feature", status="todo")
        temp_graph.add(node1)

        # Query and cache
        temp_graph.query('[data-status="todo"]')
        assert temp_graph.cache_stats["cached_queries"] == 1

        # Add another node
        node2 = Node(id="test-002", title="Test 2", type="feature", status="todo")
        temp_graph.add(node2)

        # Cache should be invalidated
        assert temp_graph.cache_stats["cached_queries"] == 0

    def test_update_invalidates_cache(self, temp_graph):
        """Updating a node should invalidate the cache."""
        node = Node(id="test-001", title="Test", type="feature", status="todo")
        temp_graph.add(node)

        # Query and cache
        temp_graph.query('[data-status="todo"]')
        assert temp_graph.cache_stats["cached_queries"] == 1

        # Update node
        node.status = "in-progress"
        temp_graph.update(node)

        # Cache should be invalidated
        assert temp_graph.cache_stats["cached_queries"] == 0

    def test_delete_invalidates_cache(self, temp_graph):
        """Deleting a node should invalidate the cache."""
        node = Node(id="test-001", title="Test", type="feature", status="todo")
        temp_graph.add(node)

        # Query and cache
        temp_graph.query('[data-status="todo"]')
        assert temp_graph.cache_stats["cached_queries"] == 1

        # Delete node
        temp_graph.delete("test-001")

        # Cache should be invalidated
        assert temp_graph.cache_stats["cached_queries"] == 0

    def test_remove_invalidates_cache(self, temp_graph):
        """Removing a node should invalidate the cache."""
        node = Node(id="test-001", title="Test", type="feature", status="todo")
        temp_graph.add(node)

        # Query and cache
        temp_graph.query('[data-status="todo"]')
        assert temp_graph.cache_stats["cached_queries"] == 1

        # Remove node
        temp_graph.remove("test-001")

        # Cache should be invalidated
        assert temp_graph.cache_stats["cached_queries"] == 0

    def test_reload_invalidates_cache(self, temp_graph):
        """Reloading the graph should invalidate the cache."""
        node = Node(id="test-001", title="Test", type="feature", status="todo")
        temp_graph.add(node)

        # Query and cache
        temp_graph.query('[data-status="todo"]')
        assert temp_graph.cache_stats["cached_queries"] == 1

        # Reload
        temp_graph.reload()

        # Cache should be invalidated
        assert temp_graph.cache_stats["cached_queries"] == 0


class TestCacheCopyBehavior:
    """Test that cache returns copies to prevent mutation."""

    def test_cache_returns_copy(self, temp_graph):
        """Cache should return a copy of the cached result."""
        node = Node(id="test-001", title="Test", type="feature", status="todo")
        temp_graph.add(node)

        # First query
        result1 = temp_graph.query('[data-status="todo"]')

        # Second query (from cache)
        result2 = temp_graph.query('[data-status="todo"]')

        # Results should have same content but be different objects
        assert result1 == result2
        assert result1 is not result2

    def test_modifying_result_does_not_affect_cache(self, temp_graph):
        """Modifying a query result should not affect the cached version."""
        node = Node(id="test-001", title="Test", type="feature", status="todo")
        temp_graph.add(node)

        # First query
        result1 = temp_graph.query('[data-status="todo"]')
        original_len = len(result1)

        # Modify result
        result1.clear()

        # Second query should return original cached result
        result2 = temp_graph.query('[data-status="todo"]')
        assert len(result2) == original_len


class TestCacheAfterInvalidation:
    """Test that cache works correctly after being invalidated."""

    def test_cache_rebuilds_after_add(self, temp_graph):
        """Cache should rebuild after being invalidated by add."""
        node1 = Node(id="test-001", title="Test 1", type="feature", status="todo")
        temp_graph.add(node1)

        # Initial query
        result1 = temp_graph.query('[data-status="todo"]')
        assert len(result1) == 1

        # Add node (invalidates cache)
        node2 = Node(id="test-002", title="Test 2", type="feature", status="todo")
        temp_graph.add(node2)

        # Query again (should re-cache with new result)
        result2 = temp_graph.query('[data-status="todo"]')
        assert len(result2) == 2
        assert temp_graph.cache_stats["cached_queries"] == 1

    def test_cache_rebuilds_after_update(self, temp_graph):
        """Cache should rebuild after being invalidated by update."""
        node = Node(id="test-001", title="Test", type="feature", status="todo")
        temp_graph.add(node)

        # Initial query for todo
        result1 = temp_graph.query('[data-status="todo"]')
        assert len(result1) == 1

        # Update node (invalidates cache)
        node.status = "in-progress"
        temp_graph.update(node)

        # Query for in-progress (should cache new result)
        result2 = temp_graph.query('[data-status="in-progress"]')
        assert len(result2) == 1
        assert temp_graph.cache_stats["cached_queries"] == 1

    def test_cache_rebuilds_after_delete(self, temp_graph):
        """Cache should rebuild after being invalidated by delete."""
        node1 = Node(id="test-001", title="Test 1", type="feature", status="todo")
        node2 = Node(id="test-002", title="Test 2", type="feature", status="todo")
        temp_graph.add(node1)
        temp_graph.add(node2)

        # Initial query
        result1 = temp_graph.query('[data-status="todo"]')
        assert len(result1) == 2

        # Delete node (invalidates cache)
        temp_graph.delete("test-001")

        # Query again (should re-cache with new result)
        result2 = temp_graph.query('[data-status="todo"]')
        assert len(result2) == 1
        assert temp_graph.cache_stats["cached_queries"] == 1


class TestCacheDisableDuringReload:
    """Test that cache is disabled during reload."""

    def test_cache_disabled_during_reload(self, temp_graph):
        """Cache should be disabled during reload operation."""
        node = Node(id="test-001", title="Test", type="feature", status="todo")
        temp_graph.add(node)

        # Verify cache is enabled before reload
        assert temp_graph._cache_enabled is True

        # Reload (cache should be disabled during, enabled after)
        temp_graph.reload()

        # Cache should be enabled again after reload
        assert temp_graph._cache_enabled is True

        # Query should work and cache
        result = temp_graph.query('[data-status="todo"]')
        assert len(result) == 1
        assert temp_graph.cache_stats["cached_queries"] == 1


class TestCacheWithComplexQueries:
    """Test caching with complex queries."""

    def test_cache_complex_selector(self, temp_graph):
        """Complex selectors should be cached correctly."""
        node1 = Node(
            id="test-001", title="Test 1", type="feature", status="todo", priority="high"
        )
        node2 = Node(
            id="test-002",
            title="Test 2",
            type="feature",
            status="todo",
            priority="low",
        )
        temp_graph.add(node1)
        temp_graph.add(node2)

        # Complex query
        selector = '[data-status="todo"][data-priority="high"]'
        result1 = temp_graph.query(selector)
        assert len(result1) == 1

        # Should be cached
        assert temp_graph.cache_stats["cached_queries"] == 1
        assert selector in temp_graph._query_cache

        # Second query should use cache
        result2 = temp_graph.query(selector)
        assert result1 == result2

    def test_multiple_complex_queries_cached(self, temp_graph):
        """Multiple different complex queries should each be cached."""
        node1 = Node(
            id="test-001", title="Test 1", type="feature", status="todo", priority="high"
        )
        node2 = Node(
            id="test-002",
            title="Test 2",
            type="feature",
            status="done",
            priority="low",
        )
        temp_graph.add(node1)
        temp_graph.add(node2)

        # Multiple queries
        temp_graph.query('[data-status="todo"][data-priority="high"]')
        temp_graph.query('[data-status="done"]')
        temp_graph.query('[data-priority="low"]')

        # Should have 3 cached queries
        assert temp_graph.cache_stats["cached_queries"] == 3
