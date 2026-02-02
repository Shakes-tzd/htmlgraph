"""
Broadcast Integration Helper - SDK to Broadcast Bridge

Provides helper functions to integrate broadcasting with SDK operations.
Handles the bridge between synchronous SDK calls and async broadcast operations.
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Get existing event loop or create new one if none exists."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, create a new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop


def broadcast_feature_save(
    feature_id: str,
    agent_id: str,
    session_id: str,
    payload: dict[str, Any],
    is_new: bool = False,
) -> None:
    """
    Broadcast feature save operation to all sessions.

    This is a synchronous wrapper that can be called from SDK save() methods.
    It handles async event loop creation and broadcasting.

    Args:
        feature_id: Feature being saved
        agent_id: Agent making the change
        session_id: Source session ID
        payload: Feature data (title, status, description, etc.)
        is_new: True if creating new feature, False if updating
    """
    try:
        # Import here to avoid circular dependencies
        from pathlib import Path

        from htmlgraph.api.broadcast import CrossSessionBroadcaster
        from htmlgraph.api.websocket import WebSocketManager

        # Get database path
        db_path = str(Path.home() / ".htmlgraph" / "htmlgraph.db")

        # Create WebSocketManager and Broadcaster instances
        # Note: These are lightweight, stateless for broadcasting
        websocket_manager = WebSocketManager(db_path)
        broadcaster = CrossSessionBroadcaster(websocket_manager, db_path)

        # Determine event type
        event_type = "created" if is_new else "updated"
        payload["event_type"] = event_type

        # Run async broadcast in event loop
        loop = get_or_create_event_loop()

        if loop.is_running():
            # We're already in an async context, schedule task
            asyncio.create_task(
                broadcaster.broadcast_feature_update(
                    feature_id=feature_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    payload=payload,
                )
            )
            # Don't wait for completion to avoid blocking
            logger.debug(
                f"Scheduled broadcast task for feature {feature_id} (async context)"
            )
        else:
            # Not in async context, run until complete
            clients_notified = loop.run_until_complete(
                broadcaster.broadcast_feature_update(
                    feature_id=feature_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    payload=payload,
                )
            )
            logger.info(
                f"Broadcast feature {feature_id} {event_type} to {clients_notified} clients"
            )

    except Exception as e:
        # Never fail the save due to broadcast error
        logger.warning(f"Failed to broadcast feature save: {e}")


def broadcast_status_change(
    feature_id: str,
    old_status: str,
    new_status: str,
    agent_id: str,
    session_id: str,
) -> None:
    """
    Broadcast feature status change to all sessions.

    Synchronous wrapper for async broadcast operation.

    Args:
        feature_id: Feature being updated
        old_status: Previous status
        new_status: New status
        agent_id: Agent making change
        session_id: Source session
    """
    try:
        from pathlib import Path

        from htmlgraph.api.broadcast import CrossSessionBroadcaster
        from htmlgraph.api.websocket import WebSocketManager

        db_path = str(Path.home() / ".htmlgraph" / "htmlgraph.db")
        websocket_manager = WebSocketManager(db_path)
        broadcaster = CrossSessionBroadcaster(websocket_manager, db_path)

        loop = get_or_create_event_loop()

        if loop.is_running():
            asyncio.create_task(
                broadcaster.broadcast_status_change(
                    feature_id=feature_id,
                    old_status=old_status,
                    new_status=new_status,
                    agent_id=agent_id,
                    session_id=session_id,
                )
            )
            logger.debug(f"Scheduled status change broadcast for {feature_id}")
        else:
            clients_notified = loop.run_until_complete(
                broadcaster.broadcast_status_change(
                    feature_id=feature_id,
                    old_status=old_status,
                    new_status=new_status,
                    agent_id=agent_id,
                    session_id=session_id,
                )
            )
            logger.info(
                f"Broadcast status change for {feature_id}: {old_status} → {new_status} "
                f"to {clients_notified} clients"
            )

    except Exception as e:
        logger.warning(f"Failed to broadcast status change: {e}")


def broadcast_link_added(
    feature_id: str,
    linked_feature_id: str,
    link_type: str,
    agent_id: str,
    session_id: str,
) -> None:
    """
    Broadcast feature link addition to all sessions.

    Synchronous wrapper for async broadcast operation.

    Args:
        feature_id: Source feature
        linked_feature_id: Target feature
        link_type: Type of relationship
        agent_id: Agent making change
        session_id: Source session
    """
    try:
        from pathlib import Path

        from htmlgraph.api.broadcast import CrossSessionBroadcaster
        from htmlgraph.api.websocket import WebSocketManager

        db_path = str(Path.home() / ".htmlgraph" / "htmlgraph.db")
        websocket_manager = WebSocketManager(db_path)
        broadcaster = CrossSessionBroadcaster(websocket_manager, db_path)

        loop = get_or_create_event_loop()

        if loop.is_running():
            asyncio.create_task(
                broadcaster.broadcast_link_added(
                    feature_id=feature_id,
                    linked_feature_id=linked_feature_id,
                    link_type=link_type,
                    agent_id=agent_id,
                    session_id=session_id,
                )
            )
            logger.debug(f"Scheduled link broadcast for {feature_id}")
        else:
            clients_notified = loop.run_until_complete(
                broadcaster.broadcast_link_added(
                    feature_id=feature_id,
                    linked_feature_id=linked_feature_id,
                    link_type=link_type,
                    agent_id=agent_id,
                    session_id=session_id,
                )
            )
            logger.info(
                f"Broadcast link addition for {feature_id} → {linked_feature_id} "
                f"({link_type}) to {clients_notified} clients"
            )

    except Exception as e:
        logger.warning(f"Failed to broadcast link addition: {e}")
