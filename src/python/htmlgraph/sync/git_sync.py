"""
Git-based synchronization manager for multi-device continuity.

Provides automatic push/pull of .htmlgraph/ directory with conflict resolution.
"""

import asyncio
import logging
import socket
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SyncStrategy(str, Enum):
    """Conflict resolution strategies."""

    AUTO_MERGE = "auto_merge"  # Let git auto-merge
    ABORT_ON_CONFLICT = "abort_on_conflict"  # Fail if conflicts
    OURS = "ours"  # Keep local on conflict
    THEIRS = "theirs"  # Take remote on conflict


class SyncStatus(str, Enum):
    """Current sync operation status."""

    IDLE = "idle"
    PUSHING = "pushing"
    PULLING = "pulling"
    CONFLICT = "conflict"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class SyncConfig:
    """Configuration for Git sync."""

    push_interval_seconds: int = 300  # 5 min
    pull_interval_seconds: int = 60  # 1 min
    remote_name: str = "origin"
    branch_name: str = "main"
    conflict_strategy: SyncStrategy = SyncStrategy.AUTO_MERGE
    auto_stash: bool = True  # Stash uncommitted changes before pull
    sync_path: str = ".htmlgraph"  # Path to sync within repo


@dataclass
class SyncResult:
    """Result of a sync operation."""

    status: SyncStatus
    operation: str  # "push" or "pull"
    timestamp: datetime
    files_changed: int = 0
    conflicts: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "files_changed": self.files_changed,
            "conflicts": self.conflicts,
            "message": self.message,
        }


class GitSyncManager:
    """Manages automatic Git sync of .htmlgraph/ directory."""

    def __init__(self, repo_root: str, config: SyncConfig | None = None):
        """
        Initialize Git sync manager.

        Args:
            repo_root: Path to git repository root
            config: Sync configuration (uses defaults if None)
        """
        self.repo_root = Path(repo_root)
        self.htmlgraph_dir = self.repo_root / ".htmlgraph"
        self.config = config or SyncConfig()
        self.last_push: datetime | None = None
        self.last_pull: datetime | None = None
        self.status = SyncStatus.IDLE
        self.sync_history: list[SyncResult] = []
        self._running = False
        self._push_task: asyncio.Task | None = None
        self._pull_task: asyncio.Task | None = None

    async def start_background_sync(self) -> None:
        """Start background sync tasks."""
        if self._running:
            logger.warning("Background sync already running")
            return

        logger.info("Starting background sync service...")
        self._running = True

        # Create sync tasks
        self._push_task = asyncio.create_task(self._push_loop())
        self._pull_task = asyncio.create_task(self._pull_loop())

        # Wait for both tasks
        try:
            await asyncio.gather(self._push_task, self._pull_task)
        except asyncio.CancelledError:
            logger.info("Background sync cancelled")

    async def stop_background_sync(self) -> None:
        """Stop background sync tasks."""
        logger.info("Stopping background sync service...")
        self._running = False

        if self._push_task:
            self._push_task.cancel()
            try:
                await self._push_task
            except asyncio.CancelledError:
                pass

        if self._pull_task:
            self._pull_task.cancel()
            try:
                await self._pull_task
            except asyncio.CancelledError:
                pass

    async def _push_loop(self) -> None:
        """Periodically push changes to remote."""
        while self._running:
            try:
                await asyncio.sleep(self.config.push_interval_seconds)
                if self._running:  # Check again after sleep
                    await self.push()
            except Exception as e:
                logger.error(f"Push error: {e}")
                self.status = SyncStatus.ERROR

    async def _pull_loop(self) -> None:
        """Periodically pull changes from remote."""
        while self._running:
            try:
                await asyncio.sleep(self.config.pull_interval_seconds)
                if self._running:  # Check again after sleep
                    await self.pull()
            except Exception as e:
                logger.error(f"Pull error: {e}")
                self.status = SyncStatus.ERROR

    async def push(self, force: bool = False) -> SyncResult:
        """
        Push local changes to remote.

        Args:
            force: Force push even if recently pushed

        Returns:
            SyncResult with operation details
        """
        # Skip if pushed recently (unless forced)
        if not force and self.last_push:
            elapsed = (datetime.now() - self.last_push).total_seconds()
            if elapsed < self.config.push_interval_seconds:
                return SyncResult(
                    status=SyncStatus.IDLE,
                    operation="push",
                    timestamp=datetime.now(),
                    message=f"Skip: {int(elapsed)}s since last push",
                )

        try:
            self.status = SyncStatus.PUSHING

            # Check for uncommitted changes in .htmlgraph
            result = await self._run_git(
                ["status", "--porcelain", str(self.config.sync_path)]
            )

            if not result:
                self.status = SyncStatus.IDLE
                sync_result = SyncResult(
                    status=SyncStatus.SUCCESS,
                    operation="push",
                    timestamp=datetime.now(),
                    message="No changes to push",
                )
                self.sync_history.append(sync_result)
                return sync_result

            # Stage changes
            await self._run_git(["add", str(self.config.sync_path)])

            # Commit
            commit_msg = f"chore: auto-sync htmlgraph from {self._get_hostname()}"
            await self._run_git(["commit", "-m", commit_msg])

            # Push to remote
            await self._run_git(
                [
                    "push",
                    self.config.remote_name,
                    f"{self.config.branch_name}:refs/heads/{self.config.branch_name}",
                ]
            )

            self.last_push = datetime.now()
            self.status = SyncStatus.SUCCESS

            logger.info(f"Pushed changes to {self.config.remote_name}")

            sync_result = SyncResult(
                status=SyncStatus.SUCCESS,
                operation="push",
                timestamp=self.last_push,
                files_changed=len(result.strip().split("\n")),
                message=f"Pushed {len(result.strip().split(chr(10)))} files",
            )
            self.sync_history.append(sync_result)
            return sync_result

        except Exception as e:
            self.status = SyncStatus.ERROR
            logger.error(f"Push failed: {e}")

            sync_result = SyncResult(
                status=SyncStatus.ERROR,
                operation="push",
                timestamp=datetime.now(),
                message=str(e),
            )
            self.sync_history.append(sync_result)
            return sync_result

    async def pull(self, force: bool = False) -> SyncResult:
        """
        Pull remote changes.

        Args:
            force: Force pull even if recently pulled

        Returns:
            SyncResult with operation details
        """
        # Skip if pulled recently (unless forced)
        if not force and self.last_pull:
            elapsed = (datetime.now() - self.last_pull).total_seconds()
            if elapsed < self.config.pull_interval_seconds:
                return SyncResult(
                    status=SyncStatus.IDLE,
                    operation="pull",
                    timestamp=datetime.now(),
                    message=f"Skip: {int(elapsed)}s since last pull",
                )

        try:
            self.status = SyncStatus.PULLING

            # Stash uncommitted changes if enabled
            if self.config.auto_stash:
                await self._run_git(
                    ["stash", "push", "-m", "auto-stash before pull"], allow_fail=True
                )

            # Fetch latest from remote
            await self._run_git(["fetch", self.config.remote_name])

            # Try to merge
            try:
                await self._run_git(
                    [
                        "merge",
                        f"{self.config.remote_name}/{self.config.branch_name}",
                        "-m",
                        "auto-merge from remote",
                    ]
                )

                self.last_pull = datetime.now()
                self.status = SyncStatus.SUCCESS

                logger.info(f"Pulled changes from {self.config.remote_name}")

                sync_result = SyncResult(
                    status=SyncStatus.SUCCESS,
                    operation="pull",
                    timestamp=self.last_pull,
                    message="Merged successfully",
                )
                self.sync_history.append(sync_result)
                return sync_result

            except subprocess.CalledProcessError:
                # Merge conflict
                conflicts = await self._get_conflicts()
                self.status = SyncStatus.CONFLICT

                logger.warning(f"Merge conflict detected: {conflicts}")

                # Handle conflict based on strategy
                if self.config.conflict_strategy == SyncStrategy.AUTO_MERGE:
                    await self._resolve_conflicts_auto()
                    await self._run_git(["commit", "-m", "auto-resolve merge conflict"])
                elif self.config.conflict_strategy == SyncStrategy.OURS:
                    await self._run_git(["checkout", "--ours", "."])
                    await self._run_git(["add", "."])
                    await self._run_git(["commit", "-m", "conflict: keep local"])
                elif self.config.conflict_strategy == SyncStrategy.THEIRS:
                    await self._run_git(["checkout", "--theirs", "."])
                    await self._run_git(["add", "."])
                    await self._run_git(["commit", "-m", "conflict: keep remote"])
                elif self.config.conflict_strategy == SyncStrategy.ABORT_ON_CONFLICT:
                    await self._run_git(["merge", "--abort"])

                    sync_result = SyncResult(
                        status=SyncStatus.CONFLICT,
                        operation="pull",
                        timestamp=datetime.now(),
                        conflicts=conflicts,
                        message=f"Merge conflict in {len(conflicts)} files",
                    )
                    self.sync_history.append(sync_result)
                    return sync_result

                self.last_pull = datetime.now()
                self.status = SyncStatus.SUCCESS

                sync_result = SyncResult(
                    status=SyncStatus.SUCCESS,
                    operation="pull",
                    timestamp=self.last_pull,
                    conflicts=conflicts,
                    message=f"Resolved conflicts in {len(conflicts)} files",
                )
                self.sync_history.append(sync_result)
                return sync_result

        except Exception as e:
            self.status = SyncStatus.ERROR
            logger.error(f"Pull failed: {e}")

            sync_result = SyncResult(
                status=SyncStatus.ERROR,
                operation="pull",
                timestamp=datetime.now(),
                message=str(e),
            )
            self.sync_history.append(sync_result)
            return sync_result

    async def _run_git(self, args: list[str], allow_fail: bool = False) -> str:
        """
        Run git command asynchronously.

        Args:
            args: Git command arguments
            allow_fail: Whether to suppress errors

        Returns:
            Command stdout as string

        Raises:
            RuntimeError: If command fails and allow_fail=False
        """
        cmd = ["git", "-C", str(self.repo_root)] + args

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)

            if process.returncode != 0 and not allow_fail:
                raise RuntimeError(f"Git command failed: {stderr.decode().strip()}")

            return stdout.decode().strip()

        except asyncio.TimeoutError as e:
            if allow_fail:
                return ""
            raise RuntimeError(f"Git command timeout: {' '.join(args)}") from e

    async def _get_conflicts(self) -> list[str]:
        """Get list of conflicted files."""
        try:
            result = await self._run_git(["diff", "--name-only", "--diff-filter=U"])
            return result.split("\n") if result else []
        except Exception:
            return []

    async def _resolve_conflicts_auto(self) -> None:
        """
        Attempt automatic conflict resolution.

        Strategy:
        - SQLite files: use ours (local)
        - JSONL files: use ours (event log is append-only)
        - Other files: accept git's merge
        """
        conflicts = await self._get_conflicts()

        for conflict in conflicts:
            if conflict.endswith(".db"):
                # SQLite: keep local version
                await self._run_git(["checkout", "--ours", conflict])
            elif conflict.endswith(".jsonl"):
                # JSONL: keep local (event log is append-only)
                await self._run_git(["checkout", "--ours", conflict])
            # Text files: accept git's merge (do nothing)

        await self._run_git(["add", "."])

    def _get_hostname(self) -> str:
        """Get hostname for commit messages."""
        return socket.gethostname()

    def get_sync_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get recent sync history.

        Args:
            limit: Maximum number of results

        Returns:
            List of sync result dictionaries
        """
        return [s.to_dict() for s in self.sync_history[-limit:]]

    def get_status(self) -> dict[str, Any]:
        """
        Get current sync status.

        Returns:
            Status dictionary with sync state and config
        """
        return {
            "status": self.status.value,
            "last_push": self.last_push.isoformat() if self.last_push else None,
            "last_pull": self.last_pull.isoformat() if self.last_pull else None,
            "config": {
                "push_interval": self.config.push_interval_seconds,
                "pull_interval": self.config.pull_interval_seconds,
                "remote": self.config.remote_name,
                "branch": self.config.branch_name,
                "conflict_strategy": self.config.conflict_strategy.value,
                "sync_path": self.config.sync_path,
            },
        }
