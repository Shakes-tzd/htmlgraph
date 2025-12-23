"""
Spike collection for managing investigation and research spikes.

Extends BaseCollection with spike-specific builder support.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK
    from htmlgraph.builders import SpikeBuilder

from htmlgraph.collections.base import BaseCollection


class SpikeCollection(BaseCollection['SpikeCollection']):
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

    def __init__(self, sdk: 'SDK'):
        """
        Initialize spike collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "spikes", "spike")
        self._sdk = sdk

    def create(self, title: str, **kwargs) -> SpikeBuilder:
        """
        Create a new spike with fluent interface.

        Args:
            title: Spike title
            **kwargs: Additional spike properties

        Returns:
            SpikeBuilder for method chaining

        Example:
            >>> spike = sdk.spikes.create("Investigate Database Options") \\
            ...     .set_spike_type(SpikeType.TECHNICAL) \\
            ...     .set_timebox_hours(2) \\
            ...     .add_steps(["Research PostgreSQL", "Research MongoDB"]) \\
            ...     .save()
        """
        from htmlgraph.builders import SpikeBuilder
        return SpikeBuilder(self._sdk, title, **kwargs)
