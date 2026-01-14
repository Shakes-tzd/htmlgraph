"""
Analytics Engine for SDK.

Centralized management of all analytics interfaces with lazy loading.
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
    from htmlgraph.graph import HtmlGraph


class AnalyticsEngine:
    """
    Centralized analytics engine with lazy loading.

    Manages all analytics interfaces:
    - analytics: Work type distribution and session analytics
    - dep_analytics: Dependency-aware graph analysis
    - cross_session_analytics: Git commit-based tracking
    - context: Context usage tracking
    - pattern_learning: Pattern learning (lazy-loaded)

    All analytics are lazy-loaded to improve SDK initialization performance.

    Example:
        >>> from htmlgraph import SDK
        >>> sdk = SDK(agent="claude")
        >>>
        >>> # Analytics are lazy-loaded on first access
        >>> dist = sdk.analytics.work_type_distribution()
        >>> bottlenecks = sdk.dep_analytics.find_bottlenecks()
        >>> usage = sdk.context.get_session_usage("session-123")
    """

    def __init__(self, sdk: Any, graph: HtmlGraph, directory: Any):
        """
        Initialize analytics engine.

        Args:
            sdk: SDK instance (parent)
            graph: HtmlGraph instance
            directory: .htmlgraph directory path
        """
        self._sdk = sdk
        self._graph = graph
        self._directory = directory

        # Lazy-loaded analytics instances
        self._analytics: Analytics | None = None
        self._dep_analytics: DependencyAnalytics | None = None
        self._cross_session_analytics: CrossSessionAnalytics | None = None
        self._context_analytics: ContextAnalytics | None = None
        self._pattern_learning: Any = None

    @property
    def analytics(self) -> Analytics:
        """
        Get work type analytics interface (lazy-loaded).

        Provides:
        - work_type_distribution(): Analyze work type distribution
        - spike_to_feature_ratio(): Calculate spike/feature ratio
        - maintenance_burden(): Calculate maintenance percentage
        - get_sessions_by_work_type(): Filter sessions by work type

        Returns:
            Analytics instance
        """
        if self._analytics is None:
            from htmlgraph.analytics import Analytics

            self._analytics = Analytics(self._sdk)
        return self._analytics

    @property
    def dep_analytics(self) -> DependencyAnalytics:
        """
        Get dependency analytics interface (lazy-loaded).

        Provides:
        - find_bottlenecks(): Identify blocking work
        - find_critical_path(): Find longest dependency chain
        - find_parallelization_opportunities(): Find parallel work
        - recommend_next_tasks(): Prioritize work
        - assess_risk(): Identify high-risk dependencies

        Returns:
            DependencyAnalytics instance
        """
        if self._dep_analytics is None:
            from htmlgraph.analytics import DependencyAnalytics

            self._dep_analytics = DependencyAnalytics(self._graph)
        return self._dep_analytics

    @property
    def cross_session_analytics(self) -> CrossSessionAnalytics:
        """
        Get cross-session analytics interface (lazy-loaded).

        Provides:
        - work_in_commit_range(): Get work between commits
        - sessions_for_feature(): Find sessions for a feature
        - work_by_author(): Analyze work by author

        Returns:
            CrossSessionAnalytics instance
        """
        if self._cross_session_analytics is None:
            from htmlgraph.analytics import CrossSessionAnalytics

            self._cross_session_analytics = CrossSessionAnalytics(self._sdk)
        return self._cross_session_analytics

    @property
    def context(self) -> ContextAnalytics:
        """
        Get context analytics interface (lazy-loaded).

        Provides:
        - get_session_usage(): Get session context usage
        - get_feature_usage(): Get feature context usage
        - get_track_usage(): Get track context usage

        Returns:
            ContextAnalytics instance
        """
        if self._context_analytics is None:
            from htmlgraph.context_analytics import ContextAnalytics

            self._context_analytics = ContextAnalytics(self._sdk)
        return self._context_analytics

    @property
    def pattern_learning(self) -> Any:
        """
        Get pattern learning interface (lazy-loaded).

        Returns:
            PatternLearner instance
        """
        if self._pattern_learning is None:
            from htmlgraph.analytics.pattern_learning import PatternLearner

            self._pattern_learning = PatternLearner(self._directory)
        return self._pattern_learning
