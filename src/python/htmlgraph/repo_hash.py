from __future__ import annotations

"""
Repository Hashing and Git Awareness Module.

Provides stable repository identification and git state tracking for:
- Unique repo identification across machines/clones
- Stable hashes from: path + remote URL + inode
- Stability across branch changes
- Monorepo support (multiple projects = different hashes)
- Git state tracking: branch, commit, dirty flag

Architecture:
    RepoHash(repo_path) → compute stable hash + git info

    Hash inputs:
    1. Absolute repository path
    2. Git remote URL (if available)
    3. File system inode

    Outputs:
    - repo_hash: "repo-abc123def456" (stable, unique)
    - git_info: {branch, commit, remote, dirty, last_commit_date}
    - monorepo_project: "project-name" (if in monorepo)
"""


import hashlib
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RepoHash:
    """
    Generate stable hashes for git repositories.

    Provides unique repository identification and git state tracking.
    Hash is stable across branch changes and independent of file modifications.
    """

    def __init__(self, repo_path: Path | None = None):
        """
        Initialize with git repository path.

        Args:
            repo_path: Path to the git repository. Defaults to current directory.

        Raises:
            OSError: If path does not exist.
        """
        if repo_path is None:
            repo_path = Path.cwd()
        else:
            repo_path = Path(repo_path)

        if not repo_path.exists():
            raise OSError(f"Repository path does not exist: {repo_path}")

        self.repo_path = repo_path.resolve()
        self._git_info_cache: dict[str, Any] | None = None
        self._repo_hash_cache: str | None = None

    def compute_repo_hash(self) -> str:
        """
        Compute stable hash from path + remote + inode.

        Hash inputs:
        1. Absolute repo path
        2. Git remote URL (if available)
        3. File system inode

        Returns:
            Hex string like 'repo-abc123def456'

        The hash is deterministic: same repo always produces same hash.
        Branch changes do not affect the hash.
        """
        if self._repo_hash_cache is not None:
            return self._repo_hash_cache

        # Get hash inputs
        path_str = str(self.repo_path.absolute())
        remote = get_git_remote(self.repo_path)
        inode = get_inode(self.repo_path)

        # Compute hash
        hash_input = compute_hash_inputs(path_str, remote, inode)
        hash_hex = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

        result = f"repo-{hash_hex}"
        self._repo_hash_cache = result
        return result

    def get_git_info(self) -> dict[str, Any]:
        """
        Get current git state.

        Returns:
            {
                "branch": "main",
                "commit": "d78e458abc123",
                "remote": "https://github.com/user/repo.git",
                "dirty": False,
                "last_commit_date": "2026-01-08T12:34:56Z"
            }

        All fields present. Non-git repos return sensible defaults.
        """
        if self._git_info_cache is not None:
            return self._git_info_cache

        result: dict[str, Any] = {
            "branch": get_current_branch(self.repo_path),
            "commit": get_current_commit(self.repo_path),
            "remote": get_git_remote(self.repo_path),
            "dirty": is_git_dirty(self.repo_path),
            "last_commit_date": get_last_commit_date(self.repo_path),
        }

        self._git_info_cache = result
        return result

    def is_monorepo(self) -> bool:
        """
        Detect if this is a monorepo structure.

        Looks for:
        - Multiple package.json files (npm/yarn monorepo)
        - Multiple pyproject.toml files (Python monorepo)
        - workspaces field in package.json

        Returns:
            True if monorepo structure detected, False otherwise.
        """
        return _detect_monorepo(self.repo_path)

    def get_monorepo_project(self) -> str | None:
        """
        If monorepo, identify which project we're in.

        Scans up from current directory to find workspace marker,
        then identifies the project subdirectory.

        Returns:
            Project name (e.g., "packages/claude-plugin") or None if not in monorepo.
        """
        return _get_monorepo_project(self.repo_path)


# Module-level functions for git operations


def compute_hash_inputs(path: str, remote: str | None, inode: int) -> str:
    """
    Combine inputs into stable hash string.

    Args:
        path: Absolute repository path
        remote: Git remote URL (optional)
        inode: File system inode

    Returns:
        Combined hash input string
    """
    # Order matters for determinism
    parts = [
        f"path:{path}",
        f"remote:{remote or 'none'}",
        f"inode:{inode}",
    ]
    return "|".join(parts)


def get_git_remote(repo_path: Path | None = None) -> str | None:
    """
    Get primary git remote URL.

    Attempts to get 'origin' remote, falls back to first available remote.

    Args:
        repo_path: Repository path. Defaults to current directory.

    Returns:
        Remote URL string or None if not a git repo.
    """
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path)

    try:
        # Try to get origin remote first
        result = subprocess.run(
            ["git", "-C", str(repo_path), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        # Fall back to first available remote
        result = subprocess.run(
            ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        logger.debug(f"Failed to get git remote for {repo_path}")
        return None


def get_current_branch(repo_path: Path | None = None) -> str | None:
    """
    Get current git branch name.

    Args:
        repo_path: Repository path. Defaults to current directory.

    Returns:
        Branch name (e.g., "main") or None if not a git repo.
    """
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path)

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            branch = result.stdout.strip()
            return branch if branch else None

        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        logger.debug(f"Failed to get current branch for {repo_path}")
        return None


def get_current_commit(repo_path: Path | None = None) -> str | None:
    """
    Get current commit SHA (short form, 7 chars).

    Args:
        repo_path: Repository path. Defaults to current directory.

    Returns:
        Short commit SHA (e.g., "d78e458") or None if not a git repo.
    """
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path)

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "rev-parse",
                "--short=7",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            commit = result.stdout.strip()
            return commit if commit else None

        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        logger.debug(f"Failed to get current commit for {repo_path}")
        return None


def is_git_dirty(repo_path: Path | None = None) -> bool:
    """
    Check if repo has uncommitted changes.

    Args:
        repo_path: Repository path. Defaults to current directory.

    Returns:
        True if repo has uncommitted changes, False if clean or not a git repo.
    """
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path)

    try:
        # Check for staged or unstaged changes
        result = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # If there's any output, repo is dirty
            return bool(result.stdout.strip())

        return False
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        logger.debug(f"Failed to check git dirty status for {repo_path}")
        return False


def get_last_commit_date(repo_path: Path | None = None) -> str | None:
    """
    Get last commit timestamp in ISO 8601 format.

    Args:
        repo_path: Repository path. Defaults to current directory.

    Returns:
        ISO 8601 timestamp (e.g., "2026-01-08T12:34:56Z") or None if not a git repo.
    """
    if repo_path is None:
        repo_path = Path.cwd()
    else:
        repo_path = Path(repo_path)

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "log",
                "-1",
                "--format=%ci",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            commit_date_str = result.stdout.strip()
            if commit_date_str:
                # Parse ISO format from git and ensure UTC timezone marker
                try:
                    # Git returns: "2026-01-08 12:34:56 +0000"
                    # Parse by replacing space with T and removing timezone
                    dt_str = commit_date_str.split("+")[0].strip().replace(" ", "T")
                    dt = datetime.fromisoformat(dt_str)
                    # Format as UTC ISO 8601
                    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except (ValueError, AttributeError, IndexError):
                    # Fallback: return as-is if parsing fails
                    return commit_date_str

        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        logger.debug(f"Failed to get last commit date for {repo_path}")
        return None


def get_inode(path: Path) -> int:
    """
    Get file system inode for unique identification.

    The inode is a unique identifier on the file system.
    Different mount points can have different inodes for the same repository.

    Args:
        path: File system path.

    Returns:
        Inode number.

    Raises:
        OSError: If stat() fails.
    """
    try:
        st = os.stat(path)
        return st.st_ino
    except OSError as e:
        logger.error(f"Failed to get inode for {path}: {e}")
        raise


# Monorepo detection helpers


def _detect_monorepo(repo_path: Path) -> bool:
    """
    Detect if repository is a monorepo.

    Looks for:
    - Multiple pyproject.toml files (Python monorepo)
    - Multiple package.json files (npm/yarn monorepo)
    - workspaces field in package.json

    Args:
        repo_path: Repository path.

    Returns:
        True if monorepo structure detected.
    """
    try:
        # Check for Python monorepo (multiple pyproject.toml)
        pyproject_files = list(repo_path.glob("**/pyproject.toml"))
        if len(pyproject_files) > 1:
            return True

        # Check for npm monorepo (multiple package.json)
        package_files = list(repo_path.glob("**/package.json"))
        if len(package_files) > 1:
            return True

        # Check for workspaces in root package.json
        root_package = repo_path / "package.json"
        if root_package.exists():
            try:
                import json

                with open(root_package) as f:
                    data = json.load(f)
                    if "workspaces" in data:
                        return True
            except (json.JSONDecodeError, OSError):
                pass

        return False
    except OSError:
        logger.debug(f"Error detecting monorepo at {repo_path}")
        return False


def _get_monorepo_project(repo_path: Path) -> str | None:
    """
    Identify which project we're in within a monorepo.

    Scans up from repo_path to find workspace marker (pyproject.toml, package.json),
    then returns relative path from workspace root to repo.

    Args:
        repo_path: Repository path (or subdirectory within monorepo).

    Returns:
        Relative path from monorepo root to project (e.g., "packages/claude-plugin")
        or None if not in monorepo.
    """
    try:
        # First, find monorepo root by scanning up from repo_path for .git
        current = repo_path.resolve()
        monorepo_root = None

        while current != current.parent:
            if (current / ".git").exists():
                monorepo_root = current
                break
            current = current.parent

        if monorepo_root is None:
            # Not in a git repo or .git not found - not a monorepo context
            return None

        # Now check if this is actually a monorepo
        if not _detect_monorepo(monorepo_root):
            return None

        # Find the project directory (first ancestor with pyproject.toml or package.json)
        current = repo_path.resolve()
        while current != current.parent:
            if (current / "pyproject.toml").exists() or (
                current / "package.json"
            ).exists():
                # Found project root, return relative path from monorepo root
                try:
                    rel_path = current.relative_to(monorepo_root)
                    result = str(rel_path)
                    return result if result != "." else None
                except ValueError:
                    return None

            if current == monorepo_root:
                # Reached monorepo root without finding project marker
                break
            current = current.parent

        return None
    except (OSError, ValueError):
        logger.debug(f"Error identifying monorepo project at {repo_path}")
        return None
