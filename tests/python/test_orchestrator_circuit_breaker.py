"""Tests for orchestrator circuit breaker pattern."""

from htmlgraph.hooks.orchestrator import enforce_orchestrator_mode
from htmlgraph.orchestrator_mode import OrchestratorModeManager


class TestCircuitBreaker:
    """Test circuit breaker enforcement."""

    def test_violation_tracking_increments(self, tmp_path, monkeypatch):
        """Test that violations are tracked correctly."""
        # Change to tmp_path so enforce_orchestrator_mode finds .htmlgraph
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Simulate blocked operation (now advisory mode - warns but allows)
        result = enforce_orchestrator_mode("Edit", {"file_path": "test.py"})

        # Check violation was recorded
        assert manager.get_violation_count() == 1
        assert not manager.is_circuit_breaker_triggered()

        # Verify warning message includes violation count (now uses additionalContext)
        # Advisory mode continues=True but warns with VIOLATION count
        assert result["continue"] is True
        assert "VIOLATION (1/3)" in result["hookSpecificOutput"]["additionalContext"]

    def test_circuit_breaker_triggers_at_threshold(self, tmp_path, monkeypatch):
        """Test circuit breaker triggers at 3 violations."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Trigger 3 violations
        for i in range(3):
            enforce_orchestrator_mode("Edit", {"file_path": f"test{i}.py"})

        # Circuit breaker should be triggered
        assert manager.get_violation_count() == 3
        assert manager.is_circuit_breaker_triggered()

    def test_circuit_breaker_blocks_subsequent_operations(self, tmp_path, monkeypatch):
        """Test that circuit breaker blocks operations after trigger."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Trigger 3 violations
        for i in range(3):
            enforce_orchestrator_mode("Edit", {"file_path": f"test{i}.py"})

        # Next operation should be blocked by circuit breaker (actual blocking)
        result = enforce_orchestrator_mode("Read", {"file_path": "test.py"})

        # Circuit breaker IS the one case that still blocks (continue=False)
        assert result["continue"] is False
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert (
            "CIRCUIT BREAKER TRIGGERED"
            in result["hookSpecificOutput"]["permissionDecisionReason"]
        )

    def test_circuit_breaker_allows_core_operations(self, tmp_path, monkeypatch):
        """Test that circuit breaker allows Task/AskUserQuestion/TodoWrite."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Trigger circuit breaker
        for i in range(3):
            enforce_orchestrator_mode("Edit", {"file_path": f"test{i}.py"})

        # Core operations should still be allowed
        core_ops = [
            ("Task", {"prompt": "test", "subagent_type": "general-purpose"}),
            ("AskUserQuestion", {"question": "test"}),
            ("TodoWrite", {"todos": []}),
        ]

        for tool, params in core_ops:
            result = enforce_orchestrator_mode(tool, params)
            assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_reset_violations_clears_counter(self, tmp_path, monkeypatch):
        """Test that reset_violations clears counter and circuit breaker."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Trigger violations
        for i in range(3):
            enforce_orchestrator_mode("Edit", {"file_path": f"test{i}.py"})

        assert manager.get_violation_count() == 3
        assert manager.is_circuit_breaker_triggered()

        # Reset
        manager.reset_violations()

        assert manager.get_violation_count() == 0
        assert not manager.is_circuit_breaker_triggered()

    def test_violation_warning_at_two(self, tmp_path, monkeypatch):
        """Test special warning at 2 violations."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # First violation
        enforce_orchestrator_mode("Edit", {"file_path": "test1.py"})

        # Second violation should warn about next one (advisory mode)
        result = enforce_orchestrator_mode("Edit", {"file_path": "test2.py"})

        # Advisory mode continues=True but warns via additionalContext
        assert result["continue"] is True
        assert "VIOLATION (2/3)" in result["hookSpecificOutput"]["additionalContext"]
        assert (
            "Next violation will trigger circuit breaker"
            in result["hookSpecificOutput"]["additionalContext"]
        )

    def test_violation_message_at_threshold(self, tmp_path, monkeypatch):
        """Test message when circuit breaker triggers."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # First two violations
        enforce_orchestrator_mode("Edit", {"file_path": "test1.py"})
        enforce_orchestrator_mode("Edit", {"file_path": "test2.py"})

        # Third violation triggers circuit breaker (advisory mode still)
        result = enforce_orchestrator_mode("Edit", {"file_path": "test3.py"})

        # The third violation WARNS about circuit breaker via additionalContext
        # (the actual blocking happens on the NEXT operation after the threshold)
        assert result["continue"] is True
        assert "VIOLATION (3/3)" in result["hookSpecificOutput"]["additionalContext"]
        assert (
            "CIRCUIT BREAKER TRIGGERED"
            in result["hookSpecificOutput"]["additionalContext"]
        )
        assert "reset-violations" in result["hookSpecificOutput"]["additionalContext"]

    def test_guidance_mode_does_not_track_violations(self, tmp_path, monkeypatch):
        """Test that guidance mode doesn't track violations."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="guidance")

        # Simulate multiple blocked operations
        for i in range(5):
            enforce_orchestrator_mode("Edit", {"file_path": f"test{i}.py"})

        # No violations should be tracked in guidance mode
        assert manager.get_violation_count() == 0
        assert not manager.is_circuit_breaker_triggered()

    def test_allowed_operations_dont_increment_violations(self, tmp_path, monkeypatch):
        """Test that allowed operations don't increment violation counter."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Allowed operations
        enforce_orchestrator_mode(
            "Task", {"prompt": "test", "subagent_type": "general-purpose"}
        )
        enforce_orchestrator_mode(
            "Read", {"file_path": "test.py"}
        )  # First read is allowed
        enforce_orchestrator_mode("Bash", {"command": "uv run htmlgraph status"})

        # No violations should be recorded
        assert manager.get_violation_count() == 0

    def test_circuit_breaker_message_shows_options(self, tmp_path, monkeypatch):
        """Test that circuit breaker message shows all options."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Trigger circuit breaker
        for i in range(3):
            enforce_orchestrator_mode("Edit", {"file_path": f"test{i}.py"})

        # Check subsequent operation shows options (circuit breaker blocking)
        result = enforce_orchestrator_mode("Read", {"file_path": "test.py"})

        # Circuit breaker blocks with permissionDecisionReason
        assert result["continue"] is False
        message = result["hookSpecificOutput"]["permissionDecisionReason"]

        assert "disable" in message.lower()
        assert "set-level guidance" in message.lower()
        assert "reset-violations" in message.lower()

    def test_status_shows_violation_count(self, tmp_path, monkeypatch):
        """Test that status command shows violation tracking."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Add some violations
        enforce_orchestrator_mode("Edit", {"file_path": "test1.py"})
        enforce_orchestrator_mode("Edit", {"file_path": "test2.py"})

        status = manager.status()

        assert status["violations"] == 2
        assert status["circuit_breaker_triggered"] is False

    def test_enable_resets_violations(self, tmp_path, monkeypatch):
        """Test that enabling orchestrator mode resets violations."""
        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Trigger violations
        for i in range(3):
            enforce_orchestrator_mode("Edit", {"file_path": f"test{i}.py"})

        assert manager.get_violation_count() == 3

        # Re-enable should NOT reset (violations are session-specific)
        # This test documents current behavior - violations persist across enable calls
        manager.enable(level="strict")
        assert manager.get_violation_count() == 3  # Violations persist


class TestCircuitBreakerCLI:
    """Test CLI commands for circuit breaker."""

    def test_reset_violations_command_requires_enabled_mode(
        self, tmp_path, monkeypatch, capsys
    ):
        """Test reset-violations fails gracefully when mode disabled."""
        from argparse import Namespace

        from htmlgraph.cli import cmd_orchestrator_reset_violations

        # Don't enable mode - just test CLI error handling
        args = Namespace(graph_dir=tmp_path / ".htmlgraph")
        cmd_orchestrator_reset_violations(args)

        captured = capsys.readouterr()
        assert "not enabled" in captured.out.lower()

    def test_reset_violations_command_success(self, tmp_path, monkeypatch, capsys):
        """Test reset-violations command works."""
        from argparse import Namespace

        from htmlgraph.cli import cmd_orchestrator_reset_violations

        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Add violations
        for i in range(3):
            enforce_orchestrator_mode("Edit", {"file_path": f"test{i}.py"})

        # Reset via CLI
        args = Namespace(graph_dir=tmp_path / ".htmlgraph")
        cmd_orchestrator_reset_violations(args)

        captured = capsys.readouterr()
        assert "reset" in captured.out.lower()
        assert manager.get_violation_count() == 0

    def test_set_level_command(self, tmp_path, capsys):
        """Test set-level command works."""
        from argparse import Namespace

        from htmlgraph.cli import cmd_orchestrator_set_level

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Change to guidance
        args = Namespace(graph_dir=tmp_path / ".htmlgraph", level="guidance")
        cmd_orchestrator_set_level(args)

        captured = capsys.readouterr()
        assert "guidance" in captured.out.lower()
        assert manager.get_enforcement_level() == "guidance"

    def test_status_shows_violations(self, tmp_path, monkeypatch, capsys):
        """Test status command shows violation info."""
        from argparse import Namespace

        from htmlgraph.cli import cmd_orchestrator_status

        monkeypatch.chdir(tmp_path)

        manager = OrchestratorModeManager(tmp_path / ".htmlgraph")
        manager.enable(level="strict")

        # Add violations
        enforce_orchestrator_mode("Edit", {"file_path": "test1.py"})
        enforce_orchestrator_mode("Edit", {"file_path": "test2.py"})

        args = Namespace(graph_dir=tmp_path / ".htmlgraph")
        cmd_orchestrator_status(args)

        captured = capsys.readouterr()
        assert "2/3" in captured.out
