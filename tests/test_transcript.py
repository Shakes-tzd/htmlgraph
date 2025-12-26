"""
Tests for Claude Code transcript integration.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from htmlgraph.transcript import (
    TranscriptReader,
    TranscriptSession,
    TranscriptEntry,
    TranscriptWatcher,
)
from htmlgraph.session_manager import SessionManager


# Sample JSONL lines from a Claude Code transcript
SAMPLE_JSONL_LINES = [
    {
        "parentUuid": None,
        "isSidechain": False,
        "userType": "external",
        "cwd": "/home/user/projects/myapp",
        "sessionId": "abc-123-def-456",
        "version": "1.0.58",
        "gitBranch": "main",
        "type": "user",
        "message": {
            "role": "user",
            "content": "Add a login function"
        },
        "uuid": "msg-001",
        "timestamp": "2025-12-25T10:00:00.000Z"
    },
    {
        "parentUuid": "msg-001",
        "isSidechain": False,
        "cwd": "/home/user/projects/myapp",
        "sessionId": "abc-123-def-456",
        "version": "1.0.58",
        "gitBranch": "main",
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I'll add a login function."},
                {"type": "thinking", "thinking": "Need to create auth module first."}
            ]
        },
        "uuid": "msg-002",
        "timestamp": "2025-12-25T10:00:05.000Z"
    },
    {
        "parentUuid": "msg-002",
        "isSidechain": False,
        "cwd": "/home/user/projects/myapp",
        "sessionId": "abc-123-def-456",
        "version": "1.0.58",
        "gitBranch": "main",
        "type": "tool_use",
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "name": "Write",
                    "input": {"file_path": "/home/user/projects/myapp/auth.py", "content": "def login(): pass"}
                }
            ]
        },
        "uuid": "msg-003",
        "timestamp": "2025-12-25T10:00:10.000Z"
    },
    {
        "parentUuid": "msg-003",
        "isSidechain": False,
        "cwd": "/home/user/projects/myapp",
        "sessionId": "abc-123-def-456",
        "version": "1.0.58",
        "gitBranch": "main",
        "type": "tool_result",
        "message": {
            "role": "user",
            "content": "File written successfully"
        },
        "uuid": "msg-004",
        "timestamp": "2025-12-25T10:00:11.000Z"
    },
]


@pytest.fixture
def temp_claude_dir():
    """Create a temporary Claude Code projects directory."""
    with TemporaryDirectory() as tmpdir:
        claude_dir = Path(tmpdir) / ".claude" / "projects"
        claude_dir.mkdir(parents=True)
        yield claude_dir


@pytest.fixture
def sample_transcript_file(temp_claude_dir):
    """Create a sample transcript file."""
    # Encode project path: /home/user/projects/myapp -> -home-user-projects-myapp
    project_dir = temp_claude_dir / "-home-user-projects-myapp"
    project_dir.mkdir()

    transcript_path = project_dir / "abc-123-def-456.jsonl"
    with transcript_path.open("w") as f:
        for line in SAMPLE_JSONL_LINES:
            f.write(json.dumps(line) + "\n")

    return transcript_path


@pytest.fixture
def temp_htmlgraph_dir():
    """Create a temporary HtmlGraph directory."""
    with TemporaryDirectory() as tmpdir:
        graph_dir = Path(tmpdir) / ".htmlgraph"
        graph_dir.mkdir()
        (graph_dir / "sessions").mkdir()
        (graph_dir / "features").mkdir()
        (graph_dir / "events").mkdir()
        yield graph_dir


class TestTranscriptEntry:
    """Tests for TranscriptEntry parsing."""

    def test_parse_user_message(self):
        """Parse a user message entry."""
        entry = TranscriptEntry.from_jsonl_line(SAMPLE_JSONL_LINES[0])

        assert entry.entry_type == "user"
        assert entry.session_id == "abc-123-def-456"
        assert entry.uuid == "msg-001"
        assert entry.message_role == "user"
        assert entry.message_content == "Add a login function"
        assert entry.cwd == "/home/user/projects/myapp"
        assert entry.git_branch == "main"
        assert entry.version == "1.0.58"

    def test_parse_assistant_with_thinking(self):
        """Parse an assistant message with thinking trace."""
        entry = TranscriptEntry.from_jsonl_line(SAMPLE_JSONL_LINES[1])

        assert entry.entry_type == "assistant"
        assert entry.message_content == "I'll add a login function."
        assert entry.thinking == "Need to create auth module first."

    def test_parse_tool_use(self):
        """Parse a tool use entry."""
        entry = TranscriptEntry.from_jsonl_line(SAMPLE_JSONL_LINES[2])

        assert entry.entry_type == "tool_use"
        assert entry.tool_name == "Write"
        assert entry.tool_input is not None
        assert "file_path" in entry.tool_input

    def test_parse_tool_result(self):
        """Parse a tool result entry."""
        entry = TranscriptEntry.from_jsonl_line(SAMPLE_JSONL_LINES[3])

        assert entry.entry_type == "tool_result"
        assert entry.message_content == "File written successfully"

    def test_to_summary(self):
        """Test human-readable summary generation."""
        user_entry = TranscriptEntry.from_jsonl_line(SAMPLE_JSONL_LINES[0])
        tool_entry = TranscriptEntry.from_jsonl_line(SAMPLE_JSONL_LINES[2])

        assert "Add a login function" in user_entry.to_summary()
        assert "Write" in tool_entry.to_summary()


class TestTranscriptReader:
    """Tests for TranscriptReader."""

    def test_read_transcript_file(self, temp_claude_dir, sample_transcript_file):
        """Read and parse a transcript file."""
        reader = TranscriptReader(temp_claude_dir)
        session = reader.read_transcript(sample_transcript_file)

        assert session.session_id == "abc-123-def-456"
        assert len(session.entries) == 4
        assert session.cwd == "/home/user/projects/myapp"
        assert session.git_branch == "main"

    def test_list_transcript_files(self, temp_claude_dir, sample_transcript_file):
        """List available transcript files."""
        reader = TranscriptReader(temp_claude_dir)
        files = list(reader.list_transcript_files())

        assert len(files) == 1
        assert files[0].name == "abc-123-def-456.jsonl"

    def test_read_session_by_id(self, temp_claude_dir, sample_transcript_file):
        """Read a session by its ID."""
        reader = TranscriptReader(temp_claude_dir)
        session = reader.read_session("abc-123-def-456")

        assert session is not None
        assert session.session_id == "abc-123-def-456"

    def test_read_nonexistent_session(self, temp_claude_dir):
        """Return None for nonexistent session."""
        reader = TranscriptReader(temp_claude_dir)
        session = reader.read_session("nonexistent-id")

        assert session is None

    def test_list_sessions(self, temp_claude_dir, sample_transcript_file):
        """List sessions with metadata."""
        reader = TranscriptReader(temp_claude_dir)
        sessions = reader.list_sessions()

        assert len(sessions) == 1
        session = sessions[0]
        assert session.session_id == "abc-123-def-456"
        assert session.user_message_count == 1  # One "user" type entry
        assert session.tool_call_count == 1  # One "tool_use" type entry

    def test_find_sessions_for_branch(self, temp_claude_dir, sample_transcript_file):
        """Find sessions that worked on a specific branch."""
        reader = TranscriptReader(temp_claude_dir)

        main_sessions = reader.find_sessions_for_branch("main")
        other_sessions = reader.find_sessions_for_branch("feature-x")

        assert len(main_sessions) == 1
        assert len(other_sessions) == 0

    def test_encode_decode_project_path(self, temp_claude_dir):
        """Test path encoding/decoding."""
        reader = TranscriptReader(temp_claude_dir)

        encoded = reader.encode_project_path("/home/user/projects/myapp")
        assert encoded == "-home-user-projects-myapp"

        decoded = reader.decode_project_path(encoded)
        assert decoded == "/home/user/projects/myapp"


class TestTranscriptSession:
    """Tests for TranscriptSession properties."""

    def test_tool_breakdown(self, temp_claude_dir, sample_transcript_file):
        """Test tool call breakdown."""
        reader = TranscriptReader(temp_claude_dir)
        session = reader.read_transcript(sample_transcript_file)

        breakdown = session.tool_breakdown
        assert "Write" in breakdown
        assert breakdown["Write"] == 1

    def test_has_thinking_traces(self, temp_claude_dir, sample_transcript_file):
        """Test thinking trace detection."""
        reader = TranscriptReader(temp_claude_dir)
        session = reader.read_transcript(sample_transcript_file)

        assert session.has_thinking_traces() is True

    def test_duration(self, temp_claude_dir, sample_transcript_file):
        """Test session duration calculation."""
        reader = TranscriptReader(temp_claude_dir)
        session = reader.read_transcript(sample_transcript_file)

        # Duration from 10:00:00 to 10:00:11 = 11 seconds
        assert session.duration_seconds == 11.0


class TestTranscriptWatcher:
    """Tests for TranscriptWatcher."""

    def test_scan_finds_new_sessions(self, temp_claude_dir, sample_transcript_file):
        """Watcher finds new transcript files."""
        reader = TranscriptReader(temp_claude_dir)
        watcher = TranscriptWatcher(reader)

        # First scan should find the session
        changed = watcher.scan()
        assert len(changed) == 1
        assert changed[0].session_id == "abc-123-def-456"

        # Second scan should find nothing new
        changed = watcher.scan()
        assert len(changed) == 0

    def test_get_latest(self, temp_claude_dir, sample_transcript_file):
        """Get the most recently modified transcript."""
        reader = TranscriptReader(temp_claude_dir)
        watcher = TranscriptWatcher(reader)

        latest = watcher.get_latest()
        assert latest is not None
        assert latest.session_id == "abc-123-def-456"


class TestSessionManagerTranscriptIntegration:
    """Tests for SessionManager transcript integration."""

    def test_link_transcript(self, temp_htmlgraph_dir):
        """Link a transcript to a session."""
        manager = SessionManager(temp_htmlgraph_dir)

        # Create a session
        session = manager.start_session(agent="claude-code")

        # Link transcript
        result = manager.link_transcript(
            session_id=session.id,
            transcript_id="abc-123-def-456",
            transcript_path="/path/to/transcript.jsonl",
            git_branch="main",
        )

        assert result is not None
        assert result.transcript_id == "abc-123-def-456"
        assert result.transcript_path == "/path/to/transcript.jsonl"
        assert result.transcript_git_branch == "main"
        assert result.transcript_synced_at is not None

    def test_find_session_by_transcript(self, temp_htmlgraph_dir):
        """Find a session by its linked transcript ID."""
        manager = SessionManager(temp_htmlgraph_dir)

        # Create and link session
        session = manager.start_session(agent="claude-code")
        linked = manager.link_transcript(
            session_id=session.id,
            transcript_id="abc-123-def-456",
        )

        # Verify link succeeded
        assert linked is not None
        assert linked.transcript_id == "abc-123-def-456"

        # Find by transcript ID (reload from disk)
        found = manager.find_session_by_transcript("abc-123-def-456")
        assert found is not None, f"Session {session.id} with transcript abc-123-def-456 not found"
        assert found.id == session.id

        # Not found for different transcript
        not_found = manager.find_session_by_transcript("different-id")
        assert not_found is None

    def test_import_transcript_events(self, temp_claude_dir, sample_transcript_file, temp_htmlgraph_dir):
        """Import events from a transcript."""
        reader = TranscriptReader(temp_claude_dir)
        manager = SessionManager(temp_htmlgraph_dir)

        # Read transcript
        transcript = reader.read_transcript(sample_transcript_file)

        # Create session and import
        session = manager.start_session(agent="claude-code")
        result = manager.import_transcript_events(
            session_id=session.id,
            transcript_session=transcript,
        )

        assert result["imported"] == 2  # user message + tool_use
        assert result["skipped"] == 2  # assistant + tool_result

        # Verify session was updated
        updated_session = manager.get_session(session.id)
        assert updated_session.transcript_id == "abc-123-def-456"
        assert updated_session.transcript_git_branch == "main"
        # Initial SessionStart + 2 imported
        assert len(updated_session.activity_log) >= 2
