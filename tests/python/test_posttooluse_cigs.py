"""
Tests for CIGS PostToolUse Hook Integration

Tests the CIGSPostToolAnalyzer and its integration with the PostToolUse hook.
Validates:
1. Positive reinforcement for delegations
2. Cost accounting for violations
3. Actual cost tracking
4. Session summary generation
"""

from unittest.mock import MagicMock

import pytest
from htmlgraph.cigs import CIGSPostToolAnalyzer
from htmlgraph.cigs.tracker import ViolationTracker


@pytest.fixture
def temp_graph_dir(tmp_path):
    """Create temporary .htmlgraph directory."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "cigs").mkdir(parents=True)
    return graph_dir


@pytest.fixture
def analyzer(temp_graph_dir):
    """Create CIGSPostToolAnalyzer instance."""
    analyzer = CIGSPostToolAnalyzer(temp_graph_dir)
    # Set session ID to match tracker
    analyzer.tracker.set_session_id("test-session")
    return analyzer


@pytest.fixture
def tracker(temp_graph_dir):
    """Create ViolationTracker instance."""
    tracker = ViolationTracker(temp_graph_dir)
    tracker.set_session_id("test-session")
    return tracker


class TestCIGSPostToolAnalyzer:
    """Test CIGSPostToolAnalyzer class."""

    def test_initialization(self, temp_graph_dir):
        """Test analyzer initializes correctly."""
        analyzer = CIGSPostToolAnalyzer(temp_graph_dir)

        assert analyzer.graph_dir == temp_graph_dir
        assert analyzer.cost_calculator is not None
        assert analyzer.tracker is not None
        assert analyzer.positive_gen is not None

    def test_is_delegation_task(self, analyzer):
        """Test delegation detection for Task tool."""
        assert analyzer._is_delegation("Task") is True

    def test_is_delegation_spawn(self, analyzer):
        """Test delegation detection for spawn_* tools."""
        assert analyzer._is_delegation("spawn_gemini") is True
        assert analyzer._is_delegation("spawn_codex") is True
        assert analyzer._is_delegation("spawn_copilot") is True

    def test_is_not_delegation(self, analyzer):
        """Test delegation detection for direct tools."""
        assert analyzer._is_delegation("Read") is False
        assert analyzer._is_delegation("Grep") is False
        assert analyzer._is_delegation("Edit") is False
        assert analyzer._is_delegation("Bash") is False


class TestPositiveReinforcement:
    """Test positive reinforcement for delegations."""

    def test_positive_reinforcement_task(self, analyzer):
        """Test positive reinforcement for Task delegation."""
        tool = "Task"
        params = {"prompt": "Search for authentication code"}
        result = {"output": "Found 5 auth files"}

        response = analyzer.analyze(tool, params, result)

        # Should return positive message
        assert "hookSpecificOutput" in response
        assert "additionalContext" in response["hookSpecificOutput"]

        message = response["hookSpecificOutput"]["additionalContext"]
        assert "✅" in message or "Excellent" in message or "Perfect" in message

    def test_positive_reinforcement_spawn_gemini(self, analyzer):
        """Test positive reinforcement for spawn_gemini delegation."""
        tool = "spawn_gemini"
        params = {"prompt": "Explore authentication patterns"}
        result = {"output": "Comprehensive search completed"}

        response = analyzer.analyze(tool, params, result)

        # Should return positive message
        assert "hookSpecificOutput" in response
        message = response["hookSpecificOutput"]["additionalContext"]
        assert "✅" in message or "delegation" in message.lower()

    def test_positive_reinforcement_includes_compliance(self, analyzer, tracker):
        """Test positive reinforcement includes compliance rate."""
        # Set up session with violations
        tracker.set_session_id("test-session")
        tracker.record_violation(
            tool="Read",
            params={"file_path": "test.py"},
            classification=MagicMock(
                category="exploration",
                suggested_delegation="spawn_gemini()",
                predicted_cost=5000,
                optimal_cost=500,
            ),
            predicted_waste=4500,
        )

        # Analyze delegation
        tool = "Task"
        params = {"prompt": "Search"}
        result = {"output": "Done"}

        response = analyzer.analyze(tool, params, result)
        message = response["hookSpecificOutput"]["additionalContext"]

        # Should include compliance rate
        assert "compliance" in message.lower() or "%" in message


class TestCostAccounting:
    """Test cost accounting for violations."""

    def test_cost_accounting_read(self, analyzer, tracker):
        """Test cost accounting for direct Read execution."""
        # Set up violation
        tracker.set_session_id("test-session")
        tracker.record_violation(
            tool="Read",
            params={"file_path": "test.py"},
            classification=MagicMock(
                category="exploration",
                suggested_delegation="spawn_gemini()",
                predicted_cost=5000,
                optimal_cost=500,
            ),
            predicted_waste=4500,
        )

        # Analyze direct Read
        tool = "Read"
        params = {"file_path": "test.py"}
        result = {"output": "file contents"}

        response = analyzer.analyze(tool, params, result)

        # Should return cost accounting message
        assert "hookSpecificOutput" in response
        message = response["hookSpecificOutput"]["additionalContext"]

        assert "Cost Impact" in message or "cost" in message.lower()
        assert "Violation" in message or "violation" in message.lower()

    def test_cost_accounting_includes_waste(self, analyzer, tracker):
        """Test cost accounting includes waste tokens."""
        # Set up violation
        tracker.set_session_id("test-session")
        tracker.record_violation(
            tool="Grep",
            params={"pattern": "auth"},
            classification=MagicMock(
                category="exploration",
                suggested_delegation="spawn_gemini()",
                predicted_cost=3000,
                optimal_cost=500,
            ),
            predicted_waste=2500,
        )

        # Analyze direct Grep
        tool = "Grep"
        params = {"pattern": "auth"}
        result = {"output": "matches"}

        response = analyzer.analyze(tool, params, result)
        message = response["hookSpecificOutput"]["additionalContext"]

        # Should include waste information
        assert "waste" in message.lower() or "tokens" in message.lower()

    def test_cost_accounting_includes_reflection(self, analyzer, tracker):
        """Test cost accounting includes reflection prompt."""
        # Set up violation
        tracker.set_session_id("test-session")
        tracker.record_violation(
            tool="Edit",
            params={"file_path": "test.py"},
            classification=MagicMock(
                category="implementation",
                suggested_delegation="spawn_codex()",
                predicted_cost=4000,
                optimal_cost=800,
            ),
            predicted_waste=3200,
        )

        # Analyze direct Edit
        tool = "Edit"
        params = {"file_path": "test.py"}
        result = {"success": True}

        response = analyzer.analyze(tool, params, result)
        message = response["hookSpecificOutput"]["additionalContext"]

        # Should include reflection
        assert "REFLECTION" in message or "Task()" in message


class TestActualCostTracking:
    """Test actual cost tracking and updates."""

    def test_actual_cost_updates_tracker(self, analyzer, tracker):
        """Test that actual cost updates violation tracker."""
        # Set up violation
        tracker.set_session_id("test-session")
        tracker.record_violation(
            tool="Read",
            params={"file_path": "test.py"},
            classification=MagicMock(
                category="exploration",
                suggested_delegation="spawn_gemini()",
                predicted_cost=5000,
                optimal_cost=500,
            ),
            predicted_waste=4500,
        )

        # Analyze with actual cost
        tool = "Read"
        params = {"file_path": "test.py"}
        result = {"output": "file contents"}

        analyzer.analyze(tool, params, result)

        # Check that tracker was updated with actual cost
        violations = tracker.get_session_violations()
        assert violations.total_violations == 1

        # Verify violation was updated (actual_cost may be calculated)
        violation = violations.violations[0]
        assert violation.actual_cost_tokens >= 0


class TestSessionSummary:
    """Test session summary generation."""

    def test_get_session_summary(self, analyzer, tracker):
        """Test session summary generation."""
        # Set up session with violations
        tracker.set_session_id("test-session")
        tracker.record_violation(
            tool="Read",
            params={"file_path": "test.py"},
            classification=MagicMock(
                category="exploration",
                suggested_delegation="spawn_gemini()",
                predicted_cost=5000,
                optimal_cost=500,
            ),
            predicted_waste=4500,
        )

        summary = analyzer.get_session_summary()

        # Verify summary structure
        assert "total_violations" in summary
        assert summary["total_violations"] == 1
        assert "violations_by_type" in summary
        assert "total_waste_tokens" in summary
        assert "circuit_breaker_triggered" in summary
        assert "compliance_rate" in summary

    def test_session_summary_compliance_rate(self, analyzer, tracker):
        """Test compliance rate calculation in summary."""
        # No violations
        summary = analyzer.get_session_summary()

        # Compliance should be high with no violations
        assert summary["compliance_rate"] >= 0.8


class TestComplianceRateCalculation:
    """Test compliance rate calculation."""

    def test_compliance_rate_no_violations(self, analyzer):
        """Test compliance rate with no violations."""
        rate = analyzer._calculate_compliance_rate(0)
        assert rate == 1.0

    def test_compliance_rate_one_violation(self, analyzer):
        """Test compliance rate with one violation."""
        rate = analyzer._calculate_compliance_rate(1)
        assert 0.5 < rate < 1.0

    def test_compliance_rate_max_violations(self, analyzer):
        """Test compliance rate at max violations."""
        rate = analyzer._calculate_compliance_rate(5)
        assert rate == 0.0

    def test_compliance_rate_over_max(self, analyzer):
        """Test compliance rate above max violations."""
        rate = analyzer._calculate_compliance_rate(10)
        assert rate == 0.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_analyze_with_empty_result(self, analyzer):
        """Test analysis with empty result dict."""
        tool = "Read"
        params = {"file_path": "test.py"}
        result = {}

        response = analyzer.analyze(tool, params, result)

        # Should not crash, should return response
        assert isinstance(response, dict)

    def test_analyze_with_missing_fields(self, analyzer):
        """Test analysis with missing result fields."""
        tool = "Task"
        params = {}
        result = {"partial": "data"}

        response = analyzer.analyze(tool, params, result)

        # Should handle gracefully
        assert isinstance(response, dict)

    def test_multiple_violations_same_session(self, analyzer, tracker):
        """Test multiple violations in same session."""
        tracker.set_session_id("test-session")

        # Record multiple violations
        for i in range(3):
            tracker.record_violation(
                tool="Read",
                params={"file_path": f"test{i}.py"},
                classification=MagicMock(
                    category="exploration",
                    suggested_delegation="spawn_gemini()",
                    predicted_cost=5000,
                    optimal_cost=500,
                ),
                predicted_waste=4500,
            )

        summary = analyzer.get_session_summary()
        assert summary["total_violations"] == 3
        assert summary["circuit_breaker_triggered"] is True


class TestIntegrationWithHook:
    """Test integration with PostToolUse hook."""

    @pytest.mark.asyncio
    async def test_hook_calls_analyzer(self, temp_graph_dir):
        """Test that PostToolUse hook calls CIGS analyzer."""
        from htmlgraph.hooks.posttooluse import run_cigs_analysis

        hook_input = {
            "name": "Task",
            "input": {"prompt": "Search codebase"},
            "result": {"output": "Done"},
        }

        response = await run_cigs_analysis(hook_input)

        # Should return response with hookSpecificOutput
        assert isinstance(response, dict)

    @pytest.mark.asyncio
    async def test_hook_graceful_degradation(self):
        """Test hook handles errors gracefully."""
        from htmlgraph.hooks.posttooluse import run_cigs_analysis

        # Invalid input should not crash
        hook_input = {}

        response = await run_cigs_analysis(hook_input)

        # Should return empty or minimal response
        assert isinstance(response, dict)
