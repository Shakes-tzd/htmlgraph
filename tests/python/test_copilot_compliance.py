"""Tests for external CLI compliance enforcement in the PreToolUse hook.

Verifies that subagents are required to attempt an external CLI (copilot,
codex, or gemini) before running direct git-write operations, and that the
check fails open on any error.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from htmlgraph.hooks.pretooluse import (
    _has_external_cli_attempt,
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
        (
            f"evt-{agent_id[:8]}",
            agent_id,
            session_id,
            tool_name,
            input_summary,
            "2026-01-01",
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Unit tests for _has_external_cli_attempt
# ---------------------------------------------------------------------------


def test_has_external_cli_attempt_detected_copilot():
    """Copilot attempt is detected when agent_events contains a matching Bash row."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    _make_db(db_path)
    _insert_event(db_path, "agent-abc123", "sess-001", "Bash", "copilot -p 'commit'")

    assert _has_external_cli_attempt(db_path, "agent-abc123", "sess-001") is True


def test_has_external_cli_attempt_detects_codex():
    """codex exec invocation is recognised as an external CLI attempt."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    _make_db(db_path)
    _insert_event(
        db_path,
        "agent-abc123",
        "sess-001",
        "Bash",
        "codex exec 'commit changes' --full-auto --json -m gpt-4.1-mini -C .",
    )

    assert _has_external_cli_attempt(db_path, "agent-abc123", "sess-001") is True


def test_has_external_cli_attempt_detects_gemini_short_flag():
    """gemini -p invocation is recognised as an external CLI attempt."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    _make_db(db_path)
    _insert_event(
        db_path,
        "agent-abc123",
        "sess-001",
        "Bash",
        "gemini -p 'commit changes' --output-format json --yolo",
    )

    assert _has_external_cli_attempt(db_path, "agent-abc123", "sess-001") is True


def test_has_external_cli_attempt_detects_gemini_long_flag():
    """gemini --prompt invocation is recognised as an external CLI attempt."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    _make_db(db_path)
    _insert_event(
        db_path,
        "agent-abc123",
        "sess-001",
        "Bash",
        "gemini --prompt 'commit changes' --yolo",
    )

    assert _has_external_cli_attempt(db_path, "agent-abc123", "sess-001") is True


def test_has_external_cli_attempt_not_detected_without_entry():
    """Returns False when no external CLI Bash event exists for agent+session."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    _make_db(db_path)
    _insert_event(db_path, "agent-abc123", "sess-001", "Bash", "git commit -m 'test'")

    assert _has_external_cli_attempt(db_path, "agent-abc123", "sess-001") is False


def test_has_external_cli_attempt_session_scoped():
    """External CLI attempt in a different session does not count."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    _make_db(db_path)
    _insert_event(db_path, "agent-abc123", "sess-OTHER", "Bash", "copilot -p 'commit'")

    # Different session — should not match
    assert _has_external_cli_attempt(db_path, "agent-abc123", "sess-001") is False


def test_has_external_cli_attempt_returns_true_on_db_error():
    """Returns True (fail-open) when the database cannot be opened."""
    result = _has_external_cli_attempt(
        "/nonexistent/path/htmlgraph.db", "agent-x", "sess-x"
    )
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
# Integration tests for pretooluse_hook external CLI compliance
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
async def test_git_write_denied_for_subagent_without_prior_external_cli():
    """Subagent running git-write without a prior external CLI attempt is denied."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _make_db(db_path)

    with (
        patch("htmlgraph.config.get_database_path", return_value=Path(db_path)),
        patch(
            "htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"
        ),
    ):
        result = await pretooluse_hook(
            _bash_tool_input("git commit -m 'test'", agent_id="agent-xyz")
        )

    # The deny may be converted to allow in non-strict mode, but the reason must be present
    reason = result.get("hookSpecificOutput", {}).get(
        "permissionDecisionReason", ""
    ) or result.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "external cli" in reason.lower() or "copilot" in reason.lower(), (
        f"Expected external CLI guidance in response, got: {result}"
    )


@pytest.mark.asyncio
async def test_git_write_allowed_for_subagent_with_prior_copilot():
    """Subagent that previously ran copilot may use git-write directly."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _make_db(db_path)
    _insert_event(db_path, "agent-xyz", "sess-001", "Bash", "copilot -p 'commit'")

    with (
        patch("htmlgraph.config.get_database_path", return_value=Path(db_path)),
        patch(
            "htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"
        ),
    ):
        result = await pretooluse_hook(
            _bash_tool_input("git commit -m 'test'", agent_id="agent-xyz")
        )

    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    assert "Try an external CLI" not in reason, (
        f"Unexpected denial for agent with prior copilot attempt: {result}"
    )


@pytest.mark.asyncio
async def test_git_write_allowed_after_codex_attempt():
    """Git-write allowed for subagent that tried codex first."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _make_db(db_path)
    _insert_event(
        db_path,
        "agent-xyz",
        "sess-001",
        "Bash",
        "codex exec 'commit changes' --full-auto --json -m gpt-4.1-mini -C .",
    )

    with (
        patch("htmlgraph.config.get_database_path", return_value=Path(db_path)),
        patch(
            "htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"
        ),
    ):
        result = await pretooluse_hook(
            _bash_tool_input("git commit -m 'test'", agent_id="agent-xyz")
        )

    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    assert "Try an external CLI" not in reason, (
        f"Unexpected denial for agent with prior codex attempt: {result}"
    )


@pytest.mark.asyncio
async def test_git_write_allowed_after_gemini_attempt():
    """Git-write allowed for subagent that tried gemini first."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _make_db(db_path)
    _insert_event(
        db_path,
        "agent-xyz",
        "sess-001",
        "Bash",
        "gemini -p 'commit changes' --output-format json --yolo",
    )

    with (
        patch("htmlgraph.config.get_database_path", return_value=Path(db_path)),
        patch(
            "htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"
        ),
    ):
        result = await pretooluse_hook(
            _bash_tool_input("git commit -m 'test'", agent_id="agent-xyz")
        )

    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    assert "Try an external CLI" not in reason, (
        f"Unexpected denial for agent with prior gemini attempt: {result}"
    )


@pytest.mark.asyncio
async def test_git_write_always_allowed_for_main_agent():
    """The main orchestrator agent (no agent_id) is never subject to external CLI enforcement."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _make_db(db_path)

    with (
        patch("htmlgraph.config.get_database_path", return_value=Path(db_path)),
        patch(
            "htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"
        ),
    ):
        # No agent_id — this is the main orchestrator
        result = await pretooluse_hook(_bash_tool_input("git commit -m 'test'"))

    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    assert "Try an external CLI" not in reason, (
        f"Main agent should not be subject to external CLI enforcement: {result}"
    )


@pytest.mark.asyncio
async def test_non_git_bash_always_allowed_regardless_of_copilot():
    """Non-git-write Bash commands are never blocked by external CLI compliance."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _make_db(db_path)
    # No external CLI attempt recorded

    with (
        patch("htmlgraph.config.get_database_path", return_value=Path(db_path)),
        patch(
            "htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"
        ),
    ):
        result = await pretooluse_hook(
            _bash_tool_input("uv run pytest", agent_id="agent-xyz")
        )

    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    assert "Try an external CLI" not in reason, (
        f"Non-git command should not trigger external CLI enforcement: {result}"
    )


@pytest.mark.asyncio
async def test_compliance_check_fails_open_on_db_error():
    """When the DB check raises an exception, the agent is not blocked."""
    with (
        patch(
            "htmlgraph.config.get_database_path",
            side_effect=Exception("DB unavailable"),
        ),
        patch(
            "htmlgraph.hooks.pretooluse.get_current_session_id", return_value="sess-001"
        ),
    ):
        result = await pretooluse_hook(
            _bash_tool_input("git commit -m 'test'", agent_id="agent-xyz")
        )

    # Must not have an external CLI denial reason — fail-open
    reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    assert "Try an external CLI" not in reason, (
        f"Compliance check should fail open on DB error, got: {result}"
    )
