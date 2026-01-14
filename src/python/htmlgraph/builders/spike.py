from __future__ import annotations

"""
Spike builder for creating spike investigation nodes.

Extends BaseBuilder with spike-specific methods like
spike_type and timebox_hours.
"""


from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.models import Node
    from htmlgraph.sdk import SDK

from htmlgraph.builders.base import BaseBuilder
from htmlgraph.ids import generate_id
from htmlgraph.models import Spike, SpikeType


class SpikeBuilder(BaseBuilder["SpikeBuilder"]):
    """
    Fluent builder for creating spikes.

    Inherits common builder methods from BaseBuilder and adds
    spike-specific methods for investigation work:
    - spike_type: Classification (technical/architectural/risk)
    - timebox_hours: Time budget
    - findings: Summary of learnings
    - decision: Final decision

    Example:
        >>> sdk = SDK(agent="claude")
        >>> spike = sdk.spikes.create("Investigate Auth Options") \\
        ...     .set_spike_type(SpikeType.ARCHITECTURAL) \\
        ...     .set_timebox_hours(4) \\
        ...     .add_steps(["Research OAuth providers", "Compare pricing"]) \\
        ...     .save()
    """

    node_type = "spike"

    def __init__(self, sdk: SDK, title: str, **kwargs: Any):
        """Initialize spike builder with spike-specific defaults."""
        super().__init__(sdk, title, **kwargs)
        # Set spike-specific defaults
        if "spike_type" not in self._data:
            self._data["spike_type"] = SpikeType.GENERAL
        if "timebox_hours" not in self._data:
            self._data["timebox_hours"] = 4
        # Auto-assign agent from SDK (critical for work tracking)
        if sdk._agent_id:
            self._data["agent_assigned"] = sdk._agent_id
        elif "agent_assigned" not in self._data:
            # This should never happen now because SDK enforces agent parameter,
            # but log warning if it does occur (for debugging)
            import logging

            logging.warning(
                f"Creating spike '{self._data.get('title', 'Unknown')}' without agent attribution. "
                "This will make work tracking impossible. Pass agent='name' to SDK() initialization."
            )

    def set_spike_type(self, spike_type: SpikeType) -> SpikeBuilder:
        """
        Set the spike investigation type.

        Args:
            spike_type: Type of spike (TECHNICAL, ARCHITECTURAL, RISK, etc.)

        Returns:
            Self for method chaining

        Example:
            >>> spike.set_spike_type(SpikeType.ARCHITECTURAL)
        """
        self._data["spike_type"] = spike_type
        return self

    def set_timebox_hours(self, hours: float) -> SpikeBuilder:
        """
        Set the time budget for this spike.

        Args:
            hours: Time budget in hours

        Returns:
            Self for method chaining

        Example:
            >>> spike.set_timebox_hours(2.5)
        """
        self._data["timebox_hours"] = int(hours)
        return self

    def set_findings(self, findings: str) -> SpikeBuilder:
        """
        Set the findings/learnings from spike investigation.

        Args:
            findings: Summary of what was learned (must be non-empty, min 10 chars)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If findings are empty or too short

        Example:
            >>> spike.set_findings("OAuth2 is best fit. Recommend Auth0.")
        """
        # Validate findings quality
        stripped = findings.strip() if findings else ""
        if not stripped:
            raise ValueError(
                "Findings cannot be empty. Provide meaningful investigation results."
            )
        if len(stripped) < 10:
            raise ValueError(
                "Findings must be at least 10 characters. Provide detailed results."
            )
        self._data["findings"] = stripped
        return self

    def set_decision(self, decision: str) -> SpikeBuilder:
        """
        Set the final decision made based on spike results.

        Args:
            decision: Decision made

        Returns:
            Self for method chaining

        Example:
            >>> spike.set_decision("Use Auth0 with social logins")
        """
        self._data["decision"] = decision
        return self

    def save(self) -> Node:
        """
        Save the spike and return the Spike instance.

        Overrides BaseBuilder.save() to create a Spike instance
        instead of a generic Node, and saves to spikes directory.

        Returns:
            Created Spike instance
        """
        # Generate collision-resistant ID if not provided
        if "id" not in self._data:
            self._data["id"] = generate_id(
                node_type="spike",
                title=self._data.get("title", ""),
            )

        spike = Spike(**self._data)

        # Save to the collection's shared graph
        # This ensures the spike is visible via sdk.spikes.get() immediately
        if hasattr(self._sdk, "spikes") and self._sdk.spikes is not None:
            graph = self._sdk.spikes._ensure_graph()
            graph.add(spike)
        else:
            # Fallback: create new graph
            from htmlgraph.graph import HtmlGraph

            graph_path = self._sdk._directory / "spikes"
            graph = HtmlGraph(graph_path, auto_load=False)
            graph.add(spike)

        return spike
