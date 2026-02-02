"""
Broadcast WebSocket Endpoint - Real-time Cross-Session Updates

WebSocket endpoint for receiving broadcast events from other sessions.
Clients subscribe to get notified when features/tracks/spikes are updated.
"""

import logging
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from htmlgraph.api.broadcast import BroadcastEventType
from htmlgraph.api.websocket import EventSubscriptionFilter, WebSocketManager

logger = logging.getLogger(__name__)


async def websocket_broadcasts_endpoint(
    websocket: WebSocket,
    websocket_manager: WebSocketManager,
    get_db: Any,
) -> None:
    """
    WebSocket endpoint for cross-session broadcast events.

    Clients connect and receive real-time notifications when:
    - Features are created/updated/deleted
    - Tracks are updated
    - Spikes are updated
    - Status changes occur
    - Links are added

    Example client code:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/broadcasts');
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'broadcast_event') {
            handleBroadcastEvent(msg);
        }
    };
    ```

    Args:
        websocket: FastAPI WebSocket connection
        websocket_manager: WebSocketManager for event distribution
        get_db: Database connection factory
    """
    client_id = str(uuid.uuid4())

    # Create subscription filter for broadcast events
    subscription_filter = EventSubscriptionFilter(
        event_types=[
            "broadcast_event",
            BroadcastEventType.FEATURE_UPDATED.value,
            BroadcastEventType.FEATURE_CREATED.value,
            BroadcastEventType.FEATURE_DELETED.value,
            BroadcastEventType.TRACK_UPDATED.value,
            BroadcastEventType.SPIKE_UPDATED.value,
            BroadcastEventType.STATUS_CHANGED.value,
            BroadcastEventType.LINK_ADDED.value,
            BroadcastEventType.COMMENT_ADDED.value,
        ]
    )

    # Connect to global broadcast channel
    # Note: Using "broadcasts" as a pseudo-session ID for global channel
    connected = await websocket_manager.connect(
        websocket=websocket,
        session_id="broadcasts",
        client_id=client_id,
        subscription_filter=subscription_filter,
    )

    if not connected:
        logger.warning(f"Failed to connect broadcast client {client_id}")
        return

    logger.info(f"Broadcast client connected: {client_id}")

    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (for heartbeat/ping)
                data = await websocket.receive_text()

                # Handle client messages
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data == "subscribe":
                    # Client can request initial state sync here
                    await websocket.send_json(
                        {
                            "type": "subscribed",
                            "client_id": client_id,
                            "message": "Connected to broadcast channel",
                        }
                    )
                else:
                    logger.debug(f"Received message from client {client_id}: {data}")

            except WebSocketDisconnect:
                logger.info(f"Broadcast client disconnected: {client_id}")
                break
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                break

    finally:
        # Cleanup on disconnect
        await websocket_manager.disconnect("broadcasts", client_id)
        logger.info(f"Broadcast client cleanup completed: {client_id}")
