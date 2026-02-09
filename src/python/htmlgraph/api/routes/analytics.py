"""
Analytics routes for HtmlGraph API.

Handles:
- Cost summary and token aggregation
- Performance metrics (execution time, success rates)
- Query performance metrics and cache statistics
"""

import logging
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter
from fastapi_cache.decorator import cache

from htmlgraph.api.cache import CACHE_TTL
from htmlgraph.api.dependencies import Dependencies

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependencies will be set by main.py
_deps: Dependencies | None = None


def init_analytics_routes(deps: Dependencies) -> None:
    """Initialize analytics routes with dependencies."""
    global _deps
    _deps = deps


def get_deps() -> Dependencies:
    """Get dependencies instance, raising error if not initialized."""
    if _deps is None:
        raise RuntimeError("Analytics routes not initialized.")
    return _deps


@router.get("/api/analytics/cost-summary")
@cache(expire=CACHE_TTL.get("analytics", 60))
async def get_cost_summary_endpoint(
    session_id: str | None = None,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """
    Get cost summary with token aggregation and breakdown.

    Returns:
    - Total tokens and event count
    - Cost breakdown by tool, model, and agent
    - Average cost per event
    """
    deps = get_deps()
    db = await deps.get_db()

    try:
        _, _, analytics_service = deps.create_services(db)
        return cast(
            dict[str, Any],
            await analytics_service.get_cost_summary(
                session_id=session_id, agent_id=agent_id
            ),
        )
    finally:
        await db.close()


@router.get("/api/analytics/performance-metrics")
@cache(expire=CACHE_TTL.get("analytics", 60))
async def get_performance_metrics_endpoint(
    session_id: str | None = None,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """
    Get performance metrics (execution time, success rates).

    Returns:
    - Duration statistics (avg, min, max)
    - Success/error rates
    - Per-tool performance metrics
    """
    deps = get_deps()
    db = await deps.get_db()

    try:
        _, _, analytics_service = deps.create_services(db)
        return cast(
            dict[str, Any],
            await analytics_service.get_performance_metrics(
                session_id=session_id, agent_id=agent_id
            ),
        )
    finally:
        await db.close()


@router.get("/api/query-metrics")
async def get_query_metrics() -> dict[str, Any]:
    """Get query performance metrics and cache statistics."""
    deps = get_deps()
    cache = deps.query_cache
    metrics = cache.get_metrics()

    total_queries = sum(m.get("count", 0) for m in metrics.values())
    total_cache_hits = sum(m.get("hits", 0) for m in metrics.values())
    hit_rate = (total_cache_hits / total_queries * 100) if total_queries > 0 else 0

    return {
        "timestamp": datetime.now().isoformat(),
        "cache_status": {
            "ttl_seconds": cache.ttl_seconds,
            "cached_queries": len(cache.cache),
            "total_queries_tracked": total_queries,
            "cache_hits": total_cache_hits,
            "cache_hit_rate_percent": round(hit_rate, 2),
        },
        "query_metrics": metrics,
    }
