#!/usr/bin/env python3
"""Bootstrap utilities for hook scripts.

Centralizes environment setup and project directory resolution used by all hooks.
Handles both development (src/python) and installed (package) modes.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path


def resolve_project_dir(cwd: str | None = None) -> str:
    """Resolve the project directory with sensible fallbacks.

    Hierarchy:
    1. CLAUDE_PROJECT_DIR environment variable (set by Claude Code)
    2. Git repository root (via git rev-parse --show-toplevel)
    3. Current working directory (or provided cwd)

    This supports running hooks in multiple contexts:
    - Within a Claude Code session
    - In git repositories
    - In arbitrary directories

    Args:
        cwd: Starting directory for git search. Defaults to os.getcwd().

    Returns:
        Absolute path to the project directory.

    Raises:
        No exceptions - always returns a valid path.
    """
    # First priority: Claude's explicit project directory
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        return env_dir

    # Second priority: Git repository root
    start_dir = cwd or os.getcwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=start_dir,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        # Git not available or not a repo - continue to fallback
        pass

    # Final fallback: current working directory
    return start_dir


def bootstrap_pythonpath(project_dir: str) -> None:
    """Bootstrap Python path for htmlgraph imports.

    Handles two common deployment modes:
    1. Development: Running inside htmlgraph repository (src/python exists)
    2. Installed: Running where htmlgraph is installed as a package (do nothing)

    This allows hooks to work correctly whether htmlgraph is:
    - Being developed locally (add src/python to path)
    - Installed in a virtual environment (already in path)
    - Installed globally (already in path)

    Args:
        project_dir: Project directory from resolve_project_dir().

    Returns:
        None (modifies sys.path in-place).

    Side Effects:
        - Modifies sys.path to ensure htmlgraph is importable
        - Adds .venv/lib/pythonX.Y/site-packages if virtual environment exists
        - Adds src/python if in htmlgraph repository
    """
    project_path = Path(project_dir)

    # First, try to use local virtual environment if it exists
    venv = project_path / ".venv"
    if venv.exists():
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidates = [
            venv / "lib" / pyver / "site-packages",  # macOS/Linux
            venv / "Lib" / "site-packages",  # Windows
        ]
        for candidate in candidates:
            if candidate.exists():
                sys.path.insert(0, str(candidate))
                break

    # Then, add src/python if this is the htmlgraph repository itself
    repo_src = project_path / "src" / "python"
    if repo_src.exists():
        sys.path.insert(0, str(repo_src))


def get_graph_dir(cwd: str | None = None) -> Path:
    """Get the .htmlgraph directory path, creating it if necessary.

    The .htmlgraph directory is the root for all HtmlGraph tracking:
    - .htmlgraph/sessions/ - Session HTML files
    - .htmlgraph/features/ - Feature tracking
    - .htmlgraph/events/ - Event JSON files
    - .htmlgraph/htmlgraph.db - SQLite database

    Args:
        cwd: Starting directory for project resolution. Defaults to os.getcwd().

    Returns:
        Path to the .htmlgraph directory (guaranteed to exist).

    Raises:
        OSError: If directory creation fails (e.g., permission denied).
    """
    project_dir = resolve_project_dir(cwd)
    graph_dir = Path(project_dir) / ".htmlgraph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    return graph_dir


def init_logger(name: str) -> logging.Logger:
    """Initialize a logger with standardized configuration.

    Sets up a logger for hook scripts with:
    - Consistent format across all hooks
    - basicConfig applied only once (subsequent calls are ignored)
    - Named logger returned (can be used for filtering)

    Format: "[TIMESTAMP] [LEVEL] [logger_name] message"

    Args:
        name: Logger name (typically __name__ from calling module).

    Returns:
        logging.Logger instance configured and ready to use.

    Example:
        ```python
        logger = init_logger(__name__)
        logger.info("Hook started")
        logger.error("Something went wrong")
        ```
    """
    # Configure basicConfig only once (subsequent calls are no-ops)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Return named logger for this module
    return logging.getLogger(name)


__all__ = [
    "resolve_project_dir",
    "bootstrap_pythonpath",
    "get_graph_dir",
    "init_logger",
]
