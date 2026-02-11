"""
Presence and WebSocket routes for HtmlGraph API.

Handles:
- Real-time event streaming via WebSocket
- Agent presence tracking
- Presence widget demo
- Live event broadcasting
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from htmlgraph.api.dependencies import Dependencies

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependencies will be set by main.py
_deps: Dependencies | None = None
_db_path: str | None = None


def init_presence_routes(deps: Dependencies, db_path: str) -> None:
    """Initialize presence routes with dependencies."""
    global _deps, _db_path
    _deps = deps
    _db_path = db_path


def get_deps() -> Dependencies:
    """Get dependencies instance, raising error if not initialized."""
    if _deps is None:
        raise RuntimeError("Presence routes not initialized.")
    return _deps


def get_db_path() -> str:
    """Get database path, raising error if not initialized."""
    if _db_path is None:
        raise RuntimeError("Presence routes not initialized.")
    return _db_path


# ========== PRESENCE WIDGET DEMO (Phase 6) ==========


@router.get("/views/presence-widget", response_class=HTMLResponse)
async def presence_widget_demo() -> HTMLResponse:
    """Phase 6 Demo: Real-time Presence Widget showing active agents across sessions."""
    widget_path = Path(__file__).parent.parent / "static" / "presence-widget-demo.html"
    if widget_path.exists():
        return HTMLResponse(content=widget_path.read_text())
    else:
        raise HTTPException(status_code=404, detail="Presence widget demo not found")


# ========== PRESENCE TRACKING API ==========


@router.get("/api/presence")
async def get_all_presence() -> dict[str, Any]:
    """Get current presence state for all agents."""
    try:
        from htmlgraph.api.presence import PresenceManager

        db_path = get_db_path()
        presence_mgr = PresenceManager(db_path=db_path)
        agents = presence_mgr.get_all_presence()

        return {
            "agents": [agent.to_dict() for agent in agents],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting presence: {e}")
        return {"agents": [], "timestamp": datetime.now().isoformat()}


@router.get("/api/presence/{agent_id}")
async def get_agent_presence(agent_id: str) -> dict[str, Any]:
    """Get presence for specific agent."""
    try:
        from htmlgraph.api.presence import PresenceManager

        db_path = get_db_path()
        presence_mgr = PresenceManager(db_path=db_path)
        presence = presence_mgr.get_agent_presence(agent_id)

        if not presence:
            raise HTTPException(status_code=404, detail="Agent not found")

        return presence.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent presence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== WEBSOCKET FOR REAL-TIME UPDATES ==========


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket, since: str | None = None) -> None:
    """WebSocket endpoint for real-time event streaming.

    OPTIMIZATION: Uses timestamp-based filtering to minimize data transfers.
    The timestamp > ? filter with DESC index makes queries O(log n) instead of O(n).

    FIX 3: Now supports loading historical events via 'since' parameter.
    - If 'since' provided: Load events from that timestamp onwards
    - If 'since' not provided: Load events from last 24 hours (default)
    - After historical load: Continue streaming real-time events

    LIVE EVENTS: Also polls live_events table for real-time spawner activity
    streaming. These events are marked as broadcast after sending and cleaned up.
    """
    await websocket.accept()
    deps = get_deps()

    # FIX 3: Determine starting timestamp
    if since:
        try:
            datetime.fromisoformat(since.replace("Z", "+00:00"))
            last_timestamp = since
        except (ValueError, AttributeError):
            last_timestamp = (datetime.now() - timedelta(hours=24)).isoformat()
    else:
        last_timestamp = (datetime.now() - timedelta(hours=24)).isoformat()

    # FIX 3: Load historical events first (before real-time streaming)
    db = await deps.get_db()
    try:
        historical_query = """
            SELECT event_id, agent_id, event_type, timestamp, tool_name,
                   input_summary, output_summary, session_id, status, model,
                   parent_event_id, execution_duration_seconds, context,
                   cost_tokens
            FROM agent_events
            WHERE timestamp >= ? AND timestamp < datetime('now')
            ORDER BY datetime(REPLACE(SUBSTR(timestamp, 1, 19), 'T', ' ')) DESC
            LIMIT 1000
        """
        cursor = await db.execute(historical_query, [last_timestamp])
        historical_rows = await cursor.fetchall()

        if historical_rows:
            historical_rows_list = list(historical_rows)
            for row in historical_rows_list:
                row_list = list(row)
                context_data = {}
                if row_list[12]:
                    try:
                        context_data = json.loads(row_list[12])
                    except (json.JSONDecodeError, TypeError):
                        pass

                event_data = {
                    "type": "event",
                    "event_id": row_list[0],
                    "agent_id": row_list[1] or "unknown",
                    "event_type": row_list[2],
                    "timestamp": row_list[3],
                    "tool_name": row_list[4],
                    "input_summary": row_list[5],
                    "output_summary": row_list[6],
                    "session_id": row_list[7],
                    "status": row_list[8],
                    "model": row_list[9],
                    "parent_event_id": row_list[10],
                    "execution_duration_seconds": row_list[11] or 0.0,
                    "cost_tokens": row_list[13] or 0,
                    "context": context_data,
                }
                await websocket.send_json(event_data)

            last_timestamp = historical_rows_list[-1][3]

    except Exception as e:
        logger.error(f"Error loading historical events: {e}")
    finally:
        await db.close()

    # Update to current time for real-time streaming
    last_timestamp = datetime.now().isoformat()
    poll_interval = 0.5
    last_live_event_id = 0

    try:
        while True:
            db = await deps.get_db()
            has_activity = False
            try:
                # ===== 1. Poll agent_events (existing logic) =====
                query = """
                    SELECT event_id, agent_id, event_type, timestamp, tool_name,
                           input_summary, output_summary, session_id, status, model,
                           parent_event_id, execution_duration_seconds, context,
                           cost_tokens
                    FROM agent_events
                    WHERE timestamp > ?
                    ORDER BY datetime(REPLACE(SUBSTR(timestamp, 1, 19), 'T', ' ')) DESC
                    LIMIT 100
                """

                cursor = await db.execute(query, [last_timestamp])
                rows = await cursor.fetchall()

                if rows:
                    has_activity = True
                    rows_list: list[list[Any]] = [list(row) for row in rows]
                    last_timestamp = rows_list[-1][3]

                    for event_row in rows_list:
                        context_data = {}
                        if event_row[12]:
                            try:
                                context_data = json.loads(event_row[12])
                            except (json.JSONDecodeError, TypeError):
                                pass

                        event_data = {
                            "type": "event",
                            "event_id": event_row[0],
                            "agent_id": event_row[1] or "unknown",
                            "event_type": event_row[2],
                            "timestamp": event_row[3],
                            "tool_name": event_row[4],
                            "input_summary": event_row[5],
                            "output_summary": event_row[6],
                            "session_id": event_row[7],
                            "status": event_row[8],
                            "model": event_row[9],
                            "parent_event_id": event_row[10],
                            "execution_duration_seconds": event_row[11] or 0.0,
                            "cost_tokens": event_row[13] or 0,
                            "context": context_data,
                        }
                        await websocket.send_json(event_data)

                # ===== 2. Poll live_events for spawner streaming =====
                live_query = """
                    SELECT id, event_type, event_data, parent_event_id,
                           session_id, spawner_type, created_at
                    FROM live_events
                    WHERE broadcast_at IS NULL AND id > ?
                    ORDER BY created_at ASC
                    LIMIT 50
                """
                live_cursor = await db.execute(live_query, [last_live_event_id])
                live_rows = list(await live_cursor.fetchall())

                if live_rows:
                    logger.info(
                        f"[WebSocket] Found {len(live_rows)} pending live_events to broadcast"
                    )
                    has_activity = True
                    broadcast_ids: list[int] = []

                    for live_row in live_rows:
                        live_id: int = live_row[0]
                        event_type: str = live_row[1]
                        event_data_json: str | None = live_row[2]
                        parent_event_id: str | None = live_row[3]
                        session_id: str | None = live_row[4]
                        spawner_type: str | None = live_row[5]
                        created_at: str = live_row[6]

                        try:
                            event_data_parsed = (
                                json.loads(event_data_json) if event_data_json else {}
                            )
                        except (json.JSONDecodeError, TypeError):
                            event_data_parsed = {}

                        spawner_event = {
                            "type": "spawner_event",
                            "live_event_id": live_id,
                            "event_type": event_type,
                            "spawner_type": spawner_type,
                            "parent_event_id": parent_event_id,
                            "session_id": session_id,
                            "timestamp": created_at,
                            "data": event_data_parsed,
                        }
                        logger.info(
                            f"[WebSocket] Sending spawner_event: id={live_id}, type={event_type}, spawner={spawner_type}"
                        )
                        await websocket.send_json(spawner_event)

                        broadcast_ids.append(live_id)
                        last_live_event_id = max(last_live_event_id, live_id)

                    if broadcast_ids:
                        logger.info(
                            f"[WebSocket] Marking {len(broadcast_ids)} events as broadcast: {broadcast_ids}"
                        )
                        placeholders = ",".join("?" for _ in broadcast_ids)
                        await db.execute(
                            f"""
                            UPDATE live_events
                            SET broadcast_at = CURRENT_TIMESTAMP
                            WHERE id IN ({placeholders})
                            """,
                            broadcast_ids,
                        )
                        await db.commit()

                # ===== 3. Periodic cleanup of old broadcast events =====
                if random.random() < 0.1:
                    await db.execute(
                        """
                        DELETE FROM live_events
                        WHERE broadcast_at IS NOT NULL
                          AND created_at < datetime('now', '-5 minutes')
                        """
                    )
                    await db.commit()

                # Adjust poll interval based on activity
                if has_activity:
                    poll_interval = 0.3
                else:
                    poll_interval = min(poll_interval * 1.2, 2.0)

            finally:
                await db.close()

            await asyncio.sleep(poll_interval)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011)


@router.websocket("/ws/presence")
async def websocket_presence(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time agent presence updates."""
    client_id = f"presence-{int(time.time() * 1000)}"
    db_path = get_db_path()

    try:
        await websocket.accept()
        logger.info(f"Presence WebSocket client connected: {client_id}")

        from htmlgraph.api.presence import PresenceManager

        presence_mgr = PresenceManager(db_path=db_path)
        initial_presence = presence_mgr.get_all_presence()

        await websocket.send_json(
            {
                "type": "presence_state",
                "agents": [p.to_dict() for p in initial_presence],
                "timestamp": datetime.now().isoformat(),
            }
        )

        poll_interval = 1.0

        while True:
            await asyncio.sleep(poll_interval)

            current_presence = presence_mgr.get_all_presence()

            await websocket.send_json(
                {
                    "type": "presence_update",
                    "agents": [p.to_dict() for p in current_presence],
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except WebSocketDisconnect:
        logger.info(f"Presence WebSocket client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Presence WebSocket error: {e}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
