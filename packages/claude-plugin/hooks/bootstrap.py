#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
HtmlGraph Hook Bootstrap Utilities

Shared bootstrap code for all Claude Code hooks.
Handles:
- Project directory resolution
- Python path bootstrapping for local imports
- Disable tracking checks
- Logger configuration
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path


def resolve_project_dir(cwd: str | None = None) -> str:
    """
    Resolve project directory from multiple sources.

    Preference order:
    1. CLAUDE_PROJECT_DIR environment variable
    2. Git repository root
    3. Current working directory

    Args:
        cwd: Optional starting directory for git search

    Returns:
        Absolute path to project directory
    """
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        return env_dir

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
        pass

    return start_dir


def bootstrap_pythonpath(project_dir: str) -> None:
    """
    Bootstrap Python import paths for htmlgraph.

    Makes `htmlgraph` importable in two modes:
    1. Running in htmlgraph repo: adds src/python to sys.path
    2. Running in project with .venv: adds venv site-packages

    Args:
        project_dir: Project directory to bootstrap
    """
    # If project has local venv, add its site-packages
    venv = Path(project_dir) / ".venv"
    if venv.exists():
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidates = [
            venv / "lib" / pyver / "site-packages",  # macOS/Linux
            venv / "Lib" / "site-packages",  # Windows
        ]
        for c in candidates:
            if c.exists():
                sys.path.insert(0, str(c))

    # If running in htmlgraph repo, add repo source
    repo_src = Path(project_dir) / "src" / "python"
    if repo_src.exists():
        sys.path.insert(0, str(repo_src))


def is_tracking_disabled() -> bool:
    """
    Check if tracking is disabled via environment variable.

    Returns:
        True if HTMLGRAPH_DISABLE_TRACKING=1
    """
    return os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1"


def init_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Initialize a logger with standardized formatting.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


def get_graph_dir(project_dir: str | None = None) -> Path:
    """
    Get or create .htmlgraph directory.

    Args:
        project_dir: Project directory (default: cwd)

    Returns:
        Path to .htmlgraph directory (created if missing)
    """
    if project_dir is None:
        project_dir = os.getcwd()

    graph_dir = Path(project_dir) / ".htmlgraph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    return graph_dir


def safe_json_output(data: dict, default_empty: bool = False) -> str:
    """
    Serialize data to JSON for hook output, with safe fallback.

    Args:
        data: Dictionary to serialize
        default_empty: Return empty dict on error if True

    Returns:
        JSON string representation of data
    """
    try:
        return json.dumps(data, default=str)
    except Exception:
        fallback = {} if default_empty else {"error": "Failed to serialize output"}
        return json.dumps(fallback)
