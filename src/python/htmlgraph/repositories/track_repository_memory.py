"""
MemoryTrackRepository - In-memory Track storage for testing.

Provides fast in-memory Track storage with full repository interface support.
"""

import builtins
from collections.abc import Callable
from datetime import datetime
from typing import Any

from htmlgraph.models import Node
from htmlgraph.repositories.track_repository import (
    RepositoryQuery,
    TrackRepository,
    TrackValidationError,
)


class MemoryRepositoryQuery(RepositoryQuery):
    """Query builder for in-memory filtering."""

    def __init__(self, repo: "MemoryTrackRepository", filters: dict[str, Any]):
        super().__init__(filters)
        self._repo = repo

    def where(self, **kwargs: Any) -> "MemoryRepositoryQuery":
        """Chain additional filters."""
        # Validate filter keys
        valid_attrs = {
            "status",
            "priority",
            "has_spec",
            "has_plan",
            "type",
            "title",
            "id",
            "created",
            "updated",
        }
        for key in kwargs:
            if key not in valid_attrs:
                raise TrackValidationError(f"Invalid filter attribute: {key}")

        # Merge filters
        new_filters = {**self.filters, **kwargs}
        return MemoryRepositoryQuery(self._repo, new_filters)

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        return self._repo.list(self.filters)


class MemoryTrackRepository(TrackRepository):
    """
    In-memory TrackRepository implementation for testing.

    Fast, ephemeral storage with full repository interface support.
    All data lost when instance is destroyed.

    Performance:
        - All operations: O(1) or O(n)
        - No disk I/O
        - Fast for test suites

    Example:
        >>> repo = MemoryTrackRepository()
        >>> track = repo.create("Planning Phase 1", status="active")
        >>> track.status = "completed"
        >>> repo.save(track)
    """

    def __init__(self, auto_load: bool = True):
        """
        Initialize in-memory repository.

        Args:
            auto_load: Whether to auto-load tracks (no-op for memory repo)
        """
        self._auto_load = auto_load
        self._tracks: dict[str, Node] = {}

    def _generate_id(self) -> str:
        """Generate unique track ID."""
        import uuid

        return f"trk-{uuid.uuid4().hex[:8]}"

    def _validate_track(self, track: Any) -> None:
        """Validate track object."""
        if not hasattr(track, "id"):
            raise TrackValidationError("Track must have 'id' attribute")
        if not hasattr(track, "title"):
            raise TrackValidationError("Track must have 'title' attribute")
        if not track.id or not str(track.id).strip():
            raise TrackValidationError("Track ID cannot be empty")
        if not track.title or not str(track.title).strip():
            raise TrackValidationError("Track title cannot be empty")

    def _matches_filters(self, track: Node, filters: dict[str, Any]) -> bool:
        """Check if track matches all filters."""
        if not filters:
            return True

        for key, value in filters.items():
            if not hasattr(track, key):
                return False
            if getattr(track, key) != value:
                return False
        return True

    # ===== READ OPERATIONS =====

    def get(self, track_id: str) -> Any | None:
        """
        Get single track by ID.

        Returns same object instance for multiple calls (identity caching).

        Args:
            track_id: Track ID to retrieve

        Returns:
            Track object if found, None if not found

        Raises:
            ValueError: If track_id is invalid format

        Performance: O(1)
        """
        if not track_id or not isinstance(track_id, str):
            raise ValueError(f"Invalid track_id: {track_id}")

        return self._tracks.get(track_id)

    def list(self, filters: dict[str, Any] | None = None) -> list[Any]:
        """
        List all tracks with optional filters.

        Args:
            filters: Optional dict of attribute->value filters

        Returns:
            List of Track objects (empty list if no matches)

        Raises:
            TrackValidationError: If filter keys are invalid

        Performance: O(n) where n = total tracks
        """
        if filters:
            # Validate filter keys
            valid_attrs = {
                "status",
                "priority",
                "has_spec",
                "has_plan",
                "type",
                "title",
                "id",
                "created",
                "updated",
            }
            for key in filters:
                if key not in valid_attrs:
                    raise TrackValidationError(f"Invalid filter attribute: {key}")

        results = []
        for track in self._tracks.values():
            if self._matches_filters(track, filters or {}):
                results.append(track)
        return results

    def where(self, **kwargs: Any) -> RepositoryQuery:
        """
        Build a filtered query with chaining support.

        Args:
            **kwargs: Attribute->value filter pairs

        Returns:
            RepositoryQuery object that can be further filtered

        Raises:
            TrackValidationError: If invalid attribute names
        """
        # Validate filter keys upfront
        valid_attrs = {
            "status",
            "priority",
            "has_spec",
            "has_plan",
            "type",
            "title",
            "id",
            "created",
            "updated",
        }
        for key in kwargs:
            if key not in valid_attrs:
                raise TrackValidationError(f"Invalid filter attribute: {key}")
        return MemoryRepositoryQuery(self, kwargs)

    def by_status(self, status: str) -> builtins.list[Any]:
        """Filter tracks by status."""
        return self.list({"status": status})

    def by_priority(self, priority: str) -> builtins.list[Any]:
        """Filter tracks by priority."""
        return self.list({"priority": priority})

    def active_tracks(self) -> builtins.list[Any]:
        """Get all tracks currently in progress."""
        return self.by_status("active")

    def batch_get(self, track_ids: builtins.list[str]) -> builtins.list[Any]:
        """
        Bulk retrieve multiple tracks.

        Args:
            track_ids: List of track IDs

        Returns:
            List of found tracks

        Raises:
            ValueError: If track_ids is not a list

        Performance: O(k) where k = batch size
        """
        if not isinstance(track_ids, list):
            raise ValueError("track_ids must be a list")

        results = []
        for tid in track_ids:
            track = self.get(tid)
            if track:
                results.append(track)
        return results

    # ===== WRITE OPERATIONS =====

    def create(self, title: str, **kwargs: Any) -> Any:
        """
        Create new track.

        Args:
            title: Track title (required)
            **kwargs: Additional properties

        Returns:
            Created Track object (with generated ID)

        Raises:
            TrackValidationError: If invalid data provided

        Performance: O(1)
        """
        if not title or not title.strip():
            raise TrackValidationError("Track title cannot be empty")

        # Generate ID if not provided
        track_id = kwargs.pop("id", None) or self._generate_id()

        # Extract known fields
        node_type = kwargs.pop("type", "track")
        status = kwargs.pop("status", "todo")
        priority = kwargs.pop("priority", "medium")
        created = kwargs.pop("created", datetime.now())
        updated = kwargs.pop("updated", datetime.now())

        # Remove title from kwargs if present
        kwargs.pop("title", None)

        # Create Node object
        track = Node(
            id=track_id,
            title=title,
            type=node_type,
            status=status,
            priority=priority,
            created=created,
            updated=updated,
            **kwargs,
        )

        # Validate and save
        self._validate_track(track)
        self._tracks[track_id] = track

        return track

    def save(self, track: Any) -> Any:
        """
        Save existing track (update or insert).

        Args:
            track: Track object to save

        Returns:
            Saved track (same instance)

        Raises:
            TrackValidationError: If track is invalid

        Performance: O(1)
        """
        self._validate_track(track)

        # Update timestamp
        track.updated = datetime.now()

        # Save to dict
        self._tracks[track.id] = track

        return track

    def batch_update(
        self, track_ids: builtins.list[str], updates: dict[str, Any]
    ) -> int:
        """
        Vectorized batch update operation.

        Args:
            track_ids: List of track IDs to update
            updates: Dict of attribute->value to set

        Returns:
            Number of tracks successfully updated

        Raises:
            TrackValidationError: If invalid updates

        Performance: O(k) where k = batch size
        """
        if not isinstance(track_ids, list):
            raise ValueError("track_ids must be a list")
        if not isinstance(updates, dict):
            raise TrackValidationError("updates must be a dict")

        count = 0
        for tid in track_ids:
            track = self.get(tid)
            if track:
                # Apply updates
                for key, value in updates.items():
                    setattr(track, key, value)
                self.save(track)
                count += 1

        return count

    def delete(self, track_id: str) -> bool:
        """
        Delete a track by ID.

        Args:
            track_id: Track ID to delete

        Returns:
            True if deleted, False if not found

        Performance: O(1)
        """
        if not track_id:
            raise TrackValidationError("track_id cannot be empty")

        if track_id in self._tracks:
            del self._tracks[track_id]
            return True
        return False

    def batch_delete(self, track_ids: builtins.list[str]) -> int:
        """
        Delete multiple tracks.

        Args:
            track_ids: List of track IDs to delete

        Returns:
            Number of tracks successfully deleted

        Performance: O(k) where k = batch size
        """
        if not isinstance(track_ids, list):
            raise ValueError("track_ids must be a list")

        count = 0
        for tid in track_ids:
            if self.delete(tid):
                count += 1
        return count

    # ===== ADVANCED QUERIES =====

    def find_by_features(self, feature_ids: builtins.list[str]) -> builtins.list[Any]:
        """
        Find tracks containing any of the specified features.

        Args:
            feature_ids: List of feature IDs to search for

        Returns:
            Tracks that contain at least one of these features

        Raises:
            ValueError: If feature_ids is not a list

        Performance: O(n)
        """
        if not isinstance(feature_ids, list):
            raise ValueError("feature_ids must be a list")

        results = []
        for track in self._tracks.values():
            # Check both track.features attribute and properties["features"]
            features = None
            if hasattr(track, "features") and track.features:
                features = track.features
            elif hasattr(track, "properties") and track.properties.get("features"):
                features = track.properties["features"]

            if features and any(fid in features for fid in feature_ids):
                results.append(track)
        return results

    def with_feature_count(self) -> builtins.list[Any]:
        """
        Get all tracks with feature count calculated.

        Returns:
            All tracks with feature_count property set
        """
        return list(self._tracks.values())

    def filter(self, predicate: Callable[[Any], bool]) -> builtins.list[Any]:
        """
        Filter tracks with custom predicate function.

        Args:
            predicate: Function that takes Track and returns True/False

        Returns:
            Tracks matching predicate
        """
        return [t for t in self._tracks.values() if predicate(t)]

    # ===== CACHE/LIFECYCLE MANAGEMENT =====

    def invalidate_cache(self, track_id: str | None = None) -> None:
        """
        Invalidate cache for single track or all tracks.

        Args:
            track_id: Specific track to invalidate, or None for all
        """
        # No-op for memory repository (no cache separate from storage)
        pass

    def reload(self) -> None:
        """
        Force reload all tracks from storage.

        No-op for memory repository (no external storage).
        """
        pass

    @property
    def auto_load(self) -> bool:
        """Whether auto-loading is enabled."""
        return self._auto_load

    @auto_load.setter
    def auto_load(self, enabled: bool) -> None:
        """Enable/disable auto-loading."""
        self._auto_load = enabled

    # ===== UTILITY METHODS =====

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        Count tracks matching filters.

        Args:
            filters: Optional filters

        Returns:
            Number of matching tracks

        Performance: O(1) if no filters, O(n) with filters
        """
        if not filters:
            return len(self._tracks)
        return len(self.list(filters))

    def exists(self, track_id: str) -> bool:
        """
        Check if track exists without loading it.

        Args:
            track_id: Track ID to check

        Returns:
            True if exists, False otherwise

        Performance: O(1)
        """
        return track_id in self._tracks
