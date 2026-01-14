from __future__ import annotations

"""
Track Builder and Collection for agent-friendly track creation.

Note: TrackBuilder has been moved to builders/track.py for better organization.
This module now provides TrackCollection and re-exports TrackBuilder for backward compatibility.
"""


from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.models import Node
    from htmlgraph.sdk import SDK

# Import TrackBuilder from its new location
from htmlgraph.builders.track import TrackBuilder  # noqa: F401
from htmlgraph.exceptions import NodeNotFoundError


class TrackCollection:
    """Collection interface for tracks with builder support and directory-based loading."""

    def __init__(self, sdk: SDK):
        self._sdk = sdk
        self._collection_name = "tracks"
        self._node_type = "track"
        self.collection_name = "tracks"  # For backward compatibility
        self.id_prefix = "track"
        self._graph: HtmlGraph | None = None  # Lazy-loaded
        self._ref_manager: Any = None  # Set by SDK during initialization

    def set_ref_manager(self, ref_manager: Any) -> None:
        """
        Set the ref manager for this collection.

        Called by SDK during initialization to enable short ref support.

        Args:
            ref_manager: RefManager instance from SDK
        """
        self._ref_manager = ref_manager

    def _ensure_graph(self) -> HtmlGraph:
        """Lazy-load the graph for tracks with multi-pattern support."""
        if self._graph is None:
            from htmlgraph.graph import HtmlGraph

            collection_path = self._sdk._directory / self._collection_name
            # Support both single-file tracks (track-xxx.html) and directory-based (track-xxx/index.html)
            self._graph = HtmlGraph(
                collection_path, auto_load=True, pattern=["*.html", "*/index.html"]
            )
        return self._graph

    def get(self, node_id: str) -> Node | None:
        """Get a track by ID."""
        return self._ensure_graph().get(node_id)

    def all(self) -> list[Node]:
        """Get all tracks (both file-based and directory-based)."""
        return [n for n in self._ensure_graph() if n.type == self._node_type]

    def where(
        self,
        status: str | None = None,
        priority: str | None = None,
        **extra_filters: Any,
    ) -> list[Node]:
        """
        Query tracks with filters.

        Example:
            active_tracks = sdk.tracks.where(status="active", priority="high")
        """

        def matches(node: Node) -> bool:
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

    @contextmanager
    def edit(self, track_id: str) -> Iterator[Node]:
        """
        Context manager for editing a track.

        Auto-saves on exit.

        Args:
            track_id: Track ID to edit

        Yields:
            The track node to edit

        Raises:
            NodeNotFoundError: If track not found

        Example:
            >>> with sdk.tracks.edit("track-abc123") as track:
            ...     track.status = "completed"
            ...     track.title = "Updated Title"
        """
        graph = self._ensure_graph()
        node = graph.get(track_id)
        if not node:
            raise NodeNotFoundError(self._node_type, track_id)

        yield node

        # Auto-save on exit
        graph.update(node)

    def create(self, title: str) -> TrackBuilder:
        """
        Create a new track with fluent interface.

        Args:
            title: Track title

        Returns:
            TrackBuilder for method chaining

        Example:
            track = sdk.tracks.create("Multi-Agent Collaboration") \\
                .set_priority("high") \\
                .save()
        """
        builder = TrackBuilder(self._sdk)
        builder._title = title
        return builder

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

    def delete(self, track_id: str) -> bool:
        """
        Delete a track by ID.

        Handles both single-file tracks (.html) and directory-based tracks (folder).

        Args:
            track_id: The track ID to delete

        Returns:
            True if deleted, False if not found

        Example:
            sdk.tracks.delete("track-abc123")
        """
        import shutil

        collection_path = self._sdk._directory / self._collection_name

        # Check for single-file track: {track_id}.html
        single_file = collection_path / f"{track_id}.html"
        if single_file.exists():
            single_file.unlink()
            # Also remove from graph cache if loaded
            if self._graph is not None and track_id in self._graph._nodes:
                self._graph._edge_index.remove_node(track_id)
                del self._graph._nodes[track_id]
            return True

        # Check for directory-based track: {track_id}/
        track_dir = collection_path / track_id
        if track_dir.exists() and track_dir.is_dir():
            shutil.rmtree(track_dir)
            # Also remove from graph cache if loaded
            if self._graph is not None and track_id in self._graph._nodes:
                self._graph._edge_index.remove_node(track_id)
                del self._graph._nodes[track_id]
            return True

        return False

    def batch_delete(self, track_ids: list[str]) -> int:
        """
        Delete multiple tracks in batch.

        Args:
            track_ids: List of track IDs to delete

        Returns:
            Number of tracks successfully deleted

        Example:
            count = sdk.tracks.batch_delete(["track-001", "track-002"])
            print(f"Deleted {count} tracks")
        """
        count = 0
        for track_id in track_ids:
            if self.delete(track_id):
                count += 1
        return count
