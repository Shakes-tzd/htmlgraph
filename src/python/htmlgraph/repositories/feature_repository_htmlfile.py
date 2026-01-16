"""
HTMLFileFeatureRepository - HTML file-based Feature storage.

Loads and saves features from HTML files using HtmlGraph's existing parser.
"""

import builtins
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph.converter import html_to_node, node_to_html
from htmlgraph.models import Node
from htmlgraph.repositories.feature_repository import (
    FeatureNotFoundError,
    FeatureRepository,
    FeatureValidationError,
    RepositoryQuery,
)


class HTMLFileRepositoryQuery(RepositoryQuery):
    """Query builder for HTML file filtering."""

    def __init__(self, repo: "HTMLFileFeatureRepository", filters: dict[str, Any]):
        super().__init__(filters)
        self._repo = repo

    def where(self, **kwargs: Any) -> "HTMLFileRepositoryQuery":
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
        return HTMLFileRepositoryQuery(self._repo, new_filters)

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        return self._repo.list(self.filters)


class HTMLFileFeatureRepository(FeatureRepository):
    """
    HTML file-based FeatureRepository implementation.

    Loads and saves features from HTML files in a directory.
    Uses HtmlGraph's existing HTML parsing and serialization.

    Features are stored as: `.htmlgraph/features/feat-XXXXX.html`

    Performance:
        - get(id): O(1) with cache, O(n) cold start
        - list(): O(n) where n = total features
        - save(): O(1) file write
        - Cache hit ratio: >90% in steady state

    Example:
        >>> repo = HTMLFileFeatureRepository(Path(".htmlgraph/features"))
        >>> feature = repo.get("feat-001")
        >>> feature.status = "done"
        >>> repo.save(feature)
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
            directory: Directory containing feature HTML files
            auto_load: Whether to auto-load features on first access
            stylesheet_path: Relative path to CSS stylesheet for new files
        """
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._auto_load = auto_load
        self._stylesheet_path = stylesheet_path

        # Identity cache: feature_id -> Node instance
        self._cache: dict[str, Node] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure features are loaded from disk."""
        if not self._loaded and self._auto_load:
            self.reload()

    def _load_from_file(self, filepath: Path) -> Node:
        """Load a single feature from HTML file."""
        try:
            node = html_to_node(filepath)
            if node.type != "feature":
                raise FeatureValidationError(
                    f"File {filepath} contains node of type '{node.type}', not 'feature'"
                )
            return node
        except Exception as e:
            raise FeatureValidationError(f"Failed to load {filepath}: {e}") from e

    def _find_file(self, feature_id: str) -> Path | None:
        """Find HTML file for a feature ID."""
        # Try direct match: feat-abc123.html
        direct = self._directory / f"{feature_id}.html"
        if direct.exists():
            return direct

        # Try scanning all files (fallback)
        for filepath in self._directory.glob("*.html"):
            if filepath.stem == feature_id:
                return filepath

        return None

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

        Performance: O(1) with cache, O(log n) without cache

        Examples:
            >>> feature = repo.get("feat-001")
            >>> feature2 = repo.get("feat-001")
            >>> assert feature is feature2  # Same instance
        """
        if not feature_id or not isinstance(feature_id, str):
            raise ValueError(f"Invalid feature_id: {feature_id}")

        self._ensure_loaded()

        # Check cache first
        if feature_id in self._cache:
            return self._cache[feature_id]

        # Load from file
        filepath = self._find_file(feature_id)
        if not filepath:
            return None

        feature = self._load_from_file(filepath)
        self._cache[feature_id] = feature
        return feature

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

        self._ensure_loaded()

        results = []
        for feature in self._cache.values():
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
        return HTMLFileRepositoryQuery(self, kwargs)

    def by_track(self, track_id: str) -> builtins.list[Node]:
        """Get all features belonging to a track."""
        if not track_id:
            raise ValueError("track_id cannot be empty")
        return self.list({"track_id": track_id})

    def by_status(self, status: str) -> builtins.list[Node]:
        """Filter features by status."""
        return self.list({"status": status})

    def by_priority(self, priority: str) -> builtins.list[Node]:
        """Filter features by priority."""
        return self.list({"priority": priority})

    def by_assigned_to(self, agent: str) -> builtins.list[Node]:
        """Get features assigned to an agent."""
        return self.list({"agent_assigned": agent})

    def batch_get(self, feature_ids: builtins.list[str]) -> builtins.list[Node]:
        """
        Bulk retrieve multiple features.

        Args:
            feature_ids: List of feature IDs

        Returns:
            List of found features

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

        # Validate and save
        self._validate_feature(feature)
        self.save(feature)

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

        # Write to file
        filepath = self._directory / f"{feature.id}.html"
        node_to_html(feature, filepath, stylesheet_path=self._stylesheet_path)

        # Update cache
        self._cache[feature.id] = feature

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
                self.save(feature)
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

        # Find and delete file
        filepath = self._find_file(feature_id)
        if not filepath:
            return False

        filepath.unlink()

        # Remove from cache
        self._cache.pop(feature_id, None)

        return True

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

        self._ensure_loaded()

        blocking = []
        for f in self._cache.values():
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
        self._ensure_loaded()
        return [f for f in self._cache.values() if predicate(f)]

    # ===== CACHE/LIFECYCLE MANAGEMENT =====

    def invalidate_cache(self, feature_id: str | None = None) -> None:
        """
        Invalidate cache for single feature or all features.

        Forces reload from storage on next access.

        Args:
            feature_id: Specific feature to invalidate, or None for all
        """
        if feature_id:
            self._cache.pop(feature_id, None)
        else:
            self._cache.clear()

    def reload(self) -> None:
        """
        Force reload all features from storage.

        Invalidates all caches and reloads from disk.
        Note: Preserves existing cache entries to maintain object identity
        for features that have been created but not yet persisted to disk.
        """
        # Keep track of existing cached entries to preserve object identity
        existing_cache = dict(self._cache)
        self._cache.clear()

        # Load all HTML files
        for filepath in self._directory.glob("*.html"):
            try:
                feature_id = filepath.stem
                # If we already have this feature in cache, keep the existing instance
                if feature_id in existing_cache:
                    self._cache[feature_id] = existing_cache[feature_id]
                else:
                    feature = self._load_from_file(filepath)
                    self._cache[feature.id] = feature
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
        Count features matching filters.

        Args:
            filters: Optional filters

        Returns:
            Number of matching features

        Performance: O(n) or O(1) if cached and no filters
        """
        if not filters:
            self._ensure_loaded()
            return len(self._cache)
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
        # Check cache first
        if feature_id in self._cache:
            return True

        # Check file system
        return self._find_file(feature_id) is not None
