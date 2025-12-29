"""
Lightweight index for tracking active auto-generated spikes.

This avoids the expensive operation of scanning all spike files on SessionManager init.
Instead, we maintain a simple JSON index that tracks only active auto-spikes.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ActiveAutoSpikeIndex:
    """
    Fast index for tracking active auto-generated spikes (session-init, transition, conversation-init).

    This is much faster than scanning all spike files on startup.
    The index is a simple JSON file that maps spike_id -> metadata.
    """

    def __init__(self, graph_dir: Path):
        """
        Initialize the index.

        Args:
            graph_dir: .htmlgraph directory
        """
        self.graph_dir = Path(graph_dir)
        self.index_path = self.graph_dir / "active-auto-spikes.json"
        self._data: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def load(self) -> None:
        """Load index from disk (lazy)."""
        if self._loaded:
            return

        if self.index_path.exists():
            try:
                with open(self.index_path) as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    f"Failed to load active-auto-spikes index: {e}. Starting fresh."
                )
                self._data = {}
        else:
            self._data = {}

        self._loaded = True

    def save(self) -> None:
        """Save index to disk."""
        try:
            with open(self.index_path, "w") as f:
                json.dump(self._data, f, indent=2)
        except OSError as e:
            logger.warning(f"Failed to save active-auto-spikes index: {e}")

    def add(
        self, spike_id: str, spike_subtype: str, session_id: str | None = None
    ) -> None:
        """
        Add an active auto-spike to the index.

        Args:
            spike_id: Spike ID
            spike_subtype: Spike subtype (session-init, transition, conversation-init)
            session_id: Optional session ID
        """
        self.load()
        self._data[spike_id] = {
            "spike_subtype": spike_subtype,
            "session_id": session_id,
        }
        self.save()

    def remove(self, spike_id: str) -> None:
        """
        Remove a spike from the index (when completed or deleted).

        Args:
            spike_id: Spike ID to remove
        """
        self.load()
        if spike_id in self._data:
            del self._data[spike_id]
            self.save()

    def get_all(self) -> set[str]:
        """
        Get all active auto-spike IDs.

        Returns:
            Set of spike IDs
        """
        self.load()
        return set(self._data.keys())

    def clear(self) -> None:
        """Clear the index (for testing or cleanup)."""
        self._data = {}
        self.save()

    def rebuild_from_disk(self) -> int:
        """
        Rebuild the index by scanning all spike files on disk.

        This is the expensive operation we're trying to avoid during normal init.
        Only call this when necessary (e.g., after manual file edits or corruption).

        Returns:
            Number of active auto-spikes found
        """
        from htmlgraph.converter import NodeConverter

        spikes_dir = self.graph_dir / "spikes"
        if not spikes_dir.exists():
            self.clear()
            return 0

        spike_converter = NodeConverter(spikes_dir)
        self._data = {}

        # Scan all spikes for active auto-generated ones
        for spike in spike_converter.load_all():
            if (
                spike.type == "spike"
                and getattr(spike, "auto_generated", False)
                and getattr(spike, "spike_subtype", None)
                in ("session-init", "transition", "conversation-init")
                and spike.status == "in-progress"
            ):
                self._data[spike.id] = {
                    "spike_subtype": spike.spike_subtype,
                    "session_id": getattr(spike, "session_id", None),
                }

        self.save()
        return len(self._data)
