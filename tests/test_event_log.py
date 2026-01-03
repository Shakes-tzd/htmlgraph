"""
Tests for event logging and delegation tracking.

Tests EventRecord with both legacy and delegation fields,
ensuring backward compatibility and proper serialization.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from htmlgraph.event_log import EventRecord, JsonlEventLog


class TestEventRecord:
    """Test EventRecord creation and serialization."""

    def test_basic_event_creation(self) -> None:
        """Test creating a basic EventRecord without delegation fields."""
        now = datetime.now()
        event = EventRecord(
            event_id="evt-001",
            timestamp=now,
            session_id="sess-001",
            agent="claude",
            tool="Bash",
            summary="Run tests",
            success=True,
            feature_id="feat-001",
            drift_score=0.95,
            start_commit="abc123",
            continued_from=None,
        )

        assert event.event_id == "evt-001"
        assert event.agent == "claude"
        assert event.tool == "Bash"
        assert event.delegated_to_ai is None
        assert event.task_id is None

    def test_event_with_delegation_fields(self) -> None:
        """Test creating EventRecord with all delegation fields."""
        now = datetime.now()
        event = EventRecord(
            event_id="evt-002",
            timestamp=now,
            session_id="sess-001",
            agent="claude",
            tool="Task",
            summary="Delegate to Gemini",
            success=True,
            feature_id="feat-001",
            drift_score=0.85,
            start_commit="abc123",
            continued_from=None,
            delegated_to_ai="gemini",
            task_id="task-gemini-001",
            task_status="completed",
            model_selected="gemini-2.0-flash",
            complexity_level="high",
            budget_mode="balanced",
            execution_duration_seconds=45.5,
            tokens_estimated=5000,
            tokens_actual=4800,
            cost_usd=0.024,
            task_findings="Successfully analyzed the codebase",
        )

        assert event.delegated_to_ai == "gemini"
        assert event.task_id == "task-gemini-001"
        assert event.task_status == "completed"
        assert event.model_selected == "gemini-2.0-flash"
        assert event.complexity_level == "high"
        assert event.budget_mode == "balanced"
        assert event.execution_duration_seconds == 45.5
        assert event.tokens_estimated == 5000
        assert event.tokens_actual == 4800
        assert event.cost_usd == 0.024
        assert event.task_findings == "Successfully analyzed the codebase"

    def test_event_partial_delegation_fields(self) -> None:
        """Test EventRecord with only some delegation fields set."""
        now = datetime.now()
        event = EventRecord(
            event_id="evt-003",
            timestamp=now,
            session_id="sess-001",
            agent="claude",
            tool="Task",
            summary="Delegate to Codex",
            success=False,
            feature_id="feat-001",
            drift_score=0.70,
            start_commit="abc123",
            continued_from=None,
            delegated_to_ai="codex",
            task_status="failed",
            complexity_level="medium",
        )

        assert event.delegated_to_ai == "codex"
        assert event.task_id is None
        assert event.task_status == "failed"
        assert event.complexity_level == "medium"
        assert event.model_selected is None
        assert event.tokens_estimated is None

    def test_event_to_json_basic(self) -> None:
        """Test serialization of basic event to JSON."""
        now = datetime.now()
        event = EventRecord(
            event_id="evt-001",
            timestamp=now,
            session_id="sess-001",
            agent="claude",
            tool="Bash",
            summary="Run tests",
            success=True,
            feature_id="feat-001",
            drift_score=0.95,
            start_commit="abc123",
            continued_from=None,
        )

        json_data = event.to_json()

        assert json_data["event_id"] == "evt-001"
        assert json_data["agent"] == "claude"
        assert json_data["success"] is True
        assert json_data["delegated_to_ai"] is None
        assert json_data["task_id"] is None
        assert "cost_usd" in json_data

    def test_event_to_json_with_delegation(self) -> None:
        """Test serialization of event with delegation fields to JSON."""
        now = datetime.now()
        event = EventRecord(
            event_id="evt-002",
            timestamp=now,
            session_id="sess-001",
            agent="claude",
            tool="Task",
            summary="Delegate to Gemini",
            success=True,
            feature_id="feat-001",
            drift_score=0.85,
            start_commit="abc123",
            continued_from=None,
            delegated_to_ai="gemini",
            task_id="task-gemini-001",
            task_status="completed",
            model_selected="gemini-2.0-flash",
            complexity_level="high",
            budget_mode="balanced",
            execution_duration_seconds=45.5,
            tokens_estimated=5000,
            tokens_actual=4800,
            cost_usd=0.024,
            task_findings="Successfully analyzed the codebase",
        )

        json_data = event.to_json()

        assert json_data["delegated_to_ai"] == "gemini"
        assert json_data["task_id"] == "task-gemini-001"
        assert json_data["task_status"] == "completed"
        assert json_data["model_selected"] == "gemini-2.0-flash"
        assert json_data["complexity_level"] == "high"
        assert json_data["budget_mode"] == "balanced"
        assert json_data["execution_duration_seconds"] == 45.5
        assert json_data["tokens_estimated"] == 5000
        assert json_data["tokens_actual"] == 4800
        assert json_data["cost_usd"] == 0.024
        assert json_data["task_findings"] == "Successfully analyzed the codebase"


class TestJsonlEventLogBackwardCompatibility:
    """Test backward compatibility for events without delegation fields."""

    def test_load_legacy_event_without_delegation_fields(self) -> None:
        """Test loading old events that don't have delegation fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir)
            log = JsonlEventLog(events_dir)

            legacy_event_json = {
                "event_id": "evt-legacy-001",
                "timestamp": "2026-01-01T10:00:00",
                "session_id": "sess-001",
                "agent": "claude",
                "tool": "Bash",
                "summary": "Old event",
                "success": True,
                "feature_id": "feat-001",
                "work_type": None,
                "drift_score": 0.9,
                "start_commit": "abc123",
                "continued_from": None,
                "session_status": None,
                "file_paths": [],
                "payload": None,
            }

            session_file = events_dir / "sess-001.jsonl"
            with session_file.open("w") as f:
                f.write(json.dumps(legacy_event_json) + "\n")

            events = log.get_session_events("sess-001")
            assert len(events) == 1
            assert events[0]["event_id"] == "evt-legacy-001"
            assert "delegated_to_ai" not in events[0]

    def test_load_mixed_events_with_and_without_delegation(self) -> None:
        """Test loading JSONL with mix of old and new events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir)
            log = JsonlEventLog(events_dir)

            legacy_event = {
                "event_id": "evt-legacy-001",
                "timestamp": "2026-01-01T10:00:00",
                "session_id": "sess-001",
                "agent": "claude",
                "tool": "Bash",
                "summary": "Old event",
                "success": True,
                "feature_id": "feat-001",
                "work_type": None,
                "drift_score": 0.9,
                "start_commit": "abc123",
                "continued_from": None,
                "session_status": None,
                "file_paths": [],
                "payload": None,
            }

            new_event = {
                "event_id": "evt-new-001",
                "timestamp": "2026-01-01T11:00:00",
                "session_id": "sess-001",
                "agent": "claude",
                "tool": "Task",
                "summary": "Delegated task",
                "success": True,
                "feature_id": "feat-001",
                "work_type": None,
                "drift_score": 0.85,
                "start_commit": "abc123",
                "continued_from": None,
                "session_status": None,
                "file_paths": [],
                "payload": None,
                "delegated_to_ai": "gemini",
                "task_id": "task-001",
                "task_status": "completed",
                "model_selected": "gemini-2.0-flash",
                "complexity_level": "high",
                "budget_mode": "balanced",
                "execution_duration_seconds": 45.5,
                "tokens_estimated": 5000,
                "tokens_actual": 4800,
                "cost_usd": 0.024,
                "task_findings": "Success",
            }

            session_file = events_dir / "sess-001.jsonl"
            with session_file.open("w") as f:
                f.write(json.dumps(legacy_event) + "\n")
                f.write(json.dumps(new_event) + "\n")

            events = log.get_session_events("sess-001", limit=None)
            assert len(events) == 2

            assert events[0]["event_id"] == "evt-legacy-001"
            assert "delegated_to_ai" not in events[0]

            assert events[1]["event_id"] == "evt-new-001"
            assert events[1]["delegated_to_ai"] == "gemini"
            assert events[1]["task_status"] == "completed"

    def test_append_new_event_after_legacy_events(self) -> None:
        """Test appending new events with delegation fields to log with legacy events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir)
            log = JsonlEventLog(events_dir)

            legacy_event = {
                "event_id": "evt-legacy-001",
                "timestamp": "2026-01-01T10:00:00",
                "session_id": "sess-001",
                "agent": "claude",
                "tool": "Bash",
                "summary": "Old event",
                "success": True,
                "feature_id": "feat-001",
                "work_type": None,
                "drift_score": 0.9,
                "start_commit": "abc123",
                "continued_from": None,
                "session_status": None,
                "file_paths": [],
                "payload": None,
            }

            session_file = events_dir / "sess-001.jsonl"
            with session_file.open("w") as f:
                f.write(json.dumps(legacy_event) + "\n")

            now = datetime.now()
            new_event = EventRecord(
                event_id="evt-new-001",
                timestamp=now,
                session_id="sess-001",
                agent="claude",
                tool="Task",
                summary="Delegated task",
                success=True,
                feature_id="feat-001",
                drift_score=0.85,
                start_commit="abc123",
                continued_from=None,
                delegated_to_ai="gemini",
                task_id="task-001",
                task_status="completed",
            )

            log.append(new_event)

            events = log.get_session_events("sess-001", limit=None)
            assert len(events) == 2
            assert events[0]["event_id"] == "evt-legacy-001"
            assert events[1]["event_id"] == "evt-new-001"
            assert events[1]["delegated_to_ai"] == "gemini"


class TestSerializationRoundTrip:
    """Test that events can be serialized and deserialized correctly."""

    def test_event_json_roundtrip_with_delegation(self) -> None:
        """Test serialize -> JSON -> deserialize with delegation fields."""
        now = datetime.now()
        original = EventRecord(
            event_id="evt-001",
            timestamp=now,
            session_id="sess-001",
            agent="claude",
            tool="Task",
            summary="Delegated work",
            success=True,
            feature_id="feat-001",
            drift_score=0.85,
            start_commit="abc123",
            continued_from=None,
            delegated_to_ai="gemini",
            task_id="task-001",
            task_status="completed",
            model_selected="gemini-2.0-flash",
            complexity_level="high",
            budget_mode="balanced",
            execution_duration_seconds=45.5,
            tokens_estimated=5000,
            tokens_actual=4800,
            cost_usd=0.024,
            task_findings="Results here",
        )

        json_data = original.to_json()

        json_str = json.dumps(json_data)
        loaded_data = json.loads(json_str)

        assert loaded_data["event_id"] == original.event_id
        assert loaded_data["delegated_to_ai"] == original.delegated_to_ai
        assert loaded_data["task_id"] == original.task_id
        assert loaded_data["task_status"] == original.task_status
        assert loaded_data["model_selected"] == original.model_selected
        assert loaded_data["complexity_level"] == original.complexity_level
        assert loaded_data["budget_mode"] == original.budget_mode
        assert (
            loaded_data["execution_duration_seconds"]
            == original.execution_duration_seconds
        )
        assert loaded_data["tokens_estimated"] == original.tokens_estimated
        assert loaded_data["tokens_actual"] == original.tokens_actual
        assert loaded_data["cost_usd"] == original.cost_usd
        assert loaded_data["task_findings"] == original.task_findings

    def test_jsonl_storage_and_retrieval(self) -> None:
        """Test storing and retrieving events from JSONL with delegation fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            events_dir = Path(tmpdir)
            log = JsonlEventLog(events_dir)

            now = datetime.now()
            event = EventRecord(
                event_id="evt-001",
                timestamp=now,
                session_id="sess-001",
                agent="claude",
                tool="Task",
                summary="Delegated work",
                success=True,
                feature_id="feat-001",
                drift_score=0.85,
                start_commit="abc123",
                continued_from=None,
                delegated_to_ai="codex",
                task_id="task-codex-001",
                task_status="completed",
                tokens_estimated=3000,
                tokens_actual=2900,
                cost_usd=0.015,
            )

            log.append(event)

            events = log.get_session_events("sess-001")
            assert len(events) == 1

            retrieved = events[0]
            assert retrieved["event_id"] == "evt-001"
            assert retrieved["delegated_to_ai"] == "codex"
            assert retrieved["task_id"] == "task-codex-001"
            assert retrieved["task_status"] == "completed"
            assert retrieved["tokens_estimated"] == 3000
            assert retrieved["tokens_actual"] == 2900
            assert retrieved["cost_usd"] == 0.015


class TestMultipleDelegations:
    """Test tracking multiple parallel delegations."""

    def test_multiple_parallel_task_ids(self) -> None:
        """Test that multiple tasks can be tracked with unique IDs."""
        now = datetime.now()

        task_ids = ["task-gemini-001", "task-codex-001", "task-copilot-001"]
        events = []

        for i, task_id in enumerate(task_ids):
            event = EventRecord(
                event_id=f"evt-{i:03d}",
                timestamp=now,
                session_id="sess-001",
                agent="orchestrator",
                tool="Task",
                summary=f"Parallel delegation {i + 1}",
                success=True,
                feature_id="feat-001",
                drift_score=0.9,
                start_commit="abc123",
                continued_from=None,
                delegated_to_ai=["gemini", "codex", "copilot"][i],
                task_id=task_id,
                task_status="running",
            )
            events.append(event)

        event_ids = [e.task_id for e in events]
        assert len(set(event_ids)) == 3
        assert event_ids == task_ids

    def test_task_status_progression(self) -> None:
        """Test tracking status progression of a delegated task."""
        now = datetime.now()

        statuses = ["pending", "running", "completed"]
        events = []

        for i, status in enumerate(statuses):
            event = EventRecord(
                event_id=f"evt-{i:03d}",
                timestamp=now,
                session_id="sess-001",
                agent="orchestrator",
                tool="Task",
                summary=f"Task status: {status}",
                success=status == "completed",
                feature_id="feat-001",
                drift_score=0.9,
                start_commit="abc123",
                continued_from=None,
                delegated_to_ai="gemini",
                task_id="task-001",
                task_status=status,
            )
            events.append(event)

        assert events[0].task_status == "pending"
        assert events[1].task_status == "running"
        assert events[2].task_status == "completed"
        assert all(e.task_id == "task-001" for e in events)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
