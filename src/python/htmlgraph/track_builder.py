"""
Track Builder and Collection for agent-friendly track creation.

Note: TrackBuilder has been moved to builders/track.py for better organization.
This module now provides TrackCollection and re-exports TrackBuilder for backward compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

# Import TrackBuilder from its new location
from htmlgraph.builders.track import TrackBuilder  # noqa: F401


class TrackCollection:
    """Collection interface for tracks with builder support and directory-based loading."""

    def __init__(self, sdk: SDK):
        self._sdk = sdk
        self._collection_name = "tracks"
        self._node_type = "track"
        self.collection_name = "tracks"  # For backward compatibility
        self.id_prefix = "track"
        self._graph = None  # Lazy-loaded

    def _ensure_graph(self):
        """Lazy-load the graph for tracks with multi-pattern support."""
        if self._graph is None:
            from htmlgraph.graph import HtmlGraph

            collection_path = self._sdk._directory / self._collection_name
            # Support both single-file tracks (track-xxx.html) and directory-based (track-xxx/index.html)
            self._graph = HtmlGraph(
                collection_path, auto_load=True, pattern=["*.html", "*/index.html"]
            )
        return self._graph

    def get(self, node_id: str):
        """Get a track by ID."""
        return self._ensure_graph().get(node_id)

    def all(self):
        """Get all tracks (both file-based and directory-based)."""
        return [n for n in self._ensure_graph() if n.type == self._node_type]

    def where(
        self, status: str | None = None, priority: str | None = None, **extra_filters
    ):
        """
        Query tracks with filters.

        Example:
            active_tracks = sdk.tracks.where(status="active", priority="high")
        """

        def matches(node):
            if node.type != self._node_type:
                return False
            if status and getattr(node, "status", None) != status:
                return False
            if priority and getattr(node, "priority", None) != priority:
                return False

            # Check extra filters
            for key, value in extra_filters.items():
                if getattr(node, key, None) != value:
                    return False

            return True

        return self._ensure_graph().filter(matches)

    def builder(self) -> TrackBuilder:
        """
        Create a new track builder with fluent interface.

        Returns:
            TrackBuilder for method chaining

        Example:
            track = sdk.tracks.builder() \\
                .title("Multi-Agent Collaboration") \\
                .priority("high") \\
                .with_spec(overview="...") \\
                .with_plan_phases([...]) \\
                .create()
        """
        return TrackBuilder(self._sdk)
