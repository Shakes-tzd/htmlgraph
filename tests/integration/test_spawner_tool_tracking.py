"""
Tests for spawner internal event tracking and tool call recording.

This test suite validates that spawner agents properly capture and record
internal tool calls made during execution, linking them as child events
under the execution phase.

NOTE: Skipped - requires spawner_event_tracker module from plugin agents directory.
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Skip entire module - spawner_event_tracker not available in test environment
pytestmark = pytest.mark.skip(reason="spawner_event_tracker module not available")
from htmlgraph.db.schema import HtmlGraphDB

# Add plugin agents directory to path for importing spawner_event_tracker
PLUGIN_AGENTS_DIR = (
    Path(__file__).parent.parent.parent
    / "packages"
    / "claude-plugin"
    / ".claude-plugin"
    / "agents"
)
sys.path.insert(0, str(PLUGIN_AGENTS_DIR))


class TestSpawnerEventTrackerToolCalls:
    """Test recording and completing tool calls within spawner phases."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            yield db_path

    @pytest.fixture
    def db_instance(self, temp_db):
        """Create a HtmlGraphDB instance with temporary database."""
        db = HtmlGraphDB(str(temp_db))
        yield db
        db.disconnect()

    def test_record_tool_call_basic(self, db_instance):
        """Test basic tool call recording."""
        from spawner_event_tracker import SpawnerEventTracker

        tracker = SpawnerEventTracker(
            delegation_event_id="event-deleg123",
            parent_agent="orchestrator",
            spawner_type="gemini",
            session_id="session-test123",
        )
        tracker.db = db_instance

        # Record a phase
        phase_event = tracker.record_phase(
            "Executing Gemini",
            spawned_agent="gemini-2.0-flash",
            tool_name="gemini-cli",
            input_summary="Test prompt",
        )
        phase_event_id = phase_event["event_id"]

        # Record a tool call within the phase
        tool_event = tracker.record_tool_call(
            tool_name="bash",
            tool_input={"command": "ls -la /tmp"},
            phase_event_id=phase_event_id,
            spawned_agent="gemini-2.0-flash",
        )

        # Verify tool call was recorded
        assert tool_event is not None
        assert "event_id" in tool_event
        assert tool_event["tool_name"] == "bash"
        assert tool_event["status"] == "running"

        # Verify in database
        cursor = db_instance.connection.cursor()
        cursor.execute(
            "SELECT * FROM agent_events WHERE event_id = ?",
            (tool_event["event_id"],),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["tool_name"] == "bash"
        assert row["parent_event_id"] == phase_event_id

    def test_complete_tool_call(self, db_instance):
        """Test completing a tool call."""
        from spawner_event_tracker import SpawnerEventTracker

        tracker = SpawnerEventTracker(
            delegation_event_id="event-deleg123",
            parent_agent="orchestrator",
            spawner_type="gemini",
            session_id="session-test123",
        )
        tracker.db = db_instance

        # Record a phase
        phase_event = tracker.record_phase(
            "Executing Gemini",
            spawned_agent="gemini-2.0-flash",
        )
        phase_event_id = phase_event["event_id"]

        # Record and complete a tool call
        tool_event = tracker.record_tool_call(
            tool_name="read_file",
            tool_input={"path": "/tmp/test.txt"},
            phase_event_id=phase_event_id,
            spawned_agent="gemini-2.0-flash",
        )

        success = tracker.complete_tool_call(
            event_id=tool_event["event_id"],
            output_summary="File contents: Hello World",
            success=True,
        )

        assert success is True

        # Verify completion in database
        cursor = db_instance.connection.cursor()
        cursor.execute(
            "SELECT * FROM agent_events WHERE event_id = ?",
            (tool_event["event_id"],),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["output_summary"] == "File contents: Hello World"
        assert row["status"] == "completed"

    def test_tool_calls_link_to_phase_event(self, db_instance):
        """Test that tool calls are properly linked to parent phase events."""
        from spawner_event_tracker import SpawnerEventTracker

        tracker = SpawnerEventTracker(
            delegation_event_id="event-deleg456",
            parent_agent="orchestrator",
            spawner_type="codex",
            session_id="session-test456",
        )
        tracker.db = db_instance

        # Record a phase
        phase_event = tracker.record_phase(
            "Executing Codex",
            spawned_agent="gpt-4",
        )
        phase_event_id = phase_event["event_id"]

        # Record multiple tool calls
        for i in range(3):
            tracker.record_tool_call(
                tool_name="bash",
                tool_input={"command": f"echo test{i}"},
                phase_event_id=phase_event_id,
                spawned_agent="gpt-4",
            )

        # Verify all tool calls link to the phase
        cursor = db_instance.connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM agent_events WHERE parent_event_id = ?",
            (phase_event_id,),
        )
        row = cursor.fetchone()
        assert row["count"] == 3

    def test_tool_call_without_database(self):
        """Test that tool call recording gracefully handles missing database."""
        from spawner_event_tracker import SpawnerEventTracker

        tracker = SpawnerEventTracker(
            delegation_event_id="event-deleg789",
            parent_agent="orchestrator",
            spawner_type="gemini",
        )
        # Explicitly set db to None to simulate database unavailable
        tracker.db = None

        # This should return empty dict, not crash
        result = tracker.record_tool_call(
            tool_name="bash",
            tool_input={"command": "ls"},
            phase_event_id="event-phase123",
        )

        assert result == {}

    def test_complete_tool_call_without_database(self):
        """Test that complete_tool_call gracefully handles missing database."""
        from spawner_event_tracker import SpawnerEventTracker

        tracker = SpawnerEventTracker(
            delegation_event_id="event-deleg789",
            parent_agent="orchestrator",
            spawner_type="gemini",
        )
        # Explicitly set db to None to simulate database unavailable
        tracker.db = None

        # This should return False, not crash
        result = tracker.complete_tool_call(
            event_id="event-tool123",
            output_summary="Test output",
            success=True,
        )

        assert result is False

    def test_tool_call_event_hierarchy(self, db_instance):
        """Test that tool calls are properly hierarchical under phases."""
        from spawner_event_tracker import SpawnerEventTracker

        tracker = SpawnerEventTracker(
            delegation_event_id="event-main",
            parent_agent="orchestrator",
            spawner_type="gemini",
            session_id="session-hierarchy",
        )
        tracker.db = db_instance

        # Record phases
        tracker.record_phase("Initialization")
        exec_event = tracker.record_phase("Execution")

        # Record tool calls under execution phase
        tracker.record_tool_call(
            tool_name="bash",
            tool_input={"command": "ls"},
            phase_event_id=exec_event["event_id"],
        )
        tracker.record_tool_call(
            tool_name="read_file",
            tool_input={"path": "test.txt"},
            phase_event_id=exec_event["event_id"],
        )

        # Verify hierarchy in database
        cursor = db_instance.connection.cursor()

        # Phases should link to delegation
        cursor.execute(
            "SELECT COUNT(*) as count FROM agent_events WHERE parent_event_id = ?",
            ("event-main",),
        )
        phase_count = cursor.fetchone()["count"]
        assert phase_count == 2  # init and exec phases

        # Tools should link to exec_event
        cursor.execute(
            "SELECT COUNT(*) as count FROM agent_events WHERE parent_event_id = ?",
            (exec_event["event_id"],),
        )
        tool_count = cursor.fetchone()["count"]
        assert tool_count == 2  # two tool calls


class TestGeminiEventParsing:
    """Test Gemini CLI JSONL event parsing."""

    def test_gemini_jsonl_format(self):
        """Test that Gemini JSONL format is as expected."""
        # Example Gemini output with tool events
        gemini_output = (
            '{"type": "tool_use", "tool": "bash", "parameters": {"command": "ls"}}\n'
            '{"type": "tool_result", "tool": "bash", "result": "file1\\nfile2", "success": true}\n'
        )

        # Verify format is valid JSON
        lines = gemini_output.strip().splitlines()
        assert len(lines) == 2

        for line in lines:
            event = json.loads(line)
            assert "type" in event


class TestCodexEventParsing:
    """Test Codex CLI JSON event parsing."""

    def test_codex_json_format(self):
        """Test that Codex JSON format is as expected."""
        # Example Codex output with tool events
        codex_output = (
            '{"type": "tool_use", "tool": "bash", "input": {"command": "ls"}}\n'
            '{"type": "tool_result", "tool": "bash", "output": "file1\\nfile2", "success": true}\n'
        )

        # Verify format is valid JSON
        lines = codex_output.strip().splitlines()
        assert len(lines) == 2

        for line in lines:
            event = json.loads(line)
            assert "type" in event


class TestCopilotToolTracking:
    """Test GitHub Copilot tool call recording."""

    def test_copilot_gh_tool_input_structure(self):
        """Test that Copilot gh tool input is properly structured."""
        tool_input = {
            "allow_tools": ["shell", "git"],
            "allow_all_tools": False,
            "deny_tools": ["dangerous"],
        }

        # Verify structure is valid
        assert "allow_tools" in tool_input
        assert "allow_all_tools" in tool_input
        assert isinstance(tool_input["allow_tools"], list)
        assert isinstance(tool_input["allow_all_tools"], bool)


class TestSpawnerEventHierarchy:
    """Test complete spawner event hierarchy."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            yield db_path

    def test_complete_spawner_event_tree(self, temp_db):
        """Test complete event hierarchy from delegation to tool calls."""
        db = HtmlGraphDB(str(temp_db))

        try:
            from spawner_event_tracker import SpawnerEventTracker

            # 1. Create session first (required for FK constraint)
            session_id = "session-test"
            db.insert_session(session_id, agent_assigned="orchestrator")

            # 2. Create a delegation event
            delegation_event_id = "event-delegation-123"

            # Record delegation
            db.insert_event(
                event_id=delegation_event_id,
                agent_id="orchestrator",
                event_type="delegation",
                session_id=session_id,
                tool_name="Task",
                input_summary="Test delegated task",
                context={"spawned_agent": "gemini-2.0-flash", "spawner_type": "gemini"},
                subagent_type="gemini",
            )

            # 3. Create tracker linked to delegation event and session
            tracker = SpawnerEventTracker(
                delegation_event_id=delegation_event_id,
                parent_agent="orchestrator",
                spawner_type="gemini",
                session_id=session_id,
            )
            tracker.db = db

            # 4. Record initialization phase (linked to delegation)
            init_event = tracker.record_phase("Initialization")
            tracker.complete_phase(init_event["event_id"], output_summary="Init done")

            # 5. Record execution phase (linked to delegation)
            exec_event = tracker.record_phase("Execution")

            # 6. Record tool calls during execution (linked to execution phase)
            tool1 = tracker.record_tool_call(
                tool_name="bash",
                tool_input={"command": "find . -name '*.py'"},
                phase_event_id=exec_event["event_id"],
                spawned_agent="gemini-2.0-flash",
            )
            tracker.complete_tool_call(
                tool1["event_id"], output_summary="Found 42 Python files", success=True
            )

            tool2 = tracker.record_tool_call(
                tool_name="read_file",
                tool_input={"path": "src/main.py"},
                phase_event_id=exec_event["event_id"],
                spawned_agent="gemini-2.0-flash",
            )
            tracker.complete_tool_call(
                tool2["event_id"], output_summary="File read successfully", success=True
            )

            # Complete execution phase
            tracker.complete_phase(exec_event["event_id"], output_summary="Exec done")

            # Verify event hierarchy in database
            cursor = db.connection.cursor()

            # Count events at each level
            cursor.execute(
                "SELECT COUNT(*) as count FROM agent_events WHERE parent_event_id = ?",
                (delegation_event_id,),
            )
            phase_count = cursor.fetchone()["count"]
            assert phase_count == 2  # init and exec phases

            cursor.execute(
                "SELECT COUNT(*) as count FROM agent_events WHERE parent_event_id = ?",
                (exec_event["event_id"],),
            )
            tool_count = cursor.fetchone()["count"]
            assert tool_count == 2  # two tool calls

            # Verify event types
            cursor.execute(
                "SELECT event_type FROM agent_events WHERE event_id = ?",
                (tool1["event_id"],),
            )
            assert cursor.fetchone()["event_type"] == "tool_call"

            cursor.execute(
                "SELECT event_type FROM agent_events WHERE event_id = ?",
                (init_event["event_id"],),
            )
            assert cursor.fetchone()["event_type"] == "tool_call"

        finally:
            db.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
