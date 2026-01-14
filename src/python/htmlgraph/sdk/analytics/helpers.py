"""
Helper functions for analytics initialization and management.

Provides utility functions for:
- Analytics engine initialization
- Lazy loading coordination
- Analytics lifecycle management
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.sdk.analytics.engine import AnalyticsEngine


def create_analytics_engine(
    sdk: Any,
    graph: HtmlGraph,
    directory: Path | str,
) -> AnalyticsEngine:
    """
    Create and initialize an analytics engine.

    Args:
        sdk: SDK instance (parent)
        graph: HtmlGraph instance
        directory: .htmlgraph directory path

    Returns:
        Initialized AnalyticsEngine instance

    Example:
        >>> from htmlgraph import SDK
        >>> from htmlgraph.sdk.analytics.helpers import create_analytics_engine
        >>>
        >>> sdk = SDK(agent="claude")
        >>> engine = create_analytics_engine(sdk, sdk._graph, sdk._directory)
        >>> dist = engine.analytics.work_type_distribution()
    """
    from htmlgraph.sdk.analytics.engine import AnalyticsEngine

    return AnalyticsEngine(sdk=sdk, graph=graph, directory=directory)


def validate_analytics_access(analytics_engine: AnalyticsEngine) -> dict[str, bool]:
    """
    Validate that all analytics interfaces are accessible.

    Tests lazy loading for all analytics properties without
    triggering expensive operations.

    Args:
        analytics_engine: AnalyticsEngine instance to validate

    Returns:
        Dict mapping analytics name to availability status

    Example:
        >>> from htmlgraph import SDK
        >>> from htmlgraph.sdk.analytics.helpers import validate_analytics_access
        >>>
        >>> sdk = SDK(agent="claude")
        >>> status = validate_analytics_access(sdk._analytics_engine)
        >>> assert all(status.values()), "All analytics should be accessible"
    """
    status = {}

    try:
        # Test Analytics interface
        _ = analytics_engine.analytics
        status["analytics"] = True
    except Exception:
        status["analytics"] = False

    try:
        # Test DependencyAnalytics interface
        _ = analytics_engine.dep_analytics
        status["dep_analytics"] = True
    except Exception:
        status["dep_analytics"] = False

    try:
        # Test CrossSessionAnalytics interface
        _ = analytics_engine.cross_session_analytics
        status["cross_session_analytics"] = True
    except Exception:
        status["cross_session_analytics"] = False

    try:
        # Test ContextAnalytics interface
        _ = analytics_engine.context
        status["context"] = True
    except Exception:
        status["context"] = False

    try:
        # Test PatternLearner interface
        _ = analytics_engine.pattern_learning
        status["pattern_learning"] = True
    except Exception:
        status["pattern_learning"] = False

    return status


def get_analytics_summary(analytics_engine: AnalyticsEngine) -> dict[str, Any]:
    """
    Get a summary of available analytics capabilities.

    Returns metadata about each analytics interface including
    availability and key methods.

    Args:
        analytics_engine: AnalyticsEngine instance

    Returns:
        Dict with analytics metadata

    Example:
        >>> from htmlgraph import SDK
        >>> from htmlgraph.sdk.analytics.helpers import get_analytics_summary
        >>>
        >>> sdk = SDK(agent="claude")
        >>> summary = get_analytics_summary(sdk._analytics_engine)
        >>> print(summary["analytics"]["methods"])
    """
    return {
        "analytics": {
            "available": analytics_engine._analytics is not None,
            "description": "Work type distribution and session analytics",
            "methods": [
                "work_type_distribution",
                "spike_to_feature_ratio",
                "maintenance_burden",
                "get_sessions_by_work_type",
            ],
        },
        "dep_analytics": {
            "available": analytics_engine._dep_analytics is not None,
            "description": "Dependency-aware graph analysis",
            "methods": [
                "find_bottlenecks",
                "find_critical_path",
                "find_parallelization_opportunities",
                "recommend_next_tasks",
                "assess_risk",
            ],
        },
        "cross_session_analytics": {
            "available": analytics_engine._cross_session_analytics is not None,
            "description": "Git commit-based cross-session tracking",
            "methods": [
                "work_in_commit_range",
                "sessions_for_feature",
                "work_by_author",
            ],
        },
        "context": {
            "available": analytics_engine._context_analytics is not None,
            "description": "Context usage tracking and analytics",
            "methods": [
                "get_session_usage",
                "get_feature_usage",
                "get_track_usage",
            ],
        },
        "pattern_learning": {
            "available": analytics_engine._pattern_learning is not None,
            "description": "Behavior pattern learning",
            "methods": [
                # Methods depend on PatternLearner implementation
            ],
        },
    }
