#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
PreToolUse Hook - Thin wrapper around package logic.

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.pretooluse package module, which runs orchestrator
enforcement and work validation in parallel.

Performance: ~40-50% faster than previous subprocess-based approach.
"""

import os
import subprocess
import sys
from pathlib import Path


# Bootstrap Python path to find local htmlgraph source
def _resolve_project_dir(cwd: str | None = None) -> str:
    """Prefer Claude's project dir env var; fall back to git root; then cwd."""
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


def _bootstrap_pythonpath(project_dir: str) -> None:
    """Make `htmlgraph` importable in two common modes."""
    venv = Path(project_dir) / ".venv"
    if venv.exists():
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidates = [
            venv / "lib" / pyver / "site-packages",
            venv / "Lib" / "site-packages",
        ]
        for c in candidates:
            if c.exists():
                sys.path.insert(0, str(c))

    repo_src = Path(project_dir) / "src" / "python"
    if repo_src.exists():
        sys.path.insert(0, str(repo_src))


project_dir_for_import = _resolve_project_dir()
_bootstrap_pythonpath(project_dir_for_import)

from htmlgraph.hooks.pretooluse import main

if __name__ == "__main__":
    main()
