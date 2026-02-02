#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
HtmlGraph Hook Cache Module

Implements TTL-based caching for frequently accessed queries.
Provides decorator and class-based caching with automatic expiration.

Usage:
    # Decorator style
    @ttl_cache(ttl_seconds=300)
    def get_session_context(session_id):
        return expensive_query(session_id)

    # Class style
    cache = TTLCache(ttl_seconds=600)
    result = cache.get_or_compute("key", lambda: expensive_operation())
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")


class TTLCache:
    """Simple TTL-based cache with automatic expiration."""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize TTL cache.

        Args:
            ttl_seconds: Time to live for cache entries in seconds
        """
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[Any, float]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """
        Get value from cache if it exists and hasn't expired.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                self._hits += 1
                return value
            else:
                # Entry expired, remove it
                del self._cache[key]

        self._misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, time.time())

    def get_or_compute(self, key: str, compute_fn: Callable[[], T]) -> T:
        """
        Get value from cache or compute it.

        Args:
            key: Cache key
            compute_fn: Function to compute value if not in cache

        Returns:
            Cached or computed value
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        value = compute_fn()
        self.set(key, value)
        return value

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit/miss counts and rates
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate_percent": hit_rate,
            "entries": len(self._cache),
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._hits = 0
        self._misses = 0


def ttl_cache(ttl_seconds: int = 300):
    """
    Decorator for TTL-based caching of function results.

    Args:
        ttl_seconds: Time to live for cache entries in seconds

    Example:
        @ttl_cache(ttl_seconds=300)
        def get_feature_context(feature_id):
            return expensive_query(feature_id)
    """

    def decorator(func: Callable) -> Callable:
        cache = TTLCache(ttl_seconds=ttl_seconds)

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Create cache key from args and kwargs
            cache_key = f"{func.__name__}:{args}:{kwargs}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result

        # Attach cache object for stats/debugging
        wrapper.cache = cache  # type: ignore[attr-defined]
        wrapper.get_cache_stats = cache.stats  # type: ignore[attr-defined]
        wrapper.clear_cache = cache.clear  # type: ignore[attr-defined]

        return wrapper

    return decorator


# Global cache instances for shared use across hooks
SESSION_CONTEXT_CACHE = TTLCache(ttl_seconds=300)  # 5 minutes
FEATURE_METADATA_CACHE = TTLCache(ttl_seconds=600)  # 10 minutes
CLASSIFICATION_RULES_CACHE = TTLCache(ttl_seconds=3600)  # 1 hour
USER_PREFERENCES_CACHE = TTLCache(ttl_seconds=900)  # 15 minutes


def get_cache_stats() -> dict[str, dict[str, Any]]:
    """Get statistics from all global caches."""
    return {
        "session_context": SESSION_CONTEXT_CACHE.stats(),
        "feature_metadata": FEATURE_METADATA_CACHE.stats(),
        "classification_rules": CLASSIFICATION_RULES_CACHE.stats(),
        "user_preferences": USER_PREFERENCES_CACHE.stats(),
    }
