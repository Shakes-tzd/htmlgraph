"""
Tests for CIGS PreToolUse Enforcer

Tests the integration of CIGS components into PreToolUse hook with:
- Escalation levels (0-3)
- Violation tracking
- Cost prediction
- Imperative message generation
- Circuit breaker triggering

Design Reference:
    .htmlgraph/spikes/computational-imperative-guidance-system-design.md
"""

import tempfile
from pathlib import Path

import pytest
from htmlgraph.cigs.tracker import ViolationTracker
from htmlgraph.hooks.cigs_pretool_enforcer import CIGSPreToolEnforcer
from htmlgraph.orchestrator_mode import OrchestratorModeManager


@pytest.fixture
def temp_graph_dir():
    """Create temporary .htmlgraph directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = Path(tmpdir) / ".htmlgraph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        yield graph_dir


@pytest.fixture
def enforcer(temp_graph_dir):
    """Create CIGS enforcer with temporary directory."""
    enforcer = CIGSPreToolEnforcer(graph_dir=temp_graph_dir)
    # Set session ID to match tracker fixture
    enforcer.tracker.set_session_id("test-session")
    return enforcer


@pytest.fixture
def tracker(temp_graph_dir):
    """Create ViolationTracker with temporary directory."""
    tracker = ViolationTracker(graph_dir=temp_graph_dir)
    tracker.set_session_id("test-session")
    # Clear any existing violations
    tracker.clear_session_file()
    return tracker


@pytest.fixture
def manager(temp_graph_dir):
    """Create OrchestratorModeManager with temporary directory."""
    return OrchestratorModeManager(temp_graph_dir)


class TestCIGSPreToolEnforcer:
    """Test CIGS PreToolUse enforcement with escalation."""

    def test_always_allowed_tools(self, enforcer, manager):
        """Test that orchestrator core tools are always allowed."""
        # Enable orchestrator mode
        manager.enable(level="strict")

        # Test orchestrator core tools
        for tool in ["Task", "AskUserQuestion", "TodoWrite"]:
            result = enforcer.enforce(tool, {})
            assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_sdk_operations_allowed(self, enforcer, manager):
        """Test that SDK operations are always allowed."""
        manager.enable(level="strict")

        # Test SDK commands
        sdk_commands = [
            "uv run htmlgraph status",
            "htmlgraph feature create 'Test'",
            "git status",
            "git diff",
        ]

        for cmd in sdk_commands:
            result = enforcer.enforce("Bash", {"command": cmd})
            assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_orchestrator_disabled_allows_all(self, enforcer, manager):
        """Test that all tools are allowed when orchestrator is disabled."""
        manager.disable()

        # Test implementation tools (normally blocked)
        for tool in ["Edit", "Write", "Read", "Grep"]:
            result = enforcer.enforce(tool, {"file_path": "test.py"})
            assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_escalation_level_0_guidance(self, enforcer, manager, tracker):
        """Test Level 0 (first violation) - Guidance message."""
        manager.enable(level="strict")

        # First violation - should get guidance
        result = enforcer.enforce("Read", {"file_path": "test.py"})

        # Should be denied in strict mode
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

        # Message should contain guidance prefix
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        assert "💡 GUIDANCE" in reason or "IMPERATIVE" in reason

        # Check violation was recorded
        summary = tracker.get_session_violations()
        assert summary.total_violations == 1

    def test_escalation_level_1_imperative(self, enforcer, manager, tracker):
        """Test Level 1 (second violation) - Imperative message with cost."""
        manager.enable(level="strict")

        # Create first violation
        enforcer.enforce("Read", {"file_path": "test1.py"})

        # Second violation - should get imperative
        result = enforcer.enforce("Grep", {"pattern": "test"})

        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        assert "🔴 IMPERATIVE" in reason or "FINAL WARNING" in reason
        assert "COST IMPACT" in reason or "tokens" in reason.lower()

        # Check violation count
        summary = tracker.get_session_violations()
        assert summary.total_violations == 2

    def test_escalation_level_2_final_warning(self, enforcer, manager, tracker):
        """Test Level 2 (third violation) - Final warning with consequences."""
        manager.enable(level="strict")

        # Create two violations
        enforcer.enforce("Read", {"file_path": "test1.py"})
        enforcer.enforce("Grep", {"pattern": "test"})

        # Third violation - should get final warning
        result = enforcer.enforce("Edit", {"file_path": "test2.py"})

        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        assert "⚠️ FINAL WARNING" in reason or "CIRCUIT BREAKER" in reason
        assert "CONSEQUENCE" in reason or "circuit breaker" in reason.lower()

        # Check violation count
        summary = tracker.get_session_violations()
        assert summary.total_violations == 3

    def test_escalation_level_3_circuit_breaker(self, enforcer, manager, tracker):
        """Test Level 3 (4+ violations) - Circuit breaker with acknowledgment."""
        manager.enable(level="strict")

        # Create three violations to trigger circuit breaker
        enforcer.enforce("Read", {"file_path": "test1.py"})
        enforcer.enforce("Grep", {"pattern": "test"})
        enforcer.enforce("Edit", {"file_path": "test2.py"})

        # Fourth violation - should trigger circuit breaker
        result = enforcer.enforce("Write", {"file_path": "test3.py"})

        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        assert "🚨 CIRCUIT BREAKER" in reason
        assert "acknowledge" in reason.lower() or "REQUIRED" in reason

        # Check violation count
        summary = tracker.get_session_violations()
        assert summary.total_violations >= 3
        assert summary.circuit_breaker_triggered

    def test_guidance_mode_allows_with_message(self, enforcer, manager, tracker):
        """Test that guidance mode allows operations but provides messages."""
        manager.enable(level="guidance")

        # Try implementation tool
        result = enforcer.enforce("Edit", {"file_path": "test.py"})

        # Should allow in guidance mode
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

        # Should still provide guidance
        assert "additionalContext" in result["hookSpecificOutput"]
        context = result["hookSpecificOutput"]["additionalContext"]
        assert len(context) > 0

    def test_violation_tracking_persistence(self, temp_graph_dir, tracker):
        """Test that violations persist across enforcer instances."""
        # Create violations with first enforcer
        enforcer1 = CIGSPreToolEnforcer(graph_dir=temp_graph_dir)
        enforcer1.tracker.set_session_id("test-session")  # Match tracker fixture
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        enforcer1.enforce("Read", {"file_path": "test1.py"})
        enforcer1.enforce("Grep", {"pattern": "test"})

        # Create new enforcer instance
        enforcer2 = CIGSPreToolEnforcer(graph_dir=temp_graph_dir)
        enforcer2.tracker.set_session_id("test-session")  # Match tracker fixture

        # Violations should persist
        summary = tracker.get_session_violations()
        assert summary.total_violations == 2

        # Next violation should be level 2 (final warning)
        result = enforcer2.enforce("Edit", {"file_path": "test2.py"})
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]
        assert "FINAL WARNING" in reason or "CIRCUIT BREAKER" in reason

    def test_exploration_sequence_detection(self, enforcer, manager):
        """Test detection of exploration sequences."""
        manager.enable(level="strict")

        # First exploration - will be denied in strict mode
        enforcer.enforce("Read", {"file_path": "test1.py"})

        # Second exploration - should be classified as sequence
        result2 = enforcer.enforce("Grep", {"pattern": "test"})

        assert result2["hookSpecificOutput"]["permissionDecision"] == "deny"
        reason = result2["hookSpecificOutput"]["permissionDecisionReason"]
        # Should mention exploration or research
        assert (
            "exploration" in reason.lower()
            or "research" in reason.lower()
            or "delegate" in reason.lower()
        )

    def test_cost_prediction_in_message(self, enforcer, manager, tracker):
        """Test that cost predictions appear in imperative messages."""
        manager.enable(level="strict")

        # Create first violation to get to imperative level
        enforcer.enforce("Read", {"file_path": "test1.py"})

        # Second violation should include cost
        result = enforcer.enforce("Edit", {"file_path": "test2.py"})

        reason = result["hookSpecificOutput"]["permissionDecisionReason"]

        # Should mention tokens or cost
        assert "tokens" in reason.lower() or "cost" in reason.lower()

    def test_compliance_rate_calculation(self, temp_graph_dir, tracker):
        """Test compliance rate calculation in violation summary."""
        enforcer = CIGSPreToolEnforcer(graph_dir=temp_graph_dir)
        enforcer.tracker.set_session_id("test-session")  # Match tracker fixture
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        # No violations - high compliance
        summary = tracker.get_session_violations()
        assert summary.compliance_rate == 1.0

        # Add violations
        enforcer.enforce("Read", {"file_path": "test1.py"})
        enforcer.enforce("Grep", {"pattern": "test"})

        summary = tracker.get_session_violations()
        # Compliance should decrease with violations
        assert summary.compliance_rate < 1.0
        assert summary.compliance_rate >= 0.0

    def test_violation_types_classification(self, temp_graph_dir, tracker):
        """Test that violations are classified by type."""
        enforcer = CIGSPreToolEnforcer(graph_dir=temp_graph_dir)
        enforcer.tracker.set_session_id("test-session")  # Match tracker fixture
        manager = OrchestratorModeManager(temp_graph_dir)
        manager.enable(level="strict")

        # Create different violation types
        enforcer.enforce("Read", {"file_path": "test.py"})  # DIRECT_EXPLORATION
        enforcer.enforce("Edit", {"file_path": "test.py"})  # DIRECT_IMPLEMENTATION
        enforcer.enforce("Bash", {"command": "pytest"})  # DIRECT_TESTING

        summary = tracker.get_session_violations()

        # Should have violations categorized by type
        assert len(summary.violations_by_type) > 0
        assert summary.total_violations == 3

    def test_error_graceful_degradation(self, temp_graph_dir):
        """Test that errors don't crash hook, just allow operations."""
        # Create enforcer with invalid/missing components
        # This tests the try/except in enforce_cigs_pretool

        from htmlgraph.hooks.cigs_pretool_enforcer import enforce_cigs_pretool

        # Test with empty/invalid input
        result = enforce_cigs_pretool({})

        # Should allow on error
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"


class TestCIGSMessageContent:
    """Test content of CIGS imperative messages."""

    def test_message_includes_why(self, enforcer, manager):
        """Test that messages include WHY delegation is required."""
        manager.enable(level="strict")

        result = enforcer.enforce("Read", {"file_path": "test.py"})
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]

        # Should include rationale
        assert "WHY" in reason or "why" in reason.lower()

    def test_message_includes_suggestion(self, enforcer, manager):
        """Test that messages include concrete delegation suggestions."""
        manager.enable(level="strict")

        result = enforcer.enforce("Edit", {"file_path": "test.py"})
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]

        # Should include delegation suggestion
        assert "INSTEAD" in reason or "delegate" in reason.lower()
        assert "Task" in reason or "spawn" in reason.lower()

    def test_circuit_breaker_message_includes_options(self, enforcer, manager, tracker):
        """Test that circuit breaker message includes recovery options."""
        manager.enable(level="strict")

        # Trigger circuit breaker
        for i in range(3):
            enforcer.enforce("Read", {"file_path": f"test{i}.py"})

        result = enforcer.enforce("Edit", {"file_path": "test.py"})
        reason = result["hookSpecificOutput"]["permissionDecisionReason"]

        # Should include all recovery options
        assert "acknowledge" in reason.lower() or "reset" in reason.lower()
        assert "disable" in reason.lower()
        assert "guidance" in reason.lower()


class TestCIGSIntegrationWithHook:
    """Test CIGS integration with actual hook format."""

    def test_hook_stdin_format(self):
        """Test that hook can parse stdin format."""
        from htmlgraph.hooks.cigs_pretool_enforcer import enforce_cigs_pretool

        # Test standard hook input format
        tool_input = {"name": "Read", "input": {"file_path": "test.py"}}

        result = enforce_cigs_pretool(tool_input)

        # Should return valid hook response
        assert "hookSpecificOutput" in result
        assert "permissionDecision" in result["hookSpecificOutput"]

    def test_hook_alternative_format(self):
        """Test alternative hook input format."""
        from htmlgraph.hooks.cigs_pretool_enforcer import enforce_cigs_pretool

        # Alternative format with tool_name and tool_input
        tool_input = {"tool_name": "Edit", "tool_input": {"file_path": "test.py"}}

        result = enforce_cigs_pretool(tool_input)

        # Should return valid hook response
        assert "hookSpecificOutput" in result
        assert "permissionDecision" in result["hookSpecificOutput"]

    def test_hook_response_format_compliance(self, enforcer, manager):
        """Test that hook responses comply with Claude Code format."""
        manager.enable(level="strict")

        result = enforcer.enforce("Edit", {"file_path": "test.py"})

        # Check required fields
        assert "hookSpecificOutput" in result
        output = result["hookSpecificOutput"]

        assert "hookEventName" in output
        assert output["hookEventName"] == "PreToolUse"

        assert "permissionDecision" in output
        assert output["permissionDecision"] in ("allow", "deny")

        # If deny, must have reason
        if output["permissionDecision"] == "deny":
            assert "permissionDecisionReason" in output

        # If allow, may have context
        if output["permissionDecision"] == "allow":
            # additionalContext is optional
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
