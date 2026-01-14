from __future__ import annotations

"""
Chore builder for creating maintenance task nodes.

Extends BaseBuilder with chore-specific methods like
chore type and recurrence.
"""


from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.builders.base import BaseBuilder


class ChoreBuilder(BaseBuilder["ChoreBuilder"]):
    """
    Fluent builder for creating chores.

    Inherits common builder methods from BaseBuilder and adds
    chore-specific methods for maintenance work:
    - chore_type: Classification of chore
    - is_recurring: Whether this repeats
    - recurrence_interval: How often it recurs

    Example:
        >>> sdk = SDK(agent="claude")
        >>> chore = sdk.chores.create("Update dependencies") \\
        ...     .set_priority("low") \\
        ...     .set_chore_type("maintenance") \\
        ...     .set_recurring(interval_days=30) \\
        ...     .save()
    """

    node_type = "chore"

    def __init__(self, sdk: SDK, title: str, **kwargs: Any):
        """Initialize chore builder with agent attribution."""
        super().__init__(sdk, title, **kwargs)
        # Auto-assign agent from SDK for work tracking
        if sdk._agent_id:
            self._data["agent_assigned"] = sdk._agent_id
        elif "agent_assigned" not in self._data:
            # Log warning if agent not assigned (defensive check)
            import logging

            logging.warning(
                f"Creating chore '{self._data.get('title', 'Unknown')}' without agent attribution. "
                "Pass agent='name' to SDK() initialization."
            )

    def set_chore_type(self, chore_type: str) -> ChoreBuilder:
        """
        Set the type of chore.

        Args:
            chore_type: Type (maintenance, refactor, cleanup, upgrade, documentation)

        Returns:
            Self for method chaining

        Example:
            >>> chore.set_chore_type("maintenance")
        """
        self._data["chore_type"] = chore_type
        return self

    def set_recurring(self, interval_days: int | None = None) -> ChoreBuilder:
        """
        Mark chore as recurring with optional interval.

        Args:
            interval_days: Days between occurrences (optional)

        Returns:
            Self for method chaining

        Example:
            >>> chore.set_recurring(interval_days=7)  # Weekly
        """
        self._data["is_recurring"] = True
        if interval_days:
            self._data["recurrence_interval_days"] = interval_days
        return self

    def set_scope(self, scope: str) -> ChoreBuilder:
        """
        Set the scope of the chore.

        Args:
            scope: Scope description (e.g., "entire codebase", "auth module")

        Returns:
            Self for method chaining

        Example:
            >>> chore.set_scope("authentication module")
        """
        self._data["scope"] = scope
        return self

    def set_estimated_effort(self, hours: float) -> ChoreBuilder:
        """
        Set estimated effort in hours.

        Args:
            hours: Estimated hours to complete

        Returns:
            Self for method chaining

        Example:
            >>> chore.set_estimated_effort(2.5)
        """
        self._data["estimated_effort_hours"] = hours
        return self
