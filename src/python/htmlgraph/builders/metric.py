from __future__ import annotations

"""
Metric builder for creating aggregated metric nodes.

Extends BaseBuilder with metric-specific methods for
time-series aggregation and trend analysis.
"""


from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.models import AggregatedMetric
    from htmlgraph.sdk import SDK

from htmlgraph.builders.base import BaseBuilder
from htmlgraph.ids import generate_id


class MetricBuilder(BaseBuilder["MetricBuilder"]):
    """
    Fluent builder for creating aggregated metrics.

    Metrics aggregate data over time periods (daily/weekly/monthly)
    and scopes (session/feature/track/agent).

    Example:
        >>> sdk = SDK(agent="claude")
        >>> metric = sdk.metrics.create("Weekly Efficiency") \\
        ...     .set_scope("agent", "claude") \\
        ...     .set_period("weekly", start=datetime(...), end=datetime(...)) \\
        ...     .set_metrics({"avg_efficiency": 0.85, "median_retry_rate": 0.12}) \\
        ...     .set_trend("improving", strength=0.15) \\
        ...     .save()
    """

    node_type = "metric"

    def __init__(self, sdk: SDK, title: str, **kwargs: Any):
        """Initialize metric builder with metric-specific defaults."""
        super().__init__(sdk, title, **kwargs)
        # Set metric-specific defaults
        if "metric_type" not in self._data:
            self._data["metric_type"] = "efficiency"
        if "scope" not in self._data:
            self._data["scope"] = "session"
        if "period" not in self._data:
            self._data["period"] = "weekly"

    def set_scope(self, scope: str, scope_id: str | None = None) -> MetricBuilder:
        """
        Set metric scope: session, feature, track, or agent.

        Args:
            scope: Scope type (session/feature/track/agent)
            scope_id: Specific ID within scope (optional)

        Returns:
            Self for method chaining

        Example:
            >>> metric.set_scope("agent", "claude")
            >>> metric.set_scope("track", "track-planning-workflow")
        """
        self._data["scope"] = scope
        if scope_id:
            self._data["scope_id"] = scope_id
        return self

    def set_period(
        self,
        period: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> MetricBuilder:
        """
        Set time period for aggregation.

        Args:
            period: Period type (daily/weekly/monthly)
            start: Period start datetime (optional)
            end: Period end datetime (optional)

        Returns:
            Self for method chaining

        Example:
            >>> metric.set_period("weekly", start=datetime(...), end=datetime(...))
        """
        self._data["period"] = period
        if start:
            self._data["period_start"] = start.isoformat()
        if end:
            self._data["period_end"] = end.isoformat()
        return self

    def set_metrics(self, metrics: dict[str, float]) -> MetricBuilder:
        """
        Set metric values dict.

        Args:
            metrics: Dictionary of metric name -> value

        Returns:
            Self for method chaining

        Example:
            >>> metric.set_metrics({
            ...     "avg_efficiency": 0.85,
            ...     "median_retry_rate": 0.12,
            ...     "tool_diversity": 0.68
            ... })
        """
        self._data["metric_values"] = metrics
        return self

    def set_percentiles(self, percentiles: dict[str, float]) -> MetricBuilder:
        """
        Set percentile values (p50, p90, p99, etc.).

        Args:
            percentiles: Dictionary of percentile name -> value

        Returns:
            Self for method chaining

        Example:
            >>> metric.set_percentiles({
            ...     "p50": 0.82,
            ...     "p90": 0.95,
            ...     "p99": 0.98
            ... })
        """
        self._data["percentiles"] = percentiles
        return self

    def set_trend(
        self,
        direction: str,
        strength: float = 0.0,
        vs_previous_pct: float = 0.0,
    ) -> MetricBuilder:
        """
        Set trend information.

        Args:
            direction: Trend direction (improving/declining/stable)
            strength: Trend strength (0.0-1.0)
            vs_previous_pct: Percentage change vs previous period

        Returns:
            Self for method chaining

        Example:
            >>> metric.set_trend("improving", strength=0.15, vs_previous_pct=8.5)
        """
        self._data["trend_direction"] = direction
        self._data["trend_strength"] = strength
        self._data["vs_previous_period_pct"] = vs_previous_pct
        return self

    def add_session(self, session_id: str) -> MetricBuilder:
        """
        Add a session to the aggregation.

        Args:
            session_id: Session ID to include

        Returns:
            Self for method chaining

        Example:
            >>> metric.add_session("session-abc-123")
        """
        if "sessions_in_period" not in self._data:
            self._data["sessions_in_period"] = []
        self._data["sessions_in_period"].append(session_id)
        self._data["data_points_count"] = len(self._data["sessions_in_period"])
        return self

    def save(self) -> AggregatedMetric:
        """
        Save the metric and return the AggregatedMetric instance.

        Overrides BaseBuilder.save() to ensure metrics are saved
        to the metrics directory.

        Returns:
            Created AggregatedMetric node instance
        """
        # Generate collision-resistant ID if not provided
        if "id" not in self._data:
            self._data["id"] = generate_id(
                node_type="metric",
                title=self._data.get("title", ""),
            )

        # Import AggregatedMetric here to avoid circular imports
        from htmlgraph.models import AggregatedMetric

        node = AggregatedMetric(**self._data)

        # Save to the metrics collection
        if hasattr(self._sdk, "metrics") and self._sdk.metrics is not None:
            graph = self._sdk.metrics._ensure_graph()
            graph.add(node)
        else:
            # Fallback: create new graph
            from htmlgraph.graph import HtmlGraph

            graph_path = self._sdk._directory / "metrics"
            graph = HtmlGraph(graph_path, auto_load=False)
            graph.add(node)

        return node
