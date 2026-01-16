"""
TrackRepository - Abstract interface for Track data access.

Unifies all data access patterns for Tracks across HtmlGraph.
Implementations handle:
- HTML file storage + SQLite database
- Lazy loading and caching
- Query building and filtering
- Concurrent access safety
- Event logging and session tracking

All implementations MUST pass TrackRepositoryComplianceTests.
"""

import builtins
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class RepositoryQuery:
    """
    Query builder for chaining filters.

    Supports method chaining:
        repo.where(status='active').where(priority='high').execute()
    """

    filters: dict[str, Any]

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        raise NotImplementedError("Subclass must implement")


class TrackRepositoryError(Exception):
    """Base exception for repository operations."""

    pass


class TrackNotFoundError(TrackRepositoryError):
    """Raised when a track is not found."""

    def __init__(self, track_id: str):
        self.track_id = track_id
        super().__init__(f"Track not found: {track_id}")


class TrackValidationError(TrackRepositoryError):
    """Raised when track data fails validation."""

    pass


class TrackConcurrencyError(TrackRepositoryError):
    """Raised when concurrent modification detected."""

    pass


class TrackRepository(ABC):
    """
    Abstract interface for Track data access.

    Unifies access to Tracks stored in HTML files and SQLite database.

    CONTRACT:
    1. **Identity Invariant**: get(id) returns same object instance for same track
    2. **Atomicity**: write operations are atomic (all-or-nothing)
    3. **Consistency**: cache stays in sync with storage
    4. **Isolation**: concurrent operations don't corrupt state
    5. **Error Handling**: all errors preserve full context

    CACHING BEHAVIOR:
    - Single object instances per track (identity, not just equality)
    - Automatic cache invalidation on writes
    - Optional auto-load on first access

    PERFORMANCE:
    - get(id): O(1) cached, O(log n) uncached
    - list(): O(n) where n = tracks
    - where(**kwargs): O(n) with early termination
    - batch_get(): O(k) where k = batch size
    - batch_update(): O(k) vectorized

    THREAD SAFETY:
    - Implementations should be thread-safe
    - Concurrent reads allowed
    - Concurrent writes serialized (via database locks or explicit locking)
    """

    # ===== READ OPERATIONS =====

    @abstractmethod
    def get(self, track_id: str) -> Any | None:
        """
        Get single track by ID.

        Returns same object instance for multiple calls with same ID.
        Implements identity caching (is, not ==).

        Args:
            track_id: Track ID to retrieve (e.g., "track-001")

        Returns:
            Track object if found, None if not found

        Raises:
            ValueError: If track_id is invalid format

        Performance: O(1) if cached, O(log n) if uncached

        Examples:
            >>> track = repo.get("track-001")
            >>> track2 = repo.get("track-001")
            >>> assert track is track2  # Identity, not just equality
            >>> assert track is not None
        """
        ...

    @abstractmethod
    def list(self, filters: dict[str, Any] | None = None) -> list[Any]:
        """
        List all tracks with optional filters.

        Returns empty list if no matches, never None.

        Args:
            filters: Optional dict of attribute->value filters.
                    Empty/None dict means no filters (returns all).

        Returns:
            List of Track objects (empty list if no matches)

        Raises:
            TrackValidationError: If filter keys are invalid

        Performance: O(n) where n = total tracks

        Examples:
            >>> all_tracks = repo.list()
            >>> assert isinstance(all_tracks, list)
            >>> active_tracks = repo.list({"status": "active"})
            >>> multiple = repo.list({"status": "active", "priority": "high"})
        """
        ...

    @abstractmethod
    def where(self, **kwargs: Any) -> RepositoryQuery:
        """
        Build a filtered query with chaining support.

        Supports method chaining for composable queries:
            repo.where(status='active').where(priority='high').execute()

        Args:
            **kwargs: Attribute->value filter pairs.
                     Common: status, priority, has_spec, has_plan

        Returns:
            RepositoryQuery object that can be further filtered or executed

        Raises:
            TrackValidationError: If invalid attribute names

        Examples:
            >>> query = repo.where(status='active')
            >>> query2 = query.where(priority='high')  # Chaining
            >>> results = query2.execute()
            >>> assert all(t.status == 'active' for t in results)
            >>> assert all(t.priority == 'high' for t in results)
        """
        ...

    @abstractmethod
    def by_status(self, status: str) -> builtins.list[Any]:
        """
        Filter tracks by status.

        Args:
            status: Status to filter by (e.g., 'planned', 'active', 'completed', 'abandoned')

        Returns:
            List of matching tracks (empty if no matches)

        Performance: O(n) with early termination

        Examples:
            >>> active_tracks = repo.by_status("active")
            >>> completed = repo.by_status("completed")
        """
        ...

    @abstractmethod
    def by_priority(self, priority: str) -> builtins.list[Any]:
        """
        Filter tracks by priority.

        Args:
            priority: Priority level (e.g., 'low', 'medium', 'high', 'critical')

        Returns:
            List of matching tracks

        Performance: O(n)

        Examples:
            >>> critical = repo.by_priority("critical")
            >>> important = repo.by_priority("high")
        """
        ...

    @abstractmethod
    def active_tracks(self) -> builtins.list[Any]:
        """
        Get all tracks currently in progress.

        Convenience method for status='active' filter.

        Returns:
            List of active tracks

        Performance: O(n) with early termination

        Examples:
            >>> current_work = repo.active_tracks()
            >>> assert all(t.status == 'active' for t in current_work)
        """
        ...

    @abstractmethod
    def batch_get(self, track_ids: builtins.list[str]) -> builtins.list[Any]:
        """
        Bulk retrieve multiple tracks.

        More efficient than multiple get() calls (vectorized).
        Returns partial results if some tracks not found.

        Args:
            track_ids: List of track IDs

        Returns:
            List of found tracks (in order of input, with None for missing)
            or list of only found tracks (implementation-dependent)

        Raises:
            ValueError: If track_ids is not a list

        Performance: O(k) where k = batch size

        Examples:
            >>> ids = ["track-001", "track-002", "track-003"]
            >>> tracks = repo.batch_get(ids)
            >>> assert len(tracks) <= len(ids)
        """
        ...

    # ===== WRITE OPERATIONS =====

    @abstractmethod
    def create(self, title: str, **kwargs: Any) -> Any:
        """
        Create new track.

        Generates ID if not provided.
        Saves to storage immediately.

        Args:
            title: Track title (required)
            **kwargs: Additional properties (priority, status, description, etc.)

        Returns:
            Created Track object (with generated ID)

        Raises:
            TrackValidationError: If invalid data provided
            TrackRepositoryError: If create fails

        Performance: O(1) cached write

        Examples:
            >>> track = repo.create("Planning Phase 1")
            >>> assert track.id is not None
            >>> track2 = repo.create("Feature Development", priority="high", status="active")
        """
        ...

    @abstractmethod
    def save(self, track: Any) -> Any:
        """
        Save existing track (update or insert).

        If track.id exists in repo, updates. Otherwise inserts.

        Args:
            track: Track object to save

        Returns:
            Saved track (same instance)

        Raises:
            TrackValidationError: If track is invalid
            TrackConcurrencyError: If track was modified elsewhere

        Performance: O(1)

        Examples:
            >>> track = repo.get("track-001")
            >>> track.status = "completed"
            >>> repo.save(track)
        """
        ...

    @abstractmethod
    def batch_update(
        self, track_ids: builtins.list[str], updates: dict[str, Any]
    ) -> int:
        """
        Vectorized batch update operation.

        Updates all specified tracks with same values.
        More efficient than individual saves.

        Args:
            track_ids: List of track IDs to update
            updates: Dict of attribute->value to set

        Returns:
            Number of tracks successfully updated

        Raises:
            TrackValidationError: If invalid updates

        Performance: O(k) vectorized where k = batch size

        Examples:
            >>> count = repo.batch_update(
            ...     ["track-1", "track-2", "track-3"],
            ...     {"status": "completed", "priority": "low"}
            ... )
            >>> assert count == 3
        """
        ...

    @abstractmethod
    def delete(self, track_id: str) -> bool:
        """
        Delete a track by ID.

        Args:
            track_id: Track ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            TrackValidationError: If track_id invalid

        Performance: O(1) cache removal, O(log n) storage deletion

        Examples:
            >>> success = repo.delete("track-001")
            >>> assert success is True or success is False
        """
        ...

    @abstractmethod
    def batch_delete(self, track_ids: builtins.list[str]) -> int:
        """
        Delete multiple tracks.

        Args:
            track_ids: List of track IDs to delete

        Returns:
            Number of tracks successfully deleted

        Raises:
            ValueError: If track_ids not a list

        Performance: O(k) where k = batch size

        Examples:
            >>> count = repo.batch_delete(["track-1", "track-2"])
            >>> assert count == 2
        """
        ...

    # ===== ADVANCED QUERIES =====

    @abstractmethod
    def find_by_features(self, feature_ids: builtins.list[str]) -> builtins.list[Any]:
        """
        Find tracks containing any of the specified features.

        Args:
            feature_ids: List of feature IDs to search for

        Returns:
            Tracks that contain at least one of these features

        Raises:
            ValueError: If feature_ids is not a list

        Performance: O(n) with early termination

        Examples:
            >>> features = ["feat-001", "feat-002"]
            >>> tracks = repo.find_by_features(features)
            >>> # Returns all tracks that contain feat-001 or feat-002
        """
        ...

    @abstractmethod
    def with_feature_count(self) -> builtins.list[Any]:
        """
        Get all tracks with feature count calculated.

        Convenience method for calculating feature counts across all tracks.

        Returns:
            All tracks with feature_count property set

        Examples:
            >>> tracks = repo.with_feature_count()
            >>> for t in tracks:
            ...     print(f"{t.title}: {len(t.features)} features")
        """
        ...

    @abstractmethod
    def filter(self, predicate: Callable[[Any], bool]) -> builtins.list[Any]:
        """
        Filter tracks with custom predicate function.

        For complex queries not covered by standard filters.

        Args:
            predicate: Function that takes Track and returns True/False

        Returns:
            Tracks matching predicate

        Examples:
            >>> recent = repo.filter(
            ...     lambda t: (datetime.now() - t.created).days < 7
            ... )
            >>> with_spec_and_plan = repo.filter(
            ...     lambda t: t.has_spec and t.has_plan
            ... )
        """
        ...

    # ===== CACHE/LIFECYCLE MANAGEMENT =====

    @abstractmethod
    def invalidate_cache(self, track_id: str | None = None) -> None:
        """
        Invalidate cache for single track or all tracks.

        Forces reload from storage on next access.
        Used when external process modifies storage.

        Args:
            track_id: Specific track to invalidate, or None for all

        Examples:
            >>> repo.invalidate_cache("track-001")  # Single track
            >>> repo.invalidate_cache()  # Clear entire cache
        """
        ...

    @abstractmethod
    def reload(self) -> None:
        """
        Force reload all tracks from storage.

        Invalidates all caches and reloads from disk/database.
        Useful for external changes or cache reconciliation.

        Examples:
            >>> repo.reload()  # Force refresh from storage
        """
        ...

    @property
    @abstractmethod
    def auto_load(self) -> bool:
        """
        Whether auto-loading is enabled.

        If True, tracks auto-load on first access.
        If False, manual reload() required.

        Returns:
            True if auto-loading enabled, False otherwise
        """
        ...

    @auto_load.setter
    @abstractmethod
    def auto_load(self, enabled: bool) -> None:
        """
        Enable/disable auto-loading.

        Args:
            enabled: True to enable auto-load, False to disable
        """
        ...

    # ===== UTILITY METHODS =====

    @abstractmethod
    def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        Count tracks matching filters.

        Args:
            filters: Optional filters (same as list())

        Returns:
            Number of matching tracks

        Performance: O(n) or O(1) if optimized with SQL count

        Examples:
            >>> total = repo.count()
            >>> active_count = repo.count({"status": "active"})
        """
        ...

    @abstractmethod
    def exists(self, track_id: str) -> bool:
        """
        Check if track exists without loading it.

        Args:
            track_id: Track ID to check

        Returns:
            True if exists, False otherwise

        Performance: O(1) if optimized

        Examples:
            >>> if repo.exists("track-001"):
            ...     track = repo.get("track-001")
        """
        ...
