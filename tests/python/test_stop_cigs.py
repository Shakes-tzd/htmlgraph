"""
Tests for CIGS Stop Hook - Session Summary Generation

Verifies that the Stop hook correctly:
1. Loads session violations from ViolationTracker
2. Detects patterns using PatternDetector
3. Calculates session costs
4. Generates autonomy recommendations
5. Builds comprehensive session summaries
6. Persists summaries to .htmlgraph/cigs/session-summaries/

Reference: .htmlgraph/spikes/computational-imperative-guidance-system-design.md (Section 2.5)
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from htmlgraph.cigs.models import (
    AutonomyLevel,
)
from htmlgraph.cigs.tracker import ViolationTracker
from htmlgraph.hooks.session_summary import CIGSSessionSummarizer


@pytest.fixture
def temp_graph_dir(tmp_path):
    """Create temporary .htmlgraph directory."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir()
    (graph_dir / "cigs").mkdir()
    return graph_dir


@pytest.fixture
def sample_violations(temp_graph_dir):
    """Create sample violations for testing."""
    tracker = ViolationTracker(temp_graph_dir)
    tracker.set_session_id("test-session-001")

    # Record some violations
    violations = [
        {
            "tool": "Read",
            "params": {"file_path": "/path/to/file.py"},
            "classification": MagicMock(
                predicted_cost=5000,
                optimal_cost=500,
                suggested_delegation="spawn_gemini()",
            ),
            "predicted_waste": 4500,
        },
        {
            "tool": "Grep",
            "params": {"pattern": "def.*", "path": "/src"},
            "classification": MagicMock(
                predicted_cost=3000,
                optimal_cost=500,
                suggested_delegation="spawn_gemini()",
            ),
            "predicted_waste": 2500,
        },
        {
            "tool": "Read",
            "params": {"file_path": "/path/to/another.py"},
            "classification": MagicMock(
                predicted_cost=5000,
                optimal_cost=500,
                suggested_delegation="spawn_gemini()",
            ),
            "predicted_waste": 4500,
        },
    ]

    for v in violations:
        tracker.record_violation(**v)

    return tracker


def test_stop_hook_loads_violations(temp_graph_dir, sample_violations):
    """Test that Stop hook loads violations from tracker."""
    summarizer = CIGSSessionSummarizer(temp_graph_dir)
    violations = summarizer.tracker.get_session_violations("test-session-001")

    assert violations.session_id == "test-session-001"
    assert violations.total_violations == 3
    assert violations.total_waste_tokens > 0


def test_stop_hook_detects_patterns(temp_graph_dir, sample_violations):
    """Test that Stop hook detects behavioral patterns."""
    summarizer = CIGSSessionSummarizer(temp_graph_dir)
    violations = summarizer.tracker.get_session_violations("test-session-001")

    patterns = summarizer._detect_patterns(violations.violations)

    # Should detect exploration_sequence (3 exploration tools)
    assert len(patterns) > 0
    pattern_names = [p.name for p in patterns]
    assert "exploration_sequence" in pattern_names


def test_stop_hook_calculates_costs(temp_graph_dir, sample_violations):
    """Test that Stop hook calculates session costs."""
    summarizer = CIGSSessionSummarizer(temp_graph_dir)
    violations = summarizer.tracker.get_session_violations("test-session-001")

    costs = summarizer._calculate_costs(violations)

    assert "total_tokens" in costs
    assert "optimal_tokens" in costs
    assert "waste_tokens" in costs
    assert "waste_percentage" in costs
    assert "efficiency_score" in costs

    # Verify waste is calculated correctly
    assert costs["waste_tokens"] == violations.total_waste_tokens
    assert costs["waste_percentage"] > 0  # Should have some waste


def test_stop_hook_generates_autonomy_recommendation(temp_graph_dir, sample_violations):
    """Test that Stop hook generates autonomy recommendation."""
    summarizer = CIGSSessionSummarizer(temp_graph_dir)
    violations = summarizer.tracker.get_session_violations("test-session-001")
    patterns = summarizer._detect_patterns(violations.violations)

    autonomy_rec = summarizer.autonomy_recommender.recommend(
        violations=violations,
        patterns=patterns,
        compliance_history=[0.4],  # Low compliance
    )

    assert isinstance(autonomy_rec, AutonomyLevel)
    assert autonomy_rec.level in ["observer", "consultant", "collaborator", "operator"]
    assert autonomy_rec.messaging_intensity in [
        "minimal",
        "moderate",
        "high",
        "maximal",
    ]
    assert autonomy_rec.enforcement_mode in ["guidance", "strict"]
    assert autonomy_rec.reason  # Should have a reason


def test_stop_hook_builds_summary_text(temp_graph_dir, sample_violations):
    """Test that Stop hook builds formatted summary text."""
    summarizer = CIGSSessionSummarizer(temp_graph_dir)
    violations = summarizer.tracker.get_session_violations("test-session-001")
    patterns = summarizer._detect_patterns(violations.violations)
    costs = summarizer._calculate_costs(violations)

    autonomy_rec = AutonomyLevel(
        level="collaborator",
        messaging_intensity="high",
        enforcement_mode="strict",
        reason="Multiple violations detected, active guidance needed",
        based_on_violations=3,
        based_on_patterns=["exploration_sequence"],
    )

    summary = summarizer._build_summary_text(violations, patterns, costs, autonomy_rec)

    # Verify summary contains key sections
    assert "## 📊 CIGS Session Summary" in summary
    assert "### Delegation Metrics" in summary
    assert "### Cost Analysis" in summary
    assert "### Autonomy Recommendation" in summary
    assert "### Learning Applied" in summary

    # Verify metrics are included
    assert "Compliance Rate:" in summary
    assert "Violations:" in summary
    assert "Circuit Breaker:" in summary
    assert "Total Context Used:" in summary
    assert "Estimated Waste:" in summary
    assert "Efficiency Score:" in summary

    # Verify autonomy recommendation
    assert "COLLABORATOR" in summary
    assert "high" in summary.lower()


def test_stop_hook_persists_summary(temp_graph_dir, sample_violations):
    """Test that Stop hook persists summary to file."""
    summarizer = CIGSSessionSummarizer(temp_graph_dir)
    violations = summarizer.tracker.get_session_violations("test-session-001")

    summary_data = {
        "session_id": "test-session-001",
        "violations": violations.to_dict(),
        "patterns": [],
        "costs": {"total_tokens": 13000, "waste_tokens": 11500},
        "autonomy_recommendation": {
            "level": "collaborator",
            "messaging_intensity": "high",
        },
    }

    summarizer._persist_summary("test-session-001", summary_data)

    # Verify file was created
    summary_file = summarizer.summaries_dir / "test-session-001.json"
    assert summary_file.exists()

    # Verify content
    with open(summary_file) as f:
        loaded = json.load(f)
        assert loaded["session_id"] == "test-session-001"
        assert "violations" in loaded
        assert "costs" in loaded


def test_stop_hook_full_summarize(temp_graph_dir, sample_violations):
    """Test complete summarize() workflow."""
    summarizer = CIGSSessionSummarizer(temp_graph_dir)
    result = summarizer.summarize("test-session-001")

    # Verify hook output structure
    assert "hookSpecificOutput" in result
    assert result["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert "additionalContext" in result["hookSpecificOutput"]

    # Verify summary content
    summary = result["hookSpecificOutput"]["additionalContext"]
    assert "CIGS Session Summary" in summary
    assert "Delegation Metrics" in summary
    assert "Cost Analysis" in summary
    assert "Autonomy Recommendation" in summary

    # Verify summary was persisted
    summary_file = summarizer.summaries_dir / "test-session-001.json"
    assert summary_file.exists()


def test_stop_hook_empty_session(temp_graph_dir):
    """Test Stop hook with session that has no violations."""
    tracker = ViolationTracker(temp_graph_dir)
    tracker.set_session_id("empty-session")

    summarizer = CIGSSessionSummarizer(temp_graph_dir)
    result = summarizer.summarize("empty-session")

    summary = result["hookSpecificOutput"]["additionalContext"]

    # Should still generate summary
    assert "CIGS Session Summary" in summary
    assert "No violations detected" in summary or "0" in summary
    assert "100%" in summary or "100/100" in summary  # Should have perfect efficiency


def test_stop_hook_circuit_breaker_triggered(temp_graph_dir):
    """Test Stop hook when circuit breaker is triggered (3+ violations)."""
    tracker = ViolationTracker(temp_graph_dir)
    tracker.set_session_id("breaker-session")

    # Record 3+ violations to trigger circuit breaker
    for i in range(4):
        tracker.record_violation(
            tool="Read",
            params={"file_path": f"/file{i}.py"},
            classification=MagicMock(
                predicted_cost=5000,
                optimal_cost=500,
                suggested_delegation="spawn_gemini()",
            ),
            predicted_waste=4500,
        )

    summarizer = CIGSSessionSummarizer(temp_graph_dir)
    result = summarizer.summarize("breaker-session")

    summary = result["hookSpecificOutput"]["additionalContext"]

    # Should show circuit breaker triggered
    assert "🚨 TRIGGERED" in summary or "Triggered" in summary
    # Should recommend operator level
    assert "OPERATOR" in summary.upper()


def test_stop_hook_compliance_history(temp_graph_dir):
    """Test that Stop hook retrieves compliance history correctly."""
    tracker = ViolationTracker(temp_graph_dir)

    # Create multiple sessions with varying compliance
    for i in range(5):
        session_id = f"session-{i}"
        tracker.set_session_id(session_id)

        # Record different numbers of violations
        for _ in range(i):  # 0, 1, 2, 3, 4 violations
            tracker.record_violation(
                tool="Read",
                params={"file_path": "/test.py"},
                classification=MagicMock(
                    predicted_cost=5000,
                    optimal_cost=500,
                    suggested_delegation="spawn_gemini()",
                ),
                predicted_waste=4500,
            )

    summarizer = CIGSSessionSummarizer(temp_graph_dir)
    compliance_history = summarizer._get_compliance_history()

    # Should have compliance rates for recent sessions
    assert len(compliance_history) > 0
    assert all(0.0 <= rate <= 1.0 for rate in compliance_history)


def test_stop_hook_format_patterns(temp_graph_dir):
    """Test pattern formatting in summary."""
    from htmlgraph.cigs.models import PatternRecord

    summarizer = CIGSSessionSummarizer(temp_graph_dir)

    patterns = [
        PatternRecord(
            id="pattern-1",
            pattern_type="anti-pattern",
            name="exploration_sequence",
            description="Multiple exploration tools in sequence",
            trigger_conditions=["3+ Read/Grep/Glob calls"],
            example_sequence=["Read", "Grep", "Read"],
            occurrence_count=2,
            correct_approach="Use spawn_gemini() for comprehensive exploration",
            delegation_suggestion="spawn_gemini(prompt='Search codebase')",
        )
    ]

    anti_patterns_text = summarizer._format_anti_patterns(patterns)

    assert "exploration_sequence" in anti_patterns_text
    assert "Multiple exploration tools" in anti_patterns_text
    assert "spawn_gemini()" in anti_patterns_text


def test_stop_hook_main_with_cigs_disabled(temp_graph_dir, monkeypatch, capsys):
    """Test main() function when CIGS is disabled."""
    from htmlgraph.hooks.session_summary import main

    # Mock stdin
    monkeypatch.setattr(
        "sys.stdin",
        MagicMock(
            read=lambda: json.dumps(
                {
                    "session_id": "test-session",
                    "cwd": str(temp_graph_dir.parent),
                }
            )
        ),
    )

    # Mock environment - CIGS disabled by default
    monkeypatch.setenv("HTMLGRAPH_CIGS_ENABLED", "0")

    main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    # Should return empty response when CIGS disabled
    assert output == {"continue": True}


def test_stop_hook_main_with_cigs_enabled(
    temp_graph_dir, monkeypatch, capsys, sample_violations
):
    """Test main() function when CIGS is enabled."""
    from htmlgraph.hooks.session_summary import main

    # Mock stdin
    input_data = {
        "session_id": "test-session-001",
        "cwd": str(temp_graph_dir.parent),
    }

    with patch("sys.stdin", MagicMock(read=lambda: json.dumps(input_data))):
        with patch("json.load", return_value=input_data):
            # Enable CIGS
            monkeypatch.setenv("HTMLGRAPH_CIGS_ENABLED", "1")

            main()

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            # Should return hook response with summary
            assert "hookSpecificOutput" in output
            assert output["hookSpecificOutput"]["hookEventName"] == "Stop"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
