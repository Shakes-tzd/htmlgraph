"""
FeatureRepository - Abstract interface for Feature data access.

Unifies all data access patterns for Features across HtmlGraph.
Implementations handle:
- HTML file storage + SQLite database
- Lazy loading and caching
- Query building and filtering
- Concurrent access safety
- Event logging and session tracking

All implementations MUST pass FeatureRepositoryComplianceTests.
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
        repo.where(status='todo').where(priority='high').execute()
    """

    filters: dict[str, Any]

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        raise NotImplementedError("Subclass must implement")


class FeatureRepositoryError(Exception):
    """Base exception for repository operations."""

    pass


class FeatureNotFoundError(FeatureRepositoryError):
    """Raised when a feature is not found."""

    def __init__(self, feature_id: str):
        self.feature_id = feature_id
        super().__init__(f"Feature not found: {feature_id}")


class FeatureValidationError(FeatureRepositoryError):
    """Raised when feature data fails validation."""

    pass


class FeatureConcurrencyError(FeatureRepositoryError):
    """Raised when concurrent modification detected."""

    pass


class FeatureRepository(ABC):
    """
    Abstract interface for Feature data access.

    Unifies access to Features stored in HTML files and SQLite database.

    CONTRACT:
    1. **Identity Invariant**: get(id) returns same object instance for same feature
    2. **Atomicity**: write operations are atomic (all-or-nothing)
    3. **Consistency**: cache stays in sync with storage
    4. **Isolation**: concurrent operations don't corrupt state
    5. **Error Handling**: all errors preserve full context

    CACHING BEHAVIOR:
    - Single object instances per feature (identity, not just equality)
    - Automatic cache invalidation on writes
    - Optional auto-load on first access

    PERFORMANCE:
    - get(id): O(1) cached, O(log n) uncached
    - list(): O(n) where n = features
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
    def get(self, feature_id: str) -> Any | None:
        """
        Get single feature by ID.

        Returns same object instance for multiple calls with same ID.
        Implements identity caching (is, not ==).

        Args:
            feature_id: Feature ID to retrieve (e.g., "feat-abc123")

        Returns:
            Feature object if found, None if not found

        Raises:
            ValueError: If feature_id is invalid format

        Performance: O(1) if cached, O(log n) if uncached

        Examples:
            >>> feature = repo.get("feat-001")
            >>> feature2 = repo.get("feat-001")
            >>> assert feature is feature2  # Identity, not just equality
            >>> assert feature is not None
        """
        ...

    @abstractmethod
    def list(self, filters: dict[str, Any] | None = None) -> list[Any]:
        """
        List all features with optional filters.

        Returns empty list if no matches, never None.

        Args:
            filters: Optional dict of attribute->value filters.
                    Empty/None dict means no filters (returns all).

        Returns:
            List of Feature objects (empty list if no matches)

        Raises:
            FeatureValidationError: If filter keys are invalid

        Performance: O(n) where n = total features

        Examples:
            >>> all_features = repo.list()
            >>> assert isinstance(all_features, list)
            >>> todo_features = repo.list({"status": "todo"})
            >>> multiple = repo.list({"status": "todo", "priority": "high"})
        """
        ...

    @abstractmethod
    def where(self, **kwargs: Any) -> RepositoryQuery:
        """
        Build a filtered query with chaining support.

        Supports method chaining for composable queries:
            repo.where(status='todo').where(priority='high').execute()

        Args:
            **kwargs: Attribute->value filter pairs.
                     Common: status, priority, assigned_to, track_id

        Returns:
            RepositoryQuery object that can be further filtered or executed

        Raises:
            FeatureValidationError: If invalid attribute names

        Examples:
            >>> query = repo.where(status='todo')
            >>> query2 = query.where(priority='high')  # Chaining
            >>> results = query2.execute()
            >>> assert all(f.status == 'todo' for f in results)
            >>> assert all(f.priority == 'high' for f in results)
        """
        ...

    @abstractmethod
    def by_track(self, track_id: str) -> builtins.list[Any]:
        """
        Get all features belonging to a track.

        Args:
            track_id: Track ID to filter by

        Returns:
            List of features in track (empty if track has no features)

        Raises:
            ValueError: If track_id is invalid format

        Performance: O(n) with early termination on match

        Examples:
            >>> features = repo.by_track("track-planning")
            >>> assert all(f.track_id == "track-planning" for f in features)
        """
        ...

    @abstractmethod
    def by_status(self, status: str) -> builtins.list[Any]:
        """
        Filter features by status.

        Args:
            status: Status to filter by (e.g., 'todo', 'in-progress', 'done')

        Returns:
            List of matching features (empty if no matches)

        Performance: O(n) with early termination

        Examples:
            >>> done_features = repo.by_status("done")
            >>> active = repo.by_status("in-progress")
        """
        ...

    @abstractmethod
    def by_priority(self, priority: str) -> builtins.list[Any]:
        """
        Filter features by priority.

        Args:
            priority: Priority level (e.g., 'low', 'medium', 'high', 'critical')

        Returns:
            List of matching features

        Performance: O(n)

        Examples:
            >>> critical = repo.by_priority("critical")
            >>> important = repo.by_priority("high")
        """
        ...

    @abstractmethod
    def by_assigned_to(self, agent: str) -> builtins.list[Any]:
        """
        Get features assigned to an agent.

        Args:
            agent: Agent ID (e.g., 'claude', 'gpt4')

        Returns:
            Features assigned to agent

        Examples:
            >>> my_work = repo.by_assigned_to("claude")
        """
        ...

    @abstractmethod
    def batch_get(self, feature_ids: builtins.list[str]) -> builtins.list[Any]:
        """
        Bulk retrieve multiple features.

        More efficient than multiple get() calls (vectorized).
        Returns partial results if some features not found.

        Args:
            feature_ids: List of feature IDs

        Returns:
            List of found features (in order of input, with None for missing)
            or list of only found features (implementation-dependent)

        Raises:
            ValueError: If feature_ids is not a list

        Performance: O(k) where k = batch size

        Examples:
            >>> ids = ["feat-001", "feat-002", "feat-003"]
            >>> features = repo.batch_get(ids)
            >>> assert len(features) <= len(ids)
        """
        ...

    # ===== WRITE OPERATIONS =====

    @abstractmethod
    def create(self, title: str, **kwargs: Any) -> Any:
        """
        Create new feature.

        Generates ID if not provided.
        Saves to storage immediately.

        Args:
            title: Feature title (required)
            **kwargs: Additional properties (priority, status, track_id, etc.)

        Returns:
            Created Feature object (with generated ID)

        Raises:
            FeatureValidationError: If invalid data provided
            FeatureRepositoryError: If create fails

        Performance: O(1) cached write

        Examples:
            >>> feature = repo.create("User Authentication")
            >>> assert feature.id is not None
            >>> feature2 = repo.create("API Rate Limiting", priority="high")
        """
        ...

    @abstractmethod
    def save(self, feature: Any) -> Any:
        """
        Save existing feature (update or insert).

        If feature.id exists in repo, updates. Otherwise inserts.

        Args:
            feature: Feature object to save

        Returns:
            Saved feature (same instance)

        Raises:
            FeatureValidationError: If feature is invalid
            FeatureConcurrencyError: If feature was modified elsewhere

        Performance: O(1)

        Examples:
            >>> feature = repo.get("feat-001")
            >>> feature.status = "in-progress"
            >>> repo.save(feature)
        """
        ...

    @abstractmethod
    def batch_update(
        self, feature_ids: builtins.list[str], updates: dict[str, Any]
    ) -> int:
        """
        Vectorized batch update operation.

        Updates all specified features with same values.
        More efficient than individual saves.

        Args:
            feature_ids: List of feature IDs to update
            updates: Dict of attribute->value to set

        Returns:
            Number of features successfully updated

        Raises:
            FeatureValidationError: If invalid updates

        Performance: O(k) vectorized where k = batch size

        Examples:
            >>> count = repo.batch_update(
            ...     ["feat-1", "feat-2", "feat-3"],
            ...     {"status": "done", "priority": "low"}
            ... )
            >>> assert count == 3
        """
        ...

    @abstractmethod
    def delete(self, feature_id: str) -> bool:
        """
        Delete a feature by ID.

        Args:
            feature_id: Feature ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            FeatureValidationError: If feature_id invalid

        Performance: O(1) cache removal, O(log n) storage deletion

        Examples:
            >>> success = repo.delete("feat-001")
            >>> assert success is True or success is False
        """
        ...

    @abstractmethod
    def batch_delete(self, feature_ids: builtins.list[str]) -> int:
        """
        Delete multiple features.

        Args:
            feature_ids: List of feature IDs to delete

        Returns:
            Number of features successfully deleted

        Raises:
            ValueError: If feature_ids not a list

        Performance: O(k) where k = batch size

        Examples:
            >>> count = repo.batch_delete(["feat-1", "feat-2"])
            >>> assert count == 2
        """
        ...

    # ===== ADVANCED QUERIES =====

    @abstractmethod
    def find_dependencies(self, feature_id: str) -> builtins.list[Any]:
        """
        Find transitive feature dependencies.

        Returns features that MUST be completed before given feature.
        Traverses dependency graph to find all transitive deps.

        Args:
            feature_id: Feature to find dependencies for

        Returns:
            List of features this feature depends on (transitive closure)

        Raises:
            FeatureNotFoundError: If feature not found

        Performance: O(n) graph traversal

        Examples:
            >>> deps = repo.find_dependencies("feat-auth")
            >>> # Returns all features that must be done before auth
            >>> assert all(f.id != "feat-auth" for f in deps)
        """
        ...

    @abstractmethod
    def find_blocking(self, feature_id: str) -> builtins.list[Any]:
        """
        Find what blocks this feature.

        Inverse of dependencies: features that depend ON this feature.
        Returns features blocked by given feature.

        Args:
            feature_id: Feature to find blockers for

        Returns:
            Features that depend on this feature

        Raises:
            FeatureNotFoundError: If feature not found

        Examples:
            >>> blockers = repo.find_blocking("feat-database-migration")
            >>> # Returns all features waiting on this one
        """
        ...

    @abstractmethod
    def filter(self, predicate: Callable[[Any], bool]) -> builtins.list[Any]:
        """
        Filter features with custom predicate function.

        For complex queries not covered by standard filters.

        Args:
            predicate: Function that takes Feature and returns True/False

        Returns:
            Features matching predicate

        Examples:
            >>> recent = repo.filter(
            ...     lambda f: (datetime.now() - f.created).days < 7
            ... )
            >>> contains_auth = repo.filter(
            ...     lambda f: "auth" in f.title.lower()
            ... )
        """
        ...

    # ===== CACHE/LIFECYCLE MANAGEMENT =====

    @abstractmethod
    def invalidate_cache(self, feature_id: str | None = None) -> None:
        """
        Invalidate cache for single feature or all features.

        Forces reload from storage on next access.
        Used when external process modifies storage.

        Args:
            feature_id: Specific feature to invalidate, or None for all

        Examples:
            >>> repo.invalidate_cache("feat-001")  # Single feature
            >>> repo.invalidate_cache()  # Clear entire cache
        """
        ...

    @abstractmethod
    def reload(self) -> None:
        """
        Force reload all features from storage.

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

        If True, features auto-load on first access.
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
        Count features matching filters.

        Args:
            filters: Optional filters (same as list())

        Returns:
            Number of matching features

        Performance: O(n) or O(1) if optimized with SQL count

        Examples:
            >>> total = repo.count()
            >>> todo_count = repo.count({"status": "todo"})
        """
        ...

    @abstractmethod
    def exists(self, feature_id: str) -> bool:
        """
        Check if feature exists without loading it.

        Args:
            feature_id: Feature ID to check

        Returns:
            True if exists, False otherwise

        Performance: O(1) if optimized

        Examples:
            >>> if repo.exists("feat-001"):
            ...     feature = repo.get("feat-001")
        """
        ...
