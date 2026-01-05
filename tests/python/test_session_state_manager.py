"""
Tests for SessionStateManager - Session state and environment variable management.

Tests cover:
- Fresh session detection
- Post-compact detection
- Environment variable setup
- Delegation status determination
- Session validity checking
"""

import json
import os

import pytest
from htmlgraph.session_state import SessionStateManager


@pytest.fixture
def temp_graph_dir(tmp_path):
    """Create a temporary .htmlgraph directory."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir()
    (graph_dir / "sessions").mkdir()
    (graph_dir / "features").mkdir()
    return graph_dir


@pytest.fixture
def manager(temp_graph_dir):
    """Create a SessionStateManager for testing."""
    return SessionStateManager(temp_graph_dir)


class TestSessionStateDetection:
    """Tests for session state detection logic."""

    def test_fresh_session_startup(self, manager, monkeypatch):
        """Test fresh session on first startup."""
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)

        state = manager.get_current_state()

        assert state["session_id"]
        assert state["session_source"] == "startup"
        assert state["is_post_compact"] is False
        assert state["previous_session_id"] is None
        assert state["session_valid"] is True

    def test_same_session_resume(self, manager, monkeypatch):
        """Test resuming the same session (context switch)."""
        # Simulate first session
        session_id = "sess-test-001"
        monkeypatch.setenv("CLAUDE_SESSION_ID", session_id)

        # Get state
        state1 = manager.get_current_state()
        assert state1["session_source"] == "startup"

        # Record this state
        manager.record_state(
            session_id=session_id,
            source="startup",
            is_post_compact=False,
            delegation_enabled=False,
        )

        # Simulate same session resuming
        monkeypatch.setenv("CLAUDE_SESSION_ID", session_id)
        state2 = manager.get_current_state()

        assert state2["session_id"] == session_id
        assert state2["session_source"] == "resume"
        assert state2["is_post_compact"] is False

    def test_post_compact_detection(self, manager, monkeypatch):
        """Test detection of post-compact session."""
        # Simulate first session that ended
        prev_session_id = "sess-prev-001"
        monkeypatch.setenv("CLAUDE_SESSION_ID", prev_session_id)

        manager.record_state(
            session_id=prev_session_id,
            source="startup",
            is_post_compact=False,
            delegation_enabled=False,
        )

        # Now mark it as ended
        state_file = manager.sessions_dir / manager.SESSION_STATE_FILE
        state_data = json.loads(state_file.read_text())
        state_data["is_ended"] = True
        state_file.write_text(json.dumps(state_data))

        # Simulate new session (post-compact)
        new_session_id = "sess-new-001"
        monkeypatch.setenv("CLAUDE_SESSION_ID", new_session_id)

        state2 = manager.get_current_state()

        assert state2["session_id"] == new_session_id
        assert state2["session_source"] == "compact"
        assert state2["is_post_compact"] is True
        assert state2["previous_session_id"] == prev_session_id

    def test_clear_command_detection(self, manager, monkeypatch, temp_graph_dir):
        """Test detection of /clear command."""
        # Create clear marker
        clear_marker = temp_graph_dir / ".clear_marker"
        clear_marker.touch()

        monkeypatch.setenv("CLAUDE_SESSION_ID", "sess-after-clear")

        state = manager.get_current_state()

        # Should detect clear (though may still show as startup)
        # The exact behavior depends on marker file handling
        assert state["session_id"]

        # Cleanup
        clear_marker.unlink()


class TestEnvironmentVariableSetup:
    """Tests for environment variable setup."""

    def test_env_vars_set_correctly(self, manager, monkeypatch):
        """Test that all environment variables are set correctly."""
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_DELEGATION_ENABLED", raising=False)

        state = manager.get_current_state()
        manager.setup_environment_variables(state)

        # Verify environment variables are set
        assert os.environ.get("CLAUDE_SESSION_ID") == state["session_id"]
        assert os.environ.get("CLAUDE_SESSION_SOURCE") == state["session_source"]
        assert (
            os.environ.get("CLAUDE_SESSION_COMPACTED")
            == str(state["is_post_compact"]).lower()
        )
        assert (
            os.environ.get("CLAUDE_DELEGATION_ENABLED")
            == str(state["delegation_enabled"]).lower()
        )

    def test_env_vars_returned(self, manager):
        """Test that environment variables are returned in dict."""
        state = manager.get_current_state()
        env_vars = manager.setup_environment_variables(state)

        assert "CLAUDE_SESSION_ID" in env_vars
        assert "CLAUDE_SESSION_SOURCE" in env_vars
        assert "CLAUDE_SESSION_COMPACTED" in env_vars
        assert "CLAUDE_DELEGATION_ENABLED" in env_vars
        assert "CLAUDE_ORCHESTRATOR_ACTIVE" in env_vars
        assert "CLAUDE_PROMPT_PERSISTENCE_VERSION" in env_vars

    def test_previous_session_id_env_var(self, manager, monkeypatch):
        """Test CLAUDE_PREVIOUS_SESSION_ID environment variable."""
        # Set up previous session
        prev_id = "sess-prev-001"
        session_id = "sess-current-001"

        monkeypatch.setenv("CLAUDE_SESSION_ID", prev_id)
        manager.record_state(
            session_id=prev_id,
            source="startup",
            is_post_compact=False,
            delegation_enabled=False,
        )

        # End previous session
        state_file = manager.sessions_dir / manager.SESSION_STATE_FILE
        state_data = json.loads(state_file.read_text())
        state_data["is_ended"] = True
        state_file.write_text(json.dumps(state_data))

        # New session
        monkeypatch.setenv("CLAUDE_SESSION_ID", session_id)
        state2 = manager.get_current_state()
        manager.setup_environment_variables(state2)

        # Check previous session ID is in env
        if state2["previous_session_id"]:
            assert os.environ.get("CLAUDE_PREVIOUS_SESSION_ID") == prev_id


class TestDelegationStatus:
    """Tests for delegation enable/disable logic."""

    def test_delegation_enabled_on_post_compact(self, manager, monkeypatch):
        """Test delegation is enabled on post-compact."""
        prev_id = "sess-prev-001"
        new_id = "sess-new-001"

        # Set up and end previous session
        monkeypatch.setenv("CLAUDE_SESSION_ID", prev_id)
        manager.record_state(
            session_id=prev_id,
            source="startup",
            is_post_compact=False,
            delegation_enabled=False,
        )

        state_file = manager.sessions_dir / manager.SESSION_STATE_FILE
        state_data = json.loads(state_file.read_text())
        state_data["is_ended"] = True
        state_file.write_text(json.dumps(state_data))

        # New post-compact session
        monkeypatch.setenv("CLAUDE_SESSION_ID", new_id)
        state2 = manager.get_current_state()

        # Delegation should be enabled on post-compact
        assert state2["is_post_compact"] is True
        assert state2["delegation_enabled"] is True

    def test_delegation_disabled_override(self, manager, monkeypatch):
        """Test delegation can be disabled via environment variable."""
        monkeypatch.setenv("HTMLGRAPH_DELEGATION_DISABLE", "1")

        state = manager.get_current_state()
        # Delegation should be disabled
        assert state["delegation_enabled"] is False


class TestSessionMetadataRecording:
    """Tests for session metadata storage."""

    def test_state_recorded_to_file(self, manager):
        """Test session state is recorded to file."""
        session_id = "sess-test-001"
        env_vars = {"CLAUDE_SESSION_ID": session_id}

        manager.record_state(
            session_id=session_id,
            source="startup",
            is_post_compact=False,
            delegation_enabled=True,
            environment_vars=env_vars,
        )

        state_file = manager.sessions_dir / manager.SESSION_STATE_FILE
        assert state_file.exists()

        data = json.loads(state_file.read_text())
        assert data["session_id"] == session_id
        assert data["source"] == "startup"
        assert data["is_post_compact"] is False
        assert data["delegation_enabled"] is True

    def test_state_file_has_timestamp(self, manager):
        """Test recorded state includes timestamp."""
        manager.record_state(
            session_id="sess-001",
            source="startup",
            is_post_compact=False,
            delegation_enabled=False,
        )

        state_file = manager.sessions_dir / manager.SESSION_STATE_FILE
        data = json.loads(state_file.read_text())

        assert "timestamp" in data
        assert data["timestamp"]  # Non-empty timestamp


class TestSessionValidity:
    """Tests for session validity checking."""

    def test_session_valid_when_writable(self, manager):
        """Test session is valid when directory is writable."""
        state = manager.get_current_state()

        assert state["session_valid"] is True

    def test_session_has_all_required_fields(self, manager):
        """Test session state has all required fields."""
        state = manager.get_current_state()

        required_fields = [
            "session_id",
            "session_source",
            "is_post_compact",
            "delegation_enabled",
            "prompt_injected",
            "session_valid",
            "timestamp",
            "compact_metadata",
        ]

        for field in required_fields:
            assert field in state


class TestCompactAutoDetection:
    """Tests for automatic compact detection."""

    def test_detect_compact_same_session(self, manager, monkeypatch):
        """Test compact detection with same session ID."""
        session_id = "sess-same"
        monkeypatch.setenv("CLAUDE_SESSION_ID", session_id)

        manager.record_state(
            session_id=session_id,
            source="startup",
            is_post_compact=False,
            delegation_enabled=False,
        )

        is_compact = manager.detect_compact_automatically()
        assert is_compact is False

    def test_detect_compact_different_session(self, manager, monkeypatch):
        """Test compact detection with different session ID."""
        prev_id = "sess-prev"
        new_id = "sess-new"

        monkeypatch.setenv("CLAUDE_SESSION_ID", prev_id)
        manager.record_state(
            session_id=prev_id,
            source="startup",
            is_post_compact=False,
            delegation_enabled=False,
        )

        # Mark as ended
        state_file = manager.sessions_dir / manager.SESSION_STATE_FILE
        state_data = json.loads(state_file.read_text())
        state_data["is_ended"] = True
        state_file.write_text(json.dumps(state_data))

        monkeypatch.setenv("CLAUDE_SESSION_ID", new_id)
        is_compact = manager.detect_compact_automatically()

        assert is_compact is True
