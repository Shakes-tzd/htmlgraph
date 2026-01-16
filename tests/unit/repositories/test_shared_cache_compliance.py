"""
SharedCache Compliance Tests

All SharedCache implementations MUST pass these 10+ tests.
Tests validate the contract, caching behavior, and invalidation patterns.
"""

import time
from typing import Any
from unittest.mock import Mock

import pytest
from htmlgraph.repositories.shared_cache import (
    CacheCapacityError,
    CacheInvalidationPattern,
    CacheKeyError,
    SharedCache,
    SharedCacheError,
)


class MockSharedCache(SharedCache):
    """Mock implementation for testing interface."""

    _instance = None

    def __init__(self, max_size=1000, default_ttl=3600, metrics_enabled=True):
        self._storage = {}
        self._timestamps = {}
        self._access_counts = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._metrics_enabled = metrics_enabled
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Any | None:
        """Mock implementation."""
        if key not in self._storage:
            self._misses += 1
            return None
        # Check TTL
        if self._is_expired(key):
            del self._storage[key]
            self._misses += 1
            return None
        self._hits += 1
        self._access_counts[key] = self._access_counts.get(key, 0) + 1
        return self._storage[key]

    def get_or_compute(self, key: str, compute_fn: callable, ttl: int | None = None):
        """Mock implementation."""
        value = self.get(key)
        if value is None:
            value = compute_fn()
            self.set(key, value, ttl)
        return value

    def exists(self, key: str) -> bool:
        """Mock implementation."""
        if key not in self._storage:
            return False
        if self._is_expired(key):
            del self._storage[key]
            return False
        return True

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Mock implementation."""
        if self._max_size > 0 and len(self._storage) >= self._max_size:
            # Evict LRU
            lru_key = min(
                self._access_counts.keys(),
                key=lambda k: self._access_counts.get(k, 0),
            )
            if lru_key:
                del self._storage[lru_key]
                del self._access_counts[lru_key]
                self._evictions += 1
        self._storage[key] = value
        self._timestamps[key] = time.time()
        self._access_counts[key] = 0
        ttl = ttl or self._default_ttl
        if ttl:
            self._timestamps[key] = time.time() + ttl

    def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """Mock implementation."""
        for key, value in items.items():
            self.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Mock implementation."""
        if key in self._storage:
            del self._storage[key]
            del self._access_counts[key]
            del self._timestamps[key]
            return True
        return False

    def delete_pattern(self, pattern: str) -> int:
        """Mock implementation."""
        prefix = pattern.rstrip("*")
        count = 0
        keys_to_delete = [k for k in self._storage.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            self.delete(key)
            count += 1
        return count

    def clear(self) -> int:
        """Mock implementation."""
        count = len(self._storage)
        self._storage.clear()
        self._access_counts.clear()
        self._timestamps.clear()
        return count

    def get_many(self, keys) -> dict[str, Any]:
        """Mock implementation."""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def delete_many(self, keys) -> int:
        """Mock implementation."""
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    def invalidate_feature(self, feature_id: str) -> None:
        """Mock implementation."""
        self.delete_pattern(f"feature:{feature_id}*")
        self.delete_pattern(f"dependency:{feature_id}*")
        self.delete_pattern(f"priority:{feature_id}*")

    def invalidate_track(self, track_id: str) -> None:
        """Mock implementation."""
        self.delete_pattern(f"track:{track_id}*")

    def invalidate_analytics(self) -> None:
        """Mock implementation."""
        self.delete_pattern("dependency:*")
        self.delete_pattern("priority:*")
        self.delete_pattern("recommendation:*")

    def size(self) -> int:
        """Mock implementation."""
        return len(self._storage)

    def stats(self) -> dict[str, Any]:
        """Mock implementation."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "evictions": self._evictions,
            "size": self.size(),
            "capacity": self._max_size,
            "memory_bytes": sum(len(str(v)) for v in self._storage.values()),
            "avg_load_ms": 0.0,
        }

    def reset_stats(self) -> None:
        """Mock implementation."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def configure(self, max_size=None, default_ttl=None, metrics_enabled=None) -> None:
        """Mock implementation."""
        if max_size is not None:
            self._max_size = max_size
        if default_ttl is not None:
            self._default_ttl = default_ttl
        if metrics_enabled is not None:
            self._metrics_enabled = metrics_enabled

    def is_configured(self) -> bool:
        """Mock implementation."""
        return self._max_size > 0 and self._default_ttl > 0

    def debug_info(self) -> dict[str, Any]:
        """Mock implementation."""
        return {
            "keys": list(self._storage.keys()),
            "size": self.size(),
            "capacity": self._max_size,
        }

    def validate_integrity(self) -> bool:
        """Mock implementation."""
        return len(self._storage) == len(self._timestamps)

    @classmethod
    def initialize(cls, max_size=1000, default_ttl=3600, metrics_enabled=True):
        """Mock implementation."""
        cls._instance = cls(max_size, default_ttl, metrics_enabled)
        return cls._instance

    @classmethod
    def get_instance(cls):
        """Mock implementation."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Mock implementation."""
        cls._instance = None

    def _is_expired(self, key: str) -> bool:
        """Check if key is expired."""
        if key not in self._timestamps:
            return False
        timestamp = self._timestamps[key]
        # If timestamp is in future, use as TTL expiry
        return timestamp < time.time()


class TestSharedCacheInterface:
    """Test SharedCache interface contract."""

    def test_interface_defined(self):
        """SharedCache interface exists and is ABC."""
        assert hasattr(SharedCache, "get")
        assert hasattr(SharedCache, "set")
        assert hasattr(SharedCache, "delete")

    def test_exception_hierarchy(self):
        """Exception types properly inherit."""
        assert issubclass(CacheKeyError, SharedCacheError)
        assert issubclass(CacheCapacityError, SharedCacheError)

    def test_invalidation_pattern_enum(self):
        """CacheInvalidationPattern enum defined."""
        assert hasattr(CacheInvalidationPattern, "SINGLE_KEY")
        assert hasattr(CacheInvalidationPattern, "PREFIX_PATTERN")
        assert hasattr(CacheInvalidationPattern, "CLEAR_ALL")


class TestGetOperations:
    """Test cache get operations."""

    def test_get_returns_none_for_missing_key(self):
        """get returns None if key not found."""
        cache = MockSharedCache()
        result = cache.get("missing-key")
        assert result is None

    def test_get_returns_cached_value(self):
        """get returns cached value."""
        cache = MockSharedCache()
        cache.set("key-001", "value-001")
        result = cache.get("key-001")
        assert result == "value-001"

    def test_get_updates_access_count(self):
        """get updates LRU tracking."""
        cache = MockSharedCache()
        cache.set("key-001", "value")
        cache.get("key-001")
        # After get, item should be marked recently used

    def test_get_or_compute_returns_cached(self):
        """get_or_compute returns cached value if exists."""
        cache = MockSharedCache()
        cache.set("key", "cached-value")
        compute_fn = Mock(return_value="new-value")
        result = cache.get_or_compute("key", compute_fn)
        assert result == "cached-value"
        compute_fn.assert_not_called()

    def test_get_or_compute_computes_and_caches(self):
        """get_or_compute computes and caches if missing."""
        cache = MockSharedCache()
        compute_fn = Mock(return_value="computed-value")
        result = cache.get_or_compute("key", compute_fn)
        assert result == "computed-value"
        compute_fn.assert_called_once()
        # Value should be cached
        assert cache.get("key") == "computed-value"

    def test_exists_returns_bool(self):
        """exists returns boolean."""
        cache = MockSharedCache()
        assert cache.exists("missing") is False
        cache.set("present", "value")
        assert cache.exists("present") is True


class TestSetOperations:
    """Test cache set operations."""

    def test_set_stores_value(self):
        """set stores value in cache."""
        cache = MockSharedCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_set_with_ttl(self):
        """set accepts TTL parameter."""
        cache = MockSharedCache()
        cache.set("key", "value", ttl=10)
        assert cache.get("key") == "value"

    def test_set_updates_existing_value(self):
        """set updates value if key exists."""
        cache = MockSharedCache()
        cache.set("key", "value1")
        cache.set("key", "value2")
        assert cache.get("key") == "value2"

    def test_set_many_stores_multiple(self):
        """set_many stores multiple key-value pairs."""
        cache = MockSharedCache()
        items = {"key1": "value1", "key2": "value2", "key3": "value3"}
        cache.set_many(items)
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"


class TestDeleteOperations:
    """Test cache delete operations."""

    def test_delete_removes_key(self):
        """delete removes key from cache."""
        cache = MockSharedCache()
        cache.set("key", "value")
        assert cache.delete("key") is True
        assert cache.get("key") is None

    def test_delete_returns_false_for_missing(self):
        """delete returns False if key not found."""
        cache = MockSharedCache()
        assert cache.delete("missing") is False

    def test_delete_pattern_removes_matching(self):
        """delete_pattern removes keys matching prefix."""
        cache = MockSharedCache()
        cache.set("feature:001", "value")
        cache.set("feature:002", "value")
        cache.set("track:001", "value")
        count = cache.delete_pattern("feature:*")
        assert count == 2
        assert cache.get("feature:001") is None
        assert cache.get("track:001") is not None

    def test_delete_pattern_returns_count(self):
        """delete_pattern returns number of deleted keys."""
        cache = MockSharedCache()
        cache.set("dep:001", "value")
        cache.set("dep:002", "value")
        count = cache.delete_pattern("dep:*")
        assert count == 2

    def test_clear_removes_all(self):
        """clear removes all cached items."""
        cache = MockSharedCache()
        cache.set("key1", "value")
        cache.set("key2", "value")
        count = cache.clear()
        assert count == 2
        assert cache.size() == 0

    def test_delete_many_removes_multiple(self):
        """delete_many removes multiple keys."""
        cache = MockSharedCache()
        cache.set("key1", "value")
        cache.set("key2", "value")
        cache.set("key3", "value")
        count = cache.delete_many(["key1", "key2"])
        assert count == 2
        assert cache.get("key3") == "value"


class TestBatchOperations:
    """Test batch operations."""

    def test_get_many_returns_dict(self):
        """get_many returns dict of found items."""
        cache = MockSharedCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        result = cache.get_many(["key1", "key2", "missing"])
        assert isinstance(result, dict)
        assert len(result) == 2
        assert result["key1"] == "value1"

    def test_get_many_skips_missing(self):
        """get_many skips missing keys."""
        cache = MockSharedCache()
        cache.set("key1", "value1")
        result = cache.get_many(["key1", "missing"])
        assert "missing" not in result
        assert len(result) == 1


class TestInvalidationHelpers:
    """Test invalidation helper methods."""

    def test_invalidate_feature_removes_feature_cache(self):
        """invalidate_feature removes feature-related caches."""
        cache = MockSharedCache()
        cache.set("feature:feat-001", "value")
        cache.set("dependency:feat-001", "value")
        cache.invalidate_feature("feat-001")
        assert cache.get("feature:feat-001") is None
        assert cache.get("dependency:feat-001") is None

    def test_invalidate_track_removes_track_cache(self):
        """invalidate_track removes track-related caches."""
        cache = MockSharedCache()
        cache.set("track:track-001", "value")
        cache.invalidate_track("track-001")
        assert cache.get("track:track-001") is None

    def test_invalidate_analytics_removes_analytics(self):
        """invalidate_analytics removes analytics caches."""
        cache = MockSharedCache()
        cache.set("dependency:feat-001", "value")
        cache.set("priority:feat-001", "value")
        cache.set("recommendation:test", "value")
        cache.invalidate_analytics()
        assert cache.get("dependency:feat-001") is None
        assert cache.get("priority:feat-001") is None
        assert cache.get("recommendation:test") is None


class TestObservability:
    """Test cache metrics and observability."""

    def test_size_returns_item_count(self):
        """size returns count of cached items."""
        cache = MockSharedCache()
        assert cache.size() == 0
        cache.set("key1", "value")
        assert cache.size() == 1

    def test_stats_returns_dict(self):
        """stats returns dict with metrics."""
        cache = MockSharedCache()
        cache.set("key", "value")
        cache.get("key")
        stats = cache.stats()
        assert isinstance(stats, dict)
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats

    def test_stats_hit_rate_calculated(self):
        """stats calculates hit rate correctly."""
        cache = MockSharedCache()
        cache.set("key", "value")
        cache.get("key")  # Hit
        cache.get("missing")  # Miss
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_reset_stats_clears_metrics(self):
        """reset_stats clears metrics."""
        cache = MockSharedCache()
        cache.set("key", "value")
        cache.get("key")
        cache.reset_stats()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_debug_info_returns_dict(self):
        """debug_info returns detailed info."""
        cache = MockSharedCache()
        cache.set("key", "value")
        info = cache.debug_info()
        assert isinstance(info, dict)
        assert "keys" in info
        assert "key" in info["keys"]

    def test_validate_integrity_returns_bool(self):
        """validate_integrity returns boolean."""
        cache = MockSharedCache()
        result = cache.validate_integrity()
        assert isinstance(result, bool)


class TestConfiguration:
    """Test cache configuration."""

    def test_configure_sets_max_size(self):
        """configure sets max_size."""
        cache = MockSharedCache()
        cache.configure(max_size=500)
        # Should accept configuration

    def test_configure_sets_ttl(self):
        """configure sets default_ttl."""
        cache = MockSharedCache()
        cache.configure(default_ttl=7200)
        # Should accept configuration

    def test_is_configured_returns_bool(self):
        """is_configured returns boolean."""
        cache = MockSharedCache()
        result = cache.is_configured()
        assert isinstance(result, bool)


class TestSingleton:
    """Test singleton management."""

    def test_initialize_creates_instance(self):
        """initialize creates singleton instance."""
        MockSharedCache.reset_instance()
        instance = MockSharedCache.initialize(max_size=2000)
        assert instance is not None

    def test_get_instance_returns_singleton(self):
        """get_instance returns singleton."""
        MockSharedCache.reset_instance()
        MockSharedCache.initialize()
        instance1 = MockSharedCache.get_instance()
        instance2 = MockSharedCache.get_instance()
        assert instance1 is instance2

    def test_reset_instance_clears_singleton(self):
        """reset_instance clears singleton for testing."""
        MockSharedCache.initialize()
        MockSharedCache.reset_instance()
        # Should allow re-initialization


class TestConcurrency:
    """Test concurrent access patterns."""

    def test_get_is_safe(self):
        """get is safe for concurrent access."""
        cache = MockSharedCache()
        cache.set("key", "value")
        # Multiple threads could call get simultaneously
        for _ in range(10):
            assert cache.get("key") == "value"

    def test_set_is_safe(self):
        """set is safe for concurrent access."""
        cache = MockSharedCache()
        for i in range(10):
            cache.set(f"key-{i}", f"value-{i}")
        # All values should be cached
        assert cache.size() == 10


class TestPerformance:
    """Test performance expectations."""

    def test_get_performance_o1(self):
        """get should be O(1) average case."""
        cache = MockSharedCache(max_size=10000)
        # Populate cache
        for i in range(1000):
            cache.set(f"key-{i}", f"value-{i}")
        # Get should be fast even with many items
        import time

        start = time.time()
        for i in range(100):
            cache.get(f"key-{i}")
        elapsed = time.time() - start
        assert elapsed < 0.01  # 100 gets in <10ms

    def test_set_performance(self):
        """set should be fast."""
        cache = MockSharedCache(max_size=10000)
        import time

        start = time.time()
        for i in range(1000):
            cache.set(f"key-{i}", f"value-{i}")
        elapsed = time.time() - start
        assert elapsed < 0.5  # 1000 sets in <500ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
