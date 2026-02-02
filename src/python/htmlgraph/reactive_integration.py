"""
Reactive Query Integration - Connect to Event Pipeline

Integrates reactive queries with the broadcast system to automatically
invalidate queries when resources (features, events, sessions) are updated.

This module provides the glue between:
- Broadcast events (resource updates)
- Reactive query manager (query invalidation)
- Event tracker (tool call tracking)

When a resource is updated:
1. Broadcast event is fired
2. This module catches it
3. Reactive query manager invalidates dependent queries
4. Query subscribers receive new results via WebSocket
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Global reactive query manager instance
_reactive_query_manager: Any = None


def set_reactive_query_manager(manager: Any) -> None:
    """
    Set global reactive query manager instance.

    Args:
        manager: ReactiveQueryManager instance
    """
    global _reactive_query_manager
    _reactive_query_manager = manager
    logger.info("Reactive query manager registered for event integration")


def get_reactive_query_manager() -> Any | None:
    """
    Get global reactive query manager instance.

    Returns:
        ReactiveQueryManager instance or None if not initialized
    """
    return _reactive_query_manager


async def on_broadcast_event(event: dict[str, Any]) -> None:
    """
    Called when a broadcast event occurs.

    Invalidates queries that depend on the updated resource.

    Args:
        event: Broadcast event data
    """
    if not _reactive_query_manager:
        return

    resource_id = event.get("resource_id")
    resource_type = event.get("resource_type")

    if resource_id and resource_type:
        try:
            await _reactive_query_manager.on_resource_updated(
                resource_id, resource_type
            )
            logger.debug(
                f"Reactive queries invalidated for {resource_type}:{resource_id}"
            )
        except Exception as e:
            logger.error(f"Error invalidating queries for {resource_id}: {e}")


async def on_tool_call_complete(
    session_id: str,
    tool_name: str,
    feature_id: str | None = None,
) -> None:
    """
    Called when a tool call completes.

    Invalidates queries that depend on the affected resources.

    Args:
        session_id: Session ID
        tool_name: Tool that was called
        feature_id: Feature ID if applicable
    """
    if not _reactive_query_manager:
        return

    try:
        # Tool calls affect events
        await _reactive_query_manager.on_resource_updated(session_id, "event")

        # If feature involved, invalidate feature queries
        if feature_id:
            await _reactive_query_manager.on_resource_updated(feature_id, "feature")

        logger.debug(
            f"Reactive queries invalidated for tool call: {tool_name} "
            f"(session={session_id}, feature={feature_id})"
        )

    except Exception as e:
        logger.error(f"Error invalidating queries for tool call: {e}")


async def on_session_start(session_id: str, agent_id: str) -> None:
    """
    Called when a session starts.

    Invalidates queries that depend on sessions.

    Args:
        session_id: Session ID
        agent_id: Agent ID
    """
    if not _reactive_query_manager:
        return

    try:
        await _reactive_query_manager.on_resource_updated(session_id, "session")
        logger.debug(f"Reactive queries invalidated for session start: {session_id}")
    except Exception as e:
        logger.error(f"Error invalidating queries for session start: {e}")


async def on_session_end(session_id: str) -> None:
    """
    Called when a session ends.

    Invalidates queries that depend on sessions.

    Args:
        session_id: Session ID
    """
    if not _reactive_query_manager:
        return

    try:
        await _reactive_query_manager.on_resource_updated(session_id, "session")
        logger.debug(f"Reactive queries invalidated for session end: {session_id}")
    except Exception as e:
        logger.error(f"Error invalidating queries for session end: {e}")
