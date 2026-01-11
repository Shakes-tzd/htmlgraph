"""
Live Event Publisher for Real-Time WebSocket Streaming.

This module provides a centralized way to publish live events that will be
streamed to connected WebSocket clients in real-time. Events are stored in
a SQLite table and polled by the WebSocket handler.

Usage:
    from htmlgraph.orchestration.live_events import LiveEventPublisher

    publisher = LiveEventPublisher()
    publisher.spawner_start("gemini", "Analyze codebase", parent_event_id="evt-123")
    publisher.spawner_phase("gemini", "executing", progress=50)
    publisher.spawner_complete("gemini", success=True, duration=15.3, response="...")
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LiveEventPublisher:
    """
    Publisher for live events that get streamed via WebSocket.

    Events are written to the live_events table in SQLite and polled
    by the dashboard WebSocket handler for real-time streaming.
    """

    def __init__(self, db_path: str | None = None):
        """
        Initialize the live event publisher.

        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        self._db_path = db_path
        self._db: Any = None

    def _get_db(self) -> Any:
        """Get or create database connection."""
        if self._db is None:
            try:
                from htmlgraph.db.schema import HtmlGraphDB

                if self._db_path:
                    self._db = HtmlGraphDB(self._db_path)
                else:
                    # Use project database path from environment or cwd
                    project_root = os.getenv("HTMLGRAPH_PROJECT_ROOT", os.getcwd())
                    default_path = str(
                        Path(project_root) / ".htmlgraph" / "index.sqlite"
                    )

                    # Check if database exists
                    if not Path(default_path).exists():
                        logger.debug(f"Database not found at {default_path}")
                        return None

                    self._db = HtmlGraphDB(default_path)
            except Exception as e:
                logger.warning(f"Failed to initialize database for live events: {e}")
                return None
        return self._db

    def _get_session_id(self) -> str | None:
        """Get current session ID from environment."""
        return os.getenv("HTMLGRAPH_PARENT_SESSION") or os.getenv("CLAUDE_SESSION_ID")

    def publish(
        self,
        event_type: str,
        event_data: dict[str, Any],
        parent_event_id: str | None = None,
        session_id: str | None = None,
        spawner_type: str | None = None,
    ) -> int | None:
        """
        Publish a live event for WebSocket streaming.

        Args:
            event_type: Type of event (e.g., spawner_start, spawner_complete)
            event_data: Event payload dictionary
            parent_event_id: Parent event ID for hierarchical linking
            session_id: Session this event belongs to
            spawner_type: Spawner type if applicable (gemini, codex, copilot)

        Returns:
            Live event ID if successful, None otherwise
        """
        db = self._get_db()
        if db is None:
            logger.debug("Database not available for live events")
            return None

        # Add timestamp to event data if not present
        if "timestamp" not in event_data:
            event_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Use session from environment if not provided
        if session_id is None:
            session_id = self._get_session_id()

        try:
            result: int | None = db.insert_live_event(
                event_type=event_type,
                event_data=event_data,
                parent_event_id=parent_event_id,
                session_id=session_id,
                spawner_type=spawner_type,
            )
            return result
        except Exception as e:
            logger.warning(f"Failed to publish live event: {e}")
            return None

    def spawner_start(
        self,
        spawner_type: str,
        prompt: str,
        parent_event_id: str | None = None,
        model: str | None = None,
        session_id: str | None = None,
    ) -> int | None:
        """
        Publish a spawner start event.

        Args:
            spawner_type: Type of spawner (gemini, codex, copilot)
            prompt: Task prompt being executed
            parent_event_id: Parent delegation event ID
            model: Model being used (optional)
            session_id: Session ID (optional, auto-detected)

        Returns:
            Live event ID if successful
        """
        event_data = {
            "spawner_type": spawner_type,
            "prompt_preview": prompt[:200] if prompt else "",
            "prompt_length": len(prompt) if prompt else 0,
            "status": "started",
            "phase": "initializing",
        }
        if model:
            event_data["model"] = model

        return self.publish(
            event_type="spawner_start",
            event_data=event_data,
            parent_event_id=parent_event_id,
            session_id=session_id,
            spawner_type=spawner_type,
        )

    def spawner_phase(
        self,
        spawner_type: str,
        phase: str,
        progress: int | None = None,
        details: str | None = None,
        parent_event_id: str | None = None,
        session_id: str | None = None,
    ) -> int | None:
        """
        Publish a spawner phase update event.

        Args:
            spawner_type: Type of spawner (gemini, codex, copilot)
            phase: Current phase (e.g., "executing", "processing", "streaming")
            progress: Progress percentage (0-100) if applicable
            details: Additional details about the phase
            parent_event_id: Parent delegation event ID
            session_id: Session ID (optional, auto-detected)

        Returns:
            Live event ID if successful
        """
        event_data: dict[str, Any] = {
            "spawner_type": spawner_type,
            "phase": phase,
            "status": "in_progress",
        }
        if progress is not None:
            event_data["progress"] = progress
        if details:
            event_data["details"] = details[:200]

        return self.publish(
            event_type="spawner_phase",
            event_data=event_data,
            parent_event_id=parent_event_id,
            session_id=session_id,
            spawner_type=spawner_type,
        )

    def spawner_complete(
        self,
        spawner_type: str,
        success: bool,
        duration_seconds: float | None = None,
        response_preview: str | None = None,
        tokens_used: int | None = None,
        error: str | None = None,
        parent_event_id: str | None = None,
        session_id: str | None = None,
    ) -> int | None:
        """
        Publish a spawner completion event.

        Args:
            spawner_type: Type of spawner (gemini, codex, copilot)
            success: Whether the spawner completed successfully
            duration_seconds: Execution duration in seconds
            response_preview: Preview of the response (first 200 chars)
            tokens_used: Number of tokens used
            error: Error message if failed
            parent_event_id: Parent delegation event ID
            session_id: Session ID (optional, auto-detected)

        Returns:
            Live event ID if successful
        """
        event_data: dict[str, Any] = {
            "spawner_type": spawner_type,
            "success": success,
            "status": "completed" if success else "failed",
            "phase": "done",
        }
        if duration_seconds is not None:
            event_data["duration_seconds"] = round(duration_seconds, 2)
        if response_preview:
            event_data["response_preview"] = response_preview[:200]
        if tokens_used is not None:
            event_data["tokens_used"] = tokens_used
        if error:
            event_data["error"] = error[:500]

        return self.publish(
            event_type="spawner_complete",
            event_data=event_data,
            parent_event_id=parent_event_id,
            session_id=session_id,
            spawner_type=spawner_type,
        )

    def spawner_tool_use(
        self,
        spawner_type: str,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
        parent_event_id: str | None = None,
        session_id: str | None = None,
    ) -> int | None:
        """
        Publish a spawner tool use event (when spawned AI uses a tool).

        Args:
            spawner_type: Type of spawner (gemini, codex, copilot)
            tool_name: Name of the tool being used
            tool_input: Tool input parameters
            parent_event_id: Parent delegation event ID
            session_id: Session ID (optional, auto-detected)

        Returns:
            Live event ID if successful
        """
        event_data: dict[str, Any] = {
            "spawner_type": spawner_type,
            "tool_name": tool_name,
            "status": "tool_use",
            "phase": "executing",
        }
        if tool_input:
            # Truncate tool input for preview
            input_str = json.dumps(tool_input)
            event_data["tool_input_preview"] = input_str[:200]

        return self.publish(
            event_type="spawner_tool_use",
            event_data=event_data,
            parent_event_id=parent_event_id,
            session_id=session_id,
            spawner_type=spawner_type,
        )

    def spawner_message(
        self,
        spawner_type: str,
        message: str,
        role: str = "assistant",
        parent_event_id: str | None = None,
        session_id: str | None = None,
    ) -> int | None:
        """
        Publish a spawner message event (when spawned AI sends a message).

        Args:
            spawner_type: Type of spawner (gemini, codex, copilot)
            message: Message content
            role: Message role (assistant, user, system)
            parent_event_id: Parent delegation event ID
            session_id: Session ID (optional, auto-detected)

        Returns:
            Live event ID if successful
        """
        event_data = {
            "spawner_type": spawner_type,
            "message_preview": message[:200] if message else "",
            "message_length": len(message) if message else 0,
            "role": role,
            "status": "streaming",
            "phase": "responding",
        }

        return self.publish(
            event_type="spawner_message",
            event_data=event_data,
            parent_event_id=parent_event_id,
            session_id=session_id,
            spawner_type=spawner_type,
        )


# Global singleton instance for convenience
_publisher: LiveEventPublisher | None = None


def get_publisher(db_path: str | None = None) -> LiveEventPublisher:
    """
    Get the global LiveEventPublisher instance.

    Args:
        db_path: Optional database path (only used on first call)

    Returns:
        LiveEventPublisher instance
    """
    global _publisher
    if _publisher is None:
        _publisher = LiveEventPublisher(db_path)
    return _publisher


def publish_live_event(
    event_type: str,
    event_data: dict[str, Any],
    parent_event_id: str | None = None,
    session_id: str | None = None,
    spawner_type: str | None = None,
) -> int | None:
    """
    Convenience function to publish a live event using the global publisher.

    Args:
        event_type: Type of event
        event_data: Event payload
        parent_event_id: Parent event ID
        session_id: Session ID
        spawner_type: Spawner type

    Returns:
        Live event ID if successful
    """
    return get_publisher().publish(
        event_type=event_type,
        event_data=event_data,
        parent_event_id=parent_event_id,
        session_id=session_id,
        spawner_type=spawner_type,
    )
