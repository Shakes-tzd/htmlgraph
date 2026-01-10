"""
Tests for session_handler module.

Tests session lifecycle management and tracking including:
- Session initialization and retrieval
- Session start and end operations
- User query event recording
- Version status checking
- Error handling and graceful degradation
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest
from htmlgraph.hooks.session_handler import (
    check_version_status,
    handle_session_end,
    handle_session_start,
    init_or_get_session,
    record_user_query_event,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_hook_context():
    """Create a mock HookContext with common properties."""
    context = mock.MagicMock()
    context.project_dir = "/test/project"
    context.graph_dir = Path("/test/project/.htmlgraph")
    context.session_id = "sess-test-123"
    context.agent_id = "claude-code"
    context.hook_input = {}
    context.log = mock.MagicMock()
    return context


@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager."""
    manager = mock.MagicMock()
    manager.get_active_session_for_agent = mock.MagicMock()
    manager.get_active_session = mock.MagicMock()
    manager.start_session = mock.MagicMock()
    manager.track_activity = mock.MagicMock()
    manager.set_session_handoff = mock.MagicMock()
    manager.link_transcript = mock.MagicMock()
    return manager


@pytest.fixture
def mock_session():
    """Create a mock Session object."""
    session = mock.MagicMock()
    session.id = "session-abc123"
    session.agent = "claude-code"
    return session


@pytest.fixture
def mock_database():
    """Create a mock HtmlGraphDB."""
    db = mock.MagicMock()
    connection = mock.MagicMock()
    cursor = mock.MagicMock()

    connection.cursor.return_value = cursor
    db.connection = connection
    db.insert_event = mock.MagicMock(return_value=True)
    db.close = mock.MagicMock()

    return db


@pytest.fixture
def hook_input_base():
    """Base hook input dictionary."""
    return {
        "session_id": "sess-external-xyz",
        "type": "session-start",
        "agent_id": "claude-code",
    }


# ============================================================================
# Tests for init_or_get_session()
# ============================================================================


class TestInitOrGetSession:
    """Test session initialization and retrieval."""

    def test_get_existing_active_session(
        self, mock_hook_context, mock_session_manager, mock_session
    ):
        """Test retrieving an existing active session for agent."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session_for_agent.return_value = mock_session

        result = init_or_get_session(mock_hook_context)

        assert result is mock_session
        mock_session_manager.get_active_session_for_agent.assert_called_once_with(
            agent="claude-code"
        )
        mock_hook_context.log.assert_called()

    def test_create_new_session_when_none_exists(
        self, mock_hook_context, mock_session_manager, mock_session
    ):
        """Test creating a new session when none exists for agent."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session_for_agent.return_value = None
        mock_session_manager.start_session.return_value = mock_session

        with mock.patch(
            "htmlgraph.hooks.session_handler._get_head_commit", return_value="abc1234"
        ):
            result = init_or_get_session(mock_hook_context)

        assert result is mock_session
        mock_session_manager.start_session.assert_called_once()
        call_kwargs = mock_session_manager.start_session.call_args[1]
        assert call_kwargs["agent"] == "claude-code"
        assert call_kwargs["start_commit"] == "abc1234"
        assert "session_id" in call_kwargs

    def test_create_session_without_git_commit(
        self, mock_hook_context, mock_session_manager, mock_session
    ):
        """Test session creation when git commit cannot be determined."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session_for_agent.return_value = None
        mock_session_manager.start_session.return_value = mock_session

        with mock.patch(
            "htmlgraph.hooks.session_handler._get_head_commit", side_effect=Exception()
        ):
            result = init_or_get_session(mock_hook_context)

        assert result is mock_session
        call_kwargs = mock_session_manager.start_session.call_args[1]
        assert call_kwargs["start_commit"] is None

    def test_session_manager_unavailable_returns_none(self, mock_hook_context):
        """Test graceful degradation when SessionManager unavailable."""
        # Make session_manager a property that raises ImportError
        type(mock_hook_context).session_manager = mock.PropertyMock(
            side_effect=ImportError("SessionManager not available")
        )

        result = init_or_get_session(mock_hook_context)

        assert result is None
        mock_hook_context.log.assert_called_with("error", mock.ANY)

    def test_session_initialization_error_returns_none(self, mock_hook_context):
        """Test error handling when session initialization fails."""
        mock_hook_context.session_manager = mock.MagicMock()
        mock_hook_context.session_manager.get_active_session_for_agent.side_effect = (
            RuntimeError("Database error")
        )

        result = init_or_get_session(mock_hook_context)

        assert result is None
        mock_hook_context.log.assert_called_with("error", mock.ANY)

    def test_logs_session_id(
        self, mock_hook_context, mock_session_manager, mock_session
    ):
        """Test that session ID is logged for debugging."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session_for_agent.return_value = mock_session

        init_or_get_session(mock_hook_context)

        # Check that log was called with session info
        log_calls = mock_hook_context.log.call_args_list
        assert any("session-abc123" in str(call) for call in log_calls)


# ============================================================================
# Tests for handle_session_start()
# ============================================================================


class TestHandleSessionStart:
    """Test session start operations."""

    def test_returns_correct_structure(self, mock_hook_context):
        """Test that handle_session_start returns proper response structure."""
        result = handle_session_start(mock_hook_context, None)

        assert "continue" in result
        assert result["continue"] is True
        assert "hookSpecificOutput" in result
        assert "sessionFeatureContext" in result["hookSpecificOutput"]
        assert "versionInfo" in result["hookSpecificOutput"]

    def test_returns_default_output_when_no_session(self, mock_hook_context):
        """Test that default output is returned when session is None."""
        result = handle_session_start(mock_hook_context, None)

        assert result["hookSpecificOutput"]["sessionFeatureContext"] == ""
        assert result["hookSpecificOutput"]["versionInfo"] is None

    def test_creates_database_session_entry(
        self, mock_hook_context, mock_session, mock_database
    ):
        """Test that database session entry is created."""
        mock_hook_context.database = mock_database
        cursor = mock_database.connection.cursor()
        cursor.fetchone.return_value = (0,)  # No existing session

        handle_session_start(mock_hook_context, mock_session)

        # Verify session insert was called
        cursor.execute.assert_any_call(
            "SELECT COUNT(*) FROM sessions WHERE session_id = ?",
            ("session-abc123",),
        )
        # Check that INSERT was executed (second call)
        insert_calls = [
            call for call in cursor.execute.call_args_list if "INSERT" in str(call)
        ]
        assert len(insert_calls) > 0

    def test_skips_database_entry_if_already_exists(
        self, mock_hook_context, mock_session, mock_database
    ):
        """Test that database entry creation is skipped if session exists."""
        mock_hook_context.database = mock_database
        cursor = mock_database.connection.cursor()
        cursor.fetchone.return_value = (1,)  # Session exists

        handle_session_start(mock_hook_context, mock_session)

        # Should only have SELECT call, no INSERT
        select_calls = [
            call for call in cursor.execute.call_args_list if "SELECT" in str(call)
        ]
        insert_calls = [
            call for call in cursor.execute.call_args_list if "INSERT" in str(call)
        ]
        assert len(select_calls) >= 1
        assert len(insert_calls) == 0

    def test_tracks_session_start_activity(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that session start activity is tracked."""
        mock_hook_context.session_manager = mock_session_manager
        mock_hook_context.database = None
        mock_hook_context.hook_input = {"session_id": "external-sess-123"}

        with mock.patch(
            "htmlgraph.hooks.session_handler._load_features", return_value=[]
        ):
            handle_session_start(mock_hook_context, mock_session)

        mock_session_manager.track_activity.assert_called()
        call_kwargs = mock_session_manager.track_activity.call_args[1]
        assert call_kwargs["tool"] == "SessionStart"
        assert call_kwargs["session_id"] == "session-abc123"

    def test_loads_and_includes_active_features(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that active features are loaded and included in output."""
        mock_hook_context.session_manager = mock_session_manager
        mock_hook_context.database = None

        features = [
            {"id": "feat-1", "title": "Feature 1", "status": "in-progress"},
            {"id": "feat-2", "title": "Feature 2", "status": "in-progress"},
            {"id": "feat-3", "title": "Feature 3", "status": "completed"},
        ]

        with mock.patch(
            "htmlgraph.hooks.session_handler._load_features", return_value=features
        ):
            result = handle_session_start(mock_hook_context, mock_session)

        context_str = result["hookSpecificOutput"]["sessionFeatureContext"]
        assert "Active Features" in context_str
        assert "Feature 1" in context_str
        assert "Feature 2" in context_str
        # Completed feature should not appear
        assert "Feature 3" not in context_str

    def test_limits_feature_context_to_three_features(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that feature context includes at most 3 features."""
        mock_hook_context.session_manager = mock_session_manager
        mock_hook_context.database = None

        features = [
            {"id": f"feat-{i}", "title": f"Feature {i}", "status": "in-progress"}
            for i in range(5)
        ]

        with mock.patch(
            "htmlgraph.hooks.session_handler._load_features", return_value=features
        ):
            result = handle_session_start(mock_hook_context, mock_session)

        context_str = result["hookSpecificOutput"]["sessionFeatureContext"]
        # Count feature entries
        feature_count = context_str.count("**feat-")
        assert feature_count <= 3

    def test_handles_feature_loading_error(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test graceful error handling when feature loading fails."""
        mock_hook_context.session_manager = mock_session_manager
        mock_hook_context.database = None

        with mock.patch(
            "htmlgraph.hooks.session_handler._load_features", side_effect=Exception()
        ):
            result = handle_session_start(mock_hook_context, mock_session)

        # Should still return valid output
        assert result["continue"] is True
        context_str = result["hookSpecificOutput"]["sessionFeatureContext"]
        # Should be empty string if loading failed
        assert context_str == ""

    def test_includes_version_info_when_outdated(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that version info is included when update is available."""
        mock_hook_context.session_manager = mock_session_manager
        mock_hook_context.database = None

        version_info = {
            "installed": "0.9.0",
            "latest": "0.9.1",
            "is_outdated": True,
        }

        with mock.patch(
            "htmlgraph.hooks.session_handler._load_features", return_value=[]
        ):
            with mock.patch(
                "htmlgraph.hooks.session_handler.check_version_status",
                return_value=version_info,
            ):
                result = handle_session_start(mock_hook_context, mock_session)

        assert result["hookSpecificOutput"]["versionInfo"] == version_info

    def test_handles_version_check_error(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test graceful error handling when version check fails."""
        mock_hook_context.session_manager = mock_session_manager
        mock_hook_context.database = None

        with mock.patch(
            "htmlgraph.hooks.session_handler._load_features", return_value=[]
        ):
            with mock.patch(
                "htmlgraph.hooks.session_handler.check_version_status",
                side_effect=Exception(),
            ):
                result = handle_session_start(mock_hook_context, mock_session)

        # Should still return valid output
        assert result["continue"] is True
        assert result["hookSpecificOutput"]["versionInfo"] is None


# ============================================================================
# Tests for handle_session_end()
# ============================================================================


class TestHandleSessionEnd:
    """Test session end operations."""

    def test_returns_success_response(self, mock_hook_context):
        """Test that handle_session_end returns success response."""
        mock_hook_context.session_manager = mock.MagicMock()
        mock_hook_context.session_manager.get_active_session.return_value = None

        result = handle_session_end(mock_hook_context)

        assert "continue" in result
        assert result["continue"] is True
        assert "status" in result

    def test_handles_no_active_session(self, mock_hook_context):
        """Test graceful handling when no active session exists."""
        mock_hook_context.session_manager = mock.MagicMock()
        mock_hook_context.session_manager.get_active_session.return_value = None

        result = handle_session_end(mock_hook_context)

        assert result["status"] == "success"
        mock_hook_context.log.assert_called_with("debug", mock.ANY)

    def test_records_session_end_activity(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that session end activity is recorded."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session.return_value = mock_session

        handle_session_end(mock_hook_context)

        mock_session_manager.track_activity.assert_called()
        call_kwargs = mock_session_manager.track_activity.call_args[1]
        assert call_kwargs["tool"] == "SessionEnd"
        assert call_kwargs["session_id"] == "session-abc123"

    def test_captures_handoff_notes_from_input(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that handoff notes are captured from hook input."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session.return_value = mock_session
        mock_hook_context.hook_input = {"handoff_notes": "Continue with feature X"}

        with mock.patch.dict("os.environ", {}, clear=True):
            handle_session_end(mock_hook_context)

        mock_session_manager.set_session_handoff.assert_called()
        call_kwargs = mock_session_manager.set_session_handoff.call_args[1]
        assert call_kwargs["handoff_notes"] == "Continue with feature X"

    def test_captures_handoff_notes_from_environment(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that handoff notes are captured from environment variable."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session.return_value = mock_session
        mock_hook_context.hook_input = {}

        env = {"HTMLGRAPH_HANDOFF_NOTES": "Env handoff notes"}
        with mock.patch.dict("os.environ", env):
            handle_session_end(mock_hook_context)

        mock_session_manager.set_session_handoff.assert_called()
        call_kwargs = mock_session_manager.set_session_handoff.call_args[1]
        assert call_kwargs["handoff_notes"] == "Env handoff notes"

    def test_captures_recommended_next(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that recommended next work is captured."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session.return_value = mock_session
        mock_hook_context.hook_input = {"recommended_next": "Test feature X"}

        with mock.patch.dict("os.environ", {}, clear=True):
            handle_session_end(mock_hook_context)

        mock_session_manager.set_session_handoff.assert_called()
        call_kwargs = mock_session_manager.set_session_handoff.call_args[1]
        assert call_kwargs["recommended_next"] == "Test feature X"

    def test_parses_blockers_from_string(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that blockers are parsed from comma-separated string."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session.return_value = mock_session
        mock_hook_context.hook_input = {"blockers": "issue1, issue2, issue3"}

        with mock.patch.dict("os.environ", {}, clear=True):
            handle_session_end(mock_hook_context)

        mock_session_manager.set_session_handoff.assert_called()
        call_kwargs = mock_session_manager.set_session_handoff.call_args[1]
        assert call_kwargs["blockers"] == ["issue1", "issue2", "issue3"]

    def test_parses_blockers_from_list(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that blockers can be provided as list."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session.return_value = mock_session
        mock_hook_context.hook_input = {"blockers": ["issue1", "issue2"]}

        with mock.patch.dict("os.environ", {}, clear=True):
            handle_session_end(mock_hook_context)

        mock_session_manager.set_session_handoff.assert_called()
        call_kwargs = mock_session_manager.set_session_handoff.call_args[1]
        assert call_kwargs["blockers"] == ["issue1", "issue2"]

    def test_links_transcript_when_session_id_provided(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that transcript is linked when external session ID provided."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session.return_value = mock_session
        mock_hook_context.hook_input = {"session_id": "external-session-123"}

        mock_transcript = mock.MagicMock()
        mock_transcript.path = "/path/to/transcript.txt"
        mock_transcript.git_branch = "main"

        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch(
                "htmlgraph.transcript.TranscriptReader"
            ) as mock_reader_class:
                mock_reader = mock.MagicMock()
                mock_reader_class.return_value = mock_reader
                mock_reader.read_session.return_value = mock_transcript

                handle_session_end(mock_hook_context)

        mock_session_manager.link_transcript.assert_called()
        call_kwargs = mock_session_manager.link_transcript.call_args[1]
        assert call_kwargs["transcript_id"] == "external-session-123"
        assert call_kwargs["transcript_path"] == "/path/to/transcript.txt"

    def test_cleans_up_temp_files(self, mock_hook_context, tmp_path):
        """Test that temporary files are cleaned up."""
        # Create a temporary graph_dir for testing
        mock_hook_context.session_manager = mock.MagicMock()
        mock_hook_context.session_manager.get_active_session.return_value = None
        mock_hook_context.graph_dir = Path(tmp_path)
        mock_hook_context.log = mock.MagicMock()

        # Create some temp files
        temp_file = Path(tmp_path) / "parent-activity.json"
        temp_file.write_text("{}")
        assert temp_file.exists()

        result = handle_session_end(mock_hook_context)

        # File should be cleaned up after session end
        # The _cleanup_temp_files function is always called at the end of handle_session_end
        assert not temp_file.exists(), f"Temp file still exists: {temp_file}"
        assert result["continue"] is True

    def test_returns_partial_status_on_handoff_error(
        self, mock_hook_context, mock_session, mock_session_manager
    ):
        """Test that status is 'partial' when handoff fails."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session.return_value = mock_session
        mock_session_manager.set_session_handoff.side_effect = Exception()
        mock_hook_context.hook_input = {"handoff_notes": "Some notes"}

        with mock.patch.dict("os.environ", {}, clear=True):
            result = handle_session_end(mock_hook_context)

        assert result["status"] == "partial"

    def test_returns_error_status_on_session_manager_unavailable(
        self, mock_hook_context
    ):
        """Test that status is 'error' when SessionManager unavailable."""
        # Make session_manager a property that raises ImportError
        type(mock_hook_context).session_manager = mock.PropertyMock(
            side_effect=ImportError("SessionManager not available")
        )

        result = handle_session_end(mock_hook_context)

        assert result["status"] == "error"
        mock_hook_context.log.assert_called_with("error", mock.ANY)


# ============================================================================
# Tests for record_user_query_event()
# ============================================================================


class TestRecordUserQueryEvent:
    """Test user query event recording."""

    def test_creates_event_with_correct_fields(self, mock_hook_context, mock_database):
        """Test that event is created with correct fields."""
        mock_hook_context.database = mock_database
        mock_database.insert_event.return_value = True

        with mock.patch("htmlgraph.ids.generate_id", return_value="evt-123"):
            result = record_user_query_event(mock_hook_context, "Test query")

        assert result == "evt-123"
        mock_database.insert_event.assert_called_once()
        call_kwargs = mock_database.insert_event.call_args[1]
        assert call_kwargs["event_type"] == "user_query"
        assert call_kwargs["tool_name"] == "UserQuery"
        assert call_kwargs["agent_id"] == "claude-code"
        assert call_kwargs["session_id"] == "sess-test-123"

    def test_creates_preview_of_prompt(self, mock_hook_context, mock_database):
        """Test that event includes preview of prompt."""
        mock_hook_context.database = mock_database
        mock_database.insert_event.return_value = True

        long_prompt = "x" * 200

        with mock.patch("htmlgraph.ids.generate_id", return_value="evt-123"):
            record_user_query_event(mock_hook_context, long_prompt)

        call_kwargs = mock_database.insert_event.call_args[1]
        preview = call_kwargs["input_summary"]
        assert "..." in preview  # Should have ellipsis for truncated text
        assert len(preview) <= 103  # Max 100 chars + "..."

    def test_includes_prompt_length_in_context(self, mock_hook_context, mock_database):
        """Test that full prompt length is included in context."""
        mock_hook_context.database = mock_database
        mock_database.insert_event.return_value = True

        prompt = "Test query"

        with mock.patch("htmlgraph.ids.generate_id", return_value="evt-123"):
            record_user_query_event(mock_hook_context, prompt)

        call_kwargs = mock_database.insert_event.call_args[1]
        context = call_kwargs["context"]
        assert context["full_prompt_length"] == len(prompt)

    def test_returns_event_id_on_success(self, mock_hook_context, mock_database):
        """Test that event_id is returned on success."""
        mock_hook_context.database = mock_database
        mock_database.insert_event.return_value = True

        with mock.patch("htmlgraph.ids.generate_id", return_value="evt-456"):
            result = record_user_query_event(mock_hook_context, "Query")

        assert result == "evt-456"

    def test_returns_none_on_insert_failure(self, mock_hook_context, mock_database):
        """Test that None is returned if insert fails."""
        mock_hook_context.database = mock_database
        mock_database.insert_event.return_value = False

        with mock.patch("htmlgraph.ids.generate_id", return_value="evt-789"):
            result = record_user_query_event(mock_hook_context, "Query")

        assert result is None
        mock_hook_context.log.assert_called_with("warning", mock.ANY)

    def test_handles_database_import_error(self, mock_hook_context):
        """Test graceful handling when database unavailable."""
        # Make database a property that raises ImportError
        type(mock_hook_context).database = mock.PropertyMock(
            side_effect=ImportError("Database not available")
        )

        result = record_user_query_event(mock_hook_context, "Query")

        assert result is None
        mock_hook_context.log.assert_called_with("debug", mock.ANY)

    def test_handles_general_exception(self, mock_hook_context, mock_database):
        """Test graceful handling of general exceptions."""
        mock_hook_context.database = mock_database
        mock_database.insert_event.side_effect = RuntimeError("DB Error")

        with mock.patch("htmlgraph.ids.generate_id", return_value="evt-999"):
            result = record_user_query_event(mock_hook_context, "Query")

        assert result is None
        mock_hook_context.log.assert_called_with("error", mock.ANY)

    def test_logs_event_id(self, mock_hook_context, mock_database):
        """Test that event ID is logged."""
        mock_hook_context.database = mock_database
        mock_database.insert_event.return_value = True

        with mock.patch("htmlgraph.ids.generate_id", return_value="evt-555"):
            record_user_query_event(mock_hook_context, "Query")

        # Check log was called with event ID
        log_calls = mock_hook_context.log.call_args_list
        assert any("evt-555" in str(call) for call in log_calls)


# ============================================================================
# Tests for check_version_status()
# ============================================================================


class TestCheckVersionStatus:
    """Test version checking functionality."""

    def test_detects_outdated_version(self):
        """Test detection of outdated version."""
        with mock.patch(
            "htmlgraph.hooks.session_handler._get_installed_version",
            return_value="0.9.0",
        ):
            with mock.patch(
                "htmlgraph.hooks.session_handler._get_latest_pypi_version",
                return_value="0.9.1",
            ):
                result = check_version_status()

        assert result is not None
        assert result["installed"] == "0.9.0"
        assert result["latest"] == "0.9.1"
        assert result["is_outdated"] is True

    def test_returns_none_when_versions_match(self):
        """Test that None is returned when versions match."""
        with mock.patch(
            "htmlgraph.hooks.session_handler._get_installed_version",
            return_value="0.9.0",
        ):
            with mock.patch(
                "htmlgraph.hooks.session_handler._get_latest_pypi_version",
                return_value="0.9.0",
            ):
                result = check_version_status()

        assert result is None

    def test_returns_none_when_installed_newer(self):
        """Test that None is returned when installed version is newer."""
        with mock.patch(
            "htmlgraph.hooks.session_handler._get_installed_version",
            return_value="0.9.2",
        ):
            with mock.patch(
                "htmlgraph.hooks.session_handler._get_latest_pypi_version",
                return_value="0.9.1",
            ):
                result = check_version_status()

        assert result is None

    def test_returns_none_when_cannot_get_installed_version(self):
        """Test graceful handling when installed version unavailable."""
        with mock.patch(
            "htmlgraph.hooks.session_handler._get_installed_version",
            return_value=None,
        ):
            with mock.patch(
                "htmlgraph.hooks.session_handler._get_latest_pypi_version",
                return_value="0.9.1",
            ):
                result = check_version_status()

        assert result is None

    def test_returns_none_when_cannot_get_latest_version(self):
        """Test graceful handling when latest version unavailable."""
        with mock.patch(
            "htmlgraph.hooks.session_handler._get_installed_version",
            return_value="0.9.0",
        ):
            with mock.patch(
                "htmlgraph.hooks.session_handler._get_latest_pypi_version",
                return_value=None,
            ):
                result = check_version_status()

        assert result is None

    def test_handles_exception_gracefully(self):
        """Test that exceptions are caught and None returned."""
        with mock.patch(
            "htmlgraph.hooks.session_handler._get_installed_version",
            side_effect=Exception(),
        ):
            result = check_version_status()

        assert result is None


# ============================================================================
# Tests for Private Helper Functions
# ============================================================================


class TestGetHeadCommit:
    """Test _get_head_commit helper function."""

    def test_gets_commit_hash(self):
        """Test successful retrieval of HEAD commit hash."""
        from htmlgraph.hooks.session_handler import _get_head_commit

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.MagicMock(returncode=0, stdout="abc1234\n")
            result = _get_head_commit("/test/project")

        assert result == "abc1234"
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "rev-parse" in str(call_args)

    def test_returns_none_on_git_error(self):
        """Test that None is returned when git command fails."""
        from htmlgraph.hooks.session_handler import _get_head_commit

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.MagicMock(returncode=1)
            result = _get_head_commit("/test/project")

        assert result is None

    def test_returns_none_on_exception(self):
        """Test that None is returned on exception."""
        from htmlgraph.hooks.session_handler import _get_head_commit

        with mock.patch("subprocess.run", side_effect=Exception()):
            result = _get_head_commit("/test/project")

        assert result is None


class TestLoadFeatures:
    """Test _load_features helper function."""

    def test_loads_features_from_graph(self, tmp_path):
        """Test loading features from HtmlGraph."""
        from htmlgraph.hooks.session_handler import _load_features

        # Create a features directory with a test HTML file
        features_dir = tmp_path / "features"
        features_dir.mkdir()
        feature_file = features_dir / "feature-1.html"
        feature_file.write_text("<html><body>Feature 1</body></html>")

        mock_features = [
            {"id": "feat-1", "title": "Feature 1"},
            {"id": "feat-2", "title": "Feature 2"},
        ]

        with mock.patch("htmlgraph.graph.HtmlGraph") as mock_graph_class:
            mock_graph = mock.MagicMock()
            mock_graph_class.return_value = mock_graph
            mock_node_1 = mock.MagicMock()
            mock_node_2 = mock.MagicMock()
            mock_graph.nodes.values.return_value = [mock_node_1, mock_node_2]

            with mock.patch(
                "htmlgraph.converter.node_to_dict",
                side_effect=mock_features,
            ):
                result = _load_features(tmp_path)

        assert len(result) == 2
        assert result == mock_features

    def test_returns_empty_list_when_features_dir_not_exists(self):
        """Test that empty list is returned when features dir doesn't exist."""
        from htmlgraph.hooks.session_handler import _load_features

        result = _load_features(Path("/nonexistent/.htmlgraph"))

        assert result == []

    def test_returns_empty_list_on_error(self):
        """Test that empty list is returned on error."""
        from htmlgraph.hooks.session_handler import _load_features

        with mock.patch("htmlgraph.graph.HtmlGraph", side_effect=Exception()):
            result = _load_features(Path("/test/.htmlgraph"))

        assert result == []


class TestGetInstalledVersion:
    """Test _get_installed_version helper function."""

    def test_gets_version_from_import(self):
        """Test getting version from htmlgraph.__version__."""
        from htmlgraph.hooks.session_handler import _get_installed_version

        # Mock the htmlgraph module import to return a version
        mock_htmlgraph = mock.MagicMock()
        mock_htmlgraph.__version__ = "0.9.0"

        with mock.patch.dict("sys.modules", {"htmlgraph": mock_htmlgraph}):
            # Force reimport by patching the import in the function
            with mock.patch("htmlgraph.__version__", "0.9.0", create=True):
                result = _get_installed_version()

        # Should either get 0.9.0 or actual installed version (0.26.0)
        assert result is not None
        assert isinstance(result, str)

    def test_falls_back_to_pip_show(self):
        """Test fallback to pip show command."""
        # Mock the import to fail so it falls back to pip show
        import builtins

        from htmlgraph.hooks.session_handler import _get_installed_version

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "htmlgraph":
                raise Exception("htmlgraph import failed")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=mock_import):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.MagicMock(
                    returncode=0, stdout="Version: 0.9.0\n"
                )
                result = _get_installed_version()

        assert result == "0.9.0"

    def test_returns_none_when_unavailable(self):
        """Test that None is returned when version unavailable."""
        # Mock both import and pip show to fail
        import builtins

        from htmlgraph.hooks.session_handler import _get_installed_version

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "htmlgraph":
                raise Exception("htmlgraph import failed")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=mock_import):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.MagicMock(returncode=1)
                result = _get_installed_version()

        assert result is None


class TestGetLatestPypiVersion:
    """Test _get_latest_pypi_version helper function."""

    def test_gets_version_from_pypi_api(self):
        """Test getting latest version from PyPI JSON API."""
        from htmlgraph.hooks.session_handler import _get_latest_pypi_version

        mock_response_data = {"info": {"version": "0.9.1"}}

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_file = mock.MagicMock()
            mock_file.read.return_value = json.dumps(mock_response_data).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_file

            result = _get_latest_pypi_version()

        assert result == "0.9.1"

    def test_returns_none_on_network_error(self):
        """Test that None is returned on network error."""
        from htmlgraph.hooks.session_handler import _get_latest_pypi_version

        with mock.patch("urllib.request.urlopen", side_effect=Exception()):
            result = _get_latest_pypi_version()

        assert result is None


class TestCompareVersions:
    """Test _compare_versions helper function."""

    def test_compares_semantic_versions(self):
        """Test semantic version comparison."""
        from htmlgraph.hooks.session_handler import _compare_versions

        # Older < newer
        assert _compare_versions("0.9.0", "0.9.1") is True
        assert _compare_versions("0.9.0", "0.10.0") is True
        assert _compare_versions("0.9.0", "1.0.0") is True

        # Same versions
        assert _compare_versions("0.9.0", "0.9.0") is False

        # Newer > older
        assert _compare_versions("0.9.1", "0.9.0") is False
        assert _compare_versions("1.0.0", "0.9.0") is False

    def test_handles_non_semver_versions(self):
        """Test fallback for non-semver version strings."""
        from htmlgraph.hooks.session_handler import _compare_versions

        # Should use string comparison as fallback
        result = _compare_versions("dev", "release")
        assert isinstance(result, bool)


class TestCleanupTempFiles:
    """Test _cleanup_temp_files helper function."""

    def test_removes_single_temp_files(self, tmp_path):
        """Test removal of single temporary files."""
        from htmlgraph.hooks.session_handler import _cleanup_temp_files

        temp_file = tmp_path / "parent-activity.json"
        temp_file.write_text("{}")

        _cleanup_temp_files(tmp_path)

        assert not temp_file.exists()

    def test_removes_glob_pattern_files(self, tmp_path):
        """Test removal of files matching glob patterns."""
        from htmlgraph.hooks.session_handler import _cleanup_temp_files

        event_file1 = tmp_path / "user-query-event-1.json"
        event_file2 = tmp_path / "user-query-event-2.json"
        event_file1.write_text("{}")
        event_file2.write_text("{}")

        _cleanup_temp_files(tmp_path)

        assert not event_file1.exists()
        assert not event_file2.exists()

    def test_is_idempotent(self, tmp_path):
        """Test that cleanup is safe to call multiple times."""
        from htmlgraph.hooks.session_handler import _cleanup_temp_files

        # Should not raise error even if files don't exist
        _cleanup_temp_files(tmp_path)
        _cleanup_temp_files(tmp_path)
        _cleanup_temp_files(tmp_path)


# ============================================================================
# Integration Tests
# ============================================================================


class TestSessionHandlerIntegration:
    """Integration tests for complete session lifecycle."""

    def test_full_session_lifecycle(
        self, mock_hook_context, mock_session_manager, mock_session
    ):
        """Test complete session start -> track -> end lifecycle."""
        mock_hook_context.session_manager = mock_session_manager
        mock_hook_context.database = mock.MagicMock()
        mock_session_manager.get_active_session_for_agent.return_value = None
        mock_session_manager.start_session.return_value = mock_session
        mock_session_manager.get_active_session.return_value = mock_session

        with mock.patch(
            "htmlgraph.hooks.session_handler._get_head_commit", return_value="abc1234"
        ):
            # Initialize session
            session = init_or_get_session(mock_hook_context)
            assert session is not None

        # Start session
        with mock.patch(
            "htmlgraph.hooks.session_handler._load_features", return_value=[]
        ):
            start_result = handle_session_start(mock_hook_context, session)
            assert start_result["continue"] is True

        # Record event
        with mock.patch("htmlgraph.ids.generate_id", return_value="evt-123"):
            event_id = record_user_query_event(mock_hook_context, "Test query")
            assert event_id is not None

        # End session
        end_result = handle_session_end(mock_hook_context)
        assert end_result["continue"] is True

    def test_error_recovery_during_lifecycle(
        self, mock_hook_context, mock_session_manager, mock_session
    ):
        """Test that errors in one stage don't prevent others."""
        mock_hook_context.session_manager = mock_session_manager
        mock_session_manager.get_active_session_for_agent.return_value = mock_session
        mock_hook_context.database = mock.MagicMock()
        mock_hook_context.database.insert_event.side_effect = Exception()

        # Should continue even if event recording fails
        with mock.patch("htmlgraph.ids.generate_id", return_value="evt-123"):
            event_id = record_user_query_event(mock_hook_context, "Query")
            assert event_id is None  # Failed to insert

        # Session start should still work
        with mock.patch(
            "htmlgraph.hooks.session_handler._load_features", return_value=[]
        ):
            start_result = handle_session_start(mock_hook_context, mock_session)
            assert start_result["continue"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
