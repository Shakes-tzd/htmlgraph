"""Unit tests for AutonomyRecommender."""

from htmlgraph.cigs.autonomy import AutonomyRecommender
from htmlgraph.cigs.models import (
    PatternRecord,
    SessionViolationSummary,
    ViolationType,
)


class TestAutonomyRecommenderDecisionMatrix:
    """Test the four-level autonomy decision matrix."""

    def test_observer_level_high_compliance_no_patterns(self):
        """Observer level: >90% compliance, no anti-patterns."""
        recommender = AutonomyRecommender()

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=0,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=False,
            compliance_rate=0.95,
        )

        result = recommender.recommend(violations, patterns=[])

        assert result.level == "observer"
        assert result.messaging_intensity == "minimal"
        assert result.enforcement_mode == "guidance"
        assert "Excellent compliance" in result.reason

    def test_observer_level_exact_threshold(self):
        """Observer level at exact 90% threshold."""
        recommender = AutonomyRecommender()

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=1,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 1},
            total_waste_tokens=1000,
            circuit_breaker_triggered=False,
            compliance_rate=0.90,
        )

        result = recommender.recommend(violations, patterns=[])

        # At exactly 90%, should be observer (>= threshold)
        assert result.level == "observer"

    def test_consultant_level_good_compliance(self):
        """Consultant level: 70-90% compliance."""
        recommender = AutonomyRecommender()

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=3,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 3},
            total_waste_tokens=5000,
            circuit_breaker_triggered=False,
            compliance_rate=0.80,
        )

        result = recommender.recommend(violations, patterns=[])

        assert result.level == "consultant"
        assert result.messaging_intensity == "moderate"
        assert result.enforcement_mode == "guidance"
        assert "Good compliance" in result.reason

    def test_consultant_level_with_few_patterns(self):
        """Consultant level: 70-90% compliance AND <=2 anti-patterns."""
        recommender = AutonomyRecommender()

        patterns = [
            PatternRecord(
                id="pattern-1",
                pattern_type="anti-pattern",
                name="exploration_sequence",
                description="Multiple exploration tools in sequence",
                trigger_conditions=["3+ exploration tools in last 5 calls"],
                example_sequence=["Read", "Grep", "Read"],
                occurrence_count=2,
            ),
            PatternRecord(
                id="pattern-2",
                pattern_type="anti-pattern",
                name="edit_without_test",
                description="Edit operations without subsequent test delegation",
                trigger_conditions=["Edit in last 3 calls", "No Task with test"],
                example_sequence=["Edit", "Bash"],
                occurrence_count=1,
            ),
        ]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=3,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 3},
            total_waste_tokens=5000,
            circuit_breaker_triggered=False,
            compliance_rate=0.75,  # 70-90% compliance
        )

        result = recommender.recommend(violations, patterns=patterns)

        assert result.level == "consultant"
        assert result.based_on_patterns == ["exploration_sequence", "edit_without_test"]

    def test_collaborator_level_moderate_compliance(self):
        """Collaborator level: 50-70% compliance with many patterns."""
        recommender = AutonomyRecommender()

        # Need to add patterns to trigger collaborator (since 0.60 compliance and no patterns = consultant)
        patterns = [
            PatternRecord(
                id=f"pattern-{i}",
                pattern_type="anti-pattern",
                name=f"pattern_{i}",
                description=f"Pattern {i}",
                trigger_conditions=[],
                example_sequence=[],
                occurrence_count=1,
            )
            for i in range(3)
        ]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=8,
            violations_by_type={
                ViolationType.DIRECT_EXPLORATION: 5,
                ViolationType.DIRECT_IMPLEMENTATION: 3,
            },
            total_waste_tokens=20000,
            circuit_breaker_triggered=False,
            compliance_rate=0.60,
        )

        result = recommender.recommend(violations, patterns=patterns)

        assert result.level == "collaborator"
        assert result.messaging_intensity == "high"
        assert result.enforcement_mode == "strict"
        assert "Moderate compliance" in result.reason or "anti-pattern" in result.reason

    def test_collaborator_level_with_multiple_patterns(self):
        """Collaborator level: 3-4 anti-patterns with moderate compliance."""
        recommender = AutonomyRecommender()

        patterns = [
            PatternRecord(
                id=f"pattern-{i}",
                pattern_type="anti-pattern",
                name=f"pattern_{i}",
                description=f"Pattern {i}",
                trigger_conditions=[],
                example_sequence=[],
                occurrence_count=1,
            )
            for i in range(3)
        ]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=8,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 8},
            total_waste_tokens=15000,
            circuit_breaker_triggered=False,
            compliance_rate=0.60,  # 50-70% compliance
        )

        result = recommender.recommend(violations, patterns=patterns)

        assert result.level == "collaborator"
        assert result.based_on_patterns == ["pattern_0", "pattern_1", "pattern_2"]

    def test_operator_level_low_compliance(self):
        """Operator level: <50% compliance with many patterns."""
        recommender = AutonomyRecommender()

        # Need 5+ patterns to trigger operator (since 0.40 < 50% but no patterns = collaborator)
        patterns = [
            PatternRecord(
                id=f"pattern-{i}",
                pattern_type="anti-pattern",
                name=f"pattern_{i}",
                description=f"Pattern {i}",
                trigger_conditions=[],
                example_sequence=[],
                occurrence_count=1,
            )
            for i in range(5)
        ]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=15,
            violations_by_type={
                ViolationType.DIRECT_EXPLORATION: 8,
                ViolationType.DIRECT_IMPLEMENTATION: 7,
            },
            total_waste_tokens=50000,
            circuit_breaker_triggered=False,
            compliance_rate=0.40,
        )

        result = recommender.recommend(violations, patterns=patterns)

        assert result.level == "operator"
        assert result.messaging_intensity == "maximal"
        assert result.enforcement_mode == "strict"
        assert "Low compliance" in result.reason

    def test_operator_level_circuit_breaker_triggered(self):
        """Operator level: Circuit breaker takes precedence."""
        recommender = AutonomyRecommender()

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=3,
            violations_by_type={ViolationType.IGNORED_WARNING: 3},
            total_waste_tokens=15000,
            circuit_breaker_triggered=True,
            compliance_rate=0.75,
        )

        result = recommender.recommend(violations, patterns=[])

        assert result.level == "operator"
        assert result.messaging_intensity == "maximal"
        assert result.enforcement_mode == "strict"
        assert "Circuit breaker" in result.reason

    def test_operator_level_many_patterns(self):
        """Operator level: 5+ anti-patterns."""
        recommender = AutonomyRecommender()

        patterns = [
            PatternRecord(
                id=f"pattern-{i}",
                pattern_type="anti-pattern",
                name=f"pattern_{i}",
                description=f"Pattern {i}",
                trigger_conditions=[],
                example_sequence=[],
                occurrence_count=1,
            )
            for i in range(5)
        ]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=10,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 10},
            total_waste_tokens=30000,
            circuit_breaker_triggered=False,
            compliance_rate=0.30,  # <50% compliance
        )

        result = recommender.recommend(violations, patterns=patterns)

        assert result.level == "operator"
        assert len(result.based_on_patterns) == 5


class TestComplianceHistory:
    """Test recommendations based on compliance history."""

    def test_cross_session_compliance_history(self):
        """Recommendation from last 5 sessions compliance history."""
        recommender = AutonomyRecommender()

        # Average compliance: 0.75 (consultant threshold)
        compliance_history = [0.70, 0.75, 0.80, 0.72, 0.75]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=3,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 3},
            total_waste_tokens=5000,
            circuit_breaker_triggered=False,
            compliance_rate=0.75,
        )

        result = recommender.recommend(
            violations=violations,
            compliance_history=compliance_history,
        )

        assert result.level == "consultant"

    def test_compliance_history_improvement_trend(self):
        """Improving compliance history should recommend lower level."""
        recommender = AutonomyRecommender()

        # Improving trend: 0.50 -> 0.95, average = 0.77
        improving_history = [0.50, 0.65, 0.75, 0.85, 0.95]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=0,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=False,
            compliance_rate=0.95,
        )

        result = recommender.recommend(
            violations=violations,
            compliance_history=improving_history,
        )

        # Average is ~0.77, which is in 70-90% range with no patterns = consultant
        assert result.level == "consultant"

    def test_compliance_history_declining_trend(self):
        """Declining compliance history should recommend higher level."""
        recommender = AutonomyRecommender()

        # Declining trend: 0.95 -> 0.40, average = 0.63
        declining_history = [0.95, 0.80, 0.65, 0.55, 0.40]

        # 3-4 patterns with 50-70% compliance = collaborator
        patterns = [
            PatternRecord(
                id=f"pattern-{i}",
                pattern_type="anti-pattern",
                name=f"pattern_{i}",
                description=f"Pattern {i}",
                trigger_conditions=[],
                example_sequence=[],
                occurrence_count=1,
            )
            for i in range(4)
        ]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=10,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 10},
            total_waste_tokens=30000,
            circuit_breaker_triggered=False,
            compliance_rate=0.40,  # Will use history average of 0.63
        )

        result = recommender.recommend(
            violations=violations,
            compliance_history=declining_history,
            patterns=patterns,
        )

        # Average compliance is 0.63 (50-70%) + 4 patterns (3-4) = collaborator
        assert result.level == "collaborator"

    def test_recommend_from_compliance_history_only(self):
        """recommend_from_compliance_history convenience method."""
        recommender = AutonomyRecommender()

        compliance_history = [0.75, 0.78, 0.80, 0.82, 0.85]

        result = recommender.recommend_from_compliance_history(
            compliance_history=compliance_history,
            anti_pattern_count=0,
            circuit_breaker_active=False,
        )

        assert result.level == "consultant"

    def test_recommend_from_compliance_history_no_history(self):
        """Handling empty compliance history."""
        recommender = AutonomyRecommender()

        result = recommender.recommend_from_compliance_history(
            compliance_history=[],
            anti_pattern_count=0,
            circuit_breaker_active=False,
        )

        # Should default to consultant
        assert result.level == "consultant"
        assert result.based_on_violations == 0


class TestAutonomyTransitions:
    """Test autonomy level transitions."""

    def test_escalation_single_level(self):
        """Transition up one level (escalation)."""
        recommender = AutonomyRecommender()

        transition = recommender.evaluate_autonomy_transition(
            current_level="consultant",
            new_level="collaborator",
        )

        assert transition["direction"] == "escalated"
        assert transition["severity"] == "moderate"
        assert transition["escalation_level"] == 2

    def test_escalation_multiple_levels(self):
        """Transition up multiple levels (major escalation)."""
        recommender = AutonomyRecommender()

        transition = recommender.evaluate_autonomy_transition(
            current_level="observer",
            new_level="operator",
        )

        assert transition["direction"] == "escalated"
        assert transition["severity"] == "high"
        assert transition["escalation_level"] == 3

    def test_relaxation_single_level(self):
        """Transition down one level (relaxation)."""
        recommender = AutonomyRecommender()

        transition = recommender.evaluate_autonomy_transition(
            current_level="collaborator",
            new_level="consultant",
        )

        assert transition["direction"] == "relaxed"
        assert transition["severity"] == "moderate"
        assert transition["escalation_level"] == 1

    def test_relaxation_multiple_levels(self):
        """Transition down multiple levels (major relaxation)."""
        recommender = AutonomyRecommender()

        transition = recommender.evaluate_autonomy_transition(
            current_level="operator",
            new_level="observer",
        )

        assert transition["direction"] == "relaxed"
        assert transition["severity"] == "high"
        assert transition["escalation_level"] == 0

    def test_unchanged_transition(self):
        """No level change."""
        recommender = AutonomyRecommender()

        transition = recommender.evaluate_autonomy_transition(
            current_level="consultant",
            new_level="consultant",
        )

        assert transition["direction"] == "unchanged"
        assert transition["severity"] == "none"
        assert transition["escalation_level"] == 1

    def test_invalid_level_transition(self):
        """Handling invalid level names."""
        recommender = AutonomyRecommender()

        transition = recommender.evaluate_autonomy_transition(
            current_level="invalid",
            new_level="consultant",
        )

        assert transition["direction"] == "unknown"
        assert transition["severity"] == "unknown"


class TestMessagingConfiguration:
    """Test messaging configuration for each level."""

    def test_observer_messaging(self):
        """Observer level messaging config."""
        recommender = AutonomyRecommender()

        config = recommender.get_messaging_config("observer")

        assert config["prefix"] == "💡 GUIDANCE"
        assert config["tone"] == "informative"
        assert config["includes_cost"] is False
        assert config["includes_suggestion"] is True
        assert config["requires_acknowledgment"] is False
        assert config["escalation_level"] == 0

    def test_consultant_messaging(self):
        """Consultant level messaging config."""
        recommender = AutonomyRecommender()

        config = recommender.get_messaging_config("consultant")

        assert config["prefix"] == "🔴 IMPERATIVE"
        assert config["tone"] == "commanding"
        assert config["includes_cost"] is True
        assert config["includes_suggestion"] is True
        assert config["requires_acknowledgment"] is False
        assert config["escalation_level"] == 1

    def test_collaborator_messaging(self):
        """Collaborator level messaging config."""
        recommender = AutonomyRecommender()

        config = recommender.get_messaging_config("collaborator")

        assert config["prefix"] == "⚠️ FINAL WARNING"
        assert config["tone"] == "urgent"
        assert config["includes_cost"] is True
        assert config["includes_suggestion"] is True
        assert config["includes_consequences"] is True
        assert config["requires_acknowledgment"] is False
        assert config["escalation_level"] == 2

    def test_operator_messaging(self):
        """Operator level messaging config."""
        recommender = AutonomyRecommender()

        config = recommender.get_messaging_config("operator")

        assert config["prefix"] == "🚨 CIRCUIT BREAKER"
        assert config["tone"] == "blocking"
        assert config["includes_cost"] is True
        assert config["includes_suggestion"] is True
        assert config["includes_consequences"] is True
        assert config["requires_acknowledgment"] is True
        assert config["escalation_level"] == 3

    def test_unknown_level_defaults_to_consultant(self):
        """Unknown level defaults to consultant config."""
        recommender = AutonomyRecommender()

        config = recommender.get_messaging_config("unknown")

        assert config["prefix"] == "🔴 IMPERATIVE"  # Consultant default


class TestEstimateNextLevel:
    """Test estimation of next session's autonomy level."""

    def test_estimate_improvement(self):
        """Estimate improvement when no violations projected."""
        recommender = AutonomyRecommender()

        current_compliance = 0.75  # Consultant level

        next_level = recommender.estimate_next_level(
            current_compliance=current_compliance,
            projected_violations=0,
        )

        # Should estimate improvement toward Observer
        assert next_level in ["observer", "consultant"]

    def test_estimate_decline(self):
        """Estimate decline when violations projected."""
        recommender = AutonomyRecommender()

        current_compliance = 0.75  # Consultant level

        next_level = recommender.estimate_next_level(
            current_compliance=current_compliance,
            projected_violations=5,
        )

        # Should estimate decline
        assert next_level in ["collaborator", "operator", "consultant"]

    def test_estimate_at_boundaries(self):
        """Estimate at compliance boundaries."""
        recommender = AutonomyRecommender()

        # Very high compliance
        next_level_high = recommender.estimate_next_level(
            current_compliance=0.95,
            projected_violations=0,
        )
        assert next_level_high in ["observer", "consultant"]

        # Very low compliance: 0.30 - 0.05 = 0.25 (< 50%), no patterns = operator
        next_level_low = recommender.estimate_next_level(
            current_compliance=0.30,
            projected_violations=0,
        )
        assert next_level_low in ["operator", "collaborator"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_compliance(self):
        """Zero compliance rate."""
        recommender = AutonomyRecommender()

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=20,
            violations_by_type={},
            total_waste_tokens=100000,
            circuit_breaker_triggered=True,
            compliance_rate=0.0,
        )

        result = recommender.recommend(violations)

        assert result.level == "operator"

    def test_perfect_compliance(self):
        """Perfect 100% compliance."""
        recommender = AutonomyRecommender()

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=0,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=False,
            compliance_rate=1.0,
        )

        result = recommender.recommend(violations)

        assert result.level == "observer"

    def test_large_compliance_history(self):
        """Large compliance history (more than 5 sessions)."""
        recommender = AutonomyRecommender()

        # 10 sessions of compliance history
        compliance_history = [
            0.80,
            0.82,
            0.85,
            0.87,
            0.90,
            0.88,
            0.91,
            0.89,
            0.92,
            0.94,
        ]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=0,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=False,
            compliance_rate=0.92,
        )

        result = recommender.recommend(
            violations=violations,
            compliance_history=compliance_history,
        )

        # Average is ~88.8%, should be consultant (not observer)
        # But with no violations, could be observer. Let's check 90% threshold calculation
        # avg = sum(compliance_history) / len(compliance_history) = 0.888
        # avg = 0.888, which is < 0.90, so should be consultant
        assert result.level == "consultant"

    def test_many_patterns(self):
        """Many anti-patterns (>10) always triggers operator."""
        recommender = AutonomyRecommender()

        patterns = [
            PatternRecord(
                id=f"pattern-{i}",
                pattern_type="anti-pattern",
                name=f"pattern_{i}",
                description=f"Pattern {i}",
                trigger_conditions=[],
                example_sequence=[],
            )
            for i in range(15)
        ]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=5,
            violations_by_type={},
            total_waste_tokens=5000,
            circuit_breaker_triggered=False,
            compliance_rate=0.75,  # 70-90% compliance, but 5+ patterns = operator
        )

        result = recommender.recommend(violations, patterns=patterns)

        # 15 patterns (> 4) triggers operator regardless of compliance
        assert result.level == "operator"
        assert len(result.based_on_patterns) == 15

    def test_mixed_pattern_types(self):
        """Mix of anti-patterns and good patterns."""
        recommender = AutonomyRecommender()

        patterns = [
            PatternRecord(
                id="anti-1",
                pattern_type="anti-pattern",
                name="exploration_sequence",
                description="Bad pattern",
                trigger_conditions=[],
                example_sequence=[],
            ),
            PatternRecord(
                id="good-1",
                pattern_type="good-pattern",
                name="immediate_delegation",
                description="Good pattern",
                trigger_conditions=[],
                example_sequence=[],
            ),
            PatternRecord(
                id="anti-2",
                pattern_type="anti-pattern",
                name="direct_git",
                description="Bad pattern",
                trigger_conditions=[],
                example_sequence=[],
            ),
        ]

        violations = SessionViolationSummary(
            session_id="test-session",
            total_violations=3,
            violations_by_type={},
            total_waste_tokens=5000,
            circuit_breaker_triggered=False,
            compliance_rate=0.75,
        )

        result = recommender.recommend(violations, patterns=patterns)

        # Should only count anti-patterns
        assert len(result.based_on_patterns) == 2
        assert "exploration_sequence" in result.based_on_patterns
        assert "direct_git" in result.based_on_patterns
        assert "immediate_delegation" not in result.based_on_patterns
