from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

"""
Tool Execution Traces Collection

Provides query interface for tool execution traces stored in tool_traces table.
Enables analysis of tool performance, error patterns, and execution hierarchies.

Example:
    >>> from htmlgraph.sdk import SDK
    >>> sdk = SDK(agent="claude")
    >>>
    >>> # Get traces for current session
    >>> traces = sdk.traces.get_traces(session_id="sess-abc123")
    >>> for trace in traces:
    ...     logger.info(f"{trace.tool_name}: {trace.duration_ms}ms")
    >>>
    >>> # Find slow tool calls
    >>> slow = sdk.traces.get_slow_traces(threshold_ms=1000)
    >>>
    >>> # Get hierarchical view (parent-child relationships)
    >>> tree = sdk.traces.get_trace_tree(trace_id="trace-xyz")
    >>> logger.info(f"Root: {tree.root.tool_name}")
    >>> logger.info(f"Children: {len(tree.children)}")
    >>>
    >>> # Get error traces for debugging
    >>> errors = sdk.traces.get_error_traces(session_id="sess-abc123")
"""


from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from htmlgraph.db.schema import HtmlGraphDB

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK


@dataclass
class TraceRecord:
    """
    Single tool execution trace.

    Represents one complete execution of a tool with timing, input, output, and status.
    Parent-child relationships via parent_tool_use_id enable hierarchical analysis.

    Attributes:
        tool_use_id: Unique identifier for this tool execution (UUID v4)
        trace_id: Parent trace ID for grouping related executions
        session_id: Session this execution belongs to
        tool_name: Name of the tool executed (e.g., "Bash", "Read", "Write")
        tool_input: Input parameters passed to the tool (dict, may be None)
        tool_output: Result returned by the tool (dict, may be None if not yet complete)
        start_time: When execution started (UTC datetime)
        end_time: When execution ended (UTC datetime, None if still running)
        duration_ms: Milliseconds to complete (None if still running or error)
        status: Execution status (started, completed, failed, timeout, cancelled)
        error_message: Error details if status is 'failed'
        parent_tool_use_id: tool_use_id of parent tool if nested (None if top-level)
    """

    tool_use_id: str
    trace_id: str
    session_id: str
    tool_name: str
    tool_input: dict | None
    tool_output: dict | None
    start_time: datetime
    end_time: datetime | None
    duration_ms: int | None
    status: str | None
    error_message: str | None
    parent_tool_use_id: str | None


@dataclass
class TraceTree:
    """
    Hierarchical view of traces (parent-child relationships).

    Enables analysis of nested tool executions where one tool invokes others.
    Example: Bash tool calls may invoke other tools as nested executions.

    Attributes:
        root: Root trace record (this execution)
        children: List of child traces (tools invoked by this tool)
    """

    root: TraceRecord
    children: list[TraceTree]


class TraceCollection:
    """
    Query interface for tool execution traces.

    Provides methods to retrieve, filter, and analyze tool execution traces
    stored in the tool_traces database table. Supports querying by session,
    tool name, performance thresholds, and error status.

    All queries return data sorted by start_time DESC (newest first).

    Example:
        >>> sdk = SDK(agent="claude")
        >>> traces = sdk.traces
        >>>
        >>> # Single trace
        >>> trace = traces.get_trace("tool-use-id-123")
        >>>
        >>> # All traces for session
        >>> all_traces = traces.get_traces("sess-123")
        >>>
        >>> # By tool name
        >>> bash_traces = traces.get_traces_by_tool("Bash")
        >>>
        >>> # Performance analysis
        >>> slow = traces.get_slow_traces(threshold_ms=1000)
        >>> errors = traces.get_error_traces("sess-123")
        >>>
        >>> # Hierarchical view
        >>> tree = traces.get_trace_tree("trace-id-123")
    """

    def __init__(self, sdk: SDK):
        """
        Initialize traces collection.

        Args:
            sdk: Parent SDK instance
        """
        self._sdk = sdk
        self._db = HtmlGraphDB()

    def _row_to_trace(self, row: tuple) -> TraceRecord:
        """
        Convert database row to TraceRecord dataclass.

        Args:
            row: SQLite row tuple from tool_traces query

        Returns:
            TraceRecord with parsed fields
        """
        import json

        # Unpack tuple: (tool_use_id, trace_id, session_id, tool_name, tool_input,
        #                tool_output, start_time, end_time, duration_ms, status,
        #                error_message, parent_tool_use_id)
        (
            tool_use_id,
            trace_id,
            session_id,
            tool_name,
            tool_input_json,
            tool_output_json,
            start_time_iso,
            end_time_iso,
            duration_ms,
            status,
            error_message,
            parent_tool_use_id,
        ) = row

        # Parse JSON fields
        tool_input = None
        if tool_input_json:
            try:
                tool_input = json.loads(tool_input_json)
            except (json.JSONDecodeError, TypeError):
                tool_input = None

        tool_output = None
        if tool_output_json:
            try:
                tool_output = json.loads(tool_output_json)
            except (json.JSONDecodeError, TypeError):
                tool_output = None

        # Parse timestamps
        start_time: datetime | None = None
        if start_time_iso:
            try:
                start_time = datetime.fromisoformat(
                    start_time_iso.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                start_time = None

        end_time: datetime | None = None
        if end_time_iso:
            try:
                end_time = datetime.fromisoformat(end_time_iso.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                end_time = None

        # Use current time if start_time is missing
        if start_time is None:
            start_time = datetime.now(timezone.utc)

        return TraceRecord(
            tool_use_id=tool_use_id,
            trace_id=trace_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            parent_tool_use_id=parent_tool_use_id,
        )

    def get_trace(self, tool_use_id: str) -> TraceRecord | None:
        """
        Get single trace by tool_use_id.

        Args:
            tool_use_id: Unique tool execution ID (UUID v4)

        Returns:
            TraceRecord if found, None otherwise
        """
        try:
            if not self._db.connection:
                self._db.connect()

            cursor = self._db.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT tool_use_id, trace_id, session_id, tool_name, tool_input,
                       tool_output, start_time, end_time, duration_ms, status,
                       error_message, parent_tool_use_id
                FROM tool_traces
                WHERE tool_use_id = ?
            """,
                (tool_use_id,),
            )

            row = cursor.fetchone()
            if row:
                return self._row_to_trace(row)

            return None
        except Exception as e:
            logger.info(f"Error getting trace {tool_use_id}: {e}")
            return None

    def get_traces(
        self,
        session_id: str,
        limit: int = 100,
        start_time: datetime | None = None,
    ) -> list[TraceRecord]:
        """
        Get traces for a session, ordered by start_time DESC (newest first).

        Args:
            session_id: Session to query
            limit: Maximum traces to return (default 100)
            start_time: Optional filter - only traces after this time

        Returns:
            List of TraceRecord objects, newest first
        """
        try:
            if not self._db.connection:
                self._db.connect()

            cursor = self._db.connection.cursor()  # type: ignore[union-attr]

            if start_time:
                start_time_iso = start_time.isoformat()
                cursor.execute(
                    """
                    SELECT tool_use_id, trace_id, session_id, tool_name, tool_input,
                           tool_output, start_time, end_time, duration_ms, status,
                           error_message, parent_tool_use_id
                    FROM tool_traces
                    WHERE session_id = ? AND start_time >= ?
                    ORDER BY start_time DESC
                    LIMIT ?
                """,
                    (session_id, start_time_iso, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT tool_use_id, trace_id, session_id, tool_name, tool_input,
                           tool_output, start_time, end_time, duration_ms, status,
                           error_message, parent_tool_use_id
                    FROM tool_traces
                    WHERE session_id = ?
                    ORDER BY start_time DESC
                    LIMIT ?
                """,
                    (session_id, limit),
                )

            rows = cursor.fetchall()
            return [self._row_to_trace(row) for row in rows]
        except Exception as e:
            logger.info(f"Error getting traces for session {session_id}: {e}")
            return []

    def get_traces_by_tool(self, tool_name: str, limit: int = 100) -> list[TraceRecord]:
        """
        Get traces for specific tool name.

        Args:
            tool_name: Name of the tool (e.g., "Bash", "Read", "Write")
            limit: Maximum traces to return (default 100)

        Returns:
            List of TraceRecord objects, newest first
        """
        try:
            if not self._db.connection:
                self._db.connect()

            cursor = self._db.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT tool_use_id, trace_id, session_id, tool_name, tool_input,
                       tool_output, start_time, end_time, duration_ms, status,
                       error_message, parent_tool_use_id
                FROM tool_traces
                WHERE tool_name = ?
                ORDER BY start_time DESC
                LIMIT ?
            """,
                (tool_name, limit),
            )

            rows = cursor.fetchall()
            return [self._row_to_trace(row) for row in rows]
        except Exception as e:
            logger.info(f"Error getting traces for tool {tool_name}: {e}")
            return []

    def get_trace_tree(self, trace_id: str) -> TraceTree | None:
        """
        Get hierarchical view with parent-child relationships.

        Recursively builds a tree of traces where each node can have children
        (tools invoked by that tool). Useful for understanding nested execution.

        Args:
            trace_id: Root trace_id to build tree from

        Returns:
            TraceTree with root and children, or None if not found
        """
        try:
            if not self._db.connection:
                self._db.connect()

            cursor = self._db.connection.cursor()  # type: ignore[union-attr]

            # Get root trace
            cursor.execute(
                """
                SELECT tool_use_id, trace_id, session_id, tool_name, tool_input,
                       tool_output, start_time, end_time, duration_ms, status,
                       error_message, parent_tool_use_id
                FROM tool_traces
                WHERE trace_id = ?
                ORDER BY start_time DESC
                LIMIT 1
            """,
                (trace_id,),
            )

            root_row = cursor.fetchone()
            if not root_row:
                return None

            root = self._row_to_trace(root_row)

            # Recursively get children
            def build_tree(parent_trace: TraceRecord) -> TraceTree:
                cursor.execute(
                    """
                    SELECT tool_use_id, trace_id, session_id, tool_name, tool_input,
                           tool_output, start_time, end_time, duration_ms, status,
                           error_message, parent_tool_use_id
                    FROM tool_traces
                    WHERE parent_tool_use_id = ?
                    ORDER BY start_time ASC
                """,
                    (parent_trace.tool_use_id,),
                )

                child_rows = cursor.fetchall()
                children = []
                for child_row in child_rows:
                    child = self._row_to_trace(child_row)
                    children.append(build_tree(child))

                return TraceTree(root=parent_trace, children=children)

            return build_tree(root)
        except Exception as e:
            logger.info(f"Error getting trace tree for {trace_id}: {e}")
            return None

    def get_slow_traces(self, threshold_ms: int, limit: int = 100) -> list[TraceRecord]:
        """
        Find traces exceeding duration threshold.

        Useful for identifying performance bottlenecks.

        Args:
            threshold_ms: Minimum duration in milliseconds
            limit: Maximum traces to return (default 100)

        Returns:
            List of slow TraceRecord objects, slowest first
        """
        try:
            if not self._db.connection:
                self._db.connect()

            cursor = self._db.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT tool_use_id, trace_id, session_id, tool_name, tool_input,
                       tool_output, start_time, end_time, duration_ms, status,
                       error_message, parent_tool_use_id
                FROM tool_traces
                WHERE duration_ms IS NOT NULL AND duration_ms >= ?
                ORDER BY duration_ms DESC
                LIMIT ?
            """,
                (threshold_ms, limit),
            )

            rows = cursor.fetchall()
            return [self._row_to_trace(row) for row in rows]
        except Exception as e:
            logger.info(f"Error getting slow traces: {e}")
            return []

    def get_error_traces(self, session_id: str, limit: int = 100) -> list[TraceRecord]:
        """
        Get traces with errors/failures.

        Filters for traces with status='failed' or error_message is not null.

        Args:
            session_id: Session to query
            limit: Maximum traces to return (default 100)

        Returns:
            List of error TraceRecord objects, newest first
        """
        try:
            if not self._db.connection:
                self._db.connect()

            cursor = self._db.connection.cursor()  # type: ignore[union-attr]
            cursor.execute(
                """
                SELECT tool_use_id, trace_id, session_id, tool_name, tool_input,
                       tool_output, start_time, end_time, duration_ms, status,
                       error_message, parent_tool_use_id
                FROM tool_traces
                WHERE session_id = ? AND (status IN ('failed', 'timeout', 'cancelled')
                                          OR error_message IS NOT NULL)
                ORDER BY start_time DESC
                LIMIT ?
            """,
                (session_id, limit),
            )

            rows = cursor.fetchall()
            return [self._row_to_trace(row) for row in rows]
        except Exception as e:
            logger.info(f"Error getting error traces: {e}")
            return []
