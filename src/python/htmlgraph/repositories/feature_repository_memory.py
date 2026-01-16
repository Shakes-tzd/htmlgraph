"""
MemoryFeatureRepository - In-memory Feature storage.

Pure in-memory implementation for testing and development.
All operations are O(1) or O(n) with no disk I/O.
"""

import builtins
from collections.abc import Callable
from datetime import datetime
from typing import Any

from htmlgraph.models import Node
from htmlgraph.repositories.feature_repository import (
    FeatureNotFoundError,
    FeatureRepository,
    FeatureValidationError,
    RepositoryQuery,
)


class MemoryRepositoryQuery(RepositoryQuery):
    """Query builder for in-memory filtering."""

    def __init__(self, repo: "MemoryFeatureRepository", filters: dict[str, Any]):
        super().__init__(filters)
        self._repo = repo

    def where(self, **kwargs: Any) -> "MemoryRepositoryQuery":
        """Chain additional filters."""
        # Validate filter keys
        valid_attrs = {
            "status",
            "priority",
            "track_id",
            "agent_assigned",
            "type",
            "title",
            "id",
            "created",
            "updated",
        }
        for key in kwargs:
            if key not in valid_attrs:
                raise FeatureValidationError(f"Invalid filter attribute: {key}")

        # Merge filters
        new_filters = {**self.filters, **kwargs}
        return MemoryRepositoryQuery(self._repo, new_filters)

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        return self._repo.list(self.filters)


class MemoryFeatureRepository(FeatureRepository):
    """
    In-memory FeatureRepository implementation.

    Stores features in a dictionary with identity caching.
    All operations are fast (O(1) or O(n)) with no disk I/O.

    Perfect for testing and development.

    Performance:
        - get(id): O(1)
        - list(): O(n)
        - create/save/delete: O(1)
        - All batch operations: O(k) where k = batch size

    Example:
        >>> repo = MemoryFeatureRepository()
        >>> feature = repo.create("User Authentication", priority="high")
        >>> feature.status = "in-progress"
        >>> repo.save(feature)
        >>> all_features = repo.list()
    """

    def __init__(self, auto_load: bool = True):
        """
        Initialize in-memory repository.

        Args:
            auto_load: Whether to enable auto-loading (always True for memory)
        """
        self._features: dict[str, Node] = {}  # Identity cache
        self._auto_load = auto_load
        self._counter = 0  # For generating IDs

    def _generate_id(self) -> str:
        """Generate unique feature ID."""
        import uuid

        return f"feat-{uuid.uuid4().hex[:8]}"

    def _validate_feature(self, feature: Any) -> None:
        """Validate feature object."""
        if not hasattr(feature, "id"):
            raise FeatureValidationError("Feature must have 'id' attribute")
        if not hasattr(feature, "title"):
            raise FeatureValidationError("Feature must have 'title' attribute")
        if not feature.id or not str(feature.id).strip():
            raise FeatureValidationError("Feature ID cannot be empty")
        if not feature.title or not str(feature.title).strip():
            raise FeatureValidationError("Feature title cannot be empty")

    def _matches_filters(self, feature: Node, filters: dict[str, Any]) -> bool:
        """Check if feature matches all filters."""
        if not filters:
            return True

        for key, value in filters.items():
            if not hasattr(feature, key):
                return False
            if getattr(feature, key) != value:
                return False
        return True

    # ===== READ OPERATIONS =====

    def get(self, feature_id: str) -> Node | None:
        """
        Get single feature by ID.

        Returns same object instance for multiple calls (identity caching).

        Args:
            feature_id: Feature ID to retrieve

        Returns:
            Feature object if found, None if not found

        Raises:
            ValueError: If feature_id is invalid format

        Performance: O(1)

        Examples:
            >>> feature = repo.get("feat-001")
            >>> feature2 = repo.get("feat-001")
            >>> assert feature is feature2  # Same instance
        """
        if not feature_id or not isinstance(feature_id, str):
            raise ValueError(f"Invalid feature_id: {feature_id}")

        return self._features.get(feature_id)

    def list(self, filters: dict[str, Any] | None = None) -> list[Node]:
        """
        List all features with optional filters.

        Args:
            filters: Optional dict of attribute->value filters

        Returns:
            List of Feature objects (empty list if no matches)

        Raises:
            FeatureValidationError: If filter keys are invalid

        Performance: O(n) where n = total features

        Examples:
            >>> all_features = repo.list()
            >>> todo_features = repo.list({"status": "todo"})
        """
        if filters:
            # Validate filter keys
            valid_attrs = {
                "status",
                "priority",
                "track_id",
                "agent_assigned",
                "type",
                "title",
                "id",
                "created",
                "updated",
            }
            for key in filters:
                if key not in valid_attrs:
                    raise FeatureValidationError(f"Invalid filter attribute: {key}")

        results = []
        for feature in self._features.values():
            if self._matches_filters(feature, filters or {}):
                results.append(feature)
        return results

    def where(self, **kwargs: Any) -> RepositoryQuery:
        """
        Build a filtered query with chaining support.

        Args:
            **kwargs: Attribute->value filter pairs

        Returns:
            RepositoryQuery object that can be further filtered

        Raises:
            FeatureValidationError: If invalid attribute names

        Examples:
            >>> query = repo.where(status='todo')
            >>> results = query.where(priority='high').execute()
        """
        return MemoryRepositoryQuery(self, kwargs)

    def by_track(self, track_id: str) -> builtins.list[Node]:
        """
        Get all features belonging to a track.

        Args:
            track_id: Track ID to filter by

        Returns:
            List of features in track

        Performance: O(n)
        """
        if not track_id:
            raise ValueError("track_id cannot be empty")
        return self.list({"track_id": track_id})

    def by_status(self, status: str) -> builtins.list[Node]:
        """
        Filter features by status.

        Args:
            status: Status to filter by

        Returns:
            List of matching features

        Performance: O(n)
        """
        return self.list({"status": status})

    def by_priority(self, priority: str) -> builtins.list[Node]:
        """
        Filter features by priority.

        Args:
            priority: Priority level

        Returns:
            List of matching features

        Performance: O(n)
        """
        return self.list({"priority": priority})

    def by_assigned_to(self, agent: str) -> builtins.list[Node]:
        """
        Get features assigned to an agent.

        Args:
            agent: Agent ID

        Returns:
            Features assigned to agent
        """
        return self.list({"agent_assigned": agent})

    def batch_get(self, feature_ids: builtins.list[str]) -> builtins.list[Node]:
        """
        Bulk retrieve multiple features.

        Args:
            feature_ids: List of feature IDs

        Returns:
            List of found features (None for missing ones omitted)

        Raises:
            ValueError: If feature_ids is not a list

        Performance: O(k) where k = batch size
        """
        if not isinstance(feature_ids, list):
            raise ValueError("feature_ids must be a list")

        results = []
        for fid in feature_ids:
            feature = self.get(fid)
            if feature:
                results.append(feature)
        return results

    # ===== WRITE OPERATIONS =====

    def create(self, title: str, **kwargs: Any) -> Node:
        """
        Create new feature.

        Args:
            title: Feature title (required)
            **kwargs: Additional properties

        Returns:
            Created Feature object (with generated ID)

        Raises:
            FeatureValidationError: If invalid data provided

        Performance: O(1)
        """
        if not title or not title.strip():
            raise FeatureValidationError("Feature title cannot be empty")

        # Generate ID if not provided
        feature_id = kwargs.pop("id", None) or self._generate_id()

        # Extract known fields from kwargs to avoid conflicts
        node_type = kwargs.pop("type", "feature")
        status = kwargs.pop("status", "todo")
        priority = kwargs.pop("priority", "medium")
        created = kwargs.pop("created", datetime.now())
        updated = kwargs.pop("updated", datetime.now())

        # Remove title from kwargs if present (already have it as parameter)
        kwargs.pop("title", None)

        # Create Node object
        feature = Node(
            id=feature_id,
            title=title,
            type=node_type,
            status=status,
            priority=priority,
            created=created,
            updated=updated,
            **kwargs,
        )

        # Validate and store
        self._validate_feature(feature)
        self._features[feature.id] = feature

        return feature

    def save(self, feature: Node) -> Node:
        """
        Save existing feature (update or insert).

        Args:
            feature: Feature object to save

        Returns:
            Saved feature (same instance)

        Raises:
            FeatureValidationError: If feature is invalid

        Performance: O(1)
        """
        self._validate_feature(feature)

        # Update timestamp
        feature.updated = datetime.now()

        # Store (updates existing or inserts new)
        self._features[feature.id] = feature

        return feature

    def batch_update(
        self, feature_ids: builtins.list[str], updates: dict[str, Any]
    ) -> int:
        """
        Vectorized batch update operation.

        Args:
            feature_ids: List of feature IDs to update
            updates: Dict of attribute->value to set

        Returns:
            Number of features successfully updated

        Raises:
            FeatureValidationError: If invalid updates

        Performance: O(k) where k = batch size
        """
        if not isinstance(feature_ids, list):
            raise ValueError("feature_ids must be a list")
        if not isinstance(updates, dict):
            raise FeatureValidationError("updates must be a dict")

        count = 0
        for fid in feature_ids:
            feature = self.get(fid)
            if feature:
                # Apply updates
                for key, value in updates.items():
                    setattr(feature, key, value)
                feature.updated = datetime.now()
                count += 1

        return count

    def delete(self, feature_id: str) -> bool:
        """
        Delete a feature by ID.

        Args:
            feature_id: Feature ID to delete

        Returns:
            True if deleted, False if not found

        Performance: O(1)
        """
        if not feature_id:
            raise FeatureValidationError("feature_id cannot be empty")

        if feature_id in self._features:
            del self._features[feature_id]
            return True
        return False

    def batch_delete(self, feature_ids: builtins.list[str]) -> int:
        """
        Delete multiple features.

        Args:
            feature_ids: List of feature IDs to delete

        Returns:
            Number of features successfully deleted

        Performance: O(k) where k = batch size
        """
        if not isinstance(feature_ids, list):
            raise ValueError("feature_ids must be a list")

        count = 0
        for fid in feature_ids:
            if self.delete(fid):
                count += 1
        return count

    # ===== ADVANCED QUERIES =====

    def find_dependencies(self, feature_id: str) -> builtins.list[Node]:
        """
        Find transitive feature dependencies.

        Args:
            feature_id: Feature to find dependencies for

        Returns:
            List of features this feature depends on

        Raises:
            FeatureNotFoundError: If feature not found

        Performance: O(n) graph traversal
        """
        feature = self.get(feature_id)
        if not feature:
            raise FeatureNotFoundError(feature_id)

        dependencies = []
        visited = set()

        def traverse(f: Node) -> None:
            if f.id in visited:
                return
            visited.add(f.id)

            # Check edges for dependencies
            if hasattr(f, "edges") and f.edges:
                depends_on = (
                    f.edges.get("depends_on", []) if isinstance(f.edges, dict) else []
                )
                for edge in depends_on:
                    target_id = (
                        edge.target_id
                        if hasattr(edge, "target_id")
                        else edge.get("target_id")
                        if isinstance(edge, dict)
                        else None
                    )
                    if target_id:
                        dep = self.get(target_id)
                        if dep and dep not in dependencies:
                            dependencies.append(dep)
                            traverse(dep)

        traverse(feature)
        return dependencies

    def find_blocking(self, feature_id: str) -> builtins.list[Node]:
        """
        Find what blocks this feature.

        Args:
            feature_id: Feature to find blockers for

        Returns:
            Features that depend on this feature

        Raises:
            FeatureNotFoundError: If feature not found
        """
        feature = self.get(feature_id)
        if not feature:
            raise FeatureNotFoundError(feature_id)

        blocking = []
        for f in self._features.values():
            if hasattr(f, "edges") and f.edges:
                depends_on = (
                    f.edges.get("depends_on", []) if isinstance(f.edges, dict) else []
                )
                for edge in depends_on:
                    target_id = (
                        edge.target_id
                        if hasattr(edge, "target_id")
                        else edge.get("target_id")
                        if isinstance(edge, dict)
                        else None
                    )
                    if target_id == feature_id:
                        blocking.append(f)

        return blocking

    def filter(self, predicate: Callable[[Node], bool]) -> builtins.list[Node]:
        """
        Filter features with custom predicate function.

        Args:
            predicate: Function that takes Feature and returns True/False

        Returns:
            Features matching predicate
        """
        return [f for f in self._features.values() if predicate(f)]

    # ===== CACHE/LIFECYCLE MANAGEMENT =====

    def invalidate_cache(self, feature_id: str | None = None) -> None:
        """
        Invalidate cache for single feature or all features.

        For memory repository, this is a no-op since we don't have
        external storage to reload from.

        Args:
            feature_id: Specific feature to invalidate, or None for all
        """
        # No-op for memory repository
        pass

    def reload(self) -> None:
        """
        Force reload all features from storage.

        For memory repository, this is a no-op since we don't have
        external storage.
        """
        # No-op for memory repository
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
        Count features matching filters.

        Args:
            filters: Optional filters

        Returns:
            Number of matching features

        Performance: O(n) or O(1) if no filters
        """
        if not filters:
            return len(self._features)
        return len(self.list(filters))

    def exists(self, feature_id: str) -> bool:
        """
        Check if feature exists without loading it.

        Args:
            feature_id: Feature ID to check

        Returns:
            True if exists, False otherwise

        Performance: O(1)
        """
        return feature_id in self._features
