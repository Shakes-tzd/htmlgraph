from __future__ import annotations

"""Event and analytics index operations for HtmlGraph."""


from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EventRebuildResult:
    """Result of rebuilding the event index."""

    db_path: Path
    inserted: int
    skipped: int


@dataclass(frozen=True)
class EventStats:
    """Statistics about events in the system."""

    total_events: int
    session_count: int
    file_count: int


@dataclass(frozen=True)
class EventQueryResult:
    """Result of querying events."""

    events: list[dict[str, Any]]
    total: int


@dataclass(frozen=True)
class EventExportResult:
    """Result of exporting sessions to JSONL."""

    written: int
    skipped: int
    failed: int


class EventOperationError(RuntimeError):
    """Base error for event operations."""


def export_sessions(*, graph_dir: Path, overwrite: bool = False) -> EventExportResult:
    """
    Export legacy session HTML logs to JSONL events.

    Args:
        graph_dir: Path to .htmlgraph directory
        overwrite: Whether to overwrite existing JSONL files

    Returns:
        EventExportResult with counts of written, skipped, failed files

    Raises:
        EventOperationError: If graph_dir doesn't exist or isn't a directory
    """
    if not graph_dir.exists():
        raise EventOperationError(f"Graph directory not found: {graph_dir}")
    if not graph_dir.is_dir():
        raise EventOperationError(f"Not a directory: {graph_dir}")

    from htmlgraph.event_migration import export_sessions_to_jsonl

    sessions_dir = graph_dir / "sessions"
    events_dir = graph_dir / "events"

    if not sessions_dir.exists():
        raise EventOperationError(f"Sessions directory not found: {sessions_dir}")

    try:
        result = export_sessions_to_jsonl(
            sessions_dir=sessions_dir,
            events_dir=events_dir,
            overwrite=overwrite,
            include_subdirs=False,
        )
        return EventExportResult(
            written=result["written"],
            skipped=result["skipped"],
            failed=result["failed"],
        )
    except Exception as e:
        raise EventOperationError(f"Failed to export sessions: {e}") from e


def rebuild_index(*, graph_dir: Path) -> EventRebuildResult:
    """
    Rebuild the SQLite analytics index from JSONL events.

    Args:
        graph_dir: Path to .htmlgraph directory

    Returns:
        EventRebuildResult with db_path and counts of inserted/skipped events

    Raises:
        EventOperationError: If events directory doesn't exist or rebuild fails
    """
    if not graph_dir.exists():
        raise EventOperationError(f"Graph directory not found: {graph_dir}")
    if not graph_dir.is_dir():
        raise EventOperationError(f"Not a directory: {graph_dir}")

    from htmlgraph.analytics_index import AnalyticsIndex
    from htmlgraph.event_log import JsonlEventLog

    events_dir = graph_dir / "events"
    db_path = graph_dir / "index.sqlite"

    if not events_dir.exists():
        raise EventOperationError(f"Events directory not found: {events_dir}")

    try:
        log = JsonlEventLog(events_dir)
        index = AnalyticsIndex(db_path)

        # Stream events from all JSONL files
        events = (event for _, event in log.iter_events())
        result = index.rebuild_from_events(events)

        return EventRebuildResult(
            db_path=db_path,
            inserted=result["inserted"],
            skipped=result["skipped"],
        )
    except Exception as e:
        raise EventOperationError(f"Failed to rebuild index: {e}") from e


def query_events(
    *,
    graph_dir: Path,
    session_id: str | None = None,
    tool: str | None = None,
    feature_id: str | None = None,
    since: str | None = None,
    limit: int | None = None,
) -> EventQueryResult:
    """
    Query events from JSONL logs with optional filters.

    Args:
        graph_dir: Path to .htmlgraph directory
        session_id: Filter by session ID (None = all sessions)
        tool: Filter by tool name (e.g., 'Bash', 'Edit')
        feature_id: Filter by attributed feature ID
        since: Only events after this timestamp (ISO string)
        limit: Maximum number of events to return

    Returns:
        EventQueryResult with matching events and total count

    Raises:
        EventOperationError: If events directory doesn't exist or query fails
    """
    if not graph_dir.exists():
        raise EventOperationError(f"Graph directory not found: {graph_dir}")
    if not graph_dir.is_dir():
        raise EventOperationError(f"Not a directory: {graph_dir}")

    from htmlgraph.event_log import JsonlEventLog

    events_dir = graph_dir / "events"

    if not events_dir.exists():
        raise EventOperationError(f"Events directory not found: {events_dir}")

    try:
        log = JsonlEventLog(events_dir)
        events = log.query_events(
            session_id=session_id,
            tool=tool,
            feature_id=feature_id,
            since=since,
            limit=limit,
        )

        return EventQueryResult(
            events=events,
            total=len(events),
        )
    except Exception as e:
        raise EventOperationError(f"Failed to query events: {e}") from e


def get_event_stats(*, graph_dir: Path) -> EventStats:
    """
    Get statistics about events in the system.

    Args:
        graph_dir: Path to .htmlgraph directory

    Returns:
        EventStats with counts of total events, sessions, and files

    Raises:
        EventOperationError: If events directory doesn't exist or stats collection fails
    """
    if not graph_dir.exists():
        raise EventOperationError(f"Graph directory not found: {graph_dir}")
    if not graph_dir.is_dir():
        raise EventOperationError(f"Not a directory: {graph_dir}")

    from htmlgraph.event_log import JsonlEventLog

    events_dir = graph_dir / "events"

    if not events_dir.exists():
        # No events directory means no events
        return EventStats(
            total_events=0,
            session_count=0,
            file_count=0,
        )

    try:
        log = JsonlEventLog(events_dir)

        # Count total events and track unique sessions
        total_events = 0
        sessions: set[str] = set()

        for _, event in log.iter_events():
            total_events += 1
            if session_id := event.get("session_id"):
                sessions.add(session_id)

        # Count JSONL files
        file_count = len(list(events_dir.glob("*.jsonl")))

        return EventStats(
            total_events=total_events,
            session_count=len(sessions),
            file_count=file_count,
        )
    except Exception as e:
        raise EventOperationError(f"Failed to get event stats: {e}") from e
