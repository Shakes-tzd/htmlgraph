"""
Cache initialization and management for HtmlGraph API.

Supports both in-memory and Redis backends via fastapi-cache2.
Provides response-level caching with metrics tracking and invalidation hooks.
"""

import logging
import time
from typing import Any

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

# Redis imports are optional - only imported when redis_url is provided
try:
    from fastapi_cache.backends.redis import RedisBackend
    from redis import asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    RedisBackend = None  # type: ignore[misc, assignment]
    aioredis = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Cache TTL constants (in seconds) per endpoint type
CACHE_TTL = {
    "activity_feed": 60,  # 1 minute for live activity
    "events": 60,  # 1 minute for events
    "stats": 300,  # 5 minutes for statistics
    "sessions": 300,  # 5 minutes for sessions
    "orchestration": 120,  # 2 minutes for orchestration data
    "spawners": 300,  # 5 minutes for spawner data
    "metrics": 60,  # 1 minute for metrics (frequently changing)
    "default": 60,  # 1 minute default
}


class QueryCache:
    """Simple in-memory cache with TTL support for query results.

    This class wraps in-memory caching with metrics tracking.
    For HTTP response-level caching, use fastapi-cache2 decorators instead.
    """

    def __init__(self, ttl_seconds: float = 30.0):
        """Initialize query cache with TTL.

        Args:
            ttl_seconds: Time-to-live for cached entries in seconds.
        """
        self.cache: dict[str, tuple[Any, float]] = {}
        self.ttl_seconds = ttl_seconds
        self.metrics: dict[str, dict[str, float]] = {}

    def get(self, key: str) -> Any | None:
        """Get cached value if exists and not expired.

        Args:
            key: Cache key to retrieve.

        Returns:
            Cached value if found and not expired, None otherwise.
        """
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self.cache[key]
            return None

        return value

    def set(self, key: str, value: Any) -> None:
        """Store value with current timestamp.

        Args:
            key: Cache key to store under.
            value: Value to cache.
        """
        self.cache[key] = (value, time.time())

    def record_metric(self, key: str, query_time_ms: float, cache_hit: bool) -> None:
        """Record performance metrics for a query.

        Args:
            key: Query cache key.
            query_time_ms: Execution time in milliseconds.
            cache_hit: Whether this was a cache hit.
        """
        if key not in self.metrics:
            self.metrics[key] = {"count": 0, "total_ms": 0, "avg_ms": 0, "hits": 0}

        metrics = self.metrics[key]
        metrics["count"] += 1
        metrics["total_ms"] += query_time_ms
        metrics["avg_ms"] = metrics["total_ms"] / metrics["count"]
        if cache_hit:
            metrics["hits"] += 1

    def get_metrics(self) -> dict[str, dict[str, float]]:
        """Get all collected metrics.

        Returns:
            Dictionary of metrics indexed by cache key.
        """
        return self.metrics

    def invalidate(self, pattern: str = "") -> int:
        """Invalidate cache entries matching a pattern.

        Args:
            pattern: Pattern to match (empty string invalidates all).

        Returns:
            Number of entries invalidated.
        """
        if not pattern:
            # Clear all cache
            count = len(self.cache)
            self.cache.clear()
            return count

        # Invalidate matching entries
        keys_to_delete = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.cache[key]
        return len(keys_to_delete)


async def init_cache_backend(redis_url: str | None = None) -> None:
    """Initialize FastAPICache with appropriate backend.

    Args:
        redis_url: Redis URL for Redis backend. If None, uses in-memory backend.
    """
    if redis_url and REDIS_AVAILABLE:
        try:
            redis = aioredis.from_url(redis_url)  # type: ignore[union-attr]
            FastAPICache.init(RedisBackend(redis), prefix="htmlgraph")  # type: ignore[arg-type]
            logger.info(f"Initialized Redis cache backend: {redis_url}")
        except Exception as e:
            logger.warning(
                f"Failed to initialize Redis backend ({e}), falling back to in-memory"
            )
            FastAPICache.init(InMemoryBackend())
    elif redis_url and not REDIS_AVAILABLE:
        logger.warning(
            "Redis URL provided but redis package not installed, using in-memory backend"
        )
        FastAPICache.init(InMemoryBackend())
    else:
        FastAPICache.init(InMemoryBackend())
        logger.debug("Initialized in-memory cache backend")


def make_cache_key(
    prefix: str,
    *args: str | int,
) -> str:
    """Build a consistent cache key from prefix and arguments.

    Args:
        prefix: Key prefix (e.g., "activity_feed").
        *args: Additional key components.

    Returns:
        Cache key string.
    """
    parts = [prefix] + [str(arg) for arg in args]
    return ":".join(parts)


async def invalidate_response_cache(pattern: str = "") -> None:
    """Invalidate fastapi-cache2 response cache entries.

    This is a placeholder for manual invalidation.
    The fastapi-cache2 library handles automatic invalidation for GET requests.

    Args:
        pattern: Pattern to match in cache keys (for future filtering).
    """
    # Note: fastapi-cache2 doesn't provide a direct invalidation API
    # Invalidation typically happens at cache expiration (TTL) or
    # by clearing the backend storage
    logger.debug(f"Cache invalidation requested (pattern: {pattern or 'all'})")


def get_cache_ttl(endpoint_type: str) -> int:
    """Get TTL for specific endpoint type.

    Args:
        endpoint_type: Type of endpoint (activity_feed, events, stats, etc.).

    Returns:
        TTL in seconds.
    """
    return CACHE_TTL.get(endpoint_type, CACHE_TTL["default"])
