"""
Unit tests for atomic file operations module.

Tests cover:
- AtomicFileWriter context manager
- Atomic JSON writes
- Safe reads with retry
- DirectoryLocker (shared/exclusive locks)
- Platform-aware atomic rename
- Orphaned temp file cleanup
- Crash-safety verification
- Error handling and edge cases
"""

import json
import os
import platform
import time
from unittest import mock

import pytest
from htmlgraph.atomic_ops import (
    AtomicFileWriter,
    DirectoryLocker,
    atomic_rename,
    cleanup_orphaned_temp_files,
    safe_temp_file,
    validate_atomic_write,
)


class TestAtomicFileWriterContextManager:
    """Test AtomicFileWriter as context manager."""

    def test_atomic_write_success(self, tmp_path):
        """Test successful atomic write via context manager."""
        target = tmp_path / "target.txt"
        content = "Hello, World!"

        with AtomicFileWriter(target) as f:
            f.write(content)

        assert target.exists()
        assert target.read_text() == content

    def test_atomic_write_creates_parent_directories(self, tmp_path):
        """Test that atomic write creates parent directories."""
        target = tmp_path / "subdir1" / "subdir2" / "file.txt"
        content = "test"

        with AtomicFileWriter(target) as f:
            f.write(content)

        assert target.exists()
        assert target.read_text() == content

    def test_atomic_write_overwrites_existing_file(self, tmp_path):
        """Test that atomic write overwrites existing file."""
        target = tmp_path / "target.txt"
        target.write_text("old content")

        with AtomicFileWriter(target) as f:
            f.write("new content")

        assert target.read_text() == "new content"

    def test_atomic_write_rollback_on_exception(self, tmp_path):
        """Test that write is rolled back if exception occurs."""
        target = tmp_path / "target.txt"
        original_content = "original"
        target.write_text(original_content)

        try:
            with AtomicFileWriter(target) as f:
                f.write("partial content")
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Original file should be unchanged
        assert target.read_text() == original_content

    def test_atomic_write_no_temp_file_on_success(self, tmp_path):
        """Test that temp file is cleaned up after successful write."""
        target = tmp_path / "target.txt"

        with AtomicFileWriter(target) as f:
            f.write("content")

        # No temp files should remain
        temp_files = list(tmp_path.glob(".tmp-*"))
        assert len(temp_files) == 0

    def test_atomic_write_with_custom_temp_dir(self, tmp_path):
        """Test atomic write with custom temp directory."""
        target = tmp_path / "target.txt"
        temp_dir = tmp_path / "temp"

        with AtomicFileWriter(target, temp_dir=temp_dir) as f:
            f.write("content")

        assert target.exists()
        assert target.read_text() == "content"

    def test_atomic_write_invalid_target_path(self):
        """Test that invalid target path raises error."""
        with pytest.raises(ValueError):
            AtomicFileWriter(None)

    def test_atomic_write_multiple_writes_same_file(self, tmp_path):
        """Test multiple sequential atomic writes to same file."""
        target = tmp_path / "target.txt"

        for i in range(3):
            with AtomicFileWriter(target) as f:
                f.write(f"content {i}")

        assert target.read_text() == "content 2"


class TestAtomicFileWriterStaticMethods:
    """Test AtomicFileWriter static convenience methods."""

    def test_atomic_write_static_method(self, tmp_path):
        """Test simple atomic_write static method."""
        target = tmp_path / "target.txt"
        content = "Hello, World!"

        AtomicFileWriter.atomic_write(target, content)

        assert target.read_text() == content

    def test_atomic_json_write(self, tmp_path):
        """Test atomic_json_write with formatting."""
        target = tmp_path / "data.json"
        data = {"key": "value", "list": [1, 2, 3]}

        AtomicFileWriter.atomic_json_write(target, data)

        assert target.exists()
        loaded = json.loads(target.read_text())
        assert loaded == data

    def test_atomic_json_write_formatting(self, tmp_path):
        """Test that JSON is properly formatted with indentation."""
        target = tmp_path / "data.json"
        data = {"a": 1, "b": 2}

        AtomicFileWriter.atomic_json_write(target, data, indent=4)

        content = target.read_text()
        # Should be indented (contains newlines and spaces)
        assert "\n" in content
        assert "    " in content

    def test_safe_read_with_retry_success(self, tmp_path):
        """Test safe_read_with_retry on readable file."""
        target = tmp_path / "target.txt"
        content = "test content"
        target.write_text(content)

        result = AtomicFileWriter.safe_read_with_retry(target)

        assert result == content

    def test_safe_read_with_retry_nonexistent_file(self, tmp_path):
        """Test safe_read_with_retry on nonexistent file raises error."""
        target = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            AtomicFileWriter.safe_read_with_retry(target, max_retries=1)

    def test_safe_read_with_retry_retries_on_transient_error(self, tmp_path):
        """Test safe_read_with_retry retries on transient errors."""
        target = tmp_path / "target.txt"
        target.write_text("content")

        # Mock open to simulate transient failure then success
        original_open = open
        call_count = [0]

        def mock_open_func(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise OSError("Simulated transient error")
            return original_open(*args, **kwargs)

        with mock.patch("builtins.open", mock_open_func):
            result = AtomicFileWriter.safe_read_with_retry(
                target, max_retries=3, retry_delay=0.01
            )

        assert result == "content"
        assert call_count[0] == 2  # Failed once, succeeded on retry


class TestAtomicRename:
    """Test platform-aware atomic rename operation."""

    def test_atomic_rename_basic(self, tmp_path):
        """Test basic atomic rename operation."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("content")

        atomic_rename(src, dst)

        assert not src.exists()
        assert dst.exists()
        assert dst.read_text() == "content"

    def test_atomic_rename_overwrites_existing(self, tmp_path):
        """Test atomic rename overwrites existing destination."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("new content")
        dst.write_text("old content")

        atomic_rename(src, dst)

        assert not src.exists()
        assert dst.read_text() == "new content"

    def test_atomic_rename_creates_parent_directory(self, tmp_path):
        """Test atomic rename creates parent directory if needed."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "subdir" / "dest.txt"
        src.write_text("content")

        atomic_rename(src, dst)

        assert dst.exists()
        assert dst.read_text() == "content"

    def test_atomic_rename_nonexistent_source(self, tmp_path):
        """Test atomic rename raises error for nonexistent source."""
        src = tmp_path / "nonexistent.txt"
        dst = tmp_path / "dest.txt"

        with pytest.raises(FileNotFoundError):
            atomic_rename(src, dst)

    def test_atomic_rename_same_source_and_dest(self, tmp_path):
        """Test atomic rename raises error when source and dest are same."""
        path = tmp_path / "file.txt"
        path.write_text("content")

        with pytest.raises(ValueError):
            atomic_rename(path, path)


class TestSafeTempFile:
    """Test safe_temp_file function."""

    def test_safe_temp_file_returns_unique_path(self, tmp_path):
        """Test that safe_temp_file returns unique paths."""
        path1 = safe_temp_file(tmp_path)
        path2 = safe_temp_file(tmp_path)

        assert path1 != path2
        assert path1.parent == tmp_path
        assert path2.parent == tmp_path

    def test_safe_temp_file_creates_parent_directory(self, tmp_path):
        """Test that safe_temp_file creates parent directory."""
        subdir = tmp_path / "subdir"
        path = safe_temp_file(subdir)

        assert path.parent == subdir
        assert subdir.exists()

    def test_safe_temp_file_with_custom_prefix(self, tmp_path):
        """Test safe_temp_file with custom prefix."""
        path = safe_temp_file(tmp_path, prefix="custom")

        assert "custom" in path.name
        assert path.name.startswith(".")


class TestCleanupOrphanedTempFiles:
    """Test cleanup_orphaned_temp_files function."""

    def test_cleanup_removes_old_temp_files(self, tmp_path):
        """Test cleanup removes temp files older than threshold."""
        # Create some temp files
        old_file = tmp_path / ".tmp-old-file"
        old_file.write_text("old")
        new_file = tmp_path / ".tmp-new-file"
        new_file.write_text("new")

        # Make old file appear old
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        os.utime(old_file, (old_time, old_time))

        # Cleanup with 24-hour threshold
        deleted_count = cleanup_orphaned_temp_files(tmp_path, age_hours=24)

        assert deleted_count == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_cleanup_nonexistent_directory(self, tmp_path):
        """Test cleanup on nonexistent directory returns 0."""
        nonexistent = tmp_path / "nonexistent"

        deleted_count = cleanup_orphaned_temp_files(nonexistent)

        assert deleted_count == 0

    def test_cleanup_no_temp_files(self, tmp_path):
        """Test cleanup returns 0 when no temp files exist."""
        (tmp_path / "regular_file.txt").write_text("content")

        deleted_count = cleanup_orphaned_temp_files(tmp_path)

        assert deleted_count == 0

    def test_cleanup_ignores_non_matching_files(self, tmp_path):
        """Test cleanup only removes .tmp-* files."""
        old_file = tmp_path / ".tmp-old-file"
        old_file.write_text("old")
        other_file = tmp_path / "not-temp.txt"
        other_file.write_text("other")

        # Make both appear old
        old_time = time.time() - (25 * 3600)
        for f in [old_file, other_file]:
            os.utime(f, (old_time, old_time))

        deleted_count = cleanup_orphaned_temp_files(tmp_path, age_hours=24)

        assert deleted_count == 1
        assert not old_file.exists()
        assert other_file.exists()


class TestValidateAtomicWrite:
    """Test validate_atomic_write function."""

    def test_validate_existing_readable_file(self, tmp_path):
        """Test validation of existing readable file."""
        target = tmp_path / "target.txt"
        target.write_text("valid content")

        assert validate_atomic_write(target)

    def test_validate_nonexistent_file(self, tmp_path):
        """Test validation fails for nonexistent file."""
        target = tmp_path / "nonexistent.txt"

        assert not validate_atomic_write(target)

    def test_validate_directory(self, tmp_path):
        """Test validation fails for directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        assert not validate_atomic_write(subdir)

    def test_validate_corrupted_file(self, tmp_path):
        """Test validation fails for corrupted file."""
        target = tmp_path / "target.txt"
        # Write invalid UTF-8 bytes
        with open(target, "wb") as f:
            f.write(b"\xff\xfe invalid utf-8")

        assert not validate_atomic_write(target)


class TestDirectoryLocker:
    """Test DirectoryLocker for concurrent access coordination."""

    def test_locker_initialization(self, tmp_path):
        """Test DirectoryLocker initialization."""
        lock_dir = tmp_path / "locks"
        locker = DirectoryLocker(lock_dir)

        assert locker.lock_dir == lock_dir
        assert lock_dir.exists()

    def test_acquire_shared_lock(self, tmp_path):
        """Test acquiring shared lock."""
        lock_dir = tmp_path / "locks"
        locker = DirectoryLocker(lock_dir)

        assert locker.acquire_shared_lock()
        assert locker.shared_lock_path.exists()

    def test_release_shared_lock(self, tmp_path):
        """Test releasing shared lock."""
        lock_dir = tmp_path / "locks"
        locker = DirectoryLocker(lock_dir)

        locker.acquire_shared_lock()
        locker.release_lock()

        assert not locker.shared_lock_path.exists()

    def test_acquire_exclusive_lock(self, tmp_path):
        """Test acquiring exclusive lock."""
        lock_dir = tmp_path / "locks"
        locker = DirectoryLocker(lock_dir)

        assert locker.acquire_exclusive_lock()
        assert locker.exclusive_lock_path.exists()

    def test_release_exclusive_lock(self, tmp_path):
        """Test releasing exclusive lock."""
        lock_dir = tmp_path / "locks"
        locker = DirectoryLocker(lock_dir)

        locker.acquire_exclusive_lock()
        locker.release_lock()

        assert not locker.exclusive_lock_path.exists()

    def test_multiple_shared_locks_allowed(self, tmp_path):
        """Test multiple processes can hold shared locks."""
        lock_dir = tmp_path / "locks"
        locker1 = DirectoryLocker(lock_dir)
        locker2 = DirectoryLocker(lock_dir)

        # Both should acquire shared locks
        assert locker1.acquire_shared_lock()
        assert locker2.acquire_shared_lock()

        locker1.release_lock()
        locker2.release_lock()

    def test_release_without_lock_is_safe(self, tmp_path):
        """Test release() is safe to call without holding lock."""
        lock_dir = tmp_path / "locks"
        locker = DirectoryLocker(lock_dir)

        # Should not raise
        locker.release_lock()

    def test_lock_timeout(self, tmp_path):
        """Test lock acquisition timeout."""
        lock_dir = tmp_path / "locks"
        locker1 = DirectoryLocker(lock_dir)
        locker2 = DirectoryLocker(lock_dir)

        # locker1 holds exclusive lock
        assert locker1.acquire_exclusive_lock()

        # locker2 should timeout waiting for exclusive lock
        assert not locker2.acquire_exclusive_lock(timeout=0.1)


class TestCrashSafety:
    """Test crash-safety properties of atomic operations."""

    def test_crash_during_write_leaves_original_intact(self, tmp_path):
        """Test that crash during write leaves original file intact."""
        target = tmp_path / "target.txt"
        original_content = "original"
        target.write_text(original_content)

        try:
            with AtomicFileWriter(target) as f:
                f.write("partial")
                raise RuntimeError("Simulated crash")
        except RuntimeError:
            pass

        # Original file should be completely intact
        assert target.read_text() == original_content

    def test_orphaned_temp_files_dont_corrupt_target(self, tmp_path):
        """Test that orphaned temp files don't corrupt target."""
        target = tmp_path / "target.txt"
        target.write_text("original")

        # Create orphaned temp file
        orphaned = tmp_path / ".tmp-orphaned"
        orphaned.write_text("orphan content")

        # Original should be unaffected
        assert target.read_text() == "original"

        # Cleanup should remove orphaned file
        cleanup_orphaned_temp_files(tmp_path, age_hours=0)
        assert not orphaned.exists()
        assert target.read_text() == "original"

    def test_concurrent_writes_to_different_files(self, tmp_path):
        """Test multiple concurrent atomic writes to different files."""
        target1 = tmp_path / "file1.txt"
        target2 = tmp_path / "file2.txt"

        with AtomicFileWriter(target1) as f:
            f.write("content1")

        with AtomicFileWriter(target2) as f:
            f.write("content2")

        assert target1.read_text() == "content1"
        assert target2.read_text() == "content2"

    def test_large_file_atomic_write(self, tmp_path):
        """Test atomic write with large file."""
        target = tmp_path / "large.txt"
        large_content = "x" * (10 * 1024 * 1024)  # 10MB

        with AtomicFileWriter(target) as f:
            f.write(large_content)

        assert target.stat().st_size == len(large_content)
        assert target.read_text() == large_content


class TestErrorHandling:
    """Test error handling in atomic operations."""

    def test_write_permission_error(self, tmp_path):
        """Test handling of permission errors."""
        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        if platform.system() != "Windows":
            readonly_dir.chmod(0o444)

            try:
                with pytest.raises(OSError):
                    with AtomicFileWriter(readonly_dir / "file.txt") as f:
                        f.write("content")
            finally:
                readonly_dir.chmod(0o755)

    def test_disk_full_simulation(self, tmp_path):
        """Test handling of disk full errors."""
        target = tmp_path / "target.txt"

        # Mock tempfile.mkstemp to simulate disk full
        def mock_mkstemp_disk_full(*args, **kwargs):
            raise OSError("No space left on device")

        with mock.patch("tempfile.mkstemp", mock_mkstemp_disk_full):
            with pytest.raises(OSError):
                with AtomicFileWriter(target) as f:
                    f.write("content")

    def test_symlink_handling(self, tmp_path):
        """Test atomic write through symlinks."""
        if platform.system() == "Windows":
            pytest.skip("Symlinks not standard on Windows")

        target = tmp_path / "target.txt"
        link = tmp_path / "link.txt"

        # First create target, then symlink to it
        target.write_text("original")
        os.symlink(target, link)

        with AtomicFileWriter(link) as f:
            f.write("content")

        # Symlink should still exist and point to updated content
        assert link.exists()
        assert link.read_text() == "content"


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_atomic_write_and_validation_workflow(self, tmp_path):
        """Test complete workflow: write, validate, read."""
        target = tmp_path / "data.json"
        data = {"key": "value", "list": [1, 2, 3]}

        # Write atomically
        AtomicFileWriter.atomic_json_write(target, data)

        # Validate
        assert validate_atomic_write(target)

        # Read with retry
        content = AtomicFileWriter.safe_read_with_retry(target)
        assert json.loads(content) == data

    def test_cleanup_and_write_workflow(self, tmp_path):
        """Test cleanup of old temp files, then new write."""
        # Create old orphaned temp files
        old_temp = tmp_path / ".tmp-old"
        old_temp.write_text("old")
        old_time = time.time() - (25 * 3600)
        os.utime(old_temp, (old_time, old_time))

        # Cleanup
        cleanup_orphaned_temp_files(tmp_path, age_hours=24)
        assert not old_temp.exists()

        # New write should work
        target = tmp_path / "new.txt"
        AtomicFileWriter.atomic_write(target, "new content")

        assert target.read_text() == "new content"
