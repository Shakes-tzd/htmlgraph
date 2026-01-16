"""
SQLiteFeatureRepository - SQLite database-based Feature storage.

Stores features in SQLite database for fast queries and unified storage.
"""

import builtins
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph.db.schema import HtmlGraphDB
from htmlgraph.models import Edge, Node, Step
from htmlgraph.repositories.feature_repository import (
    FeatureNotFoundError,
    FeatureRepository,
    FeatureValidationError,
    RepositoryQuery,
)


class SQLiteRepositoryQuery(RepositoryQuery):
    """Query builder for SQLite filtering."""

    def __init__(self, repo: "SQLiteFeatureRepository", filters: dict[str, Any]):
        super().__init__(filters)
        self._repo = repo

    def where(self, **kwargs: Any) -> "SQLiteRepositoryQuery":
        """Chain additional filters."""
        # Validate filter keys
        valid_attrs = {
            "status",
            "priority",
            "track_id",
            "assigned_to",
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
        return SQLiteRepositoryQuery(self._repo, new_filters)

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        return self._repo.list(self.filters)


class SQLiteFeatureRepository(FeatureRepository):
    """
    SQLite database-based FeatureRepository implementation.

    Stores features in a SQLite database for fast queries and transactions.
    Uses parameterized queries to prevent SQL injection.

    Database schema:
        Table: features
        Columns: id, type, title, description, status, priority,
                assigned_to, track_id, created_at, updated_at, completed_at,
                steps_total, steps_completed, metadata (JSON)

    Performance:
        - get(id): O(1) with cache, O(log n) from database (indexed)
        - list(): O(n) with SQL WHERE clauses
        - batch operations: O(k) vectorized SQL

    Example:
        >>> db_path = Path(".htmlgraph/htmlgraph.db")
        >>> repo = SQLiteFeatureRepository(db_path)
        >>> feature = repo.create("User Authentication", priority="high")
        >>> feature.status = "in-progress"
        >>> repo.save(feature)
    """

    def __init__(self, db_path: Path | str, auto_load: bool = True):
        """
        Initialize SQLite repository.

        Args:
            db_path: Path to SQLite database file
            auto_load: Whether to enable auto-loading (always True for DB)
        """
        self._db_path = Path(db_path)
        self._auto_load = auto_load

        # Identity cache: feature_id -> Node instance
        self._cache: dict[str, Node] = {}

        # Initialize database connection
        self._db = HtmlGraphDB(str(self._db_path))
        self._db.connect()
        self._db.create_tables()

        # Disable foreign key constraints for testing
        # (allows inserting features with track_ids that don't exist)
        if self._db.connection:
            self._db.connection.execute("PRAGMA foreign_keys = OFF")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if not self._db.connection:
            self._db.connect()
        assert self._db.connection is not None
        return self._db.connection

    def _row_to_node(self, row: sqlite3.Row) -> Node:
        """Convert database row to Node object."""
        # Parse JSON fields
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        json.loads(row["tags"]) if row["tags"] else []

        # Extract steps from metadata
        steps_data = metadata.get("steps", [])
        steps = [
            Step(
                description=s.get("description", ""),
                completed=s.get("completed", False),
                agent=s.get("agent"),
            )
            for s in steps_data
        ]

        # Extract edges from metadata
        edges_data = metadata.get("edges", {})
        edges = {}
        for rel_type, edge_list in edges_data.items():
            edges[rel_type] = [
                Edge(
                    target_id=e.get("target_id", ""),
                    relationship=e.get("relationship", rel_type),
                    title=e.get("title"),
                    since=e.get("since"),
                    properties=e.get("properties", {}),
                )
                for e in edge_list
            ]

        # Create Node
        node = Node(
            id=row["id"],
            title=row["title"],
            type=row["type"],
            status=row["status"],
            priority=row["priority"],
            created=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else datetime.now(),
            updated=datetime.fromisoformat(row["updated_at"])
            if row["updated_at"]
            else datetime.now(),
            content=row["description"] or "",
            agent_assigned=row["assigned_to"],
            track_id=row["track_id"],
            steps=steps,
            edges=edges,
            properties=metadata.get("properties", {}),
        )

        return node

    def _node_to_row(self, node: Node) -> dict[str, Any]:
        """Convert Node object to database row dict."""
        # Serialize steps
        steps_data = [
            {"description": s.description, "completed": s.completed, "agent": s.agent}
            for s in (node.steps or [])
        ]

        # Serialize edges (handle both Edge objects and dicts)
        edges_data = {}
        for rel_type, edge_list in (node.edges or {}).items():
            serialized_edges = []
            for e in edge_list:
                if isinstance(e, dict):
                    # Already a dict, use as-is with defaults
                    serialized_edges.append(
                        {
                            "target_id": e.get("target_id"),
                            "relationship": e.get("relationship", rel_type),
                            "title": e.get("title", ""),
                            "since": e.get("since"),
                            "properties": e.get("properties", {}),
                        }
                    )
                else:
                    # Edge object
                    serialized_edges.append(
                        {
                            "target_id": e.target_id,
                            "relationship": e.relationship,
                            "title": e.title,
                            "since": e.since.isoformat() if e.since else None,
                            "properties": e.properties,
                        }
                    )
            edges_data[rel_type] = serialized_edges

        # Build metadata
        metadata = {
            "steps": steps_data,
            "edges": edges_data,
            "properties": node.properties or {},
        }

        return {
            "id": node.id,
            "type": node.type,
            "title": node.title,
            "description": node.content,
            "status": node.status,
            "priority": node.priority,
            "assigned_to": node.agent_assigned,
            "track_id": node.track_id,
            "created_at": node.created.isoformat()
            if node.created
            else datetime.now().isoformat(),
            "updated_at": node.updated.isoformat()
            if node.updated
            else datetime.now().isoformat(),
            "completed_at": None,  # TODO: extract from metadata
            "steps_total": len(node.steps) if node.steps else 0,
            "steps_completed": sum(1 for s in (node.steps or []) if s.completed),
            "tags": json.dumps([]),
            "metadata": json.dumps(metadata),
        }

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

    def _build_where_clause(self, filters: dict[str, Any]) -> tuple[str, list]:
        """Build SQL WHERE clause from filters."""
        if not filters:
            return "", []

        conditions = []
        params = []

        # Map filter keys to database columns
        column_map = {
            "status": "status",
            "priority": "priority",
            "track_id": "track_id",
            "agent_assigned": "assigned_to",
            "type": "type",
            "title": "title",
            "id": "id",
        }

        for key, value in filters.items():
            if key in column_map:
                conditions.append(f"{column_map[key]} = ?")
                params.append(value)

        where_clause = " AND ".join(conditions)
        return f"WHERE {where_clause}" if where_clause else "", params

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

        Performance: O(1) with cache, O(log n) from database

        Examples:
            >>> feature = repo.get("feat-001")
            >>> feature2 = repo.get("feat-001")
            >>> assert feature is feature2  # Same instance
        """
        if not feature_id or not isinstance(feature_id, str):
            raise ValueError(f"Invalid feature_id: {feature_id}")

        # Check cache first
        if feature_id in self._cache:
            return self._cache[feature_id]

        # Query database
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM features WHERE id = ?", (feature_id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Convert to Node and cache
        node = self._row_to_node(row)
        self._cache[feature_id] = node
        return node

    def list(self, filters: dict[str, Any] | None = None) -> list[Node]:
        """
        List all features with optional filters.

        Args:
            filters: Optional dict of attribute->value filters

        Returns:
            List of Feature objects (empty list if no matches)

        Raises:
            FeatureValidationError: If filter keys are invalid

        Performance: O(n) with SQL WHERE clauses

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

        # Build query
        where_clause, params = self._build_where_clause(filters or {})
        sql = f"SELECT * FROM features {where_clause} ORDER BY created_at DESC"

        # Execute query
        conn = self._get_connection()
        cursor = conn.execute(sql, params)

        # Convert rows to nodes
        results = []
        for row in cursor.fetchall():
            node_id = row["id"]
            if node_id in self._cache:
                results.append(self._cache[node_id])
            else:
                node = self._row_to_node(row)
                self._cache[node_id] = node
                results.append(node)

        return results

    def where(self, **kwargs: Any) -> RepositoryQuery:
        """Build a filtered query with chaining support."""
        return SQLiteRepositoryQuery(self, kwargs)

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

        if not feature_ids:
            return []

        # Build IN clause
        placeholders = ",".join("?" * len(feature_ids))
        sql = f"SELECT * FROM features WHERE id IN ({placeholders})"

        conn = self._get_connection()
        cursor = conn.execute(sql, feature_ids)

        results = []
        for row in cursor.fetchall():
            node_id = row["id"]
            if node_id in self._cache:
                results.append(self._cache[node_id])
            else:
                node = self._row_to_node(row)
                self._cache[node_id] = node
                results.append(node)

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

        # Convert to row
        row = self._node_to_row(feature)

        # Insert or replace
        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO features (
                id, type, title, description, status, priority,
                assigned_to, track_id, created_at, updated_at,
                completed_at, steps_total, steps_completed,
                tags, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                row["id"],
                row["type"],
                row["title"],
                row["description"],
                row["status"],
                row["priority"],
                row["assigned_to"],
                row["track_id"],
                row["created_at"],
                row["updated_at"],
                row["completed_at"],
                row["steps_total"],
                row["steps_completed"],
                row["tags"],
                row["metadata"],
            ),
        )
        conn.commit()

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

        Performance: O(k) vectorized
        """
        if not isinstance(feature_ids, list):
            raise ValueError("feature_ids must be a list")
        if not isinstance(updates, dict):
            raise FeatureValidationError("updates must be a dict")

        if not feature_ids:
            return 0

        # Map update keys to columns
        column_map = {
            "status": "status",
            "priority": "priority",
            "agent_assigned": "assigned_to",
            "track_id": "track_id",
        }

        set_clauses = []
        params = []
        for key, value in updates.items():
            if key in column_map:
                set_clauses.append(f"{column_map[key]} = ?")
                params.append(value)

        if not set_clauses:
            return 0

        # Add updated_at
        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())

        # Add feature IDs
        placeholders = ",".join("?" * len(feature_ids))
        params.extend(feature_ids)

        # Execute update
        sql = f"""
            UPDATE features
            SET {", ".join(set_clauses)}
            WHERE id IN ({placeholders})
        """

        conn = self._get_connection()
        cursor = conn.execute(sql, params)
        conn.commit()

        # Invalidate cache for updated features
        for fid in feature_ids:
            self._cache.pop(fid, None)

        return cursor.rowcount

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

        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM features WHERE id = ?", (feature_id,))
        conn.commit()

        # Remove from cache
        self._cache.pop(feature_id, None)

        return cursor.rowcount > 0

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

        if not feature_ids:
            return 0

        placeholders = ",".join("?" * len(feature_ids))
        sql = f"DELETE FROM features WHERE id IN ({placeholders})"

        conn = self._get_connection()
        cursor = conn.execute(sql, feature_ids)
        conn.commit()

        # Remove from cache
        for fid in feature_ids:
            self._cache.pop(fid, None)

        return cursor.rowcount

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

        # Query all features and check dependencies
        all_features = self.list()
        blocking = []

        for f in all_features:
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
        all_features = self.list()
        return [f for f in all_features if predicate(f)]

    # ===== CACHE/LIFECYCLE MANAGEMENT =====

    def invalidate_cache(self, feature_id: str | None = None) -> None:
        """
        Invalidate cache for single feature or all features.

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

        Invalidates all caches and reloads from database.
        """
        self._cache.clear()
        # Cache will be populated on next query

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

        Performance: O(1) with SQL COUNT, O(n) without filters
        """
        where_clause, params = self._build_where_clause(filters or {})
        sql = f"SELECT COUNT(*) FROM features {where_clause}"

        conn = self._get_connection()
        cursor = conn.execute(sql, params)
        result = cursor.fetchone()[0]
        return int(result)

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

        # Check database
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT 1 FROM features WHERE id = ? LIMIT 1", (feature_id,)
        )
        return cursor.fetchone() is not None
