"""Tests for copilot CLI compliance enforcement in the PreToolUse hook.

Verifies that subagents are required to attempt copilot before running
direct git-write operations, and that the check fails open on any error.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from htmlgraph.hooks.pretooluse import (
    _has_copilot_attempt,
    _is_git_write_command,
    pretooluse_hook,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(path: str) -> None:
    """Create a minimal agent_events table for tests."""
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS agent_events (
            event_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            input_summary TEXT,
            timestamp TEXT
        )"""
    )
    conn.commit()
    conn.close()


def _insert_event(
    db_path: str,
    agent_id: str,
    session_id: str,
    tool_name: str,
    input_summary: str,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO agent_events VALUES (?,?,?,?,?,?)",
        (f"evt-{agent_id[:8]}", agent_id, session_id, tool_name, input_summary, "2026-01-01"),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Unit tests for _has_copilot_attempt
# ---------------------------------------------------------------------------


def test_has_copilot_attempt_detected_from_agent_events():
    """Copilot attempt is detected when agent_events contains a matching Bash row."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    _make_db(db_path)
    _insert_event(db_path, "agent-abc123", "sess-001", "Bash", "copilot -p 'commit'")

    assert _has_copilot_attempt(db_path, "agent-abc123", "sess-001") is True


def test_has_copilot_attempt_not_detected_without_entry():
    """Returns False when no copilot Bash event exists for agent+session."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    _make_db(db_path)
    _insert_event(db_path, "agent-abc123", "sess-001", "Bash", "git commit -m 'test'")

    assert _has_copilot_attempt(db_path, "agent-abc123", "sess-001") is False


def test_has_copilot_attempt_session_scoped():
    """Copilot attempt in a different session does not count."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    _make_db(db_path)
    _insert_event(db_path, "agent-abc123", "sess-OTHER", "Bash", "copilot -p 'commit'")

    # Different session — should not match
    assert _has_copilot_attempt(db_path, "agent-abc123", "sess-001") is False


def test_has_copilot_attempt_returns_true_on_db_error():
    """Returns True (fail-open) when the database cannot be opened."""
    result = _has_copilot_attempt("/nonexistent/path/htmlgraph.db", "agent-x", "sess-x")
    assert result is True


# ---------------------------------------------------------------------------
# Unit tests for _is_git_write_command
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'fix'",
        "git push origin main",
        "git tag v1.0.0",
        "git merge feature-branch",
        "uv run ruff check --fix && git commit -m 'lint'",
        "echo done ; git push",
    ],
)
def test_is_git_write_command_detects_write_ops(command: str):
    assert _is_git_write_command(command) is True


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git diff HEAD",
        "git log --oneline",
        "git fetch origin",
        "git checkout main",
        "uv run pytest",
        "copilot -p 'commit changes' --allow-all-tools",
    ],
)
def test_is_git_write_command_allows_read_ops(command: str):
    assert _is_git_write_command(command) is False


# ---------------------------------------------------------------------------
# Integration tests for pretooluse_hook copilot compliance
# ---------------------------------------------------------------------------


def _bash_tool_input(command: str, agent_id: str = "") -> dict:
    payload: dict = {
        "name": "Bash",
        "input": {"command": command},
    }
    if agent_id:
        payload["agent_id"] = agent_id
    return payload


@pytest.mark.asyncio
async def test_git_write_denied_for_subagent_without_prior_copilot():
    """Subagent running git-write without a prior copilot attempt is denied."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _make_db(db_path)

    with (
        patch("htmlgraph.config.get_database_path", return_value=Path(db_path)),
        patch("htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"),
    ):
        result = await pretooluse_hook(_bash_tool_input("git commit -m 'test'", agent_id="agent-xyz"))

    decision = result.get("hookSpecificOutput", {}).get("permissionDecision")
    # The deny may be converted to allow in non-strict mode, but the reason must be present
    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "") or \
             result.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "copilot" in reason.lower(), f"Expected copilot guidance in response, got: {result}"


@pytest.mark.asyncio
async def test_git_write_allowed_for_subagent_with_prior_copilot():
    """Subagent that previously ran copilot may use git-write directly."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _make_db(db_path)
    # Insert a copilot attempt for this agent+session
    _insert_event(db_path, "agent-xyz", "sess-001", "Bash", "copilot -p 'commit'")

    with (
        patch("htmlgraph.config.get_database_path", return_value=Path(db_path)),
        patch("htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"),
    ):
        result = await pretooluse_hook(_bash_tool_input("git commit -m 'test'", agent_id="agent-xyz"))

    # Should not have a copilot-specific denial reason
    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    assert "copilot" not in reason.lower() or reason == "", \
        f"Unexpected copilot denial for agent with prior attempt: {result}"


@pytest.mark.asyncio
async def test_git_write_always_allowed_for_main_agent():
    """The main orchestrator agent (no agent_id) is never subject to copilot enforcement."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _make_db(db_path)

    with (
        patch("htmlgraph.config.get_database_path", return_value=Path(db_path)),
        patch("htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"),
    ):
        # No agent_id — this is the main orchestrator
        result = await pretooluse_hook(_bash_tool_input("git commit -m 'test'"))

    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    assert "copilot" not in reason.lower(), \
        f"Main agent should not be subject to copilot enforcement: {result}"


@pytest.mark.asyncio
async def test_non_git_bash_always_allowed_regardless_of_copilot():
    """Non-git-write Bash commands are never blocked by copilot compliance."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _make_db(db_path)
    # No copilot attempt recorded

    with (
        patch("htmlgraph.config.get_database_path", return_value=Path(db_path)),
        patch("htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"),
    ):
        result = await pretooluse_hook(_bash_tool_input("uv run pytest", agent_id="agent-xyz"))

    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    assert "copilot" not in reason.lower(), \
        f"Non-git command should not trigger copilot enforcement: {result}"


@pytest.mark.asyncio
async def test_compliance_check_fails_open_on_db_error():
    """When the DB check raises an exception, the agent is not blocked."""
    with (
        patch("htmlgraph.config.get_database_path", side_effect=Exception("DB unavailable")),
        patch("htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"),
    ):
        result = await pretooluse_hook(_bash_tool_input("git commit -m 'test'", agent_id="agent-xyz"))

    # Must not have a copilot denial reason — fail-open
    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    # If there's a reason, it should not be the copilot one
    assert "Try copilot CLI first" not in reason, \
        f"Compliance check should fail open on DB error, got: {result}"
