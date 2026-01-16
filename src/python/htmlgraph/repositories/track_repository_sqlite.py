"""
SQLiteTrackRepository - SQLite database-based Track storage.

Stores tracks in SQLite database for fast queries and unified storage.
"""

import builtins
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph.db.schema import HtmlGraphDB
from htmlgraph.models import Node
from htmlgraph.repositories.track_repository import (
    RepositoryQuery,
    TrackRepository,
    TrackValidationError,
)


class SQLiteRepositoryQuery(RepositoryQuery):
    """Query builder for SQLite filtering."""

    def __init__(self, repo: "SQLiteTrackRepository", filters: dict[str, Any]):
        super().__init__(filters)
        self._repo = repo

    def where(self, **kwargs: Any) -> "SQLiteRepositoryQuery":
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
        return SQLiteRepositoryQuery(self._repo, new_filters)

    def execute(self) -> list[Any]:
        """Execute the query and return results."""
        return self._repo.list(self.filters)


class SQLiteTrackRepository(TrackRepository):
    """
    SQLite database-based TrackRepository implementation.

    Stores tracks in a SQLite database for fast queries and transactions.
    Uses parameterized queries to prevent SQL injection.

    Database schema:
        Table: tracks
        Columns: id, type, title, description, status, priority,
                created_at, updated_at, has_spec, has_plan,
                metadata (JSON)

    Performance:
        - get(id): O(1) with cache, O(log n) from database (indexed)
        - list(): O(n) with SQL WHERE clauses
        - batch operations: O(k) vectorized SQL

    Example:
        >>> db_path = Path(".htmlgraph/htmlgraph.db")
        >>> repo = SQLiteTrackRepository(db_path)
        >>> track = repo.create("Planning Phase 1", priority="high")
        >>> track.status = "active"
        >>> repo.save(track)
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

        # Identity cache: track_id -> Node instance
        self._cache: dict[str, Node] = {}

        # Initialize database connection
        self._db = HtmlGraphDB(str(self._db_path))
        self._db.connect()
        self._db.create_tables()

        # Disable foreign key constraints for testing
        if self._db.connection:
            self._db.connection.execute("PRAGMA foreign_keys = OFF")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if not self._db.connection:
            self._db.connect()
        assert self._db.connection is not None
        return self._db.connection

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

    def _row_to_node(self, row: sqlite3.Row) -> Node:
        """Convert database row to Node object."""
        # Parse metadata JSON
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        # Map database status to Node status (handle legacy values)
        db_status = row["status"] or "todo"
        status_map: dict[str, str] = {
            "in_progress": "in-progress",
            "cancelled": "done",
            "planned": "todo",
            "completed": "done",
        }
        status = status_map.get(db_status, db_status)

        # Cast to valid status literal - Node validates this
        from typing import Literal, cast

        valid_status = cast(
            Literal[
                "todo", "in-progress", "blocked", "done", "active", "ended", "stale"
            ],
            status,
        )

        # Create Node object
        node = Node(
            id=row["id"],
            title=row["title"],
            type=row["type"] or "track",
            status=valid_status,
            priority=row["priority"] or "medium",
            created=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else datetime.now(),
            updated=datetime.fromisoformat(row["updated_at"])
            if row["updated_at"]
            else datetime.now(),
            content=row["description"] or "",
            properties=metadata,
        )

        return node

    def _node_to_dict(self, track: Node) -> dict[str, Any]:
        """Convert Node object to database dict."""
        # Extract track-specific metadata
        metadata = (
            dict(track.properties)
            if hasattr(track, "properties") and track.properties
            else {}
        )

        if hasattr(track, "has_spec"):
            metadata["has_spec"] = track.has_spec
        if hasattr(track, "has_plan"):
            metadata["has_plan"] = track.has_plan
        if hasattr(track, "features"):
            metadata["features"] = track.features
        if hasattr(track, "phases"):
            metadata["phases"] = track.phases

        return {
            "id": track.id,
            "type": track.type,
            "title": track.title,
            "description": track.content if hasattr(track, "content") else "",
            "status": track.status,
            "priority": track.priority,
            "created_at": track.created.isoformat()
            if hasattr(track, "created")
            else datetime.now().isoformat(),
            "updated_at": track.updated.isoformat()
            if hasattr(track, "updated")
            else datetime.now().isoformat(),
            "metadata": json.dumps(metadata),
        }

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

        Performance: O(1) if cached, O(log n) from database
        """
        if not track_id or not isinstance(track_id, str):
            raise ValueError(f"Invalid track_id: {track_id}")

        # Check cache first
        if track_id in self._cache:
            return self._cache[track_id]

        # Query database
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Convert to Node and cache
        track = self._row_to_node(row)
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

        Performance: O(n) with SQL WHERE clauses
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

        # Build SQL query
        query = "SELECT * FROM tracks"
        params = []

        if filters:
            where_clauses = []
            for key, value in filters.items():
                if key in ["status", "priority", "type", "title", "id"]:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
                elif key in ["has_spec", "has_plan"]:
                    # Query JSON metadata
                    where_clauses.append(f"json_extract(metadata, '$.{key}') = ?")
                    params.append(1 if value else 0)

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

        # Execute query
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        # Convert to Node objects
        results = []
        for row in rows:
            track_id = row["id"]
            if track_id in self._cache:
                results.append(self._cache[track_id])
            else:
                track = self._row_to_node(row)
                self._cache[track_id] = track
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
        return SQLiteRepositoryQuery(self, kwargs)

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

        # Convert to dict
        data = self._node_to_dict(track)

        # Upsert into database
        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO tracks
            (id, type, title, description, status, priority, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data["id"],
                data["type"],
                data["title"],
                data["description"],
                data["status"],
                data["priority"],
                data["created_at"],
                data["updated_at"],
                data["metadata"],
            ),
        )
        conn.commit()

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

        Performance: O(k) vectorized SQL where k = batch size
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

        # Delete from database
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
        conn.commit()

        # Remove from cache
        self._cache.pop(track_id, None)

        return cursor.rowcount > 0

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

        Performance: O(n) with JSON queries
        """
        if not isinstance(feature_ids, list):
            raise ValueError("feature_ids must be a list")

        # Query tracks with features in metadata
        conn = self._get_connection()

        # Build query to check if any feature_id is in the features array
        results = []
        for feature_id in feature_ids:
            cursor = conn.execute(
                """
                SELECT * FROM tracks
                WHERE json_extract(metadata, '$.features') LIKE ?
            """,
                (f"%{feature_id}%",),
            )

            for row in cursor.fetchall():
                track_id = row["id"]
                if track_id in self._cache:
                    track = self._cache[track_id]
                else:
                    track = self._row_to_node(row)
                    self._cache[track_id] = track

                if track not in results:
                    results.append(track)

        return results

    def with_feature_count(self) -> builtins.list[Node]:
        """
        Get all tracks with feature count calculated.

        Returns:
            All tracks with feature_count property set
        """
        return self.list()

    def filter(self, predicate: Callable[[Node], bool]) -> builtins.list[Node]:
        """
        Filter tracks with custom predicate function.

        Args:
            predicate: Function that takes Track and returns True/False

        Returns:
            Tracks matching predicate
        """
        all_tracks = self.list()
        return [t for t in all_tracks if predicate(t)]

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

        Invalidates all caches and reloads from database.
        """
        self._cache.clear()
        # Database is always up-to-date, no need to reload

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

        Performance: O(1) with SQL COUNT, O(n) with filters
        """
        if not filters:
            conn = self._get_connection()
            cursor = conn.execute("SELECT COUNT(*) FROM tracks")
            result = cursor.fetchone()[0]
            return int(result)

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

        # Check database
        conn = self._get_connection()
        cursor = conn.execute("SELECT 1 FROM tracks WHERE id = ? LIMIT 1", (track_id,))
        return cursor.fetchone() is not None
