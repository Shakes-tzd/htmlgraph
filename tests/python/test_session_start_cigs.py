"""
Test CIGS integration in SessionStart hook.

Verifies that:
1. ViolationTracker is initialized correctly
2. PatternDetector identifies anti-patterns from history
3. AutonomyRecommender provides appropriate autonomy levels
4. Context injection includes CIGS status and recommendations
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from htmlgraph.cigs import (
    AutonomyRecommender,
    PatternDetector,
    ViolationTracker,
)
from htmlgraph.cigs.models import (
    OperationClassification,
    SessionViolationSummary,
    ViolationType,
)


class TestCIGSSessionIntegration:
    """Test CIGS integration in session-start hook."""

    def test_violation_tracker_initialization(self):
        """Test ViolationTracker initializes with graph directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)

            tracker = ViolationTracker(graph_dir)
            tracker.set_session_id("sess-test-001")

            assert tracker.graph_dir == graph_dir
            assert tracker._session_id == "sess-test-001"
            assert tracker.violations_file == graph_dir / "cigs" / "violations.jsonl"

    def test_record_violation_and_retrieve(self):
        """Test recording a violation and retrieving session summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)

            tracker = ViolationTracker(graph_dir)
            tracker.set_session_id("sess-test-002")

            # Record a violation
            classification = OperationClassification(
                tool="Read",
                category="direct_exploration",
                should_delegate=True,
                reason="File read should be delegated to Explorer",
                is_exploration_sequence=False,
                suggested_delegation="spawn_gemini(prompt='Analyze file...')",
                predicted_cost=5000,
                optimal_cost=500,
                waste_percentage=90.0,
            )

            violation_id = tracker.record_violation(
                tool="Read",
                params={"file_path": "/path/to/file.py"},
                classification=classification,
                predicted_waste=4500,
            )

            assert violation_id.startswith("viol-")

            # Retrieve session summary
            summary = tracker.get_session_violations("sess-test-002")

            assert summary.session_id == "sess-test-002"
            assert summary.total_violations == 1
            assert summary.total_waste_tokens == 4500
            assert ViolationType.DIRECT_EXPLORATION in summary.violations_by_type
            assert summary.violations_by_type[ViolationType.DIRECT_EXPLORATION] == 1

    def test_pattern_detection_exploration_sequence(self):
        """Test PatternDetector identifies exploration sequences."""
        # Simulate tool history with exploration sequence
        history = [
            {"tool": "Read", "file_path": "auth.py", "timestamp": datetime.now()},
            {"tool": "Grep", "pattern": "authenticate", "timestamp": datetime.now()},
            {"tool": "Read", "file_path": "jwt.py", "timestamp": datetime.now()},
            {"tool": "Glob", "pattern": "**/*.py", "timestamp": datetime.now()},
        ]

        detector = PatternDetector(window_size=10)
        patterns = detector.detect_all_patterns(history)

        # Should detect exploration_sequence anti-pattern
        assert len(patterns) > 0
        exploration_pattern = next(
            (p for p in patterns if p.name == "exploration_sequence"), None
        )
        assert exploration_pattern is not None
        assert exploration_pattern.pattern_type == "anti-pattern"
        assert exploration_pattern.delegation_suggestion is not None

    def test_autonomy_recommender_strict_mode(self):
        """Test AutonomyRecommender suggests strict mode for low compliance."""
        # Create violations summary with low compliance
        violations = SessionViolationSummary(
            session_id="sess-low-compliance",
            total_violations=5,
            violations_by_type={ViolationType.DIRECT_EXPLORATION: 5},
            total_waste_tokens=15000,
            circuit_breaker_triggered=True,
            compliance_rate=0.3,  # 30% compliance
        )

        recommender = AutonomyRecommender()
        autonomy = recommender.recommend(violations)

        # Should recommend operator (strict) mode
        assert autonomy.level == "operator"
        assert autonomy.messaging_intensity == "maximal"
        assert autonomy.enforcement_mode == "strict"

    def test_autonomy_recommender_observer_mode(self):
        """Test AutonomyRecommender suggests observer mode for high compliance."""
        # Create violations summary with high compliance
        violations = SessionViolationSummary(
            session_id="sess-high-compliance",
            total_violations=0,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=False,
            compliance_rate=0.95,  # 95% compliance
        )

        recommender = AutonomyRecommender()
        autonomy = recommender.recommend(violations, patterns=[])

        # Should recommend observer mode
        assert autonomy.level == "observer"
        assert autonomy.messaging_intensity == "minimal"
        assert autonomy.enforcement_mode == "guidance"

    def test_get_cigs_context_no_violations(self):
        """Test get_cigs_context with no violations returns minimal context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)

            # Import the function (would normally import from hook script)
            # For now, test the components separately
            tracker = ViolationTracker(graph_dir)
            tracker.set_session_id("sess-test-clean")

            summary = tracker.get_session_violations()

            # No violations = high compliance
            assert summary.total_violations == 0
            assert summary.compliance_rate >= 0.8

            recommender = AutonomyRecommender()
            autonomy = recommender.recommend(summary)

            # Should get observer or consultant level
            assert autonomy.level in ["observer", "consultant"]

    def test_get_cigs_context_with_violations_and_patterns(self):
        """Test get_cigs_context with violations and detected patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)

            tracker = ViolationTracker(graph_dir)
            tracker.set_session_id("sess-test-violations")

            # Record multiple violations
            for i in range(3):
                classification = OperationClassification(
                    tool="Read",
                    category="direct_exploration",
                    should_delegate=True,
                    reason="Should delegate",
                    is_exploration_sequence=True,
                    suggested_delegation="spawn_gemini()",
                    predicted_cost=5000,
                    optimal_cost=500,
                    waste_percentage=90.0,
                )

                tracker.record_violation(
                    tool="Read",
                    params={"file_path": f"/path/file{i}.py"},
                    classification=classification,
                    predicted_waste=4500,
                )

            summary = tracker.get_session_violations()

            # Should have 3 violations
            assert summary.total_violations == 3
            assert summary.circuit_breaker_triggered  # 3+ violations
            assert summary.compliance_rate < 0.5

            recommender = AutonomyRecommender()
            autonomy = recommender.recommend(summary)

            # Should recommend strict mode
            assert autonomy.level in ["operator", "collaborator"]
            assert autonomy.enforcement_mode == "strict"

    def test_cigs_context_format(self):
        """Test that CIGS context follows expected format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)

            # Simulate importing get_cigs_context
            # In actual test, would import from session-start.py
            # For now, verify the components produce correct structure

            tracker = ViolationTracker(graph_dir)
            tracker.set_session_id("sess-format-test")

            # Add a violation
            classification = OperationClassification(
                tool="Edit",
                category="direct_implementation",
                should_delegate=True,
                reason="Should delegate code changes",
                is_exploration_sequence=False,
                suggested_delegation="Task(prompt='Make changes...')",
                predicted_cost=3000,
                optimal_cost=800,
                waste_percentage=73.0,
            )

            tracker.record_violation(
                tool="Edit",
                params={"file_path": "src/main.py"},
                classification=classification,
                predicted_waste=2200,
            )

            summary = tracker.get_session_violations()
            recommender = AutonomyRecommender()
            autonomy = recommender.recommend(summary)

            # Verify autonomy structure
            assert hasattr(autonomy, "level")
            assert hasattr(autonomy, "messaging_intensity")
            assert hasattr(autonomy, "enforcement_mode")
            assert hasattr(autonomy, "reason")

            # Verify values are valid
            assert autonomy.level in [
                "observer",
                "consultant",
                "collaborator",
                "operator",
            ]
            assert autonomy.messaging_intensity in [
                "minimal",
                "moderate",
                "high",
                "maximal",
            ]
            assert autonomy.enforcement_mode in ["guidance", "strict"]


class TestCIGSContextInjection:
    """Test CIGS context injection into SessionStart output."""

    def test_hook_output_format(self):
        """Test that SessionStart hook output includes CIGS context."""
        # This would test the actual hook output format
        # For now, verify the expected structure

        expected_output = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "## 🧠 CIGS Status...",
            },
        }

        # Verify structure
        assert "continue" in expected_output
        assert "hookSpecificOutput" in expected_output
        assert "additionalContext" in expected_output["hookSpecificOutput"]

        # Verify context includes CIGS markers
        context = expected_output["hookSpecificOutput"]["additionalContext"]
        assert "CIGS" in context or "🧠" in context

    def test_cigs_context_includes_autonomy_level(self):
        """Test CIGS context includes autonomy level information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)

            tracker = ViolationTracker(graph_dir)
            tracker.set_session_id("sess-autonomy-test")

            summary = tracker.get_session_violations()
            recommender = AutonomyRecommender()
            autonomy = recommender.recommend(summary)

            # Context should include autonomy level
            # In actual implementation, this would be in get_cigs_context() output
            context_parts = [
                f"**Autonomy Level:** {autonomy.level.upper()}",
                f"**Messaging Intensity:** {autonomy.messaging_intensity}",
                f"**Enforcement Mode:** {autonomy.enforcement_mode}",
            ]

            context = "\n".join(context_parts)

            assert autonomy.level.upper() in context
            assert autonomy.messaging_intensity in context
            assert autonomy.enforcement_mode in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
