from __future__ import annotations

"""
Epic builder for creating large body of work nodes.

Extends BaseBuilder with epic-specific methods like
child features and milestones.
"""


from datetime import date
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.builders.base import BaseBuilder


class EpicBuilder(BaseBuilder["EpicBuilder"]):
    """
    Fluent builder for creating epics.

    Inherits common builder methods from BaseBuilder and adds
    epic-specific methods for large initiatives:
    - child_features: Features contained in this epic
    - target_date: Target completion date
    - success_criteria: How success is measured

    Example:
        >>> sdk = SDK(agent="claude")
        >>> epic = sdk.epics.create("v2.0 Release") \\
        ...     .set_priority("high") \\
        ...     .set_target_date(date(2025, 3, 1)) \\
        ...     .add_child_feature("feat-001") \\
        ...     .add_child_feature("feat-002") \\
        ...     .save()
    """

    node_type = "epic"

    def __init__(self, sdk: SDK, title: str, **kwargs: Any):
        """Initialize epic builder with agent attribution."""
        super().__init__(sdk, title, **kwargs)
        # Auto-assign agent from SDK for work tracking
        if sdk._agent_id:
            self._data["agent_assigned"] = sdk._agent_id
        elif "agent_assigned" not in self._data:
            # Log warning if agent not assigned (defensive check)
            import logging

            logging.warning(
                f"Creating epic '{self._data.get('title', 'Unknown')}' without agent attribution. "
                "Pass agent='name' to SDK() initialization."
            )

    def add_child_feature(self, feature_id: str) -> EpicBuilder:
        """
        Add a feature as a child of this epic.

        Args:
            feature_id: ID of the child feature

        Returns:
            Self for method chaining

        Example:
            >>> epic.add_child_feature("feat-abc123")
        """
        return self._add_edge("contains", feature_id)

    def add_child_features(self, feature_ids: list[str]) -> EpicBuilder:
        """
        Add multiple features as children of this epic.

        Args:
            feature_ids: List of child feature IDs

        Returns:
            Self for method chaining

        Example:
            >>> epic.add_child_features(["feat-001", "feat-002", "feat-003"])
        """
        for fid in feature_ids:
            self.add_child_feature(fid)
        return self

    def set_target_date(self, target: date) -> EpicBuilder:
        """
        Set target completion date.

        Args:
            target: Target date for epic completion

        Returns:
            Self for method chaining

        Example:
            >>> epic.set_target_date(date(2025, 6, 1))
        """
        return self._set_date("target_date", target)

    def set_success_criteria(self, criteria: list[str]) -> EpicBuilder:
        """
        Set success criteria for the epic.

        Args:
            criteria: List of success criteria

        Returns:
            Self for method chaining

        Example:
            >>> epic.set_success_criteria(["100% test coverage", "Zero critical bugs"])
        """
        self._data["success_criteria"] = criteria
        return self

    def set_business_value(self, value: str) -> EpicBuilder:
        """
        Set the business value statement.

        Args:
            value: Business value description

        Returns:
            Self for method chaining

        Example:
            >>> epic.set_business_value("Increase user retention by 20%")
        """
        self._data["business_value"] = value
        return self

    def set_stakeholder(self, stakeholder: str) -> EpicBuilder:
        """
        Set the primary stakeholder.

        Args:
            stakeholder: Stakeholder name or role

        Returns:
            Self for method chaining

        Example:
            >>> epic.set_stakeholder("Product Team")
        """
        self._data["stakeholder"] = stakeholder
        return self
