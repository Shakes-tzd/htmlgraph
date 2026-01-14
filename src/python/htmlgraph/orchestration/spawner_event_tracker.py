"""Spawner event tracking helper for internal activity tracking in spawned sessions.

This module provides utilities for tracking internal activities within spawner agents
and linking them to parent delegation events for observability in HtmlGraph.

Usage:
    from htmlgraph.orchestration.spawner_event_tracker import SpawnerEventTracker

    tracker = SpawnerEventTracker(
        delegation_event_id="event-abc123",
        parent_agent="orchestrator",
        spawner_type="gemini"
    )

    # Track initialization phase
    init_event = tracker.record_phase("Initializing Spawner", spawned_agent="gemini-2.0-flash")

    # Track execution phase
    exec_event = tracker.record_phase("Executing Gemini", tool_name="gemini-cli")
    tracker.complete_phase(exec_event["event_id"], output_summary="Generated output...")

    # Track completion
    tracker.record_completion(success=True, response="Result here")
"""

import os
import time
import uuid
from typing import Any


class SpawnerEventTracker:
    """Track internal activities in spawner agents with parent-child linking."""

    def __init__(
        self,
        delegation_event_id: str | None = None,
        parent_agent: str = "orchestrator",
        spawner_type: str = "generic",
        session_id: str | None = None,
    ):
        """
        Initialize spawner event tracker.

        Args:
            delegation_event_id: Parent delegation event ID to link to
            parent_agent: Agent that initiated the spawning
            spawner_type: Type of spawner (gemini, codex, copilot)
            session_id: Session ID for events
        """
        self.delegation_event_id = delegation_event_id
        self.parent_agent = parent_agent
        self.spawner_type = spawner_type
        self.session_id = session_id or f"session-{uuid.uuid4().hex[:8]}"
        self.db = None
        self.phase_events: dict[str, dict[str, Any]] = {}
        self.start_time = time.time()

        # Try to initialize database for event tracking
        try:
            from htmlgraph.config import get_database_path
            from htmlgraph.db.schema import HtmlGraphDB

            # Get correct database path from environment or project root
            db_path = get_database_path()

            if db_path.exists():
                self.db = HtmlGraphDB(str(db_path))
        except Exception:
            # Tracking is optional, continue without it
            pass

    def record_phase(
        self,
        phase_name: str,
        spawned_agent: str | None = None,
        tool_name: str | None = None,
        input_summary: str | None = None,
        status: str = "running",
        parent_phase_event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Record the start of a phase in spawner execution.

        Args:
            phase_name: Human-readable phase name (e.g., "Initializing Spawner")
            spawned_agent: Agent being spawned (optional)
            tool_name: Tool being executed (optional)
            input_summary: Summary of input (optional)
            status: Current status (running, completed, failed)
            parent_phase_event_id: Parent phase event ID for proper nesting (optional)

        Returns:
            Event dictionary with event_id and metadata
        """
        if not self.db:
            return {}

        event_id = f"event-{uuid.uuid4().hex[:8]}"
        event_type = "tool_call"

        try:
            context = {
                "phase_name": phase_name,
                "spawner_type": self.spawner_type,
                "parent_delegation_event": self.delegation_event_id,
            }
            if spawned_agent:
                context["spawned_agent"] = spawned_agent
            if tool_name:
                context["tool"] = tool_name

            # Use parent_phase_event_id if provided, otherwise use delegation_event_id
            actual_parent_event_id = parent_phase_event_id or self.delegation_event_id

            self.db.insert_event(
                event_id=event_id,
                agent_id=spawned_agent or self.parent_agent,
                event_type=event_type,
                session_id=self.session_id,
                tool_name=tool_name
                or f"HeadlessSpawner.{phase_name.replace(' ', '_').lower()}",
                input_summary=input_summary or phase_name,
                context=context,
                parent_event_id=actual_parent_event_id,
                subagent_type=self.spawner_type,
            )

            event = {
                "event_id": event_id,
                "phase_name": phase_name,
                "spawned_agent": spawned_agent,
                "tool_name": tool_name,
                "status": status,
                "start_time": time.time(),
            }
            self.phase_events[event_id] = event
            return event

        except Exception:
            # Non-fatal - tracking is best-effort
            return {}

    def complete_phase(
        self,
        event_id: str,
        output_summary: str | None = None,
        status: str = "completed",
        execution_duration: float | None = None,
    ) -> bool:
        """
        Mark a phase as completed with results.

        Args:
            event_id: Event ID from record_phase
            output_summary: Summary of output/result
            status: Final status (completed, failed)
            execution_duration: Execution time in seconds (auto-calculated if not provided)

        Returns:
            True if update successful, False otherwise
        """
        if not self.db or not event_id:
            return False

        try:
            if execution_duration is None and event_id in self.phase_events:
                execution_duration = (
                    time.time() - self.phase_events[event_id]["start_time"]
                )

            if self.db.connection is None:
                return False

            cursor = self.db.connection.cursor()
            cursor.execute(
                """
                UPDATE agent_events
                SET output_summary = ?, status = ?, execution_duration_seconds = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE event_id = ?
            """,
                (output_summary, status, execution_duration or 0.0, event_id),
            )
            self.db.connection.commit()

            if event_id in self.phase_events:
                self.phase_events[event_id]["status"] = status
                self.phase_events[event_id]["output_summary"] = output_summary

            return True
        except Exception:
            # Non-fatal
            return False

    def record_completion(
        self,
        success: bool,
        response: str | None = None,
        error: str | None = None,
        tokens_used: int = 0,
        cost: float = 0.0,
    ) -> dict[str, Any]:
        """
        Record final completion with overall results.

        Args:
            success: Whether execution succeeded
            response: Successful response/output
            error: Error message if failed
            tokens_used: Tokens consumed
            cost: Execution cost

        Returns:
            Completion event dictionary
        """
        total_duration = time.time() - self.start_time

        completion_event: dict[str, Any] = {
            "success": success,
            "duration": total_duration,
            "tokens": tokens_used,
            "cost": cost,
            "phase_count": len(self.phase_events),
        }

        if success:
            completion_event["response"] = response
        else:
            completion_event["error"] = error

        return completion_event

    def get_phase_events(self) -> dict[str, dict[str, Any]]:
        """Get all recorded phase events."""
        return self.phase_events

    def record_tool_call(
        self,
        tool_name: str,
        tool_input: dict | None,
        phase_event_id: str,
        spawned_agent: str | None = None,
    ) -> dict[str, Any]:
        """
        Record a tool call within a spawned execution phase.

        Args:
            tool_name: Name of the tool (bash, read_file, write_file, etc.)
            tool_input: Input parameters to the tool
            phase_event_id: Parent phase event ID to link to
            spawned_agent: Agent making the tool call (optional)

        Returns:
            Event dictionary with event_id and metadata
        """
        if not self.db:
            return {}

        event_id = f"event-{uuid.uuid4().hex[:8]}"

        try:
            context = {
                "tool_name": tool_name,
                "spawner_type": self.spawner_type,
                "parent_phase_event": phase_event_id,
            }
            if spawned_agent:
                context["spawned_agent"] = spawned_agent

            self.db.insert_event(
                event_id=event_id,
                agent_id=spawned_agent or self.parent_agent,
                event_type="tool_call",
                session_id=self.session_id,
                tool_name=tool_name,
                input_summary=(
                    str(tool_input)[:200] if tool_input else f"Call to {tool_name}"
                ),
                context=context,
                parent_event_id=phase_event_id,
                subagent_type=self.spawner_type,
            )

            tool_event = {
                "event_id": event_id,
                "tool_name": tool_name,
                "tool_input": tool_input,
                "phase_event_id": phase_event_id,
                "spawned_agent": spawned_agent,
                "status": "running",
                "start_time": time.time(),
            }
            return tool_event

        except Exception:
            # Non-fatal - tracking is best-effort
            return {}

    def complete_tool_call(
        self,
        event_id: str,
        output_summary: str | None = None,
        success: bool = True,
    ) -> bool:
        """
        Mark a tool call as complete with results.

        Args:
            event_id: Event ID from record_tool_call
            output_summary: Summary of tool output/result
            success: Whether the tool call succeeded

        Returns:
            True if update successful, False otherwise
        """
        if not self.db or not event_id:
            return False

        try:
            if self.db.connection is None:
                return False

            cursor = self.db.connection.cursor()
            cursor.execute(
                """
                UPDATE agent_events
                SET output_summary = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE event_id = ?
            """,
                (
                    output_summary,
                    "completed" if success else "failed",
                    event_id,
                ),
            )
            self.db.connection.commit()
            return True
        except Exception:
            # Non-fatal
            return False

    def get_event_hierarchy(self) -> dict[str, Any]:
        """
        Get the event hierarchy for this spawner execution.

        Returns:
            Dictionary with delegation event as root and phases as children
        """
        return {
            "delegation_event_id": self.delegation_event_id,
            "spawner_type": self.spawner_type,
            "session_id": self.session_id,
            "total_duration": time.time() - self.start_time,
            "phase_events": self.phase_events,
        }


def create_tracker_from_env(
    spawner_type: str = "generic",
) -> SpawnerEventTracker:
    """
    Create a SpawnerEventTracker from environment variables.

    Reads HTMLGRAPH_PARENT_EVENT, HTMLGRAPH_PARENT_AGENT, HTMLGRAPH_PARENT_SESSION
    from environment to link to parent context.

    Args:
        spawner_type: Type of spawner (gemini, codex, copilot)

    Returns:
        Initialized SpawnerEventTracker
    """
    delegation_event_id = os.getenv("HTMLGRAPH_PARENT_EVENT")
    parent_agent = os.getenv("HTMLGRAPH_PARENT_AGENT", "orchestrator")
    session_id = os.getenv("HTMLGRAPH_PARENT_SESSION")

    return SpawnerEventTracker(
        delegation_event_id=delegation_event_id,
        parent_agent=parent_agent,
        spawner_type=spawner_type,
        session_id=session_id,
    )
