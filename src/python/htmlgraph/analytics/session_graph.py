"""
Cross-Session Graph Queries - Session Relationship Index.

Provides indexed graph queries over the SQLite store for efficient
cross-session analytics. Replaces expensive linear scans of event logs
and git commands with O(log n) indexed lookups and recursive CTEs.

Key capabilities:
- sessions_for_feature: Find all sessions that touched a feature via index
- features_for_session: Find all features a session worked on
- delegation_chain: Follow parent_session_id links recursively
- handoff_path: Find path between sessions via handoffs
- feature_timeline: Chronological timeline of all work on a feature
- related_sessions: Find sessions related through shared features or delegation

Design:
- Uses SQLite indexes for O(log n) lookups instead of O(n) scans
- Recursive CTEs for delegation chain traversal
- Zero external dependencies (SQLite only)
- Works with existing HtmlGraphDB schema

Example:
    from htmlgraph.db.schema import HtmlGraphDB
    from htmlgraph.analytics.session_graph import SessionGraph

    db = HtmlGraphDB(db_path="path/to/htmlgraph.db")
    graph = SessionGraph(db)

    # Find all sessions that worked on a feature
    sessions = graph.sessions_for_feature("feat-abc123")

    # Follow delegation chain
    chain = graph.delegation_chain("session-xyz")

    # Build feature timeline
    timeline = graph.feature_timeline("feat-abc123")
"""

from __future__ import annotations

import logging
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.db.schema import HtmlGraphDB

logger = logging.getLogger(__name__)


@dataclass
class SessionNode:
    """A node in the session graph representing a single session."""

    session_id: str
    agent: str
    status: str
    created_at: datetime
    features_worked_on: list[str] = field(default_factory=list)
    parent_session_id: str | None = None
    depth: int = 0


@dataclass
class FeatureEvent:
    """A single event related to a feature across any session."""

    session_id: str
    agent: str
    timestamp: datetime
    event_type: str
    tool_name: str | None = None
    summary: str | None = None


class SessionGraph:
    """
    Property-graph view over SQLite tables for cross-session queries.

    Provides indexed lookups and recursive traversals over the session,
    event, and handoff tables in the HtmlGraph SQLite database.
    """

    def __init__(self, db: HtmlGraphDB) -> None:
        """
        Initialize SessionGraph with database reference.

        Args:
            db: HtmlGraphDB instance with active connection
        """
        self.db = db

    def ensure_indexes(self) -> None:
        """
        Create optimized indexes for cross-session graph queries.

        These indexes supplement the existing schema indexes with
        composite indexes specifically designed for graph traversal
        patterns. Safe to call multiple times (idempotent).
        """
        if not self.db.connection:
            self.db.connect()

        cursor = self.db.connection.cursor()  # type: ignore[union-attr]

        indexes = [
            # Feature -> Session mapping (sessions_for_feature)
            "CREATE INDEX IF NOT EXISTS idx_events_feature_session "
            "ON agent_events(feature_id, session_id)",
            # Session -> Feature mapping (features_for_session)
            "CREATE INDEX IF NOT EXISTS idx_events_session_feature "
            "ON agent_events(session_id, feature_id)",
            # Delegation chain traversal
            "CREATE INDEX IF NOT EXISTS idx_sessions_parent "
            "ON sessions(parent_session_id)",
            # Continuation chain traversal
            "CREATE INDEX IF NOT EXISTS idx_sessions_continued "
            "ON sessions(continued_from)",
            # Handoff from-session lookups
            "CREATE INDEX IF NOT EXISTS idx_handoff_from "
            "ON handoff_tracking(from_session_id)",
            # Handoff to-session lookups
            "CREATE INDEX IF NOT EXISTS idx_handoff_to "
            "ON handoff_tracking(to_session_id)",
        ]

        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except sqlite3.OperationalError as e:
                logger.warning(f"Index creation warning: {e}")

        self.db.connection.commit()  # type: ignore[union-attr]

    def sessions_for_feature(self, feature_id: str) -> list[SessionNode]:
        """
        Find all sessions that touched a feature - O(log n) via index.

        Uses the idx_events_feature_session index for fast lookup
        instead of scanning all events linearly.

        Args:
            feature_id: Feature ID to query

        Returns:
            List of SessionNode objects for sessions that worked on this feature
        """
        if not self.db.connection:
            self.db.connect()

        try:
            cursor = self.db.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT DISTINCT
                    s.session_id,
                    s.agent_assigned,
                    s.status,
                    s.created_at,
                    s.parent_session_id,
                    s.features_worked_on
                FROM agent_events ae
                JOIN sessions s ON ae.session_id = s.session_id
                WHERE ae.feature_id = ?
                ORDER BY s.created_at ASC
                """,
                (feature_id,),
            )

            nodes = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                features = self._parse_features_list(row_dict.get("features_worked_on"))
                if feature_id not in features:
                    features.append(feature_id)

                nodes.append(
                    SessionNode(
                        session_id=row_dict["session_id"],
                        agent=row_dict["agent_assigned"],
                        status=row_dict["status"],
                        created_at=self._parse_datetime(row_dict["created_at"]),
                        features_worked_on=features,
                        parent_session_id=row_dict.get("parent_session_id"),
                        depth=0,
                    )
                )

            return nodes

        except sqlite3.Error as e:
            logger.error(f"Error querying sessions for feature: {e}")
            return []

    def features_for_session(self, session_id: str) -> list[str]:
        """
        Find all features a session worked on.

        Uses the idx_events_session_feature index for fast lookup.

        Args:
            session_id: Session ID to query

        Returns:
            Sorted list of feature IDs
        """
        if not self.db.connection:
            self.db.connect()

        try:
            cursor = self.db.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT DISTINCT feature_id
                FROM agent_events
                WHERE session_id = ?
                  AND feature_id IS NOT NULL
                ORDER BY feature_id
                """,
                (session_id,),
            )

            return [row["feature_id"] for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Error querying features for session: {e}")
            return []

    def delegation_chain(
        self, session_id: str, max_depth: int = 10
    ) -> list[SessionNode]:
        """
        Follow parent_session_id links to build delegation chain.

        Uses a recursive CTE to efficiently traverse the delegation
        tree upward from the given session to its root ancestor.

        Args:
            session_id: Starting session ID
            max_depth: Maximum depth to traverse (default 10)

        Returns:
            List of SessionNode objects from the starting session
            up to the root ancestor, ordered by depth (0 = starting session)
        """
        if not self.db.connection:
            self.db.connect()

        try:
            cursor = self.db.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                WITH RECURSIVE chain AS (
                    SELECT session_id, parent_session_id, agent_assigned,
                           status, created_at, features_worked_on, 0 as depth
                    FROM sessions
                    WHERE session_id = ?

                    UNION ALL

                    SELECT s.session_id, s.parent_session_id, s.agent_assigned,
                           s.status, s.created_at, s.features_worked_on, c.depth + 1
                    FROM sessions s
                    JOIN chain c ON s.session_id = c.parent_session_id
                    WHERE c.depth < ?
                )
                SELECT * FROM chain
                ORDER BY depth ASC
                """,
                (session_id, max_depth),
            )

            nodes = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                nodes.append(
                    SessionNode(
                        session_id=row_dict["session_id"],
                        agent=row_dict["agent_assigned"],
                        status=row_dict["status"],
                        created_at=self._parse_datetime(row_dict["created_at"]),
                        features_worked_on=self._parse_features_list(
                            row_dict.get("features_worked_on")
                        ),
                        parent_session_id=row_dict.get("parent_session_id"),
                        depth=row_dict["depth"],
                    )
                )

            return nodes

        except sqlite3.Error as e:
            logger.error(f"Error querying delegation chain: {e}")
            return []

    def handoff_path(
        self, from_session: str, to_session: str, max_depth: int = 10
    ) -> list[SessionNode] | None:
        """
        Find the path from one session to another via handoffs.

        Performs a BFS over the handoff_tracking table to find the
        shortest path between two sessions. Follows both from_session_id
        and to_session_id links bidirectionally.

        Args:
            from_session: Starting session ID
            to_session: Target session ID
            max_depth: Maximum search depth (default 10)

        Returns:
            List of SessionNode objects forming the path, or None if no path exists
        """
        if from_session == to_session:
            node = self._get_session_node(from_session, depth=0)
            return [node] if node else None

        if not self.db.connection:
            self.db.connect()

        try:
            # BFS to find path through handoffs
            visited: set[str] = set()
            # Queue of (session_id, path_so_far)
            queue: deque[tuple[str, list[str]]] = deque()
            queue.append((from_session, [from_session]))
            visited.add(from_session)

            cursor = self.db.connection.cursor()  # type: ignore[union-attr]

            while queue:
                current_id, path = queue.popleft()

                if len(path) > max_depth + 1:
                    continue

                # Find sessions reachable via handoffs from current
                cursor.execute(
                    """
                    SELECT to_session_id FROM handoff_tracking
                    WHERE from_session_id = ? AND to_session_id IS NOT NULL
                    UNION
                    SELECT from_session_id FROM handoff_tracking
                    WHERE to_session_id = ?
                    """,
                    (current_id, current_id),
                )

                for row in cursor.fetchall():
                    neighbor_id = row[0]
                    if neighbor_id in visited:
                        continue

                    new_path = path + [neighbor_id]

                    if neighbor_id == to_session:
                        # Found the target - build SessionNode list
                        return self._build_path_nodes(new_path)

                    visited.add(neighbor_id)
                    queue.append((neighbor_id, new_path))

            return None

        except sqlite3.Error as e:
            logger.error(f"Error finding handoff path: {e}")
            return None

    def feature_timeline(self, feature_id: str) -> list[FeatureEvent]:
        """
        Build chronological timeline of all work on a feature across sessions.

        Queries agent_events for all events associated with the given
        feature, ordered chronologically.

        Args:
            feature_id: Feature ID to query

        Returns:
            List of FeatureEvent objects in chronological order
        """
        if not self.db.connection:
            self.db.connect()

        try:
            cursor = self.db.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT
                    ae.session_id,
                    s.agent_assigned,
                    ae.timestamp,
                    ae.event_type,
                    ae.tool_name,
                    ae.input_summary
                FROM agent_events ae
                JOIN sessions s ON ae.session_id = s.session_id
                WHERE ae.feature_id = ?
                ORDER BY ae.timestamp ASC
                """,
                (feature_id,),
            )

            events = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                events.append(
                    FeatureEvent(
                        session_id=row_dict["session_id"],
                        agent=row_dict["agent_assigned"],
                        timestamp=self._parse_datetime(row_dict["timestamp"]),
                        event_type=row_dict["event_type"],
                        tool_name=row_dict.get("tool_name"),
                        summary=row_dict.get("input_summary"),
                    )
                )

            return events

        except sqlite3.Error as e:
            logger.error(f"Error querying feature timeline: {e}")
            return []

    def related_sessions(
        self, session_id: str, max_depth: int = 3
    ) -> list[SessionNode]:
        """
        Find sessions related through shared features or delegation.

        Performs a BFS starting from the given session, expanding via:
        1. Shared features (sessions that worked on the same features)
        2. Delegation links (parent_session_id chains)
        3. Continuation links (continued_from chains)

        Args:
            session_id: Starting session ID
            max_depth: Maximum traversal depth (default 3)

        Returns:
            List of related SessionNode objects (excluding the starting session),
            ordered by depth then created_at
        """
        if not self.db.connection:
            self.db.connect()

        try:
            visited: set[str] = {session_id}
            result: list[SessionNode] = []
            current_layer: set[str] = {session_id}

            cursor = self.db.connection.cursor()  # type: ignore[union-attr]

            for depth in range(1, max_depth + 1):
                next_layer: set[str] = set()

                for current_id in current_layer:
                    # 1. Sessions sharing features
                    neighbors = self._find_feature_neighbors(cursor, current_id)
                    next_layer.update(neighbors - visited)

                    # 2. Delegation links (parent and children)
                    neighbors = self._find_delegation_neighbors(cursor, current_id)
                    next_layer.update(neighbors - visited)

                    # 3. Continuation links
                    neighbors = self._find_continuation_neighbors(cursor, current_id)
                    next_layer.update(neighbors - visited)

                # Build SessionNodes for the new layer
                for neighbor_id in next_layer:
                    node = self._get_session_node(neighbor_id, depth=depth)
                    if node:
                        result.append(node)

                visited.update(next_layer)
                current_layer = next_layer

                if not next_layer:
                    break

            # Sort by depth then created_at
            result.sort(key=lambda n: (n.depth, n.created_at))
            return result

        except sqlite3.Error as e:
            logger.error(f"Error querying related sessions: {e}")
            return []

    # === Private helper methods ===

    def _get_session_node(self, session_id: str, depth: int = 0) -> SessionNode | None:
        """
        Load a single session as a SessionNode.

        Args:
            session_id: Session ID to load
            depth: Depth value to assign

        Returns:
            SessionNode or None if not found
        """
        if not self.db.connection:
            self.db.connect()

        try:
            cursor = self.db.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT session_id, agent_assigned, status, created_at,
                       parent_session_id, features_worked_on
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            row_dict = dict(row)
            features = self._parse_features_list(row_dict.get("features_worked_on"))

            # Also get features from events
            event_features = self.features_for_session(session_id)
            for f in event_features:
                if f not in features:
                    features.append(f)

            return SessionNode(
                session_id=row_dict["session_id"],
                agent=row_dict["agent_assigned"],
                status=row_dict["status"],
                created_at=self._parse_datetime(row_dict["created_at"]),
                features_worked_on=features,
                parent_session_id=row_dict.get("parent_session_id"),
                depth=depth,
            )

        except sqlite3.Error as e:
            logger.error(f"Error loading session node: {e}")
            return None

    def _build_path_nodes(self, session_ids: list[str]) -> list[SessionNode]:
        """
        Build a list of SessionNodes from a list of session IDs.

        Args:
            session_ids: Ordered list of session IDs forming a path

        Returns:
            List of SessionNode objects with depth set to position in path
        """
        nodes = []
        for i, sid in enumerate(session_ids):
            node = self._get_session_node(sid, depth=i)
            if node:
                nodes.append(node)
        return nodes

    def _find_feature_neighbors(
        self, cursor: sqlite3.Cursor, session_id: str
    ) -> set[str]:
        """
        Find sessions that share features with the given session.

        Args:
            cursor: SQLite cursor
            session_id: Session to find neighbors for

        Returns:
            Set of neighbor session IDs
        """
        cursor.execute(
            """
            SELECT DISTINCT ae2.session_id
            FROM agent_events ae1
            JOIN agent_events ae2 ON ae1.feature_id = ae2.feature_id
            WHERE ae1.session_id = ?
              AND ae2.session_id != ?
              AND ae1.feature_id IS NOT NULL
            """,
            (session_id, session_id),
        )
        return {row[0] for row in cursor.fetchall()}

    def _find_delegation_neighbors(
        self, cursor: sqlite3.Cursor, session_id: str
    ) -> set[str]:
        """
        Find sessions linked via delegation (parent/child).

        Args:
            cursor: SQLite cursor
            session_id: Session to find neighbors for

        Returns:
            Set of neighbor session IDs
        """
        neighbors: set[str] = set()

        # Parent session
        cursor.execute(
            "SELECT parent_session_id FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row and row[0]:
            neighbors.add(row[0])

        # Child sessions
        cursor.execute(
            "SELECT session_id FROM sessions WHERE parent_session_id = ?",
            (session_id,),
        )
        for row in cursor.fetchall():
            neighbors.add(row[0])

        return neighbors

    def _find_continuation_neighbors(
        self, cursor: sqlite3.Cursor, session_id: str
    ) -> set[str]:
        """
        Find sessions linked via continuation (continued_from).

        Args:
            cursor: SQLite cursor
            session_id: Session to find neighbors for

        Returns:
            Set of neighbor session IDs
        """
        neighbors: set[str] = set()

        # Session this one continued from
        cursor.execute(
            "SELECT continued_from FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row and row[0]:
            neighbors.add(row[0])

        # Sessions that continued from this one
        cursor.execute(
            "SELECT session_id FROM sessions WHERE continued_from = ?",
            (session_id,),
        )
        for row in cursor.fetchall():
            neighbors.add(row[0])

        return neighbors

    @staticmethod
    def _parse_features_list(value: str | list[str] | None) -> list[str]:
        """
        Parse features_worked_on field which may be JSON string or list.

        Args:
            value: Raw value from database (JSON string, list, or None)

        Returns:
            List of feature ID strings
        """
        if value is None:
            return []

        if isinstance(value, list):
            return [str(item) for item in value]

        if isinstance(value, str):
            import json

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except (json.JSONDecodeError, TypeError):
                pass

        return []

    @staticmethod
    def _parse_datetime(value: str | datetime | None) -> datetime:
        """
        Parse datetime from various formats.

        Args:
            value: Datetime string, datetime object, or None

        Returns:
            Parsed datetime (defaults to datetime.min if unparseable)
        """
        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        return datetime.min
