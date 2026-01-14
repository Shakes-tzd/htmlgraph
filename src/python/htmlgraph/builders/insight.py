from __future__ import annotations

"""
Insight builder for creating session insight nodes.

Extends BaseBuilder with insight-specific methods for
session health scoring and pattern detection.
"""


from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.models import SessionInsight
    from htmlgraph.sdk import SDK

from htmlgraph.builders.base import BaseBuilder
from htmlgraph.ids import generate_id


class InsightBuilder(BaseBuilder["InsightBuilder"]):
    """
    Fluent builder for creating session insights.

    Insights analyze session health, detect patterns, and provide
    recommendations for improvement.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> insight = sdk.insights.create("Session ABC Health Analysis") \\
        ...     .for_session("session-abc-123") \\
        ...     .set_health_scores(efficiency=0.85, retry_rate=0.1) \\
        ...     .add_issue("High retry rate on Bash commands") \\
        ...     .add_recommendation("Use Read before Edit") \\
        ...     .save()
    """

    node_type = "insight"

    def __init__(self, sdk: SDK, title: str, **kwargs: Any):
        """Initialize insight builder with insight-specific defaults."""
        super().__init__(sdk, title, **kwargs)
        # Set insight-specific defaults
        if "insight_type" not in self._data:
            self._data["insight_type"] = "health"

    def for_session(self, session_id: str) -> InsightBuilder:
        """
        Set the source session ID.

        Args:
            session_id: ID of the session being analyzed

        Returns:
            Self for method chaining

        Example:
            >>> insight.for_session("session-abc-123")
        """
        self._data["session_id"] = session_id
        return self

    def set_health_scores(
        self,
        efficiency: float = 0.0,
        retry_rate: float = 0.0,
        context_rebuilds: int = 0,
        tool_diversity: float = 0.0,
        error_recovery: float = 0.0,
    ) -> InsightBuilder:
        """
        Set all health metric scores.

        Args:
            efficiency: Efficiency score (0.0-1.0)
            retry_rate: Retry rate (0.0-1.0, lower is better)
            context_rebuilds: Number of context rebuilds
            tool_diversity: Tool diversity score (0.0-1.0)
            error_recovery: Error recovery rate (0.0-1.0)

        Returns:
            Self for method chaining

        Example:
            >>> insight.set_health_scores(
            ...     efficiency=0.85,
            ...     retry_rate=0.12,
            ...     tool_diversity=0.70
            ... )
        """
        self._data["efficiency_score"] = efficiency
        self._data["retry_rate"] = retry_rate
        self._data["context_rebuild_count"] = context_rebuilds
        self._data["tool_diversity"] = tool_diversity
        self._data["error_recovery_rate"] = error_recovery
        # Calculate overall health score
        self._data["overall_health_score"] = (
            efficiency + (1 - retry_rate) + tool_diversity
        ) / 3
        return self

    def add_issue(self, issue: str) -> InsightBuilder:
        """
        Add a detected issue.

        Args:
            issue: Description of the issue

        Returns:
            Self for method chaining

        Example:
            >>> insight.add_issue("High retry rate on file operations")
        """
        if "issues_detected" not in self._data:
            self._data["issues_detected"] = []
        self._data["issues_detected"].append(issue)
        return self

    def add_recommendation(self, rec: str) -> InsightBuilder:
        """
        Add a recommendation for improvement.

        Args:
            rec: Recommendation text

        Returns:
            Self for method chaining

        Example:
            >>> insight.add_recommendation("Use Read before attempting Edit")
        """
        if "recommendations" not in self._data:
            self._data["recommendations"] = []
        self._data["recommendations"].append(rec)
        return self

    def add_pattern_match(
        self, pattern_id: str, is_anti: bool = False
    ) -> InsightBuilder:
        """
        Add a matched pattern ID.

        Args:
            pattern_id: ID of the matched pattern
            is_anti: Whether this is an anti-pattern match

        Returns:
            Self for method chaining

        Example:
            >>> insight.add_pattern_match("pattern-efficient-testing", is_anti=False)
            >>> insight.add_pattern_match("pattern-excessive-retries", is_anti=True)
        """
        key = "anti_patterns_matched" if is_anti else "patterns_matched"
        if key not in self._data:
            self._data[key] = []
        self._data[key].append(pattern_id)
        return self

    def save(self) -> SessionInsight:
        """
        Save the insight and return the SessionInsight instance.

        Overrides BaseBuilder.save() to ensure insights are saved
        to the insights directory.

        Returns:
            Created SessionInsight instance
        """
        # Generate collision-resistant ID if not provided
        if "id" not in self._data:
            self._data["id"] = generate_id(
                node_type="insight",
                title=self._data.get("title", ""),
            )

        # Import SessionInsight here to avoid circular imports
        from htmlgraph.models import SessionInsight

        node = SessionInsight(**self._data)

        # Save to the insights collection
        if hasattr(self._sdk, "insights") and self._sdk.insights is not None:
            graph = self._sdk.insights._ensure_graph()
            graph.add(node)
        else:
            # Fallback: create new graph
            from htmlgraph.graph import HtmlGraph

            graph_path = self._sdk._directory / "insights"
            graph = HtmlGraph(graph_path, auto_load=False)
            graph.add(node)

        return node
