"""
Testing routes for HtmlGraph API.

Handles:
- Test event injection (development only)
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from htmlgraph.api.dependencies import Dependencies

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependencies will be set by main.py
_deps: Dependencies | None = None


def init_testing_routes(deps: Dependencies) -> None:
    """Initialize testing routes with dependencies."""
    global _deps
    _deps = deps


def get_deps() -> Dependencies:
    """Get dependencies instance, raising error if not initialized."""
    if _deps is None:
        raise RuntimeError("Testing routes not initialized.")
    return _deps


@router.post("/api/test-event")
async def test_event_injection(request: Request) -> dict[str, str]:
    """
    Test endpoint for injecting events during development.

    This endpoint allows the test harness to inject events that will be
    broadcast to all connected WebSocket clients, simulating real agent activity.

    Body should be an event object with:
    - event_id: str
    - tool_name: str
    - agent_id: str
    - timestamp: str
    - input_summary: str (optional)
    - execution_duration_seconds: float (optional)
    - status: str (optional)
    - parent_event_id: str (optional)
    - model: str (optional)
    - feature_id: str (optional)
    """
    deps = get_deps()
    try:
        event_data = await request.json()

        # Insert into agent_events table
        db = await deps.get_db()
        try:
            # Generate session_id if not provided
            session_id = event_data.get("session_id", "test-session")

            await db.execute(
                """
                INSERT INTO agent_events (
                    event_id, tool_name, agent_id, timestamp,
                    input_summary, execution_duration_seconds, status,
                    parent_event_id, model, feature_id, session_id,
                    event_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    event_data.get("event_id"),
                    event_data.get("tool_name"),
                    event_data.get("agent_id"),
                    event_data.get("timestamp"),
                    event_data.get("input_summary"),
                    event_data.get("execution_duration_seconds", 0.0),
                    event_data.get("status", "recorded"),
                    event_data.get("parent_event_id"),
                    event_data.get("model"),
                    event_data.get("feature_id"),
                    session_id,
                    "tool_call",
                ],
            )
            await db.commit()

            logger.info(
                f"[TestEvent] Injected event: {event_data.get('event_id')} ({event_data.get('tool_name')})"
            )

            return {
                "status": "ok",
                "message": f"Event {event_data.get('event_id')} injected successfully",
            }
        finally:
            await db.close()

    except Exception as e:
        logger.error(f"[TestEvent] Error injecting event: {e}")
        raise HTTPException(status_code=500, detail=str(e))
