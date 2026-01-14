from __future__ import annotations

"""
SessionInsight collection for managing session insights.

Extends BaseCollection with insight-specific query methods.
"""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.models import Node
    from htmlgraph.sdk import SDK

from htmlgraph.collections.base import BaseCollection


class InsightCollection(BaseCollection["InsightCollection"]):
    """
    Collection interface for session insights.

    Provides all base collection methods plus insight-specific
    queries for analyzing session efficiency and detecting issues.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> insight = sdk.insights.for_session("sess-abc-123")
        >>>
        >>> # Query insights
        >>> low_eff = sdk.insights.get_low_efficiency(threshold=0.7)
        >>> with_issues = sdk.insights.get_with_issues()
    """

    _collection_name = "insights"
    _node_type = "insight"

    def __init__(self, sdk: SDK):
        """
        Initialize insight collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "insights", "insight")
        self._sdk = sdk

        # Set builder class for create() method
        from htmlgraph.builders import InsightBuilder

        self._builder_class = InsightBuilder

    def for_session(self, session_id: str) -> Node | None:
        """
        Get insight for a specific session.

        Args:
            session_id: Session ID to find insight for

        Returns:
            Insight node if found, None otherwise

        Example:
            >>> insight = sdk.insights.for_session("sess-abc-123")
        """
        results = list(self.where(session_id=session_id))
        return results[0] if results else None

    def get_low_efficiency(self, threshold: float = 0.7) -> list[Node]:
        """
        Get insights with efficiency below threshold.

        Args:
            threshold: Minimum efficiency score (0.0 to 1.0)

        Returns:
            List of insights with efficiency_score < threshold

        Example:
            >>> low_eff = sdk.insights.get_low_efficiency(threshold=0.6)
        """
        return [
            i
            for i in self.all()
            if hasattr(i, "efficiency_score") and i.efficiency_score < threshold
        ]

    def get_with_issues(self) -> list[Node]:
        """
        Get insights that detected issues.

        Returns:
            List of insights where issues_detected is True

        Example:
            >>> problematic = sdk.insights.get_with_issues()
        """
        return [
            i for i in self.all() if hasattr(i, "issues_detected") and i.issues_detected
        ]
