"""
Broadcast API Routes - Cross-Session Synchronization

REST API endpoints for broadcasting feature/track/spike updates
across all active sessions.
"""

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from htmlgraph.api.broadcast import CrossSessionBroadcaster

logger = logging.getLogger(__name__)


class FeatureUpdateRequest(BaseModel):
    """Request model for feature update broadcasts."""

    title: str | None = None
    status: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    priority: str | None = None


class StatusChangeRequest(BaseModel):
    """Request model for status change broadcasts."""

    new_status: str


class LinkAddRequest(BaseModel):
    """Request model for link addition broadcasts."""

    linked_feature_id: str
    link_type: str


def create_broadcast_router(
    broadcaster: CrossSessionBroadcaster,
    get_db: Any,
) -> APIRouter:
    """
    Create broadcast API router with dependency injection.

    Args:
        broadcaster: CrossSessionBroadcaster instance
        get_db: Database connection factory

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/broadcast", tags=["broadcast"])

    @router.post("/features/{feature_id}")
    async def broadcast_feature_update(
        feature_id: str,
        update: FeatureUpdateRequest,
        agent_id: str = Header(..., alias="X-Agent-ID"),
        session_id: str = Header(..., alias="X-Session-ID"),
    ) -> dict[str, Any]:
        """
        Broadcast feature update to all sessions.

        Headers:
        - X-Agent-ID: Agent making the change
        - X-Session-ID: Source session ID

        Body:
        ```json
        {
            "title": "new title",
            "status": "in_progress",
            "description": "updated description",
            "tags": ["api", "backend"],
            "priority": "high"
        }
        ```

        Returns:
        ```json
        {
            "success": true,
            "feature_id": "feat-123",
            "clients_notified": 5,
            "timestamp": "2025-01-01T12:00:00"
        }
        ```
        """
        # Validate feature exists
        try:
            db = await get_db()
            try:
                cursor = await db.execute(
                    "SELECT id FROM nodes WHERE id = ? AND type = 'feature'",
                    [feature_id],
                )
                if not await cursor.fetchone():
                    raise HTTPException(
                        status_code=404, detail=f"Feature {feature_id} not found"
                    )
            finally:
                await db.close()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error checking feature: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        # Build payload from request
        payload = {}
        if update.title is not None:
            payload["title"] = update.title
        if update.status is not None:
            payload["status"] = update.status
        if update.description is not None:
            payload["description"] = update.description
        if update.tags is not None:
            payload["tags"] = ",".join(update.tags) if update.tags else ""
        if update.priority is not None:
            payload["priority"] = update.priority

        # Broadcast update
        clients_notified = await broadcaster.broadcast_feature_update(
            feature_id=feature_id,
            agent_id=agent_id,
            session_id=session_id,
            payload=payload,
        )

        from datetime import datetime

        return {
            "success": True,
            "feature_id": feature_id,
            "clients_notified": clients_notified,
            "timestamp": datetime.now().isoformat(),
        }

    @router.post("/features/{feature_id}/status")
    async def update_feature_status(
        feature_id: str,
        request: StatusChangeRequest,
        agent_id: str = Header(..., alias="X-Agent-ID"),
        session_id: str = Header(..., alias="X-Session-ID"),
    ) -> dict[str, Any]:
        """
        Update feature status and broadcast to all sessions.

        Valid statuses: todo, in_progress, blocked, done
        """
        # Validate status
        valid_statuses = ["todo", "in_progress", "blocked", "done"]
        if request.new_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {request.new_status}. Must be one of {valid_statuses}",
            )

        # Get current status
        try:
            db = await get_db()
            try:
                cursor = await db.execute(
                    "SELECT status FROM nodes WHERE id = ? AND type = 'feature'",
                    [feature_id],
                )
                row = await cursor.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=404, detail=f"Feature {feature_id} not found"
                    )

                old_status = row[0] if row[0] else "todo"
            finally:
                await db.close()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error fetching feature status: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        # Broadcast status change
        clients_notified = await broadcaster.broadcast_status_change(
            feature_id=feature_id,
            old_status=old_status,
            new_status=request.new_status,
            agent_id=agent_id,
            session_id=session_id,
        )

        from datetime import datetime

        return {
            "success": True,
            "feature_id": feature_id,
            "old_status": old_status,
            "new_status": request.new_status,
            "clients_notified": clients_notified,
            "timestamp": datetime.now().isoformat(),
        }

    @router.post("/features/{feature_id}/links")
    async def add_feature_link(
        feature_id: str,
        request: LinkAddRequest,
        agent_id: str = Header(..., alias="X-Agent-ID"),
        session_id: str = Header(..., alias="X-Session-ID"),
    ) -> dict[str, Any]:
        """
        Add feature link and broadcast to all sessions.

        Valid link types: depends_on, blocks, related
        """
        # Validate link type
        valid_link_types = ["depends_on", "blocks", "related"]
        if request.link_type not in valid_link_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid link type: {request.link_type}. Must be one of {valid_link_types}",
            )

        # Validate both features exist
        try:
            db = await get_db()
            try:
                cursor = await db.execute(
                    "SELECT id FROM nodes WHERE id IN (?, ?) AND type = 'feature'",
                    [feature_id, request.linked_feature_id],
                )
                rows = await cursor.fetchall()
                if len(rows) != 2:
                    raise HTTPException(
                        status_code=404, detail="One or both features not found"
                    )
            finally:
                await db.close()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error validating features: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        # Broadcast link addition
        clients_notified = await broadcaster.broadcast_link_added(
            feature_id=feature_id,
            linked_feature_id=request.linked_feature_id,
            link_type=request.link_type,
            agent_id=agent_id,
            session_id=session_id,
        )

        from datetime import datetime

        return {
            "success": True,
            "feature_id": feature_id,
            "linked_feature_id": request.linked_feature_id,
            "link_type": request.link_type,
            "clients_notified": clients_notified,
            "timestamp": datetime.now().isoformat(),
        }

    @router.post("/tracks/{track_id}")
    async def broadcast_track_update(
        track_id: str,
        update: dict[str, Any],
        agent_id: str = Header(..., alias="X-Agent-ID"),
        session_id: str = Header(..., alias="X-Session-ID"),
    ) -> dict[str, Any]:
        """Broadcast track update to all sessions."""
        # Validate track exists
        try:
            db = await get_db()
            try:
                cursor = await db.execute(
                    "SELECT id FROM nodes WHERE id = ? AND type = 'track'",
                    [track_id],
                )
                if not await cursor.fetchone():
                    raise HTTPException(
                        status_code=404, detail=f"Track {track_id} not found"
                    )
            finally:
                await db.close()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error checking track: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        # Broadcast update
        clients_notified = await broadcaster.broadcast_track_update(
            track_id=track_id,
            agent_id=agent_id,
            session_id=session_id,
            payload=update,
        )

        from datetime import datetime

        return {
            "success": True,
            "track_id": track_id,
            "clients_notified": clients_notified,
            "timestamp": datetime.now().isoformat(),
        }

    @router.post("/spikes/{spike_id}")
    async def broadcast_spike_update(
        spike_id: str,
        update: dict[str, Any],
        agent_id: str = Header(..., alias="X-Agent-ID"),
        session_id: str = Header(..., alias="X-Session-ID"),
    ) -> dict[str, Any]:
        """Broadcast spike update to all sessions."""
        # Validate spike exists
        try:
            db = await get_db()
            try:
                cursor = await db.execute(
                    "SELECT id FROM nodes WHERE id = ? AND type = 'spike'",
                    [spike_id],
                )
                if not await cursor.fetchone():
                    raise HTTPException(
                        status_code=404, detail=f"Spike {spike_id} not found"
                    )
            finally:
                await db.close()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error checking spike: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        # Broadcast update
        clients_notified = await broadcaster.broadcast_spike_update(
            spike_id=spike_id,
            agent_id=agent_id,
            session_id=session_id,
            payload=update,
        )

        from datetime import datetime

        return {
            "success": True,
            "spike_id": spike_id,
            "clients_notified": clients_notified,
            "timestamp": datetime.now().isoformat(),
        }

    return router
