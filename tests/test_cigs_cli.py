"""
Tests for CIGS CLI commands.

Tests all CIGS-related CLI commands:
- htmlgraph cigs status
- htmlgraph cigs summary [session-id]
- htmlgraph cigs patterns
- htmlgraph cigs reset-violations
- htmlgraph orchestrator acknowledge-violation

NOTE: These tests are skipped because the CIGS CLI commands are not yet implemented.
The CLI functions (cmd_cigs_status, cmd_cigs_summary, etc.) need to be added to
htmlgraph.cli before these tests can run.
"""

import tempfile
from pathlib import Path

import pytest

# Skip entire module - CIGS CLI commands not yet implemented
pytestmark = pytest.mark.skip(reason="CIGS CLI commands not yet implemented")
from htmlgraph.cigs.models import (
    PatternRecord,
)
from htmlgraph.cigs.pattern_storage import PatternStorage
from htmlgraph.cigs.tracker import ViolationTracker
from htmlgraph.orchestrator_mode import OrchestratorModeManager


@pytest.fixture
def temp_graph_dir():
    """Create temporary graph directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = Path(tmpdir) / ".htmlgraph"
        graph_dir.mkdir(parents=True)
        yield graph_dir


@pytest.fixture
def tracker_with_violations(temp_graph_dir, monkeypatch):
    """Create ViolationTracker with sample violations."""
    # Set environment variable for session ID
    monkeypatch.setenv("HTMLGRAPH_SESSION_ID", "test-session-123")

    tracker = ViolationTracker(temp_graph_dir)

    # Add some violations
    for i in range(3):
        tracker.record_violation(
            tool="Read",
            params={"file_path": f"/path/to/file{i}.py"},
            classification=type(
                "obj",
                (object,),
                {
                    "is_exploration_sequence": i == 2,
                    "reason": f"Test violation {i}",
                    "suggested_delegation": "spawn_gemini()",
                    "predicted_cost": 5000,
                    "optimal_cost": 500,
                },
            )(),
            predicted_waste=4500,
        )

    return tracker


@pytest.fixture
def pattern_storage_with_patterns(temp_graph_dir):
    """Create PatternStorage with sample patterns."""
    storage = PatternStorage(temp_graph_dir)

    # Add anti-patterns
    anti_pattern1 = PatternRecord(
        id="pattern-001",
        pattern_type="anti-pattern",
        name="exploration_sequence",
        description="Multiple exploration tools in sequence",
        trigger_conditions=["3+ exploration tools"],
        example_sequence=["Read", "Grep", "Read"],
        occurrence_count=5,
        sessions_affected=["sess-1", "sess-2"],
        correct_approach="Use spawn_gemini() for exploration",
        delegation_suggestion="spawn_gemini(prompt='...')",
    )

    anti_pattern2 = PatternRecord(
        id="pattern-002",
        pattern_type="anti-pattern",
        name="edit_without_test",
        description="Edit operations without test delegation",
        trigger_conditions=["Edit without test"],
        example_sequence=["Edit", "Write"],
        occurrence_count=3,
        sessions_affected=["sess-1"],
        correct_approach="Include testing in Task() prompt",
        delegation_suggestion="Task(prompt='Make changes AND run tests')",
    )

    # Add good pattern
    good_pattern = PatternRecord(
        id="pattern-003",
        pattern_type="good-pattern",
        name="proper_delegation",
        description="Proper use of spawn_gemini() for exploration",
        trigger_conditions=["spawn_gemini called"],
        example_sequence=["Task"],
        occurrence_count=10,
        sessions_affected=["sess-2", "sess-3"],
    )

    storage.add_pattern(anti_pattern1)
    storage.add_pattern(anti_pattern2)
    storage.add_pattern(good_pattern)

    return storage


class TestCIGSStatus:
    """Tests for 'htmlgraph cigs status' command."""

    def test_cigs_status_shows_violations(
        self, temp_graph_dir, tracker_with_violations, capsys
    ):
        """Test that cigs status shows violation summary."""
        # Import here to get the command function
        from htmlgraph.cli import cmd_cigs_status

        # Create args
        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()

        # Run command
        cmd_cigs_status(args)

        # Check output
        captured = capsys.readouterr()
        assert "CIGS Status" in captured.out
        assert "test-session-123" in captured.out
        assert "Violations: 3/3" in captured.out
        assert "Circuit Breaker: 🚨 TRIGGERED" in captured.out

    def test_cigs_status_shows_autonomy_level(
        self, temp_graph_dir, tracker_with_violations, capsys
    ):
        """Test that cigs status shows autonomy recommendation."""
        from htmlgraph.cli import cmd_cigs_status

        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_cigs_status(args)

        captured = capsys.readouterr()
        assert "Autonomy Level:" in captured.out
        assert "Messaging Intensity:" in captured.out
        assert "Enforcement Mode:" in captured.out

    def test_cigs_status_shows_patterns(
        self,
        temp_graph_dir,
        tracker_with_violations,
        pattern_storage_with_patterns,
        capsys,
    ):
        """Test that cigs status shows detected patterns."""
        from htmlgraph.cli import cmd_cigs_status

        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_cigs_status(args)

        captured = capsys.readouterr()
        assert "Anti-Patterns Detected:" in captured.out


class TestCIGSSummary:
    """Tests for 'htmlgraph cigs summary' command."""

    def test_cigs_summary_current_session(
        self, temp_graph_dir, tracker_with_violations, capsys
    ):
        """Test cigs summary for current session."""
        from htmlgraph.cli import cmd_cigs_summary

        args = type(
            "obj", (object,), {"graph_dir": str(temp_graph_dir), "session_id": None}
        )()
        cmd_cigs_summary(args)

        captured = capsys.readouterr()
        assert "CIGS Session Summary" in captured.out
        assert "test-session-123" in captured.out
        assert "Total Violations: 3" in captured.out

    def test_cigs_summary_specific_session(
        self, temp_graph_dir, tracker_with_violations, capsys
    ):
        """Test cigs summary for specific session."""
        from htmlgraph.cli import cmd_cigs_summary

        args = type(
            "obj",
            (object,),
            {"graph_dir": str(temp_graph_dir), "session_id": "test-session-123"},
        )()
        cmd_cigs_summary(args)

        captured = capsys.readouterr()
        assert "test-session-123" in captured.out

    def test_cigs_summary_shows_violation_details(
        self, temp_graph_dir, tracker_with_violations, capsys
    ):
        """Test that summary shows detailed violation information."""
        from htmlgraph.cli import cmd_cigs_summary

        args = type(
            "obj", (object,), {"graph_dir": str(temp_graph_dir), "session_id": None}
        )()
        cmd_cigs_summary(args)

        captured = capsys.readouterr()
        assert "Recent Violations" in captured.out
        assert "Read" in captured.out
        assert "Should have:" in captured.out

    def test_cigs_summary_no_active_session(self, temp_graph_dir, capsys):
        """Test cigs summary with no active session."""
        from htmlgraph.cli import cmd_cigs_summary

        tracker = ViolationTracker(temp_graph_dir)
        tracker._session_id = None

        args = type(
            "obj", (object,), {"graph_dir": str(temp_graph_dir), "session_id": None}
        )()
        cmd_cigs_summary(args)

        captured = capsys.readouterr()
        assert "No active session" in captured.out


class TestCIGSPatterns:
    """Tests for 'htmlgraph cigs patterns' command."""

    def test_cigs_patterns_shows_anti_patterns(
        self, temp_graph_dir, pattern_storage_with_patterns, capsys
    ):
        """Test that patterns command shows anti-patterns."""
        from htmlgraph.cli import cmd_cigs_patterns

        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_cigs_patterns(args)

        captured = capsys.readouterr()
        assert "CIGS Pattern Analysis" in captured.out
        assert "Anti-Patterns Detected:" in captured.out
        assert "exploration_sequence" in captured.out
        assert "edit_without_test" in captured.out

    def test_cigs_patterns_shows_good_patterns(
        self, temp_graph_dir, pattern_storage_with_patterns, capsys
    ):
        """Test that patterns command shows good patterns."""
        from htmlgraph.cli import cmd_cigs_patterns

        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_cigs_patterns(args)

        captured = capsys.readouterr()
        assert "Good Patterns Observed:" in captured.out
        assert "proper_delegation" in captured.out

    def test_cigs_patterns_shows_occurrence_counts(
        self, temp_graph_dir, pattern_storage_with_patterns, capsys
    ):
        """Test that patterns command shows occurrence counts."""
        from htmlgraph.cli import cmd_cigs_patterns

        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_cigs_patterns(args)

        captured = capsys.readouterr()
        assert "Occurrences: 5" in captured.out
        assert "Occurrences: 3" in captured.out

    def test_cigs_patterns_shows_remediation(
        self, temp_graph_dir, pattern_storage_with_patterns, capsys
    ):
        """Test that patterns command shows remediation suggestions."""
        from htmlgraph.cli import cmd_cigs_patterns

        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_cigs_patterns(args)

        captured = capsys.readouterr()
        assert "Fix:" in captured.out
        assert "Instead:" in captured.out
        assert "spawn_gemini()" in captured.out

    def test_cigs_patterns_no_patterns(self, temp_graph_dir, capsys):
        """Test patterns command when no patterns detected."""
        from htmlgraph.cli import cmd_cigs_patterns

        # Create empty storage
        PatternStorage(temp_graph_dir)

        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_cigs_patterns(args)

        captured = capsys.readouterr()
        assert "No anti-patterns detected yet" in captured.out


class TestCIGSResetViolations:
    """Tests for 'htmlgraph cigs reset-violations' command."""

    def test_cigs_reset_violations_with_confirmation(
        self, temp_graph_dir, tracker_with_violations, capsys, monkeypatch
    ):
        """Test reset-violations with user confirmation."""
        from htmlgraph.cli import cmd_cigs_reset_violations

        # Mock user input to confirm
        monkeypatch.setattr("builtins.input", lambda *_, **__: "y")

        args = type(
            "obj", (object,), {"graph_dir": str(temp_graph_dir), "yes": False}
        )()
        cmd_cigs_reset_violations(args)

        captured = capsys.readouterr()
        assert "Violations reset" in captured.out
        assert "Circuit breaker: cleared" in captured.out

    def test_cigs_reset_violations_skip_confirmation(
        self, temp_graph_dir, tracker_with_violations, capsys
    ):
        """Test reset-violations with --yes flag."""
        from htmlgraph.cli import cmd_cigs_reset_violations

        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir), "yes": True})()
        cmd_cigs_reset_violations(args)

        captured = capsys.readouterr()
        assert "Violations reset" in captured.out

    def test_cigs_reset_violations_cancelled(
        self, temp_graph_dir, tracker_with_violations, capsys, monkeypatch
    ):
        """Test reset-violations cancelled by user."""
        from htmlgraph.cli import cmd_cigs_reset_violations

        # Mock user input to cancel
        monkeypatch.setattr("builtins.input", lambda *_, **__: "n")

        args = type(
            "obj", (object,), {"graph_dir": str(temp_graph_dir), "yes": False}
        )()
        cmd_cigs_reset_violations(args)

        captured = capsys.readouterr()
        assert "Reset cancelled" in captured.out

    def test_cigs_reset_violations_no_violations(
        self, temp_graph_dir, capsys, monkeypatch
    ):
        """Test reset-violations when no violations exist."""
        from htmlgraph.cli import cmd_cigs_reset_violations

        # Set session ID via environment
        monkeypatch.setenv("HTMLGRAPH_SESSION_ID", "test-session")

        # Initialize tracker to ensure session ID is set
        _ = ViolationTracker(temp_graph_dir)

        args = type(
            "obj", (object,), {"graph_dir": str(temp_graph_dir), "yes": False}
        )()
        cmd_cigs_reset_violations(args)

        captured = capsys.readouterr()
        assert "No violations to reset" in captured.out


class TestOrchestratorAcknowledgeViolation:
    """Tests for 'htmlgraph orchestrator acknowledge-violation' command."""

    def test_acknowledge_violation_clears_circuit_breaker(self, temp_graph_dir, capsys):
        """Test acknowledge-violation resets circuit breaker."""
        from htmlgraph.cli import cmd_orchestrator_acknowledge_violation

        # Set up circuit breaker
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable()
        for _ in range(3):
            manager.increment_violation()

        assert manager.is_circuit_breaker_triggered()

        # Acknowledge violation
        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_orchestrator_acknowledge_violation(args)

        # Verify reset
        assert not manager.is_circuit_breaker_triggered()
        assert manager.get_violation_count() == 0

        captured = capsys.readouterr()
        assert "Circuit breaker acknowledged" in captured.out

    def test_acknowledge_violation_no_circuit_breaker(self, temp_graph_dir, capsys):
        """Test acknowledge-violation when no circuit breaker triggered."""
        from htmlgraph.cli import cmd_orchestrator_acknowledge_violation

        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable()

        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_orchestrator_acknowledge_violation(args)

        captured = capsys.readouterr()
        assert "No circuit breaker to acknowledge" in captured.out


class TestCIGSCLIIntegration:
    """Integration tests for CIGS CLI commands."""

    def test_full_workflow(self, temp_graph_dir, capsys, monkeypatch):
        """Test complete CIGS workflow: violations -> status -> patterns -> reset."""
        from htmlgraph.cli import (
            cmd_cigs_reset_violations,
            cmd_cigs_status,
            cmd_cigs_summary,
        )

        # Set session ID via environment
        monkeypatch.setenv("HTMLGRAPH_SESSION_ID", "workflow-session")

        # Create violations
        tracker = ViolationTracker(temp_graph_dir)

        for i in range(2):
            tracker.record_violation(
                tool="Read",
                params={"file_path": f"/path/to/file{i}.py"},
                classification=type(
                    "obj",
                    (object,),
                    {
                        "is_exploration_sequence": False,
                        "reason": f"Test {i}",
                        "suggested_delegation": "spawn_gemini()",
                        "predicted_cost": 5000,
                        "optimal_cost": 500,
                    },
                )(),
                predicted_waste=4500,
            )

        # Check status
        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_cigs_status(args)
        captured = capsys.readouterr()
        assert "Violations: 2/3" in captured.out

        # Check summary
        args = type(
            "obj", (object,), {"graph_dir": str(temp_graph_dir), "session_id": None}
        )()
        cmd_cigs_summary(args)
        captured = capsys.readouterr()
        assert "workflow-session" in captured.out

        # Reset violations
        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir), "yes": True})()
        cmd_cigs_reset_violations(args)
        captured = capsys.readouterr()
        assert "Violations reset" in captured.out

        # Verify reset
        summary = tracker.get_session_violations()
        assert summary.total_violations == 0

    def test_cli_output_formatting(
        self, temp_graph_dir, tracker_with_violations, capsys
    ):
        """Test that CLI output is well-formatted and user-friendly."""
        from htmlgraph.cli import cmd_cigs_status, cmd_cigs_summary

        # Test status formatting
        args = type("obj", (object,), {"graph_dir": str(temp_graph_dir)})()
        cmd_cigs_status(args)

        captured = capsys.readouterr()

        # Check for formatting elements
        assert "===" in captured.out
        assert "•" in captured.out  # Bullet points
        assert "🚨" in captured.out  # Emoji indicators

        # Test summary formatting (which uses separator lines)
        args = type(
            "obj", (object,), {"graph_dir": str(temp_graph_dir), "session_id": None}
        )()
        cmd_cigs_summary(args)

        captured = capsys.readouterr()
        assert "─" in captured.out  # Separator lines


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
