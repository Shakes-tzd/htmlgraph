"""
Task attribution mixin for SDK - subagent work tracking.

Provides methods for tracking which subagent did what work.
"""

from __future__ import annotations

from typing import Any


class TaskAttributionMixin:
    """
    Mixin providing task attribution capabilities to SDK.

    Tracks which subagent executed what work for observability.
    """

    def get_task_attribution(self, task_id: str) -> dict[str, Any]:
        """
        Get attribution - which subagent did what work in this task?

        Queries the database to find all events associated with a Claude Code task,
        showing which subagent executed each tool call.

        Args:
            task_id: Claude Code's internal task ID (available from Task() response)

        Returns:
            Dictionary with task_id, by_subagent mapping, and total_events count

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.get_task_attribution("task-abc123-xyz789")
            >>> for subagent, events in result['by_subagent'].items():
            ...     logger.info(f"{subagent}:")
            ...     for event in events:
            ...         logger.info(f"  - {event['tool']}: {event['summary']}")
            >>> logger.info(f"Total events: {result['total_events']}")

        See also:
            get_subagent_work: Get all work grouped by subagent in a session
        """
        from htmlgraph.config import get_database_path
        from htmlgraph.db.schema import HtmlGraphDB

        try:
            db = HtmlGraphDB(str(get_database_path()))
            events = db.get_events_for_task(task_id)

            # Group by subagent_type
            by_subagent: dict[str, list[dict[str, Any]]] = {}
            for event in events:
                agent = event.get("subagent_type", "orchestrator")
                if agent not in by_subagent:
                    by_subagent[agent] = []
                by_subagent[agent].append(
                    {
                        "tool": event.get("tool_name"),
                        "summary": event.get("input_summary"),
                        "timestamp": event.get("created_at"),
                        "event_id": event.get("event_id"),
                        "success": not event.get("is_error", False),
                    }
                )

            return {
                "task_id": task_id,
                "by_subagent": by_subagent,
                "total_events": len(events),
            }
        except Exception as e:
            return {
                "task_id": task_id,
                "by_subagent": {},
                "total_events": 0,
                "error": str(e),
            }

    def get_subagent_work(self, session_id: str) -> dict[str, list[dict[str, Any]]]:
        """
        Get all work grouped by which subagent did it in a session.

        Shows which subagent (researcher, general-purpose, etc.) executed each
        tool call within a session.

        Args:
            session_id: Session ID to analyze

        Returns:
            Dictionary mapping subagent_type to list of events they executed.
            Each event includes: tool_name, input_summary, output_summary, created_at, event_id

        Example:
            >>> sdk = SDK(agent="claude")
            >>> work = sdk.get_subagent_work("sess-123")
            >>> for subagent, events in work.items():
            ...     logger.info(f"{subagent} ({len(events)} events):")
            ...     for event in events:
            ...         logger.info(f"  - {event['tool_name']}: {event['input_summary']}")

        See also:
            get_task_attribution: Get work for a specific Claude Code task
            analyze_session: Get session metrics and analytics
        """
        from htmlgraph.config import get_database_path
        from htmlgraph.db.schema import HtmlGraphDB

        try:
            db = HtmlGraphDB(str(get_database_path()))
            return db.get_subagent_work(session_id)
        except Exception:
            return {}
