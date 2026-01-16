"""
SharedCache - Unified caching layer for all HtmlGraph operations.

Consolidates 16+ separate cache implementations.
Provides:
- Centralized cache with LRU eviction
- TTL-based expiration
- Pattern-based invalidation
- Thread-safe singleton access
- Metrics and observability

All implementations MUST pass SharedCacheComplianceTests.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass  # For forward references


class CacheInvalidationPattern(Enum):
    """Cache invalidation patterns."""

    SINGLE_KEY = "single"  # Invalidate one key
    PREFIX_PATTERN = "prefix"  # Invalidate keys matching prefix (e.g., "feature:*")
    RESOURCE_CHANGED = "resource"  # Invalidate all derived caches
    CLEAR_ALL = "all"  # Clear entire cache


def get_shared_cache() -> "SharedCache":
    """
    Get singleton instance of SharedCache.

    Ensures only one cache instance across application.

    Returns:
        SharedCache singleton

    Examples:
        >>> cache = get_shared_cache()
        >>> cache.set("mykey", value, ttl=3600)
        >>> value = cache.get("mykey")
    """
    if not hasattr(get_shared_cache, "_instance"):
        raise RuntimeError(
            "SharedCache not initialized. Call initialize_shared_cache() first."
        )
    instance: SharedCache = get_shared_cache._instance  # type: ignore[attr-defined]
    return instance


class SharedCacheError(Exception):
    """Base exception for cache operations."""

    pass


class CacheKeyError(SharedCacheError):
    """Raised when cache key is invalid."""

    pass


class CacheCapacityError(SharedCacheError):
    """Raised when cache reaches max capacity and can't evict."""

    pass


class SharedCache(ABC):
    """
    Unified caching layer for all HtmlGraph data access.

    Addresses cache fragmentation and invalidation gaps:
    - 16+ separate cache implementations → 1 unified cache
    - 4+ critical invalidation gaps → Centralized invalidation
    - No cache coherence → Pattern-based invalidation
    - No metrics → Built-in cache statistics

    CONTRACT:
    1. **Coherence**: Cache always consistent with storage
    2. **Atomicity**: get/set operations are atomic
    3. **Isolation**: Concurrent access safe
    4. **Efficiency**: O(1) get/set, O(1) delete with O(n) patterns
    5. **Observability**: Metrics tracked automatically

    INVALIDATION SIGNALS:
    When underlying data changes, cache must be invalidated:
    - Feature changed → invalidate "feature:*", "dependency:*", "analytics:*"
    - Track changed → invalidate "track:*", "feature:*"
    - Analytics invalidate → invalidate "dependency:*", "priority:*", "recommendation:*"

    CACHE KEYS (Convention):
    - "feature:{id}" - Individual feature
    - "feature:list:{filter}" - Feature list with filter
    - "track:{id}" - Individual track
    - "dependency:{id}" - Dependency analysis
    - "priority:{id}" - Priority score
    - "recommendation:*" - Recommendations

    PERFORMANCE:
    - get(key): O(1) average
    - set(key, value, ttl): O(1) average
    - delete(key): O(1) average
    - delete_pattern(pattern): O(n) where n = matching keys
    - clear(): O(n) where n = total keys
    - size(): O(1)

    MEMORY MANAGEMENT:
    - LRU (Least Recently Used) eviction when max_size exceeded
    - TTL-based automatic expiration
    - Configurable max cache size

    THREAD SAFETY:
    - Thread-safe for concurrent reads
    - Thread-safe for concurrent writes (serialized)
    - No deadlock risk
    - Atomic operations (no partial states visible)
    """

    # ===== GET OPERATIONS =====

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """
        Retrieve cached value by key.

        Returns None if key not found or expired.
        Updates LRU tracking (moves item to "most recently used").

        Args:
            key: Cache key (e.g., "feature:feat-001")

        Returns:
            Cached value if found and not expired, None otherwise

        Raises:
            CacheKeyError: If key format is invalid

        Performance: O(1) average case

        Examples:
            >>> cache = get_shared_cache()
            >>> value = cache.get("feature:feat-001")
            >>> if value is None:
            ...     # Recompute and cache
            ...     value = load_feature("feat-001")
            ...     cache.set("feature:feat-001", value)
        """
        ...

    @abstractmethod
    def get_or_compute(
        self, key: str, compute_fn: Callable[[], Any], ttl: int | None = None
    ) -> Any:
        """
        Get cached value or compute and cache if missing.

        Avoids cache-miss pattern boilerplate:
            cache.get() → check None → compute → cache.set()

        Args:
            key: Cache key
            compute_fn: Function taking no args, returns value to cache
            ttl: Time-to-live in seconds (None = use default)

        Returns:
            Cached or newly computed value

        Performance: O(1) if cached, O(?) if computed

        Examples:
            >>> def load_deps():
            ...     return analyze_dependencies("feat-001")
            >>> deps = cache.get_or_compute("dependency:feat-001", load_deps)
        """
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Does NOT count as access for LRU purposes.

        Args:
            key: Cache key to check

        Returns:
            True if key exists and not expired, False otherwise

        Performance: O(1)

        Examples:
            >>> if cache.exists("feature:feat-001"):
            ...     print("Already cached")
        """
        ...

    # ===== SET OPERATIONS =====

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Cache a value with optional time-to-live.

        If key exists, updates value and TTL.
        If cache at max capacity, evicts LRU item.

        Args:
            key: Cache key (e.g., "feature:feat-001")
            value: Value to cache (must be serializable)
            ttl: Time-to-live in seconds (None = default)

        Raises:
            CacheKeyError: If key format invalid
            CacheCapacityError: If can't make space

        Performance: O(1) average case

        Examples:
            >>> feature = load_feature("feat-001")
            >>> cache.set("feature:feat-001", feature, ttl=3600)  # 1 hour
            >>> cache.set("priority:feat-001", 0.95)  # Use default TTL
        """
        ...

    @abstractmethod
    def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """
        Cache multiple key-value pairs at once.

        More efficient than multiple set() calls.

        Args:
            items: Dict of key -> value to cache
            ttl: TTL for all items (None = default)

        Performance: O(k) where k = items count

        Examples:
            >>> cache.set_many({
            ...     "feature:feat-001": feature1,
            ...     "feature:feat-002": feature2,
            ...     "feature:feat-003": feature3,
            ... }, ttl=3600)
        """
        ...

    # ===== DELETE OPERATIONS =====

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete single cached value.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False if not found

        Performance: O(1)

        Examples:
            >>> cache.delete("feature:feat-001")
        """
        ...

    @abstractmethod
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all cached values matching pattern.

        Patterns use prefix matching:
        - "feature:*" → deletes all keys starting with "feature:"
        - "dependency:feat-*" → deletes "dependency:feat-001", etc.

        Args:
            pattern: Prefix pattern to match (e.g., "feature:*")

        Returns:
            Number of keys deleted

        Performance: O(n) where n = matching keys

        Examples:
            >>> # Invalidate all feature cache when features change
            >>> count = cache.delete_pattern("feature:*")
            >>> print(f"Invalidated {count} cached features")

            >>> # Invalidate all analytics when dependencies change
            >>> cache.delete_pattern("dependency:*")
            >>> cache.delete_pattern("priority:*")
            >>> cache.delete_pattern("recommendation:*")
        """
        ...

    @abstractmethod
    def clear(self) -> int:
        """
        Clear all cached values.

        Args: None

        Returns:
            Number of items cleared

        Examples:
            >>> cache.clear()
        """
        ...

    # ===== BATCH OPERATIONS =====

    @abstractmethod
    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """
        Retrieve multiple cached values at once.

        Returns only found keys (missing keys skipped).

        Args:
            keys: List of cache keys

        Returns:
            Dict of key -> value for found items

        Performance: O(k) where k = keys count

        Examples:
            >>> values = cache.get_many([
            ...     "feature:feat-001",
            ...     "feature:feat-002",
            ...     "feature:feat-003",
            ... ])
            >>> for key, value in values.items():
            ...     print(f"{key}: {value}")
        """
        ...

    @abstractmethod
    def delete_many(self, keys: list[str]) -> int:
        """
        Delete multiple cached values at once.

        Args:
            keys: List of cache keys to delete

        Returns:
            Number of keys successfully deleted

        Performance: O(k) where k = keys count

        Examples:
            >>> count = cache.delete_many([
            ...     "feature:feat-001",
            ...     "feature:feat-002",
            ... ])
        """
        ...

    # ===== INVALIDATION HELPERS =====

    @abstractmethod
    def invalidate_feature(self, feature_id: str) -> None:
        """
        Invalidate all caches related to a feature.

        Convenience method that invalidates:
        - Feature data: "feature:{id}"
        - Feature lists: "feature:list:*"
        - Dependencies: "dependency:{id}" + "dependency:*:blocking_for_{id}"
        - Analytics: "priority:{id}", "recommendation:*"

        Args:
            feature_id: Feature ID to invalidate

        Examples:
            >>> # When feature changes
            >>> cache.invalidate_feature("feat-001")
        """
        ...

    @abstractmethod
    def invalidate_track(self, track_id: str) -> None:
        """
        Invalidate all caches related to a track.

        Invalidates:
        - Track data: "track:{id}"
        - Track features: "track:{id}:features"
        - Analytics: cascades to feature invalidation

        Args:
            track_id: Track ID to invalidate

        Examples:
            >>> cache.invalidate_track("track-planning")
        """
        ...

    @abstractmethod
    def invalidate_analytics(self) -> None:
        """
        Invalidate all analytics caches.

        Used when dependencies change or major data update occurs.

        Invalidates:
        - "dependency:*"
        - "priority:*"
        - "recommendation:*"
        - "critical_path:*"
        - "blocking:*"

        Examples:
            >>> # When dependencies added/removed
            >>> cache.invalidate_analytics()
        """
        ...

    # ===== OBSERVABILITY =====

    @abstractmethod
    def size(self) -> int:
        """
        Get current number of cached items.

        Returns:
            Count of items in cache

        Performance: O(1)

        Examples:
            >>> print(f"Cache has {cache.size()} items")
        """
        ...

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """
        Get detailed cache statistics.

        Returns dict with:
        - hits: Total cache hits
        - misses: Total cache misses
        - hit_rate: Hit rate (0-1)
        - evictions: Number of items evicted
        - size: Current item count
        - capacity: Max item count
        - memory_bytes: Approximate memory usage
        - avg_load_ms: Average load time for computed values

        Returns:
            Dict with cache metrics

        Performance: O(1)

        Examples:
            >>> metrics = cache.stats()
            >>> print(f"Hit rate: {metrics['hit_rate']:.1%}")
            >>> print(f"Evictions: {metrics['evictions']}")
            >>> print(f"Memory: {metrics['memory_bytes'] / 1024:.1f} KB")
        """
        ...

    @abstractmethod
    def reset_stats(self) -> None:
        """
        Reset cache statistics to zero.

        Clears hit/miss counters but keeps cached data.

        Examples:
            >>> cache.reset_stats()
        """
        ...

    # ===== CONFIGURATION =====

    @abstractmethod
    def configure(
        self,
        max_size: int | None = None,
        default_ttl: int | None = None,
        metrics_enabled: bool | None = None,
    ) -> None:
        """
        Configure cache behavior.

        Args:
            max_size: Max cached items (default: 1000)
            default_ttl: Default time-to-live in seconds (default: 3600)
            metrics_enabled: Track stats automatically (default: True)

        Examples:
            >>> cache.configure(max_size=5000, default_ttl=7200)
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if cache is properly configured.

        Returns:
            True if cache is ready to use

        Examples:
            >>> if not cache.is_configured():
            ...     cache.configure(max_size=1000)
        """
        ...

    # ===== DEBUG / UTILITY =====

    @abstractmethod
    def debug_info(self) -> dict[str, Any]:
        """
        Get detailed debug information.

        Includes:
        - All cached keys
        - TTL for each key
        - Access count for each key
        - LRU order
        - Memory per item

        Returns:
            Dict with detailed cache state

        Examples:
            >>> info = cache.debug_info()
            >>> for key in info['keys']:
            ...     print(f"{key}: {info['memory'][key]} bytes")
        """
        ...

    @abstractmethod
    def validate_integrity(self) -> bool:
        """
        Validate cache internal consistency.

        Checks:
        - No expired items accessible
        - LRU order correct
        - Size tracking accurate
        - All items parseable

        Returns:
            True if cache valid, False if corrupted

        Examples:
            >>> if not cache.validate_integrity():
            ...     cache.clear()  # Rebuild
            ...     cache.reload()
        """
        ...

    # ===== SINGLETON MANAGEMENT =====

    @classmethod
    @abstractmethod
    def initialize(
        cls, max_size: int = 1000, default_ttl: int = 3600, metrics_enabled: bool = True
    ) -> "SharedCache":
        """
        Initialize singleton cache instance.

        Must be called once at application startup.

        Args:
            max_size: Max cached items
            default_ttl: Default time-to-live
            metrics_enabled: Enable statistics tracking

        Returns:
            Initialized SharedCache singleton

        Examples:
            >>> cache = SharedCache.initialize(max_size=5000)
            >>> # Later, get singleton:
            >>> cache = get_shared_cache()
        """
        ...

    @classmethod
    @abstractmethod
    def get_instance(cls) -> "SharedCache":
        """
        Get singleton instance.

        Must call initialize() once before calling this.

        Returns:
            SharedCache singleton

        Raises:
            RuntimeError: If not initialized

        Examples:
            >>> cache = SharedCache.get_instance()
        """
        ...

    @classmethod
    @abstractmethod
    def reset_instance(cls) -> None:
        """
        Reset singleton (for testing only).

        Clears instance and forces re-initialization next time.

        Examples:
            >>> SharedCache.reset_instance()  # Testing only
        """
        ...
