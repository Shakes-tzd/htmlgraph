"""
Subagent Context Detection for Orchestrator Mode

This module provides utilities to detect when code is executing within a
delegated subagent context (spawned via Task() tool) vs. the main orchestrator.

Key Problem:
PreToolUse hooks (orchestrator-enforce.py, validator.py) enforce delegation
rules that block direct tool use in strict mode. However, subagents MUST use
tools directly - that's the delegated work. Without context detection, subagents
get blocked, making strict orchestrator mode unusable.

Solution:
Detect subagent context via multiple signals:
1. Environment variables set by Claude Code when spawning Task() subagents
2. Session state markers in database
3. Parent session tracking

Usage:
    from htmlgraph.hooks.subagent_detection import is_subagent_context

    if is_subagent_context():
        # Allow direct tool use - this is delegated work
        return {"continue": True}
    else:
        # Enforce delegation rules - this is orchestrator
        return enforce_delegation(tool, params)
"""

import os
from pathlib import Path
from typing import Any


def is_subagent_context() -> bool:
    """
    Check if we're executing within a delegated subagent (spawned via Task()).

    Detection Strategy (in priority order):
    1. CLAUDE_SUBAGENT_ID environment variable (set by Task() spawner)
    2. CLAUDE_PARENT_SESSION_ID environment variable (set by Task() spawner)
    3. Session state marker in database (is_subagent flag)
    4. Active session has parent_session_id set

    Returns:
        True if executing in subagent context, False if orchestrator context

    Note:
        - Gracefully degrades if detection mechanisms fail (returns False)
        - False positives are safe (allow direct tool use)
        - False negatives would break subagents (must be avoided)
    """
    # Check 1: Direct environment variable from Task() spawner
    if os.getenv("CLAUDE_SUBAGENT_ID"):
        return True

    # Check 2: Parent session ID indicates we're a subagent
    if os.getenv("CLAUDE_PARENT_SESSION_ID"):
        return True

    # Check 3: Session state marker in database
    try:
        session_state = _load_session_state()
        if session_state.get("is_subagent", False):
            return True

        # Check 4: Session has parent_session_id
        if session_state.get("parent_session_id"):
            return True
    except Exception:
        # Graceful degradation - if we can't check, assume NOT subagent
        # This is safe because it only allows stricter enforcement
        pass

    # Check 5: Query database for active session with parent_session_id
    try:
        if _has_parent_session_in_db():
            return True
    except Exception:
        pass

    return False


def _load_session_state() -> dict[str, Any]:
    """
    Load session state from .htmlgraph/session-state.json.

    Returns:
        Session state dict, or empty dict if not found
    """
    try:
        # Find .htmlgraph directory
        graph_dir = _find_graph_dir()
        if not graph_dir:
            return {}

        state_file = graph_dir / "session-state.json"
        if not state_file.exists():
            return {}

        import json

        result: dict[str, Any] = json.loads(state_file.read_text())
        return result
    except Exception:
        return {}


def _has_parent_session_in_db() -> bool:
    """
    Check if current session has a parent_session_id in database.

    Returns:
        True if session is a subagent (has parent), False otherwise
    """
    try:
        graph_dir = _find_graph_dir()
        if not graph_dir:
            return False

        db_path = graph_dir / "htmlgraph.db"
        if not db_path.exists():
            return False

        import sqlite3

        # Get current session ID from environment or database

        # We need hook_input to create context, but we don't have it here
        # Fall back to environment check
        session_id = os.getenv("HTMLGRAPH_SESSION_ID") or os.getenv("CLAUDE_SESSION_ID")

        if not session_id:
            # Try to get most recent session from database
            conn = sqlite3.connect(str(db_path), timeout=1.0)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id FROM sessions
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                session_id = row[0]
            conn.close()

            if not session_id:
                return False

        # Check if this session has a parent
        conn = sqlite3.connect(str(db_path), timeout=1.0)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT parent_session_id FROM sessions
            WHERE session_id = ?
        """,
            (session_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return True

    except Exception:
        pass

    return False


def _find_graph_dir() -> Path | None:
    """
    Find .htmlgraph directory starting from current working directory.

    Returns:
        Path to .htmlgraph directory, or None if not found
    """
    try:
        cwd = Path.cwd()
        graph_dir = cwd / ".htmlgraph"

        if graph_dir.exists():
            return graph_dir

        # Search up to 3 parent directories
        for parent in [cwd.parent, cwd.parent.parent, cwd.parent.parent.parent]:
            candidate = parent / ".htmlgraph"
            if candidate.exists():
                return candidate

    except Exception:
        pass

    return None


__all__ = [
    "is_subagent_context",
]
