from __future__ import annotations

"""
Phase builder for creating project phase nodes.

Extends BaseBuilder with phase-specific methods like
phase ordering and dependencies.
"""


from datetime import date
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.builders.base import BaseBuilder


class PhaseBuilder(BaseBuilder["PhaseBuilder"]):
    """
    Fluent builder for creating phases.

    Inherits common builder methods from BaseBuilder and adds
    phase-specific methods for project planning:
    - phase_number: Ordering within project
    - start_date/end_date: Phase timeline
    - deliverables: What the phase produces

    Example:
        >>> sdk = SDK(agent="claude")
        >>> phase = sdk.phases.create("Phase 1: Core Library") \\
        ...     .set_priority("high") \\
        ...     .set_phase_number(1) \\
        ...     .set_deliverables(["Core API", "Unit tests", "Documentation"]) \\
        ...     .save()
    """

    node_type = "phase"

    def __init__(self, sdk: SDK, title: str, **kwargs: Any):
        """Initialize phase builder with agent attribution."""
        super().__init__(sdk, title, **kwargs)
        # Auto-assign agent from SDK for work tracking
        if sdk._agent_id:
            self._data["agent_assigned"] = sdk._agent_id
        elif "agent_assigned" not in self._data:
            # Log warning if agent not assigned (defensive check)
            import logging

            logging.warning(
                f"Creating phase '{self._data.get('title', 'Unknown')}' without agent attribution. "
                "Pass agent='name' to SDK() initialization."
            )

    def set_phase_number(self, number: int) -> PhaseBuilder:
        """
        Set the phase number for ordering.

        Args:
            number: Phase sequence number

        Returns:
            Self for method chaining

        Example:
            >>> phase.set_phase_number(1)
        """
        self._data["phase_number"] = number
        return self

    def set_start_date(self, start: date) -> PhaseBuilder:
        """
        Set phase start date.

        Args:
            start: Start date

        Returns:
            Self for method chaining

        Example:
            >>> phase.set_start_date(date(2025, 1, 1))
        """
        return self._set_date("start_date", start)

    def set_end_date(self, end: date) -> PhaseBuilder:
        """
        Set phase end date.

        Args:
            end: End date

        Returns:
            Self for method chaining

        Example:
            >>> phase.set_end_date(date(2025, 3, 31))
        """
        return self._set_date("end_date", end)

    def set_deliverables(self, deliverables: list[str]) -> PhaseBuilder:
        """
        Set phase deliverables.

        Args:
            deliverables: List of deliverable items

        Returns:
            Self for method chaining

        Example:
            >>> phase.set_deliverables(["API docs", "SDK release", "Examples"])
        """
        self._data["deliverables"] = deliverables
        return self

    def add_milestone(self, milestone: str) -> PhaseBuilder:
        """
        Add a milestone to the phase.

        Args:
            milestone: Milestone description

        Returns:
            Self for method chaining

        Example:
            >>> phase.add_milestone("Alpha release")
        """
        return self._append_to_list("milestones", milestone)

    def follows(self, phase_id: str) -> PhaseBuilder:
        """
        Set this phase to follow another phase.

        Args:
            phase_id: ID of the preceding phase

        Returns:
            Self for method chaining

        Example:
            >>> phase.follows("phase-core-library")
        """
        return self._add_edge("follows", phase_id)

    def set_exit_criteria(self, criteria: list[str]) -> PhaseBuilder:
        """
        Set exit criteria for completing the phase.

        Args:
            criteria: List of exit criteria

        Returns:
            Self for method chaining

        Example:
            >>> phase.set_exit_criteria(["All tests passing", "Code review complete"])
        """
        self._data["exit_criteria"] = criteria
        return self
