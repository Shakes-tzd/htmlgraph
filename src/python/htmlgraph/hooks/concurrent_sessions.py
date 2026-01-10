"""
Concurrent Session Detection and Formatting.

Provides utilities to detect other active sessions and format them
for injection into the orchestrator's context at session start.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from htmlgraph.db.schema import HtmlGraphDB


def get_concurrent_sessions(
    db: HtmlGraphDB,
    current_session_id: str,
    minutes: int = 30,
) -> list[dict[str, Any]]:
    """
    Get other sessions that are currently active.

    Args:
        db: Database connection
        current_session_id: Current session to exclude
        minutes: Look back window for activity

    Returns:
        List of concurrent session dicts with id, agent_id, last_user_query, etc.
    """
    if not db.connection:
        db.connect()

    try:
        cursor = db.connection.cursor()  # type: ignore[union-attr]
        # Use datetime format that matches database (without timezone)
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor.execute(
            """
            SELECT
                session_id as id,
                agent_assigned as agent_id,
                created_at,
                status,
                (SELECT input_summary FROM agent_events
                 WHERE session_id = sessions.session_id
                 ORDER BY timestamp DESC LIMIT 1) as last_user_query,
                (SELECT timestamp FROM agent_events
                 WHERE session_id = sessions.session_id
                 ORDER BY timestamp DESC LIMIT 1) as last_user_query_at
            FROM sessions
            WHERE status = 'active'
              AND session_id != ?
              AND created_at > ?
            ORDER BY created_at DESC
            """,
            (current_session_id, cutoff),
        )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception:  # pragma: no cover
        # Gracefully handle database errors
        return []


def format_concurrent_sessions_markdown(sessions: list[dict[str, Any]]) -> str:
    """
    Format concurrent sessions as markdown for context injection.

    Args:
        sessions: List of session dicts from get_concurrent_sessions

    Returns:
        Markdown formatted string for system prompt injection
    """
    if not sessions:
        return ""

    lines = ["## Concurrent Sessions (Active Now)", ""]

    for session in sessions:
        session_id = session.get("id", "unknown")
        session_id = session_id[:12] if len(session_id) > 12 else session_id
        agent = session.get("agent_id", "unknown")
        query = session.get("last_user_query", "No recent query")
        last_active = session.get("last_user_query_at")

        # Calculate time ago
        time_ago = "unknown"
        if last_active:
            try:
                last_dt = datetime.fromisoformat(
                    last_active.replace("Z", "+00:00")
                    if isinstance(last_active, str)
                    else last_active
                )
                delta = datetime.now(timezone.utc) - last_dt
                if delta.total_seconds() < 60:
                    time_ago = "just now"
                elif delta.total_seconds() < 3600:
                    time_ago = f"{int(delta.total_seconds() // 60)} min ago"
                else:
                    time_ago = f"{int(delta.total_seconds() // 3600)} hours ago"
            except (ValueError, TypeError, AttributeError):
                time_ago = "unknown"

        # Truncate query for display
        query_display = (
            query[:50] + "..." if query and len(query) > 50 else (query or "Unknown")
        )

        lines.append(f'- **{session_id}** ({agent}): "{query_display}" - {time_ago}')

    lines.append("")
    lines.append("*Coordinate with concurrent sessions to avoid duplicate work.*")
    lines.append("")

    return "\n".join(lines)


def get_recent_completed_sessions(
    db: HtmlGraphDB,
    hours: int = 24,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Get recently completed sessions for handoff context.

    Args:
        db: Database connection
        hours: Look back window
        limit: Maximum sessions to return

    Returns:
        List of recently completed session dicts
    """
    if not db.connection:
        db.connect()

    try:
        cursor = db.connection.cursor()  # type: ignore[union-attr]
        # Use datetime format that matches database (without timezone)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cursor.execute(
            """
            SELECT session_id as id, agent_assigned as agent_id, created_at as started_at,
                   completed_at, total_events,
                   (SELECT input_summary FROM agent_events
                    WHERE session_id = sessions.session_id
                    ORDER BY timestamp DESC LIMIT 1) as last_user_query
            FROM sessions
            WHERE status = 'completed'
              AND completed_at > ?
            ORDER BY completed_at DESC
            LIMIT ?
            """,
            (cutoff, limit),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception:  # pragma: no cover
        # Gracefully handle database errors
        return []


def format_recent_work_markdown(sessions: list[dict[str, Any]]) -> str:
    """
    Format recently completed sessions as markdown.

    Args:
        sessions: List of completed session dicts

    Returns:
        Markdown formatted string
    """
    if not sessions:
        return ""

    lines = ["## Recent Work (Last 24 Hours)", ""]

    for session in sessions:
        session_id = session.get("id", "unknown")
        session_id = session_id[:12] if len(session_id) > 12 else session_id
        query = session.get("last_user_query", "No query recorded")
        total_events = session.get("total_events") or 0

        query_display = (
            query[:60] + "..." if query and len(query) > 60 else (query or "Unknown")
        )

        lines.append(f"- `{session_id}`: {query_display} ({total_events} events)")

    lines.append("")

    return "\n".join(lines)


__all__ = [
    "get_concurrent_sessions",
    "format_concurrent_sessions_markdown",
    "get_recent_completed_sessions",
    "format_recent_work_markdown",
]
