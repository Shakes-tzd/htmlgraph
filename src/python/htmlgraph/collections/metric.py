from __future__ import annotations

"""
AggregatedMetric collection for managing aggregated metrics.

Extends BaseCollection with metric-specific query methods.
"""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.models import Node
    from htmlgraph.sdk import SDK

from htmlgraph.collections.base import BaseCollection


class MetricCollection(BaseCollection["MetricCollection"]):
    """
    Collection interface for aggregated metrics.

    Provides all base collection methods plus metric-specific
    queries for analyzing trends and retrieving latest metrics.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> latest = sdk.metrics.get_latest(scope="session", period="weekly")
        >>>
        >>> # Query metrics
        >>> trending = sdk.metrics.get_trend(scope="session")
    """

    _collection_name = "metrics"
    _node_type = "metric"

    def __init__(self, sdk: SDK):
        """
        Initialize metric collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "metrics", "metric")
        self._sdk = sdk

        # Set builder class for create() method
        from htmlgraph.builders import MetricBuilder

        self._builder_class = MetricBuilder

    def get_latest(self, scope: str = "session", period: str = "weekly") -> Node | None:
        """
        Get the most recent metric for a scope/period.

        Args:
            scope: Metric scope (e.g., "session", "feature", "agent")
            period: Time period (e.g., "daily", "weekly", "monthly")

        Returns:
            Most recent metric node if found, None otherwise

        Example:
            >>> latest = sdk.metrics.get_latest(scope="session", period="weekly")
        """
        results = list(self.where(scope=scope, period=period))
        if not results:
            return None
        # Sort by period_end descending (most recent first)
        results.sort(key=lambda m: getattr(m, "period_end", "") or "", reverse=True)
        return results[0]

    def get_trend(self, scope: str = "session") -> list[Node]:
        """
        Get metrics showing trends for a scope.

        Filters out metrics with "stable" trend_direction.

        Args:
            scope: Metric scope to filter by

        Returns:
            List of metrics with non-stable trends

        Example:
            >>> trending = sdk.metrics.get_trend(scope="session")
        """
        return [
            m
            for m in self.where(scope=scope)
            if hasattr(m, "trend_direction") and m.trend_direction != "stable"
        ]
