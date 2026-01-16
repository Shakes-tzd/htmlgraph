"""
MemorySharedCache - In-memory singleton cache with LRU eviction and TTL.

Thread-safe implementation using RLock for concurrent access.
Provides O(1) operations for get/set/delete with pattern-based invalidation.
"""

import fnmatch
import threading
import time
from collections.abc import Callable
from typing import Any, Optional

from .shared_cache import (
    CacheCapacityError,
    CacheKeyError,
    SharedCache,
)


class MemorySharedCache(SharedCache):
    """
    In-memory cache with LRU eviction and TTL support.

    Features:
    - Thread-safe singleton pattern
    - O(1) get/set/delete operations
    - LRU eviction when max_size exceeded
    - TTL-based automatic expiration
    - Pattern-based invalidation (prefix matching)
    - Comprehensive statistics tracking

    Performance:
    - get(key): O(1) average
    - set(key, value, ttl): O(1) average
    - delete(key): O(1)
    - delete_pattern(pattern): O(n) where n = total keys
    - clear(): O(n)
    """

    _instance: Optional["MemorySharedCache"] = None
    _lock_class = threading.RLock()

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,
        metrics_enabled: bool = True,
    ):
        """Initialize cache with configuration."""
        self._cache: dict[str, tuple[Any, float | None]] = {}
        self._access_times: dict[str, float] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._metrics_enabled = metrics_enabled
        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_load_time_ms": 0.0,
            "load_count": 0,
        }

    # ===== SINGLETON MANAGEMENT =====

    @classmethod
    def initialize(
        cls, max_size: int = 1000, default_ttl: int = 3600, metrics_enabled: bool = True
    ) -> "MemorySharedCache":
        """Initialize singleton cache instance."""
        with cls._lock_class:
            if cls._instance is None:
                cls._instance = cls(max_size, default_ttl, metrics_enabled)
            return cls._instance

    @classmethod
    def get_instance(cls) -> "MemorySharedCache":
        """Get singleton instance."""
        with cls._lock_class:
            if cls._instance is None:
                raise RuntimeError("Cache not initialized. Call initialize() first.")
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing only)."""
        with cls._lock_class:
            cls._instance = None

    # ===== GET OPERATIONS =====

    def get(self, key: str) -> Any | None:
        """Retrieve cached value by key."""
        if not key:
            raise CacheKeyError("Cache key cannot be empty")

        with self._lock:
            if key not in self._cache:
                if self._metrics_enabled:
                    self._stats["misses"] += 1
                return None

            value, ttl_expiry = self._cache[key]

            # Check TTL expiration
            if ttl_expiry is not None and ttl_expiry < time.time():
                del self._cache[key]
                del self._access_times[key]
                if self._metrics_enabled:
                    self._stats["misses"] += 1
                return None

            # Update LRU tracking
            self._access_times[key] = time.time()

            if self._metrics_enabled:
                self._stats["hits"] += 1

            return value

    def get_or_compute(
        self, key: str, compute_fn: Callable[[], Any], ttl: int | None = None
    ) -> Any:
        """Get cached value or compute and cache if missing."""
        value = self.get(key)
        if value is not None:
            return value

        # Compute and cache
        start_time = time.time()
        value = compute_fn()
        elapsed_ms = (time.time() - start_time) * 1000

        if self._metrics_enabled:
            self._stats["total_load_time_ms"] += elapsed_ms
            self._stats["load_count"] += 1

        self.set(key, value, ttl)
        return value

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        with self._lock:
            if key not in self._cache:
                return False

            value, ttl_expiry = self._cache[key]

            # Check TTL expiration
            if ttl_expiry is not None and ttl_expiry < time.time():
                del self._cache[key]
                del self._access_times[key]
                return False

            return True

    # ===== SET OPERATIONS =====

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Cache a value with optional time-to-live."""
        if not key:
            raise CacheKeyError("Cache key cannot be empty")

        with self._lock:
            # Evict LRU if needed and key doesn't already exist
            if len(self._cache) >= self._max_size and key not in self._cache:
                if not self._access_times:
                    raise CacheCapacityError("Cache at capacity and can't evict")

                # Find and evict LRU item
                lru_key = min(self._access_times, key=lambda k: self._access_times[k])
                del self._cache[lru_key]
                del self._access_times[lru_key]

                if self._metrics_enabled:
                    self._stats["evictions"] += 1

            # Calculate TTL expiry
            ttl_seconds = ttl if ttl is not None else self._default_ttl
            ttl_expiry = time.time() + ttl_seconds if ttl_seconds else None

            # Store value and update access time
            self._cache[key] = (value, ttl_expiry)
            self._access_times[key] = time.time()

    def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """Cache multiple key-value pairs at once."""
        for key, value in items.items():
            self.set(key, value, ttl)

    # ===== DELETE OPERATIONS =====

    def delete(self, key: str) -> bool:
        """Delete single cached value."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._access_times[key]
                return True
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all cached values matching pattern."""
        with self._lock:
            # Convert pattern to prefix if using wildcard syntax
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                matching_keys = [k for k in self._cache if k.startswith(prefix)]
            else:
                matching_keys = [k for k in self._cache if fnmatch.fnmatch(k, pattern)]

            for key in matching_keys:
                del self._cache[key]
                del self._access_times[key]

            return len(matching_keys)

    def clear(self) -> int:
        """Clear all cached values."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._access_times.clear()
            return count

    # ===== BATCH OPERATIONS =====

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Retrieve multiple cached values at once."""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def delete_many(self, keys: list[str]) -> int:
        """Delete multiple cached values at once."""
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    # ===== INVALIDATION HELPERS =====

    def invalidate_feature(self, feature_id: str) -> None:
        """Invalidate all caches related to a feature."""
        with self._lock:
            self.delete(f"feature:{feature_id}")
            self.delete_pattern("feature:list:*")
            self.delete(f"dependency:{feature_id}")
            self.delete_pattern(f"dependency:*:blocking_for_{feature_id}")
            self.delete(f"priority:{feature_id}")
            self.delete_pattern("recommendation:*")

    def invalidate_track(self, track_id: str) -> None:
        """Invalidate all caches related to a track."""
        with self._lock:
            self.delete(f"track:{track_id}")
            self.delete(f"track:{track_id}:features")
            self.delete_pattern("track:list:*")
            # Tracks can affect features, so invalidate feature analytics
            self.delete_pattern("recommendation:*")

    def invalidate_analytics(self) -> None:
        """Invalidate all analytics caches."""
        with self._lock:
            self.delete_pattern("dependency:*")
            self.delete_pattern("priority:*")
            self.delete_pattern("recommendation:*")
            self.delete_pattern("critical_path:*")
            self.delete_pattern("blocking:*")

    # ===== OBSERVABILITY =====

    def size(self) -> int:
        """Get current number of cached items."""
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """Get detailed cache statistics."""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests if total_requests > 0 else 0.0
            )

            avg_load_ms = (
                self._stats["total_load_time_ms"] / self._stats["load_count"]
                if self._stats["load_count"] > 0
                else 0.0
            )

            # Estimate memory usage (rough approximation)
            # Assume average 1KB per cached item
            memory_bytes = len(self._cache) * 1024

            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": hit_rate,
                "evictions": self._stats["evictions"],
                "size": len(self._cache),
                "capacity": self._max_size,
                "memory_bytes": memory_bytes,
                "avg_load_ms": avg_load_ms,
            }

    def reset_stats(self) -> None:
        """Reset cache statistics to zero."""
        with self._lock:
            self._stats = {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "total_load_time_ms": 0.0,
                "load_count": 0,
            }

    # ===== CONFIGURATION =====

    def configure(
        self,
        max_size: int | None = None,
        default_ttl: int | None = None,
        metrics_enabled: bool | None = None,
    ) -> None:
        """Configure cache behavior."""
        with self._lock:
            if max_size is not None:
                self._max_size = max_size
            if default_ttl is not None:
                self._default_ttl = default_ttl
            if metrics_enabled is not None:
                self._metrics_enabled = metrics_enabled

    def is_configured(self) -> bool:
        """Check if cache is properly configured."""
        return self._max_size > 0 and self._default_ttl >= 0 and self._cache is not None

    # ===== DEBUG / UTILITY =====

    def debug_info(self) -> dict[str, Any]:
        """Get detailed debug information."""
        with self._lock:
            keys_info = {}
            for key in self._cache:
                value, ttl_expiry = self._cache[key]
                keys_info[key] = {
                    "ttl_remaining": (
                        ttl_expiry - time.time() if ttl_expiry is not None else None
                    ),
                    "access_time": self._access_times.get(key),
                }

            # Sort by LRU order (oldest first)
            lru_order = sorted(
                self._access_times.keys(), key=lambda k: self._access_times[k]
            )

            return {
                "keys": list(self._cache.keys()),
                "key_info": keys_info,
                "lru_order": lru_order,
                "size": len(self._cache),
                "capacity": self._max_size,
                "stats": self.stats(),
            }

    def validate_integrity(self) -> bool:
        """Validate cache internal consistency."""
        with self._lock:
            try:
                # Check no expired items
                current_time = time.time()
                for key, (value, ttl_expiry) in self._cache.items():
                    if ttl_expiry is not None and ttl_expiry < current_time:
                        return False  # Expired item found

                # Check all cache keys have access times
                if set(self._cache.keys()) != set(self._access_times.keys()):
                    return False

                # Check size tracking
                if len(self._cache) > self._max_size:
                    return False

                return True
            except Exception:
                return False
