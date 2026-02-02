"""
Git-based synchronization for multi-device continuity.

Enables automatic sync of .htmlgraph/ directory across devices via Git.
"""

from .git_sync import (
    GitSyncManager,
    SyncConfig,
    SyncResult,
    SyncStatus,
    SyncStrategy,
)

__all__ = [
    "GitSyncManager",
    "SyncConfig",
    "SyncStrategy",
    "SyncStatus",
    "SyncResult",
]
