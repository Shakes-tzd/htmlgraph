"""
Reactive Query API Routes - WebSocket and HTTP Endpoints

Provides API endpoints for:
- WebSocket subscriptions to reactive queries
- HTTP endpoints for query management
- Query listing and metadata

Example WebSocket usage:
    const ws = new WebSocket('ws://localhost:8000/ws/query/features_by_status');
    ws.onmessage = (event) => {
        const result = JSON.parse(event.data);
        // result contains: { type: "query_state", query_id, rows, row_count, ... }
        updateDashboard(result);
    };

Example HTTP usage:
    GET /api/query/features_by_status
    Returns: { query_id, timestamp, rows, row_count, execution_time_ms }

    GET /api/queries
    Returns: { queries: [...] }
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Global reactive query manager instance (set by main app)
reactive_query_manager: Any = None


def set_reactive_query_manager(manager: Any) -> None:
    """Set global reactive query manager instance."""
    global reactive_query_manager
    reactive_query_manager = manager


def create_reactive_routes() -> APIRouter:
    """Create FastAPI router for reactive query endpoints."""
    router = APIRouter(prefix="/api", tags=["reactive-queries"])

    @router.websocket("/ws/query/{query_id}")
    async def websocket_query_endpoint(websocket: WebSocket, query_id: str) -> None:
        """
        WebSocket endpoint for reactive query subscriptions.

        Client receives:
        - Initial query result on connection
        - Updates whenever query result changes

        Args:
            websocket: FastAPI WebSocket connection
            query_id: Query to subscribe to
        """
        if reactive_query_manager is None:
            logger.error("ReactiveQueryManager not initialized")
            await websocket.close(code=1011)  # Internal error
            return

        client_id = str(uuid.uuid4())

        try:
            await websocket.accept()

            # Subscribe to query
            initial_result = await reactive_query_manager.subscribe_to_query(
                query_id, client_id
            )

            if initial_result is None:
                logger.warning(f"Query not found: {query_id}")
                await websocket.close(code=1008)  # Policy violation (not found)
                return

            # Send initial result
            await websocket.send_json(
                {
                    "type": "query_state",
                    **initial_result.to_dict(),
                }
            )

            logger.info(
                f"Client {client_id} subscribed to query {query_id}, "
                f"sent {initial_result.row_count} rows"
            )

            # Keep connection open to receive updates
            # Updates are pushed from server via broadcast
            while True:
                try:
                    # Receive heartbeat/ping from client
                    data = await websocket.receive_text()

                    if data == "ping":
                        await websocket.send_json({"type": "pong"})
                    else:
                        logger.debug(f"Received message from {client_id}: {data}")

                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")
                    break

        except Exception as e:
            logger.error(f"WebSocket error for query {query_id}: {e}")

        finally:
            # Cleanup
            reactive_query_manager.unsubscribe_from_query(query_id, client_id)
            logger.info(f"Client {client_id} unsubscribed from query {query_id}")

    @router.get("/query/{query_id}")
    async def get_query_result(query_id: str) -> dict[str, Any]:
        """
        Get current result of a query (HTTP endpoint).

        Args:
            query_id: Query to retrieve

        Returns:
            Query result with rows and metadata

        Raises:
            HTTPException: If query not found
        """
        if reactive_query_manager is None:
            raise HTTPException(
                status_code=500, detail="ReactiveQueryManager not initialized"
            )

        result = await reactive_query_manager.get_query_result(query_id)

        if result is None:
            raise HTTPException(status_code=404, detail=f"Query not found: {query_id}")

        result_dict: dict[str, Any] = result.to_dict()
        return result_dict

    @router.get("/queries")
    async def list_queries() -> dict[str, Any]:
        """
        List all registered queries.

        Returns:
            Dictionary with list of queries and metadata
        """
        if reactive_query_manager is None:
            raise HTTPException(
                status_code=500, detail="ReactiveQueryManager not initialized"
            )

        queries = reactive_query_manager.list_queries()

        return {
            "queries": queries,
            "count": len(queries),
        }

    @router.post("/query/{query_id}/invalidate")
    async def invalidate_query(query_id: str) -> dict[str, Any]:
        """
        Manually invalidate a query (force re-execution).

        Args:
            query_id: Query to invalidate

        Returns:
            Success message

        Raises:
            HTTPException: If query not found
        """
        if reactive_query_manager is None:
            raise HTTPException(
                status_code=500, detail="ReactiveQueryManager not initialized"
            )

        if query_id not in reactive_query_manager.queries:
            raise HTTPException(status_code=404, detail=f"Query not found: {query_id}")

        await reactive_query_manager.invalidate_query(query_id)

        return {
            "status": "success",
            "message": f"Query {query_id} invalidated",
        }

    return router
