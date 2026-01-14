"""
Analytics Registry Mixin for SDK.

Provides property-based access to analytics interfaces via composition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.analytics import (
        Analytics,
        CrossSessionAnalytics,
        DependencyAnalytics,
    )
    from htmlgraph.context_analytics import ContextAnalytics
    from htmlgraph.sdk.analytics.engine import AnalyticsEngine


class AnalyticsRegistry:
    """
    Mixin that provides property-based access to analytics.

    Delegates to AnalyticsEngine for lazy loading while maintaining
    backward-compatible property API.

    Properties:
        analytics: Work type analytics
        dep_analytics: Dependency analytics
        cross_session_analytics: Cross-session analytics
        context: Context analytics
        pattern_learning: Pattern learning

    Example:
        >>> class SDK(AnalyticsRegistry):
        ...     def __init__(self):
        ...         self._analytics_engine = AnalyticsEngine(...)
        ...
        >>> sdk = SDK()
        >>> sdk.analytics.work_type_distribution()
        >>> sdk.dep_analytics.find_bottlenecks()
    """

    _analytics_engine: AnalyticsEngine

    @property
    def analytics(self) -> Analytics:
        """
        Work type analytics interface (lazy-loaded).

        Provides session-level work type analysis, distribution metrics,
        and work type filtering.

        Returns:
            Analytics instance
        """
        return self._analytics_engine.analytics

    @property
    def dep_analytics(self) -> DependencyAnalytics:
        """
        Dependency analytics interface (lazy-loaded).

        Provides graph-based dependency analysis including bottleneck
        detection, critical path analysis, and parallelization recommendations.

        Returns:
            DependencyAnalytics instance
        """
        return self._analytics_engine.dep_analytics

    @property
    def cross_session_analytics(self) -> CrossSessionAnalytics:
        """
        Cross-session analytics interface (lazy-loaded).

        Provides Git commit-based analytics spanning multiple sessions
        and tracking work across the project history.

        Returns:
            CrossSessionAnalytics instance
        """
        return self._analytics_engine.cross_session_analytics

    @property
    def context(self) -> ContextAnalytics:
        """
        Context analytics interface (lazy-loaded).

        Provides hierarchical context usage tracking and analytics
        from Activity → Session → Feature → Track.

        Returns:
            ContextAnalytics instance
        """
        return self._analytics_engine.context

    @property
    def pattern_learning(self) -> Any:
        """
        Pattern learning interface (lazy-loaded).

        Provides behavior pattern learning and analysis capabilities.

        Returns:
            PatternLearner instance
        """
        return self._analytics_engine.pattern_learning
