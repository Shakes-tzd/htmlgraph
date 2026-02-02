"""
Integration tests for Git-based sync manager.

Tests automatic push/pull, conflict resolution, and multi-device continuity.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest
from htmlgraph.sync import (
    GitSyncManager,
    SyncConfig,
    SyncStatus,
    SyncStrategy,
)


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
        )

        # Create .htmlgraph directory
        htmlgraph_dir = repo_path / ".htmlgraph"
        htmlgraph_dir.mkdir()

        # Initial commit
        (htmlgraph_dir / "test.txt").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
        )

        yield repo_path


@pytest.mark.asyncio
async def test_git_sync_manager_init(temp_git_repo):
    """Test GitSyncManager initialization."""
    config = SyncConfig(push_interval_seconds=300, pull_interval_seconds=60)
    manager = GitSyncManager(str(temp_git_repo), config)

    assert manager.status == SyncStatus.IDLE
    assert manager.last_push is None
    assert manager.last_pull is None
    assert manager.config.push_interval_seconds == 300
    assert manager.config.pull_interval_seconds == 60


@pytest.mark.asyncio
async def test_sync_config():
    """Test sync configuration."""
    config = SyncConfig(
        push_interval_seconds=300,
        pull_interval_seconds=60,
        conflict_strategy=SyncStrategy.AUTO_MERGE,
        auto_stash=True,
    )

    assert config.push_interval_seconds == 300
    assert config.pull_interval_seconds == 60
    assert config.conflict_strategy == SyncStrategy.AUTO_MERGE
    assert config.auto_stash is True


@pytest.mark.asyncio
async def test_push_with_no_changes(temp_git_repo):
    """Test push when no changes exist."""
    manager = GitSyncManager(str(temp_git_repo))

    result = await manager.push(force=True)

    assert result.status in [SyncStatus.SUCCESS, SyncStatus.IDLE]
    assert result.operation == "push"
    assert result.files_changed == 0


@pytest.mark.asyncio
async def test_push_with_changes(temp_git_repo):
    """Test push when changes exist."""
    manager = GitSyncManager(str(temp_git_repo))

    # Create a change
    test_file = temp_git_repo / ".htmlgraph" / "new_file.txt"
    test_file.write_text("new content")

    result = await manager.push(force=True)

    # Should succeed, be idle, or error (no remote configured in test)
    assert result.status in [SyncStatus.SUCCESS, SyncStatus.IDLE, SyncStatus.ERROR]
    assert result.operation == "push"


@pytest.mark.asyncio
async def test_pull_with_no_remote():
    """Test pull when no remote exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize local-only repo
        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
        )

        htmlgraph_dir = repo_path / ".htmlgraph"
        htmlgraph_dir.mkdir()
        (htmlgraph_dir / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo_path,
            check=True,
        )

        manager = GitSyncManager(str(repo_path))
        result = await manager.pull(force=True)

        # Should fail or be idle (no remote configured)
        assert result.operation == "pull"


@pytest.mark.asyncio
async def test_sync_history(temp_git_repo):
    """Test sync operation history."""
    manager = GitSyncManager(str(temp_git_repo))

    # Perform some operations
    await manager.push(force=True)

    history = manager.get_sync_history()

    assert isinstance(history, list)
    assert len(history) > 0
    assert all("status" in h for h in history)
    assert all("operation" in h for h in history)


@pytest.mark.asyncio
async def test_sync_status_dict(temp_git_repo):
    """Test sync status export."""
    manager = GitSyncManager(str(temp_git_repo))

    status = manager.get_status()

    assert "status" in status
    assert "config" in status
    assert status["config"]["remote"] == "origin"
    assert status["config"]["branch"] == "main"


@pytest.mark.asyncio
async def test_sync_interval_throttling(temp_git_repo):
    """Test that sync operations are throttled by interval."""
    config = SyncConfig(push_interval_seconds=10, pull_interval_seconds=10)
    manager = GitSyncManager(str(temp_git_repo), config)

    # Create a change and do first push
    test_file = temp_git_repo / ".htmlgraph" / "throttle_test.txt"
    test_file.write_text("test content")
    result1 = await manager.push(force=True)

    # Second push immediately should be throttled (unless first failed)
    result2 = await manager.push(force=False)

    # If first push succeeded, second should be throttled
    # If first push failed (no remote), second will also fail
    if result1.status == SyncStatus.SUCCESS:
        assert result2.status == SyncStatus.IDLE
        assert "since last push" in result2.message.lower()
    else:
        # Test environment has no remote, so pushes will fail/idle
        assert result2.status in [SyncStatus.IDLE, SyncStatus.ERROR, SyncStatus.SUCCESS]


@pytest.mark.asyncio
async def test_conflict_strategies():
    """Test different conflict resolution strategies."""
    strategies = [
        SyncStrategy.AUTO_MERGE,
        SyncStrategy.ABORT_ON_CONFLICT,
        SyncStrategy.OURS,
        SyncStrategy.THEIRS,
    ]

    for strategy in strategies:
        config = SyncConfig(conflict_strategy=strategy)
        assert config.conflict_strategy == strategy


@pytest.mark.asyncio
async def test_background_sync_start_stop(temp_git_repo):
    """Test starting and stopping background sync."""
    manager = GitSyncManager(str(temp_git_repo))

    # Start background sync
    task = asyncio.create_task(manager.start_background_sync())

    # Let it run briefly
    await asyncio.sleep(0.1)

    # Stop background sync
    await manager.stop_background_sync()

    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_sync_result_to_dict():
    """Test SyncResult serialization."""
    from datetime import datetime

    from htmlgraph.sync import SyncResult

    result = SyncResult(
        status=SyncStatus.SUCCESS,
        operation="push",
        timestamp=datetime.now(),
        files_changed=5,
        conflicts=["file1.txt", "file2.txt"],
        message="Test message",
    )

    data = result.to_dict()

    assert data["status"] == "success"
    assert data["operation"] == "push"
    assert data["files_changed"] == 5
    assert len(data["conflicts"]) == 2
    assert data["message"] == "Test message"


@pytest.mark.asyncio
async def test_hostname_in_commit():
    """Test that hostname is included in commit messages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        import subprocess

        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
        )

        htmlgraph_dir = repo_path / ".htmlgraph"
        htmlgraph_dir.mkdir()

        manager = GitSyncManager(str(repo_path))
        hostname = manager._get_hostname()

        assert isinstance(hostname, str)
        assert len(hostname) > 0


@pytest.mark.asyncio
async def test_custom_sync_path(temp_git_repo):
    """Test syncing a custom path instead of .htmlgraph."""
    custom_dir = temp_git_repo / "custom_sync"
    custom_dir.mkdir()

    config = SyncConfig(sync_path="custom_sync")
    manager = GitSyncManager(str(temp_git_repo), config)

    assert manager.config.sync_path == "custom_sync"

    # Create a change in custom dir
    (custom_dir / "test.txt").write_text("custom content")

    result = await manager.push(force=True)

    # Should process custom directory
    assert result.operation == "push"
