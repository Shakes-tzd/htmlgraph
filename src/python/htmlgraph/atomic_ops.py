"""
Atomic file operations with crash-safe handling.

Provides atomic file write operations that prevent partial file corruption
through a temp-file-and-rename pattern. Crash-safe without requiring locks
or external dependencies.

Key Features:
- Atomic writes via temp file + rename pattern
- Platform-aware (Windows, macOS, Linux)
- No external dependencies (stdlib only: os, pathlib, tempfile)
- Retry logic for concurrent access
- Orphaned temp file cleanup
- Type hints and comprehensive docstrings

Architecture:
- AtomicFileWriter: Context manager for streaming writes
- DirectoryLocker: Lightweight coordination via marker files
- atomic_rename: Platform-aware rename operation
- safe_temp_file: Create unique temp file paths
- cleanup_orphaned_temp_files: Cleanup crashed writes

Usage:
    # Method 1: Context manager (streaming writes)
    from htmlgraph.atomic_ops import AtomicFileWriter

    with AtomicFileWriter(Path("target.txt")) as f:
        f.write("content")
        # File is committed atomically when context exits

    # Method 2: Simple atomic write
    from htmlgraph.atomic_ops import AtomicFileWriter
    AtomicFileWriter.atomic_write(Path("target.txt"), "content")

    # Method 3: Atomic JSON write
    from htmlgraph.atomic_ops import AtomicFileWriter
    AtomicFileWriter.atomic_json_write(Path("data.json"), {"key": "value"})

Crash Safety:
- Write to temp file first (original untouched)
- If crash occurs: temp file remains, target unmodified
- On recovery: cleanup_orphaned_temp_files() removes orphaned files
- Result: No partial or corrupted files ever written to target
"""

import json
import logging
import os
import platform
import tempfile
import time
from pathlib import Path
from typing import TextIO

logger = logging.getLogger(__name__)


class AtomicFileWriter:
    """
    Context manager for atomic file writes with crash safety.

    Uses temp file + atomic rename pattern to ensure that writes are
    all-or-nothing: either the entire file is written, or the original
    file remains unchanged.

    Attributes:
        target_path: Final file location
        temp_file: Temporary file handle
        temp_path: Path to temporary file
    """

    def __init__(self, target_path: Path, temp_dir: Path | None = None) -> None:
        """
        Initialize atomic writer for target file.

        Args:
            target_path: Final file location (after atomic rename)
            temp_dir: Directory for temp file (default: same as target_path)

        Raises:
            ValueError: If target_path is empty or None
        """
        if not target_path:
            raise ValueError("target_path cannot be None or empty")

        self.target_path = Path(target_path)
        self.temp_dir = Path(temp_dir) if temp_dir else self.target_path.parent
        self.temp_file: TextIO | None = None
        self.temp_path: Path | None = None

    def __enter__(self) -> TextIO:
        """
        Create and open temporary file for writing.

        Creates a unique temp file in the same directory as target_path
        (or in temp_dir if specified). This ensures the temp file is on
        the same filesystem for atomic rename.

        Returns:
            File handle for writing (buffered text mode)

        Raises:
            OSError: If temp file creation fails (disk full, permissions, etc.)
        """
        try:
            # Create parent directories if they don't exist
            self.temp_dir.mkdir(parents=True, exist_ok=True)

            # Create temp file in same directory as target (same filesystem)
            # This is critical for os.rename() atomicity on the same filesystem
            temp_fd, temp_path_str = tempfile.mkstemp(
                dir=str(self.temp_dir), prefix=".tmp-", suffix=".tmp"
            )
            self.temp_path = Path(temp_path_str)

            # Convert file descriptor to file object
            self.temp_file = os.fdopen(temp_fd, "w", encoding="utf-8")
            return self.temp_file

        except OSError as e:
            logger.error(f"Failed to create temp file in {self.temp_dir}: {e}")
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """
        Commit write (atomic rename) or rollback on error.

        If no exception occurred: performs atomic rename of temp file to target.
        If exception occurred: deletes temp file and re-raises exception.

        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred

        Raises:
            OSError: If atomic rename fails after successful write
            (Re-raises any exception from the with block)
        """
        if self.temp_file:
            try:
                self.temp_file.close()
            except OSError as e:
                logger.error(f"Failed to close temp file {self.temp_path}: {e}")
                # Try to cleanup temp file before re-raising
                if self.temp_path and self.temp_path.exists():
                    try:
                        self.temp_path.unlink()
                    except OSError:
                        pass
                raise

        # If exception occurred during write, delete temp file and re-raise
        if exc_type is not None:
            if self.temp_path and self.temp_path.exists():
                try:
                    self.temp_path.unlink()
                    logger.debug(f"Rolled back temp file {self.temp_path}")
                except OSError as e:
                    logger.warning(f"Failed to cleanup temp file {self.temp_path}: {e}")
            # Don't suppress the exception
            return

        # No exception: commit via atomic rename
        if self.temp_path:
            try:
                atomic_rename(self.temp_path, self.target_path)
                logger.debug(f"Atomically committed {self.target_path}")
            except OSError as e:
                # Rename failed - cleanup temp and raise
                try:
                    self.temp_path.unlink()
                except OSError:
                    pass
                logger.error(
                    f"Failed to rename {self.temp_path} to {self.target_path}: {e}"
                )
                raise

    @staticmethod
    def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
        """
        Simple atomic write without context manager.

        Convenience method for one-shot atomic writes. Equivalent to:
            with AtomicFileWriter(path) as f:
                f.write(content)

        Args:
            path: Target file path
            content: Text content to write
            encoding: Text encoding (default: utf-8)

        Raises:
            OSError: If write or rename fails
            ValueError: If path is invalid
        """
        writer = AtomicFileWriter(path)
        with writer as f:
            f.write(content)

    @staticmethod
    def atomic_json_write(path: Path, data: dict[str, object], indent: int = 2) -> None:
        """
        Atomic JSON write with formatting.

        Convenience method for atomic JSON writes with pretty-printing.
        Ensures JSON file is never partially written or corrupted.

        Args:
            path: Target JSON file path
            data: Dictionary/object to write as JSON
            indent: JSON indentation level (default: 2 for readability)

        Raises:
            OSError: If write or rename fails
            TypeError: If data is not JSON serializable
            ValueError: If path is invalid
        """
        writer = AtomicFileWriter(path)
        with writer as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.write("\n")  # Add trailing newline for text files

    @staticmethod
    def safe_read_with_retry(
        path: Path, max_retries: int = 3, retry_delay: float = 0.1
    ) -> str:
        """
        Read file with retry on concurrent access.

        Handles transient failures (file being written by another process)
        by retrying with exponential backoff. Useful when reading files
        that may be updated concurrently.

        Args:
            path: File to read
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Delay in seconds between retries (default: 0.1)

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist and all retries exhausted
            OSError: If read failed after all retries
        """
        last_error: OSError | None = None

        for attempt in range(max_retries):
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)  # Exponential backoff
                    logger.debug(
                        f"Read retry {attempt + 1}/{max_retries} for {path} "
                        f"(waiting {wait_time:.2f}s): {e}"
                    )
                    time.sleep(wait_time)

        # All retries exhausted
        logger.error(f"Failed to read {path} after {max_retries} retries: {last_error}")
        raise last_error if last_error else FileNotFoundError(f"Cannot read {path}")


class DirectoryLocker:
    """
    Lightweight directory-level coordination for concurrent writes.

    Uses marker files (not OS-level locks) to coordinate access between
    multiple processes. Supports shared locks (multiple readers) and
    exclusive locks (single writer).

    Marker Files:
    - .lock-shared-{pid}: Process holding shared lock
    - .lock-exclusive-{pid}: Process holding exclusive lock

    Attributes:
        lock_dir: Directory containing lock marker files
        pid: Current process ID
    """

    def __init__(self, lock_dir: Path) -> None:
        """
        Initialize lock directory.

        Args:
            lock_dir: Directory where lock marker files are stored

        Raises:
            OSError: If lock directory cannot be created
        """
        self.lock_dir = Path(lock_dir)
        self.pid = os.getpid()
        self.shared_lock_path: Path | None = None
        self.exclusive_lock_path: Path | None = None

        # Create lock directory
        try:
            self.lock_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create lock directory {lock_dir}: {e}")
            raise

    def acquire_shared_lock(self, timeout: float = 5.0) -> bool:
        """
        Acquire shared lock (multiple readers allowed).

        Shared locks allow multiple processes to hold the lock simultaneously.
        Useful for coordinating read-heavy operations.

        Args:
            timeout: Max seconds to wait for lock (default: 5.0)

        Returns:
            True if lock acquired, False if timeout exceeded

        Raises:
            OSError: If lock file creation fails
        """
        self.shared_lock_path = self.lock_dir / f".lock-shared-{self.pid}"
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                # Try to create lock file (atomic)
                self.shared_lock_path.touch(exist_ok=True)
                logger.debug(f"Acquired shared lock: {self.shared_lock_path}")
                return True
            except OSError as e:
                logger.warning(f"Failed to acquire shared lock: {e}")
                time.sleep(0.01)

        logger.error(f"Timeout acquiring shared lock after {timeout} seconds")
        return False

    def acquire_exclusive_lock(self, timeout: float = 5.0) -> bool:
        """
        Acquire exclusive lock (single writer only).

        Exclusive locks prevent other processes from writing. Useful for
        coordinating write operations on shared resources.

        Args:
            timeout: Max seconds to wait for lock (default: 5.0)

        Returns:
            True if lock acquired, False if timeout exceeded

        Raises:
            OSError: If lock file creation fails
        """
        self.exclusive_lock_path = self.lock_dir / f".lock-exclusive-{self.pid}"
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                # Check if any exclusive locks exist
                exclusive_locks = list(self.lock_dir.glob(".lock-exclusive-*"))
                if exclusive_locks:
                    time.sleep(0.01)
                    continue

                # Try to create lock file
                self.exclusive_lock_path.touch(exist_ok=True)
                logger.debug(f"Acquired exclusive lock: {self.exclusive_lock_path}")
                return True
            except OSError as e:
                logger.warning(f"Failed to acquire exclusive lock: {e}")
                time.sleep(0.01)

        logger.error(f"Timeout acquiring exclusive lock after {timeout} seconds")
        return False

    def release_lock(self) -> None:
        """
        Release lock (both shared and exclusive).

        Safe to call even if no lock is held. Cleans up marker files.

        Raises:
            OSError: If lock file deletion fails (continues anyway)
        """
        for lock_path in [self.shared_lock_path, self.exclusive_lock_path]:
            if lock_path and lock_path.exists():
                try:
                    lock_path.unlink()
                    logger.debug(f"Released lock: {lock_path}")
                except OSError as e:
                    logger.warning(f"Failed to release lock {lock_path}: {e}")


def atomic_rename(src: Path, dst: Path) -> None:
    """
    Platform-aware atomic rename operation.

    Handles platform differences:
    - Linux/macOS: os.rename() is atomic by default
    - Windows: os.replace() is atomic on Windows 7+
    - All platforms: Overwrites existing destination

    Args:
        src: Source file path
        dst: Destination file path

    Raises:
        OSError: If rename fails (file doesn't exist, permissions, etc.)
        ValueError: If source and destination are the same
    """
    src = Path(src)
    dst = Path(dst)

    if src == dst:
        raise ValueError("Source and destination paths are identical")

    if not src.exists():
        raise FileNotFoundError(f"Source file does not exist: {src}")

    try:
        # Ensure parent directory exists
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Platform-aware atomic rename
        if platform.system() == "Windows":
            # Windows: os.replace() is atomic (overwrites existing)
            os.replace(str(src), str(dst))
        else:
            # Linux/macOS: os.rename() is atomic (overwrites existing)
            os.rename(str(src), str(dst))

        logger.debug(f"Atomic rename: {src} -> {dst}")

    except OSError as e:
        logger.error(f"Failed to rename {src} to {dst}: {e}")
        raise


def safe_temp_file(base_dir: Path, prefix: str = "tmp") -> Path:
    """
    Create unique temp file path (doesn't create file).

    Returns a unique path for a temp file without actually creating it.
    Useful for planning where to write a temp file before opening.

    Args:
        base_dir: Directory to create temp file in
        prefix: Temp file prefix (default: "tmp")

    Returns:
        Path object (file not created)

    Raises:
        OSError: If base_dir cannot be accessed
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename using timestamp + random
    import random
    import string

    timestamp = int(time.time() * 1000000)  # Microsecond precision
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    filename = f".{prefix}-{timestamp}-{random_suffix}.tmp"

    return base_dir / filename


def cleanup_orphaned_temp_files(base_dir: Path, age_hours: float = 24) -> int:
    """
    Remove temp files older than age_hours.

    Cleans up orphaned temp files left from crashed writes. Temp files
    matching pattern ".tmp-*" older than age_hours are deleted.

    Args:
        base_dir: Directory to scan for orphaned temp files
        age_hours: Age threshold in hours (default: 24)

    Returns:
        Number of temp files deleted

    Raises:
        OSError: If base_dir doesn't exist or cannot be accessed
    """
    base_dir = Path(base_dir)
    if not base_dir.exists():
        logger.debug(f"Cleanup directory does not exist: {base_dir}")
        return 0

    deleted_count = 0
    age_seconds = age_hours * 3600
    current_time = time.time()

    try:
        for temp_file in base_dir.glob(".tmp-*"):
            try:
                # Check file age
                file_time = temp_file.stat().st_mtime
                file_age = current_time - file_time

                if file_age > age_seconds:
                    temp_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted orphaned temp file: {temp_file}")
            except (OSError, FileNotFoundError) as e:
                # File may be in use or deleted by another process
                logger.debug(f"Failed to cleanup {temp_file}: {e}")
                continue

    except OSError as e:
        logger.error(f"Failed to scan {base_dir} for orphaned temp files: {e}")
        raise

    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} orphaned temp files from {base_dir}")

    return deleted_count


def validate_atomic_write(path: Path) -> bool:
    """
    Verify file was written atomically (complete, not partial).

    Checks that a file exists and is readable. A complete atomic write
    will have a valid, readable file. Partial writes or corrupted files
    will fail to read.

    Args:
        path: File to validate

    Returns:
        True if file exists and is readable, False otherwise
    """
    path = Path(path)

    if not path.exists():
        logger.debug(f"File does not exist: {path}")
        return False

    if not path.is_file():
        logger.debug(f"Path is not a file: {path}")
        return False

    try:
        # Try to read file to verify it's not corrupted
        with open(path, encoding="utf-8") as f:
            f.read()
        return True
    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"File is corrupted or unreadable: {path}: {e}")
        return False
