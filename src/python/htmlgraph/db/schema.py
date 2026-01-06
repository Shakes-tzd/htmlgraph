"""
HtmlGraph SQLite Schema - Phase 1 Backend Storage

This module defines the comprehensive SQLite schema for HtmlGraph agent observability,
replacing HTML file storage with structured relational database.

Key design principles:
- Normalize data while preserving flexibility via JSON columns
- Index frequently queried fields for performance
- Track audit trails (created_at, updated_at)
- Support graph relationships via edge tracking
- Enable full observability of agent activities

Tables:
- agent_events: All agent tool calls, results, errors, delegations
- features: Feature/bug/spike/chore/epic work items
- sessions: Agent session tracking with metrics
- tracks: Multi-feature initiatives
- agent_collaboration: Handoffs and parallel work
- graph_edges: General relationship tracking
- event_log_archive: Historical event log for querying
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HtmlGraphDB:
    """
    SQLite database manager for HtmlGraph observability backend.

    Provides schema creation, migrations, and query helpers for storing
    and retrieving agent events, features, sessions, and collaborations.
    """

    def __init__(self, db_path: str | None = None):
        """
        Initialize HtmlGraph database.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default: .htmlgraph/htmlgraph.db in project root
            db_path = str(Path.home() / ".htmlgraph" / "htmlgraph.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection: sqlite3.Connection | None = None

        # Auto-initialize schema on first instantiation
        self.connect()
        self.create_tables()

    def connect(self) -> sqlite3.Connection:
        """
        Connect to SQLite database, creating it if needed.

        Returns:
            SQLite connection object
        """
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        # Enable foreign keys
        self.connection.execute("PRAGMA foreign_keys = ON")
        return self.connection

    def disconnect(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def create_tables(self) -> None:
        """
        Create all required tables in SQLite database.

        Tables created:
        1. agent_events - Core event tracking
        2. features - Work items (features, bugs, spikes, etc.)
        3. sessions - Agent sessions with metrics
        4. tracks - Multi-feature initiatives
        5. agent_collaboration - Handoffs and parallel work
        6. graph_edges - Flexible relationship tracking
        7. event_log_archive - Historical event log
        8. indexes - Performance optimization
        """
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()  # type: ignore[union-attr]

        # 1. AGENT_EVENTS TABLE - Core event tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_events (
                event_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK(
                    event_type IN ('tool_call', 'tool_result', 'error', 'delegation',
                                   'completion', 'start', 'end', 'check_point')
                ),
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                tool_name TEXT,
                input_summary TEXT,
                output_summary TEXT,
                context JSON,
                session_id TEXT NOT NULL,
                parent_agent_id TEXT,
                parent_event_id TEXT,
                cost_tokens INTEGER DEFAULT 0,
                status TEXT DEFAULT 'recorded',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (parent_event_id) REFERENCES agent_events(event_id)
            )
        """)

        # 2. FEATURES TABLE - Work items (features, bugs, spikes, chores, epics)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS features (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL CHECK(
                    type IN ('feature', 'bug', 'spike', 'chore', 'epic', 'task')
                ),
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'todo' CHECK(
                    status IN ('todo', 'in_progress', 'blocked', 'done', 'cancelled')
                ),
                priority TEXT DEFAULT 'medium' CHECK(
                    priority IN ('low', 'medium', 'high', 'critical')
                ),
                assigned_to TEXT,
                track_id TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                steps_total INTEGER DEFAULT 0,
                steps_completed INTEGER DEFAULT 0,
                parent_feature_id TEXT,
                tags JSON,
                metadata JSON,
                FOREIGN KEY (track_id) REFERENCES tracks(track_id),
                FOREIGN KEY (parent_feature_id) REFERENCES features(id)
            )
        """)

        # 3. SESSIONS TABLE - Agent sessions with metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                agent_assigned TEXT NOT NULL,
                parent_session_id TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                total_events INTEGER DEFAULT 0,
                total_tokens_used INTEGER DEFAULT 0,
                context_drift REAL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'active' CHECK(
                    status IN ('active', 'completed', 'paused', 'failed')
                ),
                transcript_id TEXT,
                transcript_path TEXT,
                transcript_synced DATETIME,
                start_commit TEXT,
                end_commit TEXT,
                is_subagent BOOLEAN DEFAULT FALSE,
                features_worked_on JSON,
                metadata JSON,
                FOREIGN KEY (parent_session_id) REFERENCES sessions(session_id)
            )
        """)

        # 4. TRACKS TABLE - Multi-feature initiatives
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                track_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium' CHECK(
                    priority IN ('low', 'medium', 'high', 'critical')
                ),
                status TEXT NOT NULL DEFAULT 'todo' CHECK(
                    status IN ('todo', 'in_progress', 'blocked', 'done', 'cancelled')
                ),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                features JSON,
                metadata JSON
            )
        """)

        # 5. AGENT_COLLABORATION TABLE - Handoffs and parallel work
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_collaboration (
                handoff_id TEXT PRIMARY KEY,
                from_agent TEXT NOT NULL,
                to_agent TEXT NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                feature_id TEXT,
                session_id TEXT NOT NULL,
                handoff_type TEXT CHECK(
                    handoff_type IN ('delegation', 'parallel', 'sequential', 'fallback')
                ),
                status TEXT DEFAULT 'pending' CHECK(
                    status IN ('pending', 'accepted', 'rejected', 'completed', 'failed')
                ),
                reason TEXT,
                context JSON,
                result JSON,
                FOREIGN KEY (feature_id) REFERENCES features(id),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        # 6. GRAPH_EDGES TABLE - Flexible relationship tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_edges (
                edge_id TEXT PRIMARY KEY,
                from_node_id TEXT NOT NULL,
                from_node_type TEXT NOT NULL,
                to_node_id TEXT NOT NULL,
                to_node_type TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata JSON
            )
        """)

        # 7. EVENT_LOG_ARCHIVE TABLE - Historical event queries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_log_archive (
                archive_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                event_date DATE NOT NULL,
                event_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                summary TEXT,
                archived_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        # 8. Create indexes for performance
        self._create_indexes(cursor)

        if self.connection:
            self.connection.commit()
        logger.info(f"SQLite schema created at {self.db_path}")

    def _create_indexes(self, cursor: sqlite3.Cursor) -> None:
        """
        Create indexes on frequently queried fields.

        Args:
            cursor: SQLite cursor for executing queries
        """
        indexes = [
            # agent_events indexes
            "CREATE INDEX IF NOT EXISTS idx_agent_events_session ON agent_events(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_agent_events_agent ON agent_events(agent_id)",
            "CREATE INDEX IF NOT EXISTS idx_agent_events_timestamp ON agent_events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_agent_events_type ON agent_events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_agent_events_parent_event ON agent_events(parent_event_id)",
            # features indexes
            "CREATE INDEX IF NOT EXISTS idx_features_status ON features(status)",
            "CREATE INDEX IF NOT EXISTS idx_features_type ON features(type)",
            "CREATE INDEX IF NOT EXISTS idx_features_track ON features(track_id)",
            "CREATE INDEX IF NOT EXISTS idx_features_assigned ON features(assigned_to)",
            "CREATE INDEX IF NOT EXISTS idx_features_parent ON features(parent_feature_id)",
            "CREATE INDEX IF NOT EXISTS idx_features_created ON features(created_at)",
            # sessions indexes
            "CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_assigned)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id)",
            # tracks indexes
            "CREATE INDEX IF NOT EXISTS idx_tracks_status ON tracks(status)",
            "CREATE INDEX IF NOT EXISTS idx_tracks_created ON tracks(created_at)",
            # collaboration indexes
            "CREATE INDEX IF NOT EXISTS idx_collaboration_from_agent ON agent_collaboration(from_agent)",
            "CREATE INDEX IF NOT EXISTS idx_collaboration_to_agent ON agent_collaboration(to_agent)",
            "CREATE INDEX IF NOT EXISTS idx_collaboration_feature ON agent_collaboration(feature_id)",
            # graph_edges indexes
            "CREATE INDEX IF NOT EXISTS idx_edges_from ON graph_edges(from_node_id)",
            "CREATE INDEX IF NOT EXISTS idx_edges_to ON graph_edges(to_node_id)",
            "CREATE INDEX IF NOT EXISTS idx_edges_type ON graph_edges(relationship_type)",
        ]

        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except sqlite3.OperationalError as e:
                logger.warning(f"Index creation warning: {e}")

    def insert_event(
        self,
        event_id: str,
        agent_id: str,
        event_type: str,
        session_id: str,
        tool_name: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        context: dict[str, Any] | None = None,
        parent_agent_id: str | None = None,
        parent_event_id: str | None = None,
        cost_tokens: int = 0,
    ) -> bool:
        """
        Insert an agent event into the database.

        Args:
            event_id: Unique event identifier
            agent_id: Agent that generated this event
            event_type: Type of event (tool_call, tool_result, error, etc.)
            session_id: Session this event belongs to
            tool_name: Tool that was called (optional)
            input_summary: Summary of tool input (optional)
            output_summary: Summary of tool output (optional)
            context: Additional metadata as JSON (optional)
            parent_agent_id: Parent agent if delegated (optional)
            parent_event_id: Parent event if nested (optional)
            cost_tokens: Token usage estimate (optional)

        Returns:
            True if insert successful, False otherwise
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                INSERT INTO agent_events
                (event_id, agent_id, event_type, session_id, tool_name,
                 input_summary, output_summary, context, parent_agent_id,
                 parent_event_id, cost_tokens)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event_id,
                    agent_id,
                    event_type,
                    session_id,
                    tool_name,
                    input_summary,
                    output_summary,
                    json.dumps(context) if context else None,
                    parent_agent_id,
                    parent_event_id,
                    cost_tokens,
                ),
            )
            self.connection.commit()  # type: ignore[union-attr]
            return True
        except sqlite3.Error as e:
            logger.error(f"Error inserting event: {e}")
            return False

    def insert_feature(
        self,
        feature_id: str,
        feature_type: str,
        title: str,
        status: str = "todo",
        priority: str = "medium",
        assigned_to: str | None = None,
        track_id: str | None = None,
        description: str | None = None,
        steps_total: int = 0,
        tags: list | None = None,
    ) -> bool:
        """
        Insert a feature/bug/spike work item.

        Args:
            feature_id: Unique feature identifier
            feature_type: Type (feature, bug, spike, chore, epic)
            title: Feature title
            status: Current status (todo, in_progress, done, etc.)
            priority: Priority level (low, medium, high, critical)
            assigned_to: Assigned agent (optional)
            track_id: Parent track ID (optional)
            description: Feature description (optional)
            steps_total: Total implementation steps
            tags: Tags for categorization (optional)

        Returns:
            True if insert successful, False otherwise
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                INSERT INTO features
                (id, type, title, status, priority, assigned_to, track_id,
                 description, steps_total, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    feature_id,
                    feature_type,
                    title,
                    status,
                    priority,
                    assigned_to,
                    track_id,
                    description,
                    steps_total,
                    json.dumps(tags) if tags else None,
                ),
            )
            self.connection.commit()  # type: ignore[union-attr]
            return True
        except sqlite3.Error as e:
            logger.error(f"Error inserting feature: {e}")
            return False

    def insert_session(
        self,
        session_id: str,
        agent_assigned: str,
        parent_session_id: str | None = None,
        is_subagent: bool = False,
        transcript_id: str | None = None,
        transcript_path: str | None = None,
    ) -> bool:
        """
        Insert a new session record.

        Args:
            session_id: Unique session identifier
            agent_assigned: Primary agent for this session
            parent_session_id: Parent session if subagent (optional)
            is_subagent: Whether this is a subagent session
            transcript_id: ID of Claude transcript (optional)
            transcript_path: Path to transcript file (optional)

        Returns:
            True if insert successful, False otherwise
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                INSERT INTO sessions
                (session_id, agent_assigned, parent_session_id, is_subagent,
                 transcript_id, transcript_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    agent_assigned,
                    parent_session_id,
                    is_subagent,
                    transcript_id,
                    transcript_path,
                ),
            )
            self.connection.commit()  # type: ignore[union-attr]
            return True
        except sqlite3.Error as e:
            logger.error(f"Error inserting session: {e}")
            return False

    def update_feature_status(
        self,
        feature_id: str,
        status: str,
        steps_completed: int | None = None,
    ) -> bool:
        """
        Update feature status and completion progress.

        Args:
            feature_id: Feature to update
            status: New status (todo, in_progress, done, etc.)
            steps_completed: Number of steps completed (optional)

        Returns:
            True if update successful, False otherwise
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()  # type: ignore[union-attr]
            if steps_completed is not None:
                cursor.execute(
                    """
                    UPDATE features
                    SET status = ?, steps_completed = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (status, steps_completed, feature_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE features
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (status, feature_id),
                )

            # Auto-set completed_at if status is done
            if status == "done":
                cursor.execute(
                    """
                    UPDATE features
                    SET completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (feature_id,),
                )

            self.connection.commit()  # type: ignore[union-attr]
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating feature: {e}")
            return False

    def get_session_events(self, session_id: str) -> list[dict[str, Any]]:
        """
        Get all events for a session.

        Args:
            session_id: Session to query

        Returns:
            List of event dictionaries
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT * FROM agent_events
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """,
                (session_id,),
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error querying events: {e}")
            return []

    def get_feature_by_id(self, feature_id: str) -> dict[str, Any] | None:
        """
        Get a feature by ID.

        Args:
            feature_id: Feature ID to retrieve

        Returns:
            Feature dictionary or None if not found
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT * FROM features WHERE id = ?
            """,
                (feature_id,),
            )

            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error fetching feature: {e}")
            return None

    def get_features_by_status(self, status: str) -> list[dict[str, Any]]:
        """
        Get all features with a specific status.

        Args:
            status: Status to filter by

        Returns:
            List of feature dictionaries
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT * FROM features
                WHERE status = ?
                ORDER BY priority DESC, created_at DESC
            """,
                (status,),
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error querying features: {e}")
            return []

    def _ensure_session_exists(
        self, session_id: str, agent_id: str | None = None
    ) -> bool:
        """
        Ensure a session record exists in the database.

        Creates a placeholder session if it doesn't exist. Useful for
        handling foreign key constraints when recording delegations
        before the session is explicitly created.

        Args:
            session_id: Session ID to ensure exists
            agent_id: Agent assigned to session (optional, defaults to 'system')

        Returns:
            True if session exists or was created, False on error
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()  # type: ignore[union-attr]

            # Check if session already exists
            cursor.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
            if cursor.fetchone():
                return True

            # Session doesn't exist, create placeholder
            cursor.execute(
                """
                INSERT INTO sessions
                (session_id, agent_assigned, status)
                VALUES (?, ?, 'active')
            """,
                (session_id, agent_id or "system"),
            )
            self.connection.commit()  # type: ignore[union-attr]
            return True

        except sqlite3.Error as e:
            # Session might exist but check failed, continue anyway
            logger.debug(f"Session creation warning: {e}")
            return False

    def record_collaboration(
        self,
        handoff_id: str,
        from_agent: str,
        to_agent: str,
        session_id: str,
        feature_id: str | None = None,
        handoff_type: str = "delegation",
        reason: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Record an agent handoff or collaboration event.

        Args:
            handoff_id: Unique handoff identifier
            from_agent: Agent handing off work
            to_agent: Agent receiving work
            session_id: Session this handoff occurs in
            feature_id: Feature being handed off (optional)
            handoff_type: Type of handoff (delegation, parallel, sequential, fallback)
            reason: Reason for handoff (optional)
            context: Additional context (optional)

        Returns:
            True if record successful, False otherwise
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                INSERT INTO agent_collaboration
                (handoff_id, from_agent, to_agent, session_id, feature_id,
                 handoff_type, reason, context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    handoff_id,
                    from_agent,
                    to_agent,
                    session_id,
                    feature_id,
                    handoff_type,
                    reason,
                    json.dumps(context) if context else None,
                ),
            )
            self.connection.commit()  # type: ignore[union-attr]
            return True
        except sqlite3.Error as e:
            logger.error(f"Error recording collaboration: {e}")
            return False

    def record_delegation_event(
        self,
        from_agent: str,
        to_agent: str,
        task_description: str,
        session_id: str | None = None,
        feature_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Record a delegation event from one agent to another.

        This is a convenience method that wraps record_collaboration
        with sensible defaults for Task() delegation tracking.

        Handles foreign key constraints by creating placeholder session
        if it doesn't exist.

        Args:
            from_agent: Agent delegating work
            to_agent: Agent receiving work
            task_description: Description of the delegated task
            session_id: Session this delegation occurs in (optional, auto-creates if missing)
            feature_id: Feature being delegated (optional)
            context: Additional metadata (optional)

        Returns:
            Handoff ID if successful, None otherwise
        """
        import uuid

        if not self.connection:
            self.connect()

        # Auto-create session if not provided or doesn't exist
        if not session_id:
            session_id = f"session-{uuid.uuid4().hex[:8]}"

        # Ensure session exists (create placeholder if needed)
        self._ensure_session_exists(session_id, from_agent)

        handoff_id = f"hand-{uuid.uuid4().hex[:8]}"

        # Prepare context with task description
        delegation_context = context or {}
        delegation_context["task_description"] = task_description

        success = self.record_collaboration(
            handoff_id=handoff_id,
            from_agent=from_agent,
            to_agent=to_agent,
            session_id=session_id,
            feature_id=feature_id,
            handoff_type="delegation",
            reason=task_description,
            context=delegation_context,
        )

        return handoff_id if success else None

    def get_delegations(
        self,
        session_id: str | None = None,
        from_agent: str | None = None,
        to_agent: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Query delegation events with optional filtering.

        Args:
            session_id: Filter by session (optional)
            from_agent: Filter by source agent (optional)
            to_agent: Filter by target agent (optional)
            limit: Maximum number of results

        Returns:
            List of delegation events as dictionaries
        """
        if not self.connection:
            self.connect()

        try:
            cursor = self.connection.cursor()  # type: ignore[union-attr]

            # Build dynamic WHERE clause
            where_clauses = ["handoff_type = 'delegation'"]
            params: list[str | int] = []

            if session_id:
                where_clauses.append("session_id = ?")
                params.append(session_id)
            if from_agent:
                where_clauses.append("from_agent = ?")
                params.append(from_agent)
            if to_agent:
                where_clauses.append("to_agent = ?")
                params.append(to_agent)

            where_sql = " AND ".join(where_clauses)

            cursor.execute(
                f"""
                SELECT handoff_id, from_agent, to_agent, timestamp, reason,
                       feature_id, session_id, status, context
                FROM agent_collaboration
                WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                params + [limit],
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error querying delegations: {e}")
            return []

    def close(self) -> None:
        """Clean up database connection."""
        self.disconnect()
