from __future__ import annotations

"""
Phase collection for managing project phase work items.

Extends BaseCollection with phase-specific builder support.
"""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.collections.base import BaseCollection


class PhaseCollection(BaseCollection["PhaseCollection"]):
    """
    Collection interface for phases with builder support.

    Provides all base collection methods plus a fluent builder
    interface for creating new phases.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> phase = sdk.phases.create("Phase 1: Core Library") \\
        ...     .set_priority("high") \\
        ...     .set_phase_number(1) \\
        ...     .set_deliverables(["Core API", "Tests"]) \\
        ...     .save()
        >>>
        >>> # Query phases
        >>> active_phases = sdk.phases.where(status="in-progress")
    """

    _collection_name = "phases"
    _node_type = "phase"

    def __init__(self, sdk: SDK):
        """
        Initialize phase collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "phases", "phase")
        self._sdk = sdk

        # Set builder class for create() method
        from htmlgraph.builders.phase import PhaseBuilder

        self._builder_class = PhaseBuilder
