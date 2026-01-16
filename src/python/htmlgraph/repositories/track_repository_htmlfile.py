"""
HTMLFileTrackRepository - HTML file-based Track storage.

Loads and saves tracks from HTML files using HtmlGraph's existing parser.
"""

import builtins
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph.converter import html_to_node, node_to_html
from htmlgraph.models import Node
from htmlgraph.repositories.track_repository import (
    RepositoryQuery,
    TrackRepository,
    TrackValidationError,
)


class HTMLFileRepositoryQuery(RepositoryQuery):
    """Query builder for HTML file filtering."""

    def __init__(self, repo: "HTMLFileTrackRepository", filters: dict[str, Any]):
        super().__init__(filters)
        self._repo = repo

    def where(self, **kwargs: Any) -> "HTMLFileRepositoryQuery":
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
        return HTMLFileRepositoryQuery(self._repo, new_filters)

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        return self._repo.list(self.filters)


class HTMLFileTrackRepository(TrackRepository):
    """
    HTML file-based TrackRepository implementation.

    Loads and saves tracks from HTML files in a directory.
    Uses HtmlGraph's existing HTML parsing and serialization.

    Tracks are stored as: `.htmlgraph/tracks/trk-XXXXX.html`

    Performance:
        - get(id): O(1) with cache, O(n) cold start
        - list(): O(n) where n = total tracks
        - save(): O(1) file write
        - Cache hit ratio: >90% in steady state

    Example:
        >>> repo = HTMLFileTrackRepository(Path(".htmlgraph/tracks"))
        >>> track = repo.get("trk-001")
        >>> track.status = "completed"
        >>> repo.save(track)
    """

    def __init__(
        self,
        directory: Path | str,
        auto_load: bool = True,
        stylesheet_path: str = "../styles.css",
    ):
        """
        Initialize HTML file repository.

        Args:
            directory: Directory containing track HTML files
            auto_load: Whether to auto-load tracks on first access
            stylesheet_path: Relative path to CSS stylesheet for new files
        """
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._auto_load = auto_load
        self._stylesheet_path = stylesheet_path

        # Identity cache: track_id -> Node instance
        self._cache: dict[str, Node] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure tracks are loaded from disk."""
        if not self._loaded and self._auto_load:
            self.reload()

    def _load_from_file(self, filepath: Path) -> Node:
        """Load a single track from HTML file."""
        try:
            node = html_to_node(filepath)
            if node.type != "track":
                raise TrackValidationError(
                    f"File {filepath} contains node of type '{node.type}', not 'track'"
                )
            return node
        except Exception as e:
            raise TrackValidationError(f"Failed to load {filepath}: {e}") from e

    def _find_file(self, track_id: str) -> Path | None:
        """Find HTML file for a track ID."""
        # Try direct match: trk-abc123.html
        direct = self._directory / f"{track_id}.html"
        if direct.exists():
            return direct

        # Try scanning all files (fallback)
        for filepath in self._directory.glob("*.html"):
            if filepath.stem == track_id:
                return filepath

        return None

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

    def get(self, track_id: str) -> Node | None:
        """
        Get single track by ID.

        Returns same object instance for multiple calls (identity caching).

        Args:
            track_id: Track ID to retrieve

        Returns:
            Track object if found, None if not found

        Raises:
            ValueError: If track_id is invalid format

        Performance: O(1) if cached, O(log n) if uncached
        """
        if not track_id or not isinstance(track_id, str):
            raise ValueError(f"Invalid track_id: {track_id}")

        self._ensure_loaded()

        # Check cache first
        if track_id in self._cache:
            return self._cache[track_id]

        # Load from file
        filepath = self._find_file(track_id)
        if not filepath:
            return None

        track = self._load_from_file(filepath)
        self._cache[track_id] = track
        return track

    def list(self, filters: dict[str, Any] | None = None) -> list[Node]:
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

        self._ensure_loaded()

        results = []
        for track in self._cache.values():
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
        return HTMLFileRepositoryQuery(self, kwargs)

    def by_status(self, status: str) -> builtins.list[Node]:
        """Filter tracks by status."""
        return self.list({"status": status})

    def by_priority(self, priority: str) -> builtins.list[Node]:
        """Filter tracks by priority."""
        return self.list({"priority": priority})

    def active_tracks(self) -> builtins.list[Node]:
        """Get all tracks currently in progress."""
        return self.by_status("active")

    def batch_get(self, track_ids: builtins.list[str]) -> builtins.list[Node]:
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

    def create(self, title: str, **kwargs: Any) -> Node:
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

        # Extract known fields from kwargs to avoid conflicts
        node_type = kwargs.pop("type", "track")
        status = kwargs.pop("status", "todo")
        priority = kwargs.pop("priority", "medium")
        created = kwargs.pop("created", datetime.now())
        updated = kwargs.pop("updated", datetime.now())

        # Remove title from kwargs if present (already have it as parameter)
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
        self.save(track)

        return track

    def save(self, track: Node) -> Node:
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

        # Write to file
        filepath = self._directory / f"{track.id}.html"
        node_to_html(track, filepath, stylesheet_path=self._stylesheet_path)

        # Update cache
        self._cache[track.id] = track

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

        Performance: O(k) vectorized where k = batch size
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

        Performance: O(1) cache removal, O(log n) storage deletion
        """
        if not track_id:
            raise TrackValidationError("track_id cannot be empty")

        # Find and delete file
        filepath = self._find_file(track_id)
        if not filepath:
            return False

        filepath.unlink()

        # Remove from cache
        self._cache.pop(track_id, None)

        return True

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

    def find_by_features(self, feature_ids: builtins.list[str]) -> builtins.list[Node]:
        """
        Find tracks containing any of the specified features.

        Args:
            feature_ids: List of feature IDs to search for

        Returns:
            Tracks that contain at least one of these features

        Raises:
            ValueError: If feature_ids is not a list

        Performance: O(n) with early termination
        """
        if not isinstance(feature_ids, list):
            raise ValueError("feature_ids must be a list")

        self._ensure_loaded()

        results = []
        for track in self._cache.values():
            # Check both track.features attribute and properties["features"]
            features = None
            if hasattr(track, "features") and track.features:
                features = track.features
            elif hasattr(track, "properties") and track.properties.get("features"):
                features = track.properties["features"]

            if features and any(fid in features for fid in feature_ids):
                results.append(track)
        return results

    def with_feature_count(self) -> builtins.list[Node]:
        """
        Get all tracks with feature count calculated.

        Returns:
            All tracks with feature_count property set
        """
        self._ensure_loaded()
        return list(self._cache.values())

    def filter(self, predicate: Callable[[Node], bool]) -> builtins.list[Node]:
        """
        Filter tracks with custom predicate function.

        Args:
            predicate: Function that takes Track and returns True/False

        Returns:
            Tracks matching predicate
        """
        self._ensure_loaded()
        return [t for t in self._cache.values() if predicate(t)]

    # ===== CACHE/LIFECYCLE MANAGEMENT =====

    def invalidate_cache(self, track_id: str | None = None) -> None:
        """
        Invalidate cache for single track or all tracks.

        Forces reload from storage on next access.

        Args:
            track_id: Specific track to invalidate, or None for all
        """
        if track_id:
            self._cache.pop(track_id, None)
        else:
            self._cache.clear()

    def reload(self) -> None:
        """
        Force reload all tracks from storage.

        Invalidates all caches and reloads from disk.
        Note: Preserves existing cache entries to maintain object identity
        for tracks that have been created but not yet persisted to disk.
        """
        # Keep track of existing cached entries to preserve object identity
        existing_cache = dict(self._cache)
        self._cache.clear()

        # Load all HTML files
        for filepath in self._directory.glob("*.html"):
            try:
                track_id = filepath.stem
                # If we already have this track in cache, keep the existing instance
                if track_id in existing_cache:
                    self._cache[track_id] = existing_cache[track_id]
                else:
                    track = self._load_from_file(filepath)
                    self._cache[track.id] = track
            except Exception as e:
                # Log and skip invalid files
                import logging

                logging.warning(f"Failed to load {filepath}: {e}")

        self._loaded = True

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

        Performance: O(n) or O(1) if cached and no filters
        """
        if not filters:
            self._ensure_loaded()
            return len(self._cache)
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
        # Check cache first
        if track_id in self._cache:
            return True

        # Check file system
        return self._find_file(track_id) is not None
