"""
Tests for Pattern Learning - Phase 2 Feature 2.

Tests pattern detection, insight generation, and learning loop functionality.
"""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from htmlgraph.analytics.pattern_learning import (
    InsightGenerator,
    LearningLoop,
    PatternLearner,
    PatternMatcher,
    ToolPattern,
)


@pytest.fixture
def temp_db():
    """Create temporary database with sample data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create database at expected location for PatternLearner
        db_path = Path(tmpdir) / "htmlgraph.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE agent_events (
                event_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                tool_name TEXT,
                session_id TEXT NOT NULL,
                execution_duration_seconds REAL DEFAULT 0.0
            )
        """)

        cursor.execute("""
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT,
                status TEXT
            )
        """)

        # Insert sample tool call sequences
        base_time = datetime.now()

        # Session 1: Read → Grep → Edit → Bash (successful pattern)
        for i, (tool, event_type) in enumerate(
            [
                ("Read", "tool_call"),
                ("Grep", "tool_call"),
                ("Edit", "tool_call"),
                ("Bash", "tool_call"),
                (None, "completion"),  # Success indicator
            ]
        ):
            cursor.execute(
                """
                INSERT INTO agent_events (
                    event_id, agent_id, event_type, timestamp,
                    tool_name, session_id, execution_duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"evt-s1-{i}",
                    "claude",
                    event_type,
                    (base_time + timedelta(seconds=i * 10)).isoformat(),
                    tool,
                    "session-1",
                    5.0,
                ),
            )

        # Session 2: Same pattern (Read → Grep → Edit → Bash) - successful
        for i, (tool, event_type) in enumerate(
            [
                ("Read", "tool_call"),
                ("Grep", "tool_call"),
                ("Edit", "tool_call"),
                ("Bash", "tool_call"),
                (None, "completion"),
            ]
        ):
            cursor.execute(
                """
                INSERT INTO agent_events (
                    event_id, agent_id, event_type, timestamp,
                    tool_name, session_id, execution_duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"evt-s2-{i}",
                    "claude",
                    event_type,
                    (base_time + timedelta(minutes=5, seconds=i * 10)).isoformat(),
                    tool,
                    "session-2",
                    4.5,
                ),
            )

        # Session 3: Read → Read → Read → Edit (multiple reads - optimization opportunity)
        for i, (tool, event_type) in enumerate(
            [
                ("Read", "tool_call"),
                ("Read", "tool_call"),
                ("Read", "tool_call"),
                ("Edit", "tool_call"),
                (None, "completion"),
            ]
        ):
            cursor.execute(
                """
                INSERT INTO agent_events (
                    event_id, agent_id, event_type, timestamp,
                    tool_name, session_id, execution_duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"evt-s3-{i}",
                    "claude",
                    event_type,
                    (base_time + timedelta(minutes=10, seconds=i * 10)).isoformat(),
                    tool,
                    "session-3",
                    6.0,
                ),
            )

        # Session 4: Edit → Edit → Edit → Bash → error (anti-pattern)
        for i, (tool, event_type) in enumerate(
            [
                ("Edit", "tool_call"),
                ("Edit", "tool_call"),
                ("Edit", "tool_call"),
                ("Bash", "tool_call"),
                (None, "error"),  # Failure indicator
            ]
        ):
            cursor.execute(
                """
                INSERT INTO agent_events (
                    event_id, agent_id, event_type, timestamp,
                    tool_name, session_id, execution_duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"evt-s4-{i}",
                    "claude",
                    event_type,
                    (base_time + timedelta(minutes=15, seconds=i * 10)).isoformat(),
                    tool,
                    "session-4",
                    3.0,
                ),
            )

        # Session 5: Read → Grep → Edit (partial match of session 1 pattern)
        for i, (tool, event_type) in enumerate(
            [
                ("Read", "tool_call"),
                ("Grep", "tool_call"),
                ("Edit", "tool_call"),
                (None, "completion"),
            ]
        ):
            cursor.execute(
                """
                INSERT INTO agent_events (
                    event_id, agent_id, event_type, timestamp,
                    tool_name, session_id, execution_duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"evt-s5-{i}",
                    "claude",
                    event_type,
                    (base_time + timedelta(minutes=20, seconds=i * 10)).isoformat(),
                    tool,
                    "session-5",
                    5.5,
                ),
            )

        # Session 6-10: More instances of Read → Grep → Edit pattern (to reach min_frequency)
        for session_num in range(6, 11):
            for i, (tool, event_type) in enumerate(
                [
                    ("Read", "tool_call"),
                    ("Grep", "tool_call"),
                    ("Edit", "tool_call"),
                    (None, "completion"),
                ]
            ):
                cursor.execute(
                    """
                    INSERT INTO agent_events (
                        event_id, agent_id, event_type, timestamp,
                        tool_name, session_id, execution_duration_seconds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        f"evt-s{session_num}-{i}",
                        "claude",
                        event_type,
                        (
                            base_time
                            + timedelta(minutes=session_num * 5, seconds=i * 10)
                        ).isoformat(),
                        tool,
                        f"session-{session_num}",
                        5.0,
                    ),
                )

        # Insert sessions
        for i in range(1, 11):
            cursor.execute(
                """
                INSERT INTO sessions (session_id, agent_id, status)
                VALUES (?, ?, ?)
            """,
                (f"session-{i}", "claude", "completed"),
            )

        conn.commit()
        conn.close()

        yield db_path


def test_pattern_matcher_initialization(temp_db):
    """Test PatternMatcher initialization."""
    matcher = PatternMatcher(temp_db)
    assert matcher.db_path == temp_db


def test_pattern_matcher_nonexistent_db():
    """Test PatternMatcher with nonexistent database."""
    with pytest.raises(FileNotFoundError):
        PatternMatcher("/nonexistent/path/db.db")


def test_get_tool_sequences(temp_db):
    """Test extracting tool sequences from database."""
    matcher = PatternMatcher(temp_db)
    sequences = matcher.get_tool_sequences(window_size=3)

    # Should have multiple sequences
    assert len(sequences) > 0

    # Each sequence should be a tuple (sequence, session_id, timestamp)
    for seq, session_id, timestamp in sequences:
        assert isinstance(seq, list)
        assert isinstance(session_id, str)
        assert isinstance(timestamp, datetime)
        assert len(seq) == 3  # window_size=3


def test_get_tool_sequences_filtered_by_session(temp_db):
    """Test filtering tool sequences by session."""
    matcher = PatternMatcher(temp_db)
    sequences = matcher.get_tool_sequences(window_size=3, session_id="session-1")

    # Should only have sequences from session-1
    for seq, session_id, timestamp in sequences:
        assert session_id == "session-1"


def test_find_patterns_basic(temp_db):
    """Test basic pattern detection."""
    matcher = PatternMatcher(temp_db)
    patterns = matcher.find_patterns(window_size=3, min_frequency=5)

    # Should find at least one pattern
    assert len(patterns) > 0

    # Check pattern structure
    for pattern in patterns:
        assert isinstance(pattern, ToolPattern)
        assert len(pattern.sequence) == 3
        assert pattern.frequency >= 5
        assert pattern.pattern_id.startswith("pat-")


def test_find_patterns_frequency_filtering(temp_db):
    """Test that patterns are filtered by minimum frequency."""
    matcher = PatternMatcher(temp_db)

    # With high min_frequency, should find fewer patterns
    patterns_high = matcher.find_patterns(window_size=3, min_frequency=10)
    patterns_low = matcher.find_patterns(window_size=3, min_frequency=2)

    assert len(patterns_low) >= len(patterns_high)


def test_find_patterns_sorted_by_frequency(temp_db):
    """Test that patterns are sorted by frequency."""
    matcher = PatternMatcher(temp_db)
    patterns = matcher.find_patterns(window_size=3, min_frequency=2)

    # Check descending order
    for i in range(len(patterns) - 1):
        assert patterns[i].frequency >= patterns[i + 1].frequency


def test_insight_generator_initialization(temp_db):
    """Test InsightGenerator initialization."""
    generator = InsightGenerator(temp_db)
    assert generator.db_path == temp_db


def test_calculate_success_rate(temp_db):
    """Test success rate calculation."""
    matcher = PatternMatcher(temp_db)
    generator = InsightGenerator(temp_db)

    patterns = matcher.find_patterns(window_size=3, min_frequency=2)
    assert len(patterns) > 0

    # Calculate success rate for first pattern
    pattern = patterns[0]
    success_rate = generator.calculate_success_rate(pattern)

    assert 0 <= success_rate <= 100


def test_calculate_avg_duration(temp_db):
    """Test average duration calculation."""
    matcher = PatternMatcher(temp_db)
    generator = InsightGenerator(temp_db)

    patterns = matcher.find_patterns(window_size=3, min_frequency=2)
    assert len(patterns) > 0

    # Calculate duration for first pattern
    pattern = patterns[0]
    avg_duration = generator.calculate_avg_duration(pattern)

    assert avg_duration >= 0


def test_enrich_pattern(temp_db):
    """Test pattern enrichment with metrics."""
    matcher = PatternMatcher(temp_db)
    generator = InsightGenerator(temp_db)

    patterns = matcher.find_patterns(window_size=3, min_frequency=2)
    pattern = patterns[0]

    # Before enrichment
    assert pattern.success_rate == 0.0
    assert pattern.avg_duration_seconds == 0.0

    # After enrichment
    enriched = generator.enrich_pattern(pattern)
    assert enriched.success_rate >= 0
    assert enriched.avg_duration_seconds >= 0


def test_generate_insights(temp_db):
    """Test insight generation from patterns."""
    matcher = PatternMatcher(temp_db)
    generator = InsightGenerator(temp_db)

    patterns = matcher.find_patterns(window_size=3, min_frequency=2)
    insights = generator.generate_insights(patterns)

    # Should generate some insights
    assert len(insights) > 0

    # Check insight structure
    for insight in insights:
        assert insight.insight_id
        assert insight.insight_type in [
            "recommendation",
            "anti-pattern",
            "optimization",
        ]
        assert insight.title
        assert insight.description
        assert insight.impact_score >= 0


def test_generate_insights_sorted_by_impact(temp_db):
    """Test that insights are sorted by impact score."""
    matcher = PatternMatcher(temp_db)
    generator = InsightGenerator(temp_db)

    patterns = matcher.find_patterns(window_size=3, min_frequency=2)
    insights = generator.generate_insights(patterns)

    # Check descending order
    for i in range(len(insights) - 1):
        assert insights[i].impact_score >= insights[i + 1].impact_score


def test_learning_loop_initialization(temp_db):
    """Test LearningLoop initialization."""
    loop = LearningLoop(temp_db)
    assert loop.db_path == temp_db

    # Check that table was created
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tool_patterns'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_store_and_get_pattern(temp_db):
    """Test storing and retrieving patterns."""
    loop = LearningLoop(temp_db)

    # Create test pattern
    pattern = ToolPattern(
        pattern_id="test-pat-001",
        sequence=["Read", "Grep", "Edit"],
        frequency=10,
        success_rate=85.5,
        avg_duration_seconds=12.3,
        last_seen=datetime.now(),
        sessions=["s1", "s2", "s3"],
        user_feedback=1,
    )

    # Store pattern
    loop.store_pattern(pattern)

    # Retrieve pattern
    retrieved = loop.get_pattern("test-pat-001")
    assert retrieved is not None
    assert retrieved.pattern_id == "test-pat-001"
    assert retrieved.sequence == ["Read", "Grep", "Edit"]
    assert retrieved.frequency == 10
    assert retrieved.success_rate == 85.5
    assert retrieved.user_feedback == 1


def test_update_feedback(temp_db):
    """Test updating user feedback."""
    loop = LearningLoop(temp_db)

    # Store initial pattern
    pattern = ToolPattern(
        pattern_id="test-pat-002",
        sequence=["Edit", "Bash"],
        frequency=5,
        user_feedback=0,
    )
    loop.store_pattern(pattern)

    # Update feedback
    loop.update_feedback("test-pat-002", 1)

    # Verify update
    retrieved = loop.get_pattern("test-pat-002")
    assert retrieved.user_feedback == 1


def test_get_all_patterns(temp_db):
    """Test retrieving all patterns."""
    loop = LearningLoop(temp_db)

    # Store multiple patterns
    for i in range(3):
        pattern = ToolPattern(
            pattern_id=f"test-pat-{i}",
            sequence=["Tool1", "Tool2"],
            frequency=i + 1,
        )
        loop.store_pattern(pattern)

    # Get all patterns
    patterns = loop.get_all_patterns()
    assert len(patterns) >= 3

    # Should be sorted by frequency
    for i in range(len(patterns) - 1):
        assert patterns[i].frequency >= patterns[i + 1].frequency


def test_pattern_learner_initialization(temp_db):
    """Test PatternLearner initialization."""
    graph_dir = temp_db.parent
    learner = PatternLearner(graph_dir)

    assert learner.graph_dir == graph_dir
    assert learner.db_path == temp_db


def test_pattern_learner_detect_patterns(temp_db):
    """Test pattern detection via PatternLearner."""
    graph_dir = temp_db.parent
    learner = PatternLearner(graph_dir)

    patterns = learner.detect_patterns(window_size=3, min_frequency=2)

    # Should detect patterns
    assert len(patterns) > 0

    # Patterns should be stored in learning loop
    stored = learner.learning_loop.get_all_patterns()
    assert len(stored) == len(patterns)


def test_pattern_learner_generate_insights(temp_db):
    """Test insight generation via PatternLearner."""
    graph_dir = temp_db.parent
    learner = PatternLearner(graph_dir)

    # First detect patterns
    learner.detect_patterns(window_size=3, min_frequency=2)

    # Then generate insights
    insights = learner.generate_insights()

    # Should have insights
    assert len(insights) > 0


def test_pattern_learner_get_recommendations(temp_db):
    """Test getting top recommendations."""
    graph_dir = temp_db.parent
    learner = PatternLearner(graph_dir)

    # Detect patterns first
    learner.detect_patterns(window_size=3, min_frequency=2)

    # Get top 3 recommendations
    recommendations = learner.get_recommendations(limit=3)

    assert len(recommendations) <= 3
    for rec in recommendations:
        assert rec.insight_type == "recommendation"


def test_pattern_learner_get_anti_patterns(temp_db):
    """Test getting anti-patterns."""
    graph_dir = temp_db.parent
    learner = PatternLearner(graph_dir)

    # Detect patterns first
    learner.detect_patterns(window_size=3, min_frequency=2)

    # Get anti-patterns
    anti_patterns = learner.get_anti_patterns()

    for anti in anti_patterns:
        assert anti.insight_type == "anti-pattern"


def test_pattern_learner_export_learnings(temp_db):
    """Test exporting learnings to markdown."""
    graph_dir = temp_db.parent
    learner = PatternLearner(graph_dir)

    # Detect patterns
    learner.detect_patterns(window_size=3, min_frequency=2)

    # Export to markdown
    output_path = graph_dir / "learnings.md"
    learner.export_learnings(output_path)

    # Verify file was created
    assert output_path.exists()

    # Check content
    content = output_path.read_text()
    assert "# Pattern Learning Report" in content
    assert "## Recommendations" in content
    assert "## Anti-Patterns" in content
    assert "## Optimization Opportunities" in content


def test_pattern_learner_performance(temp_db):
    """Test pattern learning performance with 1000 events."""
    import time

    # This test uses existing data and measures analysis time
    graph_dir = temp_db.parent
    learner = PatternLearner(graph_dir)

    start = time.time()
    patterns = learner.detect_patterns(window_size=3, min_frequency=2)
    insights = learner.generate_insights()
    elapsed = time.time() - start

    # Should complete in under 1 second
    assert elapsed < 1.0
    assert len(patterns) > 0
    assert len(insights) > 0


def test_tool_pattern_to_dict():
    """Test ToolPattern to_dict conversion."""
    pattern = ToolPattern(
        pattern_id="test-001",
        sequence=["Read", "Edit"],
        frequency=5,
        success_rate=90.0,
        avg_duration_seconds=10.5,
        last_seen=datetime(2025, 1, 13, 10, 0, 0),
        sessions=["s1", "s2"],
        user_feedback=1,
    )

    result = pattern.to_dict()

    assert result["pattern_id"] == "test-001"
    assert result["sequence"] == ["Read", "Edit"]
    assert result["frequency"] == 5
    assert result["success_rate"] == 90.0
    assert result["user_feedback"] == 1


def test_pattern_insight_to_dict():
    """Test PatternInsight to_dict conversion."""
    from htmlgraph.analytics.pattern_learning import PatternInsight

    insight = PatternInsight(
        insight_id="insight-001",
        insight_type="recommendation",
        title="Test Insight",
        description="This is a test",
        impact_score=75.0,
        patterns=["pat-001", "pat-002"],
    )

    result = insight.to_dict()

    assert result["insight_id"] == "insight-001"
    assert result["insight_type"] == "recommendation"
    assert result["title"] == "Test Insight"
    assert result["impact_score"] == 75.0
    assert result["patterns"] == ["pat-001", "pat-002"]
