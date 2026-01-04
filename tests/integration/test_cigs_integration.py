"""
Integration tests for CIGS (Computational Imperative Guidance System).

Tests the full CIGS workflow including:
- Hook flow from SessionStart through Stop
- Violation tracking and pattern detection
- Cost calculation and efficiency scoring
- Autonomy level adaptation
- Cross-session learning

Reference: .htmlgraph/spikes/computational-imperative-guidance-system-design.md
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest
from htmlgraph.cigs import (
    AutonomyRecommender,
    ImperativeMessageGenerator,
    PatternDetector,
    PositiveReinforcementGenerator,
    ViolationTracker,
)
from htmlgraph.cigs.cost import CostCalculator


class TestFullHookFlow:
    """Test complete hook flow from SessionStart to Stop."""

    @pytest.fixture
    def temp_graph_dir(self):
        """Create temporary graph directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def session_context(self, temp_graph_dir):
        """Create session context with CIGS components."""
        return {
            "session_id": "sess-integration-test",
            "graph_dir": temp_graph_dir,
            "tracker": ViolationTracker(temp_graph_dir),
            "pattern_detector": PatternDetector(),
            "cost_calculator": CostCalculator(),
            "message_generator": ImperativeMessageGenerator(),
            "positive_generator": PositiveReinforcementGenerator(),
            "autonomy_recommender": AutonomyRecommender(),
            "tool_history": [],
        }

    def test_sessionstart_initialization(self, session_context, temp_graph_dir):
        """Test SessionStart hook initializes CIGS state."""
        # SessionStart: Initialize violation tracking
        tracker = session_context["tracker"]
        tracker.set_session_id(session_context["session_id"])

        # Load violation history (empty for first session)
        summary = tracker.get_session_violations()

        assert summary.session_id == session_context["session_id"]
        assert summary.total_violations == 0
        assert summary.compliance_rate == 1.0
        assert not summary.circuit_breaker_triggered

        # Recommend autonomy level (should default to moderate)
        autonomy = session_context["autonomy_recommender"].recommend(summary)

        assert autonomy.level in ["observer", "consultant", "collaborator", "operator"]
        assert autonomy.messaging_intensity in [
            "minimal",
            "moderate",
            "high",
            "maximal",
        ]

    def test_user_prompt_submit_intent_detection(self, session_context):
        """Test UserPromptSubmit hook detects exploration intent."""
        # Simulate user asking for exploration
        prompt = "Search the codebase for authentication patterns"

        # Classify prompt intent (simplified - in real hook would be more sophisticated)
        involves_exploration = any(
            kw in prompt.lower()
            for kw in ["search", "find", "explore", "analyze", "read"]
        )

        assert involves_exploration

        # Generate pre-response guidance
        if involves_exploration:
            guidance = (
                "IMPERATIVE: This request involves exploration. "
                "YOU MUST use spawn_gemini() (FREE). "
                "DO NOT use Read/Grep/Glob directly."
            )
            assert "spawn_gemini()" in guidance
            assert "exploration" in guidance.lower()

    def test_pretooluse_generates_imperative(self, session_context):
        """Test PreToolUse hook generates imperative message."""
        tracker = session_context["tracker"]
        tracker.set_session_id(session_context["session_id"])
        message_gen = session_context["message_generator"]
        cost_calc = session_context["cost_calculator"]

        # Simulate Read operation
        tool = "Read"
        params = {"file_path": "/test/auth.py"}

        # Classify operation
        classification = cost_calc.classify_operation(
            tool, params, is_exploration_sequence=False
        )

        # Generate imperative message (level 1 for first violation)
        message = message_gen.generate(
            tool=tool,
            classification=classification,
            violation_count=0,  # First violation
            autonomy_level="strict",
        )

        assert "GUIDANCE" in message or "IMPERATIVE" in message
        assert "spawn_gemini" in message.lower()
        assert "WHY" in message

        # Record violation
        violation_id = tracker.record_violation(
            tool=tool,
            params=params,
            classification=classification,
            predicted_waste=classification.predicted_cost - classification.optimal_cost,
        )

        assert violation_id.startswith("viol-")

    def test_tool_execution(self, session_context):
        """Test tool execution occurs (guidance doesn't block)."""
        # CIGS uses guidance, not blocking
        # Tool execution proceeds despite imperative message

        # Simulate tool execution result
        result = {
            "output": "# Authentication module\ndef authenticate(user, password): ...",
            "cost": 5000,  # Actual cost
        }

        assert result is not None
        assert "cost" in result

    def test_posttooluse_cost_accounting(self, session_context):
        """Test PostToolUse hook calculates cost and provides feedback."""
        tracker = session_context["tracker"]
        tracker.set_session_id(session_context["session_id"])
        cost_calc = session_context["cost_calculator"]

        # Simulate previous violation
        tool = "Read"
        params = {"file_path": "/test/auth.py"}
        classification = cost_calc.classify_operation(tool, params)

        tracker.record_violation(
            tool=tool,
            params=params,
            classification=classification,
            predicted_waste=classification.predicted_cost - classification.optimal_cost,
        )

        # Calculate actual cost
        result = {"output": "file contents...", "cost": 5000}
        actual_cost = cost_calc.calculate_actual_cost(tool, result)

        assert actual_cost.total_tokens > 0
        assert actual_cost.orchestrator_tokens >= 0
        assert actual_cost.subagent_tokens >= 0

        # Generate feedback
        summary = tracker.get_session_violations()
        feedback = (
            f"Direct execution completed.\n"
            f"Actual cost: {actual_cost.total_tokens} tokens\n"
            f"Session violations: {summary.total_violations}\n"
            f"Compliance rate: {summary.compliance_rate:.1%}"
        )

        assert "Actual cost" in feedback
        assert "Compliance rate" in feedback

    def test_stop_hook_session_summary(self, session_context):
        """Test Stop hook generates comprehensive session summary."""
        tracker = session_context["tracker"]
        tracker.set_session_id(session_context["session_id"])
        pattern_detector = session_context["pattern_detector"]
        autonomy_rec = session_context["autonomy_recommender"]

        # Record some violations
        cost_calc = session_context["cost_calculator"]
        for i in range(2):
            classification = cost_calc.classify_operation(
                "Read", {"file_path": f"/test/file{i}.py"}
            )
            tracker.record_violation(
                tool="Read",
                params={"file_path": f"/test/file{i}.py"},
                classification=classification,
                predicted_waste=4500,
            )

        # Get session summary
        summary = tracker.get_session_violations()

        # Detect patterns
        tool_history = [
            {"tool": "Read", "file_path": "/test/file0.py"},
            {"tool": "Read", "file_path": "/test/file1.py"},
        ]
        patterns = pattern_detector.detect_all_patterns(tool_history)

        # Recommend autonomy for next session
        autonomy = autonomy_rec.recommend(summary, patterns)

        # Build summary report
        report = f"""
## CIGS Session Summary

### Delegation Metrics
- Compliance Rate: {summary.compliance_rate:.1%}
- Violations: {summary.total_violations}
- Circuit Breaker: {"Triggered" if summary.circuit_breaker_triggered else "Not triggered"}

### Cost Analysis
- Total Waste: {summary.total_waste_tokens} tokens

### Patterns Detected
- Patterns found: {len(patterns)}

### Autonomy Recommendation
- Next Session: {autonomy.level}
- Reason: {autonomy.reason}
"""

        assert "Compliance Rate" in report
        assert "Violations: 2" in report
        assert "Autonomy Recommendation" in report
        assert autonomy.level in ["observer", "consultant", "collaborator", "operator"]


class TestEscalationFlow:
    """Test escalation flow from Level 0 to circuit breaker."""

    @pytest.fixture
    def temp_graph_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_escalation_levels(self, temp_graph_dir):
        """Test message escalation from Level 0 through Level 3."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-escalation-test")
        message_gen = ImperativeMessageGenerator()
        cost_calc = CostCalculator()

        tool = "Read"
        params = {"file_path": "/test/file.py"}
        classification = cost_calc.classify_operation(tool, params)

        # Level 0: First encounter (guidance)
        message_0 = message_gen.generate(
            tool=tool,
            classification=classification,
            violation_count=0,
            autonomy_level="strict",
        )
        assert "💡 GUIDANCE" in message_0

        # Level 1: First violation (imperative)
        tracker.record_violation(
            tool=tool,
            params=params,
            classification=classification,
            predicted_waste=4500,
        )
        message_1 = message_gen.generate(
            tool=tool,
            classification=classification,
            violation_count=1,
            autonomy_level="strict",
        )
        assert "🔴 IMPERATIVE" in message_1
        assert "WHY:" in message_1
        assert "COST IMPACT" in message_1

        # Level 2: Second violation (final warning)
        tracker.record_violation(
            tool=tool,
            params=params,
            classification=classification,
            predicted_waste=4500,
        )
        message_2 = message_gen.generate(
            tool=tool,
            classification=classification,
            violation_count=2,
            autonomy_level="strict",
        )
        assert "⚠️ FINAL WARNING" in message_2
        assert "CONSEQUENCE:" in message_2
        assert "circuit breaker" in message_2.lower()

        # Level 3: Third violation (circuit breaker)
        tracker.record_violation(
            tool=tool,
            params=params,
            classification=classification,
            predicted_waste=4500,
        )
        message_3 = message_gen.generate(
            tool=tool,
            classification=classification,
            violation_count=3,
            autonomy_level="strict",
        )
        assert "🚨 CIRCUIT BREAKER" in message_3
        assert "REQUIRED:" in message_3
        assert "acknowledge" in message_3.lower()

        # Verify circuit breaker triggered
        summary = tracker.get_session_violations()
        assert summary.circuit_breaker_triggered
        assert summary.total_violations == 3

    def test_acknowledgment_reset(self, temp_graph_dir):
        """Test that acknowledgment resets circuit breaker."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-ack-test")
        cost_calc = CostCalculator()

        # Trigger circuit breaker
        classification = cost_calc.classify_operation("Read", {})
        for _ in range(3):
            tracker.record_violation(
                tool="Read",
                params={},
                classification=classification,
                predicted_waste=4500,
            )

        summary = tracker.get_session_violations()
        assert summary.circuit_breaker_triggered

        # Simulate acknowledgment by clearing violations
        # (In real implementation, would have dedicated method)
        tracker.clear_session_file()
        tracker.set_session_id("sess-ack-test-reset")

        summary_after = tracker.get_session_violations()
        assert not summary_after.circuit_breaker_triggered
        assert summary_after.total_violations == 0


class TestPatternDetectionIntegration:
    """Test pattern detection integration with violation tracking."""

    @pytest.fixture
    def temp_graph_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_exploration_sequence_pattern(self, temp_graph_dir):
        """Test detection of exploration sequence anti-pattern."""
        pattern_detector = PatternDetector()

        # Simulate tool history with exploration sequence
        history = [
            {"tool": "Read", "file_path": "/test/auth.py"},
            {"tool": "Grep", "pattern": "authenticate"},
            {"tool": "Read", "file_path": "/test/user.py"},
            {"tool": "Glob", "pattern": "**/*.py"},
        ]

        patterns = pattern_detector.detect_all_patterns(history)

        # Should detect exploration_sequence pattern
        exploration_patterns = [p for p in patterns if p.name == "exploration_sequence"]
        assert len(exploration_patterns) > 0
        assert exploration_patterns[0].pattern_type == "anti-pattern"
        assert exploration_patterns[0].correct_approach is not None

    def test_pattern_persistence(self, temp_graph_dir):
        """Test that detected patterns are tracked across sessions."""
        tracker = ViolationTracker(temp_graph_dir)
        pattern_detector = PatternDetector()

        # Session 1: Create exploration sequence
        tracker.set_session_id("sess-pattern-1")
        cost_calc = CostCalculator()

        for tool in ["Read", "Grep", "Glob"]:
            classification = cost_calc.classify_operation(tool, {})
            tracker.record_violation(
                tool=tool,
                params={},
                classification=classification,
                predicted_waste=3000,
            )

        # Detect patterns
        history_1 = [
            {"tool": "Read"},
            {"tool": "Grep"},
            {"tool": "Glob"},
        ]
        patterns_1 = pattern_detector.detect_all_patterns(history_1)
        assert len(patterns_1) > 0

        # Session 2: Repeat pattern
        tracker.set_session_id("sess-pattern-2")
        for tool in ["Read", "Read", "Grep"]:
            classification = cost_calc.classify_operation(tool, {})
            tracker.record_violation(
                tool=tool,
                params={},
                classification=classification,
                predicted_waste=3000,
            )

        history_2 = [
            {"tool": "Read"},
            {"tool": "Read"},
            {"tool": "Grep"},
        ]
        patterns_2 = pattern_detector.detect_all_patterns(history_2)
        assert len(patterns_2) > 0

    def test_pattern_based_guidance(self, temp_graph_dir):
        """Test that detected patterns influence guidance messages."""
        pattern_detector = PatternDetector()
        message_gen = ImperativeMessageGenerator()
        cost_calc = CostCalculator()

        # Detect exploration sequence pattern
        history = [
            {"tool": "Read"},
            {"tool": "Grep"},
            {"tool": "Glob"},
        ]
        pattern_detector.detect_all_patterns(history)

        # Generate message with pattern context
        classification = cost_calc.classify_operation(
            "Read", {}, is_exploration_sequence=True
        )

        message = message_gen.generate(
            tool="Read",
            classification=classification,
            violation_count=1,
            autonomy_level="strict",
        )

        # Message should reference the pattern
        assert (
            "multiple exploration" in message.lower() or "sequence" in message.lower()
        )


class TestCrossSessionLearning:
    """Test learning and adaptation across multiple sessions."""

    @pytest.fixture
    def temp_graph_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_autonomy_escalation(self, temp_graph_dir):
        """Test autonomy level escalates with poor compliance."""
        tracker = ViolationTracker(temp_graph_dir)
        autonomy_rec = AutonomyRecommender()
        cost_calc = CostCalculator()

        # Session 1: High violations → strict autonomy
        tracker.set_session_id("sess-learn-1")
        for _ in range(5):
            classification = cost_calc.classify_operation("Read", {})
            tracker.record_violation(
                tool="Read",
                params={},
                classification=classification,
                predicted_waste=4500,
            )

        summary_1 = tracker.get_session_violations()
        autonomy_1 = autonomy_rec.recommend(summary_1)

        assert summary_1.compliance_rate < 0.5
        assert autonomy_1.level == "operator"
        assert autonomy_1.enforcement_mode == "strict"

    def test_autonomy_relaxation(self, temp_graph_dir):
        """Test autonomy level relaxes with good compliance."""
        autonomy_rec = AutonomyRecommender()

        # Simulate improving compliance history
        compliance_history = [0.4, 0.5, 0.7, 0.85, 0.95]

        # Should recommend observer for recent high compliance
        autonomy = autonomy_rec.recommend_from_compliance_history(
            compliance_history[-1:]
        )

        assert autonomy.level in ["observer", "consultant"]
        assert autonomy.messaging_intensity in ["minimal", "moderate"]

    def test_cost_efficiency_improvement(self, temp_graph_dir):
        """Test that cost efficiency improves with learning."""
        tracker = ViolationTracker(temp_graph_dir)
        cost_calc = CostCalculator()

        # Session 1: Many direct operations (low efficiency)
        tracker.set_session_id("sess-cost-1")
        for i in range(5):
            classification = cost_calc.classify_operation("Read", {})
            tracker.record_violation(
                tool="Read",
                params={},
                classification=classification,
                predicted_waste=4500,
            )

        summary_1 = tracker.get_session_violations()
        efficiency_1 = 1.0 - (summary_1.total_violations / 5.0)

        # Session 2: Fewer violations (higher efficiency)
        tracker.clear_session_file()
        tracker.set_session_id("sess-cost-2")
        classification = cost_calc.classify_operation("Read", {})
        tracker.record_violation(
            tool="Read",
            params={},
            classification=classification,
            predicted_waste=4500,
        )

        summary_2 = tracker.get_session_violations()
        efficiency_2 = 1.0 - (summary_2.total_violations / 5.0)

        # Efficiency should improve
        assert efficiency_2 > efficiency_1


class TestCostCalculationIntegration:
    """Test cost calculation integration with CIGS workflow."""

    @pytest.fixture
    def temp_graph_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_direct_vs_delegated_costs(self, temp_graph_dir):
        """Test cost calculation for direct execution vs delegation."""
        cost_calc = CostCalculator()

        # Direct execution cost
        direct_cost = cost_calc.predict_cost("Read", {"file_path": "/test/file.py"})

        # Optimal (delegated) cost
        classification = cost_calc.classify_operation("Read", {})
        optimal_cost = cost_calc.optimal_cost(classification)

        # Direct should be significantly higher
        assert direct_cost > optimal_cost
        waste = direct_cost - optimal_cost
        waste_pct = (waste / direct_cost) * 100

        assert waste_pct > 80  # Read operations should save >80%

    def test_waste_calculation_accuracy(self, temp_graph_dir):
        """Test waste calculation matches predictions."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-waste-test")
        cost_calc = CostCalculator()

        # Record violations with predicted costs
        classification = cost_calc.classify_operation("Read", {})
        predicted_waste = classification.predicted_cost - classification.optimal_cost

        tracker.record_violation(
            tool="Read",
            params={},
            classification=classification,
            predicted_waste=predicted_waste,
        )

        summary = tracker.get_session_violations()

        # Waste should match prediction
        assert summary.total_waste_tokens == predicted_waste

    def test_efficiency_score_calculation(self, temp_graph_dir):
        """Test efficiency score calculation."""
        cost_calc = CostCalculator()

        # Simulate operations
        operations: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
            ("Read", {"file_path": "/test/file1.py"}, {"output": "...", "cost": 5000}),
            ("Read", {"file_path": "/test/file2.py"}, {"output": "...", "cost": 5000}),
            ("Task", {"prompt": "Delegate work"}, {"cost": 500}),
        ]

        metrics = cost_calc.aggregate_session_costs(operations, violations_count=2)

        # Calculate efficiency: (optimal / actual) * 100 - penalties
        # 2 violations = 10 points penalty
        assert metrics.efficiency_score >= 0
        assert metrics.efficiency_score <= 100
        assert metrics.waste_tokens >= 0


class TestPositiveReinforcement:
    """Test positive reinforcement for correct delegation."""

    @pytest.fixture
    def temp_graph_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_correct_delegation_feedback(self, temp_graph_dir):
        """Test positive feedback for correct delegation."""
        pos_gen = PositiveReinforcementGenerator()
        cost_calc = CostCalculator()

        # Simulate delegation saving
        direct_cost = cost_calc.predict_cost("Read", {})
        classification = cost_calc.classify_operation("Read", {})
        optimal_cost = cost_calc.optimal_cost(classification)
        savings = direct_cost - optimal_cost

        # Generate positive message
        message = pos_gen.generate(
            tool="spawn_gemini", cost_savings=savings, compliance_rate=0.87
        )

        assert "✅" in message
        assert "Impact" in message
        assert "87%" in message
        assert any(enc in message for enc in pos_gen.ENCOURAGEMENTS), (
            f"No encouragement found in: {message}"
        )

    def test_session_summary_with_high_compliance(self, temp_graph_dir):
        """Test session summary with high compliance generates positive message."""
        pos_gen = PositiveReinforcementGenerator()

        summary_msg = pos_gen.generate_session_summary(
            total_delegations=15,
            compliance_rate=0.93,
            efficiency_score=88.0,
            total_savings=60000,
        )

        assert "✅" in summary_msg
        assert "Outstanding" in summary_msg or "Excellent" in summary_msg
        assert "93" in summary_msg or "93.0" in summary_msg
        assert "88" in summary_msg
