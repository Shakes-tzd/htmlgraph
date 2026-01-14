from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

"""
Spike collection for managing investigation and research spikes.

Extends BaseCollection with spike-specific builder support.
"""


from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.collections.base import BaseCollection


class SpikeCollection(BaseCollection["SpikeCollection"]):
    """
    Collection interface for spikes with builder support.

    Provides all base collection methods plus a fluent builder
    interface for creating new investigation spikes.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> spike = sdk.spikes.create("Investigate Auth Options") \\
        ...     .set_spike_type(SpikeType.ARCHITECTURAL) \\
        ...     .set_timebox_hours(4) \\
        ...     .add_steps(["Research OAuth providers", "Compare pricing"]) \\
        ...     .save()
        >>>
        >>> # Query spikes
        >>> active = sdk.spikes.where(status="in-progress")
        >>> all_spikes = sdk.spikes.all()
    """

    _collection_name = "spikes"
    _node_type = "spike"

    def __init__(self, sdk: SDK):
        """
        Initialize spike collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "spikes", "spike")
        self._sdk = sdk

        # Set builder class for create() method
        from htmlgraph.builders import SpikeBuilder

        self._builder_class = SpikeBuilder

    def get_latest(self, agent: str | None = None, limit: int = 1) -> list:
        """
        Get the most recent spike(s), optionally filtered by agent.

        Useful for retrieving subagent findings after delegation.

        Args:
            agent: Filter by agent_assigned (optional)
            limit: Maximum number of spikes to return (default: 1)

        Returns:
            List of most recent Spike nodes (newest first)

        Example:
            >>> # Get latest spike from explorer subagent
            >>> sdk = SDK(agent="orchestrator")
            >>> findings = sdk.spikes.get_latest(agent="explorer")
            >>> if findings:
            ...     print(findings[0].findings)
            >>>
            >>> # Get latest 5 spikes from any agent
            >>> recent = sdk.spikes.get_latest(limit=5)
        """
        from datetime import timezone

        # Get all spikes
        all_spikes = self.all()

        # Filter by agent if specified
        # Check both agent_assigned and model_name fields
        if agent:
            all_spikes = [
                s
                for s in all_spikes
                if (s.agent_assigned and agent.lower() in s.agent_assigned.lower())
                or (s.model_name and agent.lower() in s.model_name.lower())
            ]

        # Normalize to UTC for comparison
        def to_comparable(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt

        # Sort by created timestamp (newest first)
        all_spikes.sort(key=lambda s: to_comparable(s.created), reverse=True)

        # Return limited results
        return all_spikes[:limit]
