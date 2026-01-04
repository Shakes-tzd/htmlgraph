"""
Unit tests for ImperativeMessageGenerator with all 4 escalation levels.

Tests the complete imperative messaging system for CIGS, including:
- Level 0: Guidance (informative)
- Level 1: Imperative (commanding)
- Level 2: Final Warning (urgent + consequences)
- Level 3: Circuit Breaker (requires acknowledgment)

Reference: .htmlgraph/spikes/computational-imperative-guidance-system-design.md (Part 4)
"""

import pytest
from htmlgraph.cigs import ImperativeMessageGenerator, PositiveReinforcementGenerator
from htmlgraph.cigs.models import OperationClassification


class TestImperativeMessageGenerator:
    """Test suite for ImperativeMessageGenerator with all escalation levels."""

    @pytest.fixture
    def generator(self):
        """Create message generator instance."""
        return ImperativeMessageGenerator()

    @pytest.fixture
    def sample_classification_exploration(self):
        """Sample classification for exploration operation (Read)."""
        return OperationClassification(
            tool="Read",
            category="direct_exploration",
            should_delegate=True,
            reason="Multiple files need to be read to understand architecture",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini(prompt='Search and analyze authentication implementation')",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

    @pytest.fixture
    def sample_classification_implementation(self):
        """Sample classification for implementation operation (Edit)."""
        return OperationClassification(
            tool="Edit",
            category="direct_implementation",
            should_delegate=True,
            reason="Code changes require testing iteration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_codex(prompt='Implement feature X with tests')",
            predicted_cost=8000,
            optimal_cost=1000,
            waste_percentage=87.5,
        )

    @pytest.fixture
    def sample_classification_git(self):
        """Sample classification for git operation."""
        return OperationClassification(
            tool="Bash",
            category="direct_git",
            should_delegate=True,
            reason="Git operations trigger hooks and have cascading effects",
            is_exploration_sequence=False,
            suggested_delegation="spawn_copilot(prompt='Commit changes with appropriate message')",
            predicted_cost=3000,
            optimal_cost=800,
            waste_percentage=73.3,
        )

    # ========================================================================
    # LEVEL 0: GUIDANCE (Informative)
    # ========================================================================

    def test_level_0_guidance_message(
        self, generator, sample_classification_exploration
    ):
        """Test Level 0 (Guidance) message generation."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=0,
            autonomy_level="observer",
        )

        # Check structure
        assert "💡 GUIDANCE:" in message
        assert "**WHY:**" in message
        assert "**INSTEAD:**" in message
        assert "spawn_gemini" in message

        # Should NOT include cost at Level 0
        assert "**COST IMPACT:**" not in message
        assert "**CONSEQUENCE:**" not in message
        assert "**REQUIRED:**" not in message

    def test_level_0_includes_rationale(
        self, generator, sample_classification_exploration
    ):
        """Test that Level 0 includes WHY rationale."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=0,
        )

        assert "**WHY:**" in message
        assert "unpredictable scope" in message or "strategic context" in message

    def test_level_0_includes_suggestion(
        self, generator, sample_classification_exploration
    ):
        """Test that Level 0 includes delegation suggestion."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=0,
        )

        assert "**INSTEAD:**" in message
        assert sample_classification_exploration.suggested_delegation in message

    # ========================================================================
    # LEVEL 1: IMPERATIVE (Commanding)
    # ========================================================================

    def test_level_1_imperative_message(
        self, generator, sample_classification_exploration
    ):
        """Test Level 1 (Imperative) message generation."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=1,
            autonomy_level="strict",
        )

        # Check structure
        assert "🔴 IMPERATIVE:" in message
        assert "YOU MUST delegate" in message
        assert "**WHY:**" in message
        assert "**COST IMPACT:**" in message  # NOW includes cost
        assert "**INSTEAD:**" in message

        # Should NOT include consequences yet
        assert "**CONSEQUENCE:**" not in message
        assert "**REQUIRED:**" not in message

    def test_level_1_includes_cost_impact(
        self, generator, sample_classification_exploration
    ):
        """Test that Level 1 includes cost impact details."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=1,
        )

        assert "**COST IMPACT:**" in message
        assert "5,000 tokens" in message  # predicted_cost
        assert "500 tokens" in message  # optimal_cost
        assert "90%" in message or "savings" in message  # waste_percentage

    def test_level_1_different_tools(
        self, generator, sample_classification_implementation
    ):
        """Test Level 1 messages for different tool types."""
        message = generator.generate(
            tool="Edit",
            classification=sample_classification_implementation,
            violation_count=1,
        )

        assert "🔴 IMPERATIVE:" in message
        assert "Edit" in message or "delegate" in message
        assert "spawn_codex" in message

    # ========================================================================
    # LEVEL 2: FINAL WARNING (Urgent + Consequences)
    # ========================================================================

    def test_level_2_final_warning_message(
        self, generator, sample_classification_exploration
    ):
        """Test Level 2 (Final Warning) message generation."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=2,
            autonomy_level="strict",
        )

        # Check structure
        assert "⚠️ FINAL WARNING:" in message
        assert "YOU MUST delegate" in message
        assert "**WHY:**" in message
        assert "**COST IMPACT:**" in message
        assert "**INSTEAD:**" in message
        assert "**CONSEQUENCE:**" in message  # NOW includes consequences

        # Should NOT require acknowledgment yet
        assert "**REQUIRED:**" not in message

    def test_level_2_includes_consequence(
        self, generator, sample_classification_exploration
    ):
        """Test that Level 2 includes consequence warning."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=2,
        )

        assert "**CONSEQUENCE:**" in message
        assert "circuit breaker" in message.lower()
        assert "next violation" in message.lower()

    def test_level_2_urgency_tone(self, generator, sample_classification_exploration):
        """Test that Level 2 has urgent tone."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=2,
        )

        # Should have urgent language
        assert "⚠️" in message
        assert "FINAL WARNING" in message
        assert "MUST" in message

    # ========================================================================
    # LEVEL 3: CIRCUIT BREAKER (Blocking + Acknowledgment)
    # ========================================================================

    def test_level_3_circuit_breaker_message(
        self, generator, sample_classification_exploration
    ):
        """Test Level 3 (Circuit Breaker) message generation."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=3,
            autonomy_level="strict",
        )

        # Check complete structure
        assert "🚨 CIRCUIT BREAKER:" in message
        assert "YOU MUST delegate" in message
        assert "**WHY:**" in message
        assert "**COST IMPACT:**" in message
        assert "**INSTEAD:**" in message
        assert "**CONSEQUENCE:**" in message
        assert "**REQUIRED:**" in message  # NOW requires acknowledgment

    def test_level_3_requires_acknowledgment(
        self, generator, sample_classification_exploration
    ):
        """Test that Level 3 requires explicit acknowledgment."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=3,
        )

        assert "**REQUIRED:**" in message
        assert "Acknowledge this violation" in message
        assert "orchestrator acknowledge-violation" in message
        assert "OR disable enforcement" in message
        assert "set-level guidance" in message

    def test_level_3_blocking_tone(self, generator, sample_classification_exploration):
        """Test that Level 3 has blocking/critical tone."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=3,
        )

        assert "🚨" in message  # Alert emoji
        assert "CIRCUIT BREAKER" in message
        assert "ACTIVE" in message or "exceeded threshold" in message.lower()

    def test_level_3_caps_at_three(self, generator, sample_classification_exploration):
        """Test that violation counts >3 still use Level 3 messaging."""
        message_3 = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=3,
        )
        message_5 = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=5,
        )

        # Both should be circuit breaker level
        assert "🚨 CIRCUIT BREAKER:" in message_3
        assert "🚨 CIRCUIT BREAKER:" in message_5
        assert "**REQUIRED:**" in message_3
        assert "**REQUIRED:**" in message_5

    # ========================================================================
    # TOOL-SPECIFIC MESSAGING
    # ========================================================================

    def test_read_tool_specific_message(
        self, generator, sample_classification_exploration
    ):
        """Test Read tool has specific message."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=1,
        )

        assert "delegate file reading" in message.lower() or "Read" in message

    def test_grep_tool_specific_message(self, generator):
        """Test Grep tool has specific message."""
        classification = OperationClassification(
            tool="Grep",
            category="direct_exploration",
            should_delegate=True,
            reason="Search operation",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini(prompt='Search codebase for pattern X')",
            predicted_cost=3000,
            optimal_cost=500,
            waste_percentage=83.3,
        )

        message = generator.generate(
            tool="Grep",
            classification=classification,
            violation_count=1,
        )

        assert "delegate code search" in message.lower() or "Grep" in message

    def test_edit_tool_specific_message(
        self, generator, sample_classification_implementation
    ):
        """Test Edit tool has specific message."""
        message = generator.generate(
            tool="Edit",
            classification=sample_classification_implementation,
            violation_count=1,
        )

        assert "delegate code changes" in message.lower() or "Edit" in message

    def test_bash_git_specific_message(self, generator, sample_classification_git):
        """Test Bash (git) tool has specific message."""
        message = generator.generate(
            tool="Bash",
            classification=sample_classification_git,
            violation_count=1,
        )

        assert "delegate" in message.lower()
        assert "spawn_copilot" in message

    # ========================================================================
    # CATEGORY-SPECIFIC RATIONALES
    # ========================================================================

    def test_exploration_rationale(self, generator, sample_classification_exploration):
        """Test exploration category has correct rationale."""
        message = generator.generate(
            tool="Read",
            classification=sample_classification_exploration,
            violation_count=1,
        )

        assert "**WHY:**" in message
        assert (
            "unpredictable scope" in message
            or "3-5 reads" in message
            or "tactical details" in message
        )

    def test_implementation_rationale(
        self, generator, sample_classification_implementation
    ):
        """Test implementation category has correct rationale."""
        message = generator.generate(
            tool="Edit",
            classification=sample_classification_implementation,
            violation_count=1,
        )

        assert "**WHY:**" in message
        assert (
            "iteration" in message
            or "write → test → fix" in message
            or "architecture" in message
        )

    def test_git_rationale(self, generator, sample_classification_git):
        """Test git category has correct rationale."""
        message = generator.generate(
            tool="Bash",
            classification=sample_classification_git,
            violation_count=1,
        )

        assert "**WHY:**" in message
        assert (
            "cascade" in message.lower()
            or "hooks" in message
            or "conflicts" in message
            or "60%" in message
        )

    # ========================================================================
    # EDGE CASES
    # ========================================================================

    def test_missing_cost_info(self, generator):
        """Test message generation when cost info is missing."""
        classification = OperationClassification(
            tool="Read",
            category="direct_exploration",
            should_delegate=True,
            reason="Test",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini(prompt='Test')",
            predicted_cost=0,  # Missing
            optimal_cost=0,  # Missing
            waste_percentage=0.0,
        )

        message = generator.generate(
            tool="Read",
            classification=classification,
            violation_count=1,
        )

        # Should still generate valid message with generic cost language
        assert "**COST IMPACT:**" in message
        assert "tactical details" in message or "context" in message

    def test_unknown_tool_fallback(self, generator):
        """Test fallback message for unknown tool."""
        classification = OperationClassification(
            tool="UnknownTool",
            category="unknown",
            should_delegate=True,
            reason="Unknown operation",
            is_exploration_sequence=False,
            suggested_delegation="Task(prompt='Handle this operation')",
            predicted_cost=1000,
            optimal_cost=200,
            waste_percentage=80.0,
        )

        message = generator.generate(
            tool="UnknownTool",
            classification=classification,
            violation_count=1,
        )

        assert "YOU MUST delegate" in message
        assert "UnknownTool" in message

    def test_different_autonomy_levels(
        self, generator, sample_classification_exploration
    ):
        """Test that autonomy level doesn't break message generation."""
        for autonomy in ["strict", "guided", "observer", "operator"]:
            message = generator.generate(
                tool="Read",
                classification=sample_classification_exploration,
                violation_count=1,
                autonomy_level=autonomy,
            )

            assert "🔴 IMPERATIVE:" in message
            assert "YOU MUST delegate" in message


class TestPositiveReinforcementGenerator:
    """Test suite for PositiveReinforcementGenerator."""

    @pytest.fixture
    def generator(self):
        """Create positive reinforcement generator instance."""
        return PositiveReinforcementGenerator()

    def test_positive_message_basic(self, generator):
        """Test basic positive reinforcement message."""
        message = generator.generate(
            tool="Task",
            cost_savings=4500,
            compliance_rate=0.87,
        )

        assert "✅" in message
        assert "4,500 tokens" in message
        assert "87%" in message
        assert "Subagent handled tactical details" in message

    def test_positive_message_with_session_waste(self, generator):
        """Test positive message includes session waste when provided."""
        message = generator.generate(
            tool="spawn_gemini",
            cost_savings=3000,
            compliance_rate=0.92,
            session_waste=12000,
        )

        assert "✅" in message
        assert "12,000 tokens" in message or "saved" in message

    def test_compliance_rate_encouragement_high(self, generator):
        """Test encouragement text for high compliance rate (>90%)."""
        message = generator.generate(
            tool="Task",
            cost_savings=1000,
            compliance_rate=0.93,
        )

        assert "Outstanding" in message or "Keep up the excellent" in message

    def test_compliance_rate_encouragement_medium(self, generator):
        """Test encouragement text for medium compliance rate (75-90%)."""
        message = generator.generate(
            tool="Task",
            cost_savings=1000,
            compliance_rate=0.82,
        )

        assert "Keep it up" in message or "improves response quality" in message

    def test_compliance_rate_encouragement_low(self, generator):
        """Test encouragement text for lower compliance rate (<75%)."""
        message = generator.generate(
            tool="Task",
            cost_savings=1000,
            compliance_rate=0.65,
        )

        assert "Good progress" in message or "Continue delegating" in message

    def test_session_summary_outstanding(self, generator):
        """Test session summary for outstanding performance."""
        message = generator.generate_session_summary(
            total_delegations=45,
            compliance_rate=0.94,
            efficiency_score=85,
            total_savings=52000,
        )

        assert "✅" in message
        assert "Outstanding Performance" in message
        assert "45" in message
        assert "94" in message or "94.0%" in message
        assert "85" in message
        assert "52,000" in message

    def test_session_summary_good(self, generator):
        """Test session summary for good performance."""
        message = generator.generate_session_summary(
            total_delegations=32,
            compliance_rate=0.78,
            efficiency_score=72,
            total_savings=28000,
        )

        assert "Good Performance" in message
        assert "Strong delegation patterns" in message

    def test_session_summary_needs_improvement(self, generator):
        """Test session summary for performance that needs improvement."""
        message = generator.generate_session_summary(
            total_delegations=18,
            compliance_rate=0.62,
            efficiency_score=58,
            total_savings=15000,
        )

        assert "Room for Improvement" in message
        assert "Next Session" in message
        assert "Focus on delegating" in message


# ========================================================================
# EXAMPLE OUTPUT SHOWCASE
# ========================================================================


def test_example_outputs_showcase():
    """
    Showcase example outputs for all 4 escalation levels.

    This test generates and prints example messages for documentation purposes.
    """
    generator = ImperativeMessageGenerator()

    classification = OperationClassification(
        tool="Read",
        category="direct_exploration",
        should_delegate=True,
        reason="Multiple files need exploration",
        is_exploration_sequence=False,
        suggested_delegation="spawn_gemini(prompt='Search and analyze authentication implementation across the codebase')",
        predicted_cost=5000,
        optimal_cost=500,
        waste_percentage=90.0,
    )

    print("\n" + "=" * 80)
    print("EXAMPLE OUTPUTS: All 4 Escalation Levels")
    print("=" * 80)

    for level in range(4):
        message = generator.generate(
            tool="Read",
            classification=classification,
            violation_count=level,
            autonomy_level="strict",
        )

        print(f"\n{'─' * 80}")
        print(f"LEVEL {level}: {generator.ESCALATION_LEVELS[level]['prefix']}")
        print(f"Tone: {generator.ESCALATION_LEVELS[level]['tone']}")
        print(f"{'─' * 80}")
        print(message)

    print("\n" + "=" * 80)
    print("END EXAMPLES")
    print("=" * 80 + "\n")
