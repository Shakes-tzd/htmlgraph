"""
API routes for Git sync management.

Provides REST endpoints for manual sync triggers, status queries, and configuration.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from htmlgraph.sync import GitSyncManager, SyncStrategy

router = APIRouter(prefix="/api/sync", tags=["sync"])

# Global sync manager (initialized by server startup)
sync_manager: GitSyncManager | None = None


def init_sync_manager(manager: GitSyncManager) -> None:
    """Initialize the global sync manager."""
    global sync_manager
    sync_manager = manager


@router.post("/push")
async def trigger_push(force: bool = False) -> dict[str, Any]:
    """
    Manually trigger push to remote.

    Args:
        force: Force push even if recently pushed

    Returns:
        Sync result dictionary

    Raises:
        HTTPException: If sync manager not initialized
    """
    if sync_manager is None:
        raise HTTPException(status_code=503, detail="Sync manager not initialized")

    result = await sync_manager.push(force=force)
    return result.to_dict()


@router.post("/pull")
async def trigger_pull(force: bool = False) -> dict[str, Any]:
    """
    Manually trigger pull from remote.

    Args:
        force: Force pull even if recently pulled

    Returns:
        Sync result dictionary

    Raises:
        HTTPException: If sync manager not initialized
    """
    if sync_manager is None:
        raise HTTPException(status_code=503, detail="Sync manager not initialized")

    result = await sync_manager.pull(force=force)
    return result.to_dict()


@router.get("/status")
async def get_sync_status() -> dict[str, Any]:
    """
    Get current sync status.

    Returns:
        Status dictionary with sync state and config

    Raises:
        HTTPException: If sync manager not initialized
    """
    if sync_manager is None:
        raise HTTPException(status_code=503, detail="Sync manager not initialized")

    return sync_manager.get_status()


@router.get("/history")
async def get_sync_history(limit: int = 50) -> dict[str, Any]:
    """
    Get sync operation history.

    Args:
        limit: Maximum number of results

    Returns:
        Dictionary with history list

    Raises:
        HTTPException: If sync manager not initialized
    """
    if sync_manager is None:
        raise HTTPException(status_code=503, detail="Sync manager not initialized")

    return {"history": sync_manager.get_sync_history(limit)}


@router.post("/config")
async def update_sync_config(
    push_interval: int | None = None,
    pull_interval: int | None = None,
    conflict_strategy: str | None = None,
) -> dict[str, Any]:
    """
    Update sync configuration.

    Args:
        push_interval: Push interval in seconds
        pull_interval: Pull interval in seconds
        conflict_strategy: Conflict resolution strategy

    Returns:
        Success status and updated config

    Raises:
        HTTPException: If sync manager not initialized or invalid parameters
    """
    if sync_manager is None:
        raise HTTPException(status_code=503, detail="Sync manager not initialized")

    try:
        if push_interval is not None:
            if push_interval < 10:
                raise ValueError("Push interval must be >= 10 seconds")
            sync_manager.config.push_interval_seconds = push_interval

        if pull_interval is not None:
            if pull_interval < 10:
                raise ValueError("Pull interval must be >= 10 seconds")
            sync_manager.config.pull_interval_seconds = pull_interval

        if conflict_strategy is not None:
            sync_manager.config.conflict_strategy = SyncStrategy(conflict_strategy)

        return {"success": True, "config": sync_manager.get_status()["config"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/start")
async def start_background_sync() -> dict[str, Any]:
    """
    Start background sync service.

    Returns:
        Success status

    Raises:
        HTTPException: If sync manager not initialized
    """
    if sync_manager is None:
        raise HTTPException(status_code=503, detail="Sync manager not initialized")

    # Start in background (don't await)
    import asyncio

    asyncio.create_task(sync_manager.start_background_sync())

    return {"success": True, "message": "Background sync started"}


@router.post("/stop")
async def stop_background_sync() -> dict[str, Any]:
    """
    Stop background sync service.

    Returns:
        Success status

    Raises:
        HTTPException: If sync manager not initialized
    """
    if sync_manager is None:
        raise HTTPException(status_code=503, detail="Sync manager not initialized")

    await sync_manager.stop_background_sync()

    return {"success": True, "message": "Background sync stopped"}
