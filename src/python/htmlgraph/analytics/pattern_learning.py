"""
Pattern Learning from Agent Behavior - Phase 2 Feature 2.

Analyzes tool call sequences to identify patterns, anti-patterns, and optimization
opportunities. Provides actionable recommendations based on historical behavior.

Key Components:
1. PatternMatcher - Identifies sequences of tool types from event history
2. InsightGenerator - Converts patterns to actionable recommendations
3. LearningLoop - Stores patterns and refines based on user feedback

Usage:
    from htmlgraph.analytics.pattern_learning import PatternLearner

    learner = PatternLearner()
    patterns = learner.detect_patterns(min_frequency=5)
    insights = learner.generate_insights()
    recommendations = learner.get_recommendations()
"""

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ToolPattern:
    """
    Represents a detected tool call sequence pattern.

    Attributes:
        pattern_id: Unique identifier for the pattern
        sequence: List of tool names in order (e.g., ["Read", "Grep", "Edit"])
        frequency: Number of times this pattern occurs
        success_rate: Percentage of times pattern led to successful outcomes
        avg_duration_seconds: Average time taken for this pattern
        last_seen: When this pattern was last observed
        sessions: List of session IDs where pattern occurred
        user_feedback: User feedback score (1=helpful, 0=neutral, -1=unhelpful)
    """

    pattern_id: str
    sequence: list[str]
    frequency: int = 0
    success_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    last_seen: datetime | None = None
    sessions: list[str] = field(default_factory=list)
    user_feedback: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert pattern to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "sequence": self.sequence,
            "frequency": self.frequency,
            "success_rate": self.success_rate,
            "avg_duration_seconds": self.avg_duration_seconds,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "sessions": self.sessions,
            "user_feedback": self.user_feedback,
        }


@dataclass
class PatternInsight:
    """
    Actionable insight generated from pattern analysis.

    Attributes:
        insight_id: Unique identifier
        insight_type: Type of insight (recommendation, anti-pattern, optimization)
        title: Human-readable title
        description: Detailed explanation
        impact_score: Estimated impact (0-100)
        patterns: Related pattern IDs
    """

    insight_id: str
    insight_type: str  # "recommendation", "anti-pattern", "optimization"
    title: str
    description: str
    impact_score: float
    patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert insight to dictionary."""
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
            "title": self.title,
            "description": self.description,
            "impact_score": self.impact_score,
            "patterns": self.patterns,
        }


class PatternMatcher:
    """
    Identifies sequences of tool types from event history.

    Uses sliding window approach to find common tool call patterns.
    """

    def __init__(self, db_path: Path | str):
        """
        Initialize pattern matcher.

        Args:
            db_path: Path to HtmlGraph database
        """
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_tool_sequences(
        self, window_size: int = 3, session_id: str | None = None
    ) -> list[tuple[list[str], str, datetime]]:
        """
        Extract tool call sequences from database.

        Args:
            window_size: Number of consecutive tools in each sequence
            session_id: Optional session ID to filter by

        Returns:
            List of (sequence, session_id, timestamp) tuples
        """
        conn = self._get_connection()
        try:
            # Query tool calls ordered by timestamp
            query = """
                SELECT tool_name, session_id, timestamp
                FROM agent_events
                WHERE event_type = 'tool_call'
                AND tool_name IS NOT NULL
            """

            params: tuple[Any, ...] = ()
            if session_id:
                query += " AND session_id = ?"
                params = (session_id,)

            query += " ORDER BY timestamp ASC"

            cursor = conn.cursor()
            cursor.execute(query, params)

            # Group by session and extract sequences
            session_tools: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
            for row in cursor.fetchall():
                tool = row["tool_name"]
                sess_id = row["session_id"]
                timestamp = (
                    datetime.fromisoformat(row["timestamp"])
                    if isinstance(row["timestamp"], str)
                    else row["timestamp"]
                )
                session_tools[sess_id].append((tool, timestamp))

            # Extract sliding windows
            sequences = []
            for sess_id, tools in session_tools.items():
                for i in range(len(tools) - window_size + 1):
                    sequence = [t[0] for t in tools[i : i + window_size]]
                    timestamp = tools[i + window_size - 1][
                        1
                    ]  # Use last tool's timestamp
                    sequences.append((sequence, sess_id, timestamp))

            return sequences
        finally:
            conn.close()

    def find_patterns(
        self, window_size: int = 3, min_frequency: int = 5
    ) -> list[ToolPattern]:
        """
        Identify common tool call patterns.

        Args:
            window_size: Size of tool sequence window (default: 3)
            min_frequency: Minimum occurrences to be considered a pattern

        Returns:
            List of detected patterns sorted by frequency
        """
        sequences = self.get_tool_sequences(window_size=window_size)

        # Count sequence frequencies
        sequence_data: dict[tuple[str, ...], list[tuple[str, datetime]]] = defaultdict(
            list
        )
        for seq, sess_id, timestamp in sequences:
            sequence_data[tuple(seq)].append((sess_id, timestamp))

        # Filter by minimum frequency
        patterns = []
        for seq_tuple, occurrences in sequence_data.items():
            if len(occurrences) >= min_frequency:
                sequence = list(seq_tuple)
                pattern_id = self._generate_pattern_id(sequence)

                sessions = [occ[0] for occ in occurrences]
                last_seen = max(occ[1] for occ in occurrences)

                pattern = ToolPattern(
                    pattern_id=pattern_id,
                    sequence=sequence,
                    frequency=len(occurrences),
                    last_seen=last_seen,
                    sessions=sessions,
                )
                patterns.append(pattern)

        # Sort by frequency descending
        patterns.sort(key=lambda p: p.frequency, reverse=True)
        return patterns

    def _generate_pattern_id(self, sequence: list[str]) -> str:
        """Generate unique pattern ID from sequence."""
        seq_str = "->".join(sequence)
        # Simple hash-based ID
        import hashlib

        hash_obj = hashlib.md5(seq_str.encode())
        return f"pat-{hash_obj.hexdigest()[:8]}"


class InsightGenerator:
    """
    Converts patterns to actionable recommendations.

    Analyzes pattern success rates, costs, and contexts to generate
    insights about workflow optimization.
    """

    def __init__(self, db_path: Path | str):
        """
        Initialize insight generator.

        Args:
            db_path: Path to HtmlGraph database
        """
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def calculate_success_rate(self, pattern: ToolPattern) -> float:
        """
        Calculate success rate for a pattern.

        Success defined as: pattern followed by passing tests or completion,
        not followed by error/failure events.

        Args:
            pattern: Pattern to analyze

        Returns:
            Success rate as percentage (0-100)
        """
        if not pattern.sessions:
            return 0.0

        conn = self._get_connection()
        try:
            successes = 0
            for session_id in set(pattern.sessions):
                # Check if session has more successes than failures
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        SUM(CASE WHEN event_type = 'completion' THEN 1 ELSE 0 END) as completions,
                        SUM(CASE WHEN event_type = 'error' THEN 1 ELSE 0 END) as errors
                    FROM agent_events
                    WHERE session_id = ?
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()

                completions = row["completions"] or 0
                errors = row["errors"] or 0

                # Session is successful if completions > errors
                if completions > errors:
                    successes += 1

            return (successes / len(set(pattern.sessions))) * 100
        finally:
            conn.close()

    def calculate_avg_duration(self, pattern: ToolPattern) -> float:
        """
        Calculate average duration for pattern execution.

        Args:
            pattern: Pattern to analyze

        Returns:
            Average duration in seconds
        """
        if not pattern.sessions:
            return 0.0

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT AVG(execution_duration_seconds) as avg_duration
                FROM agent_events
                WHERE session_id IN ({})
                AND execution_duration_seconds > 0
                """.format(",".join("?" * len(set(pattern.sessions)))),
                tuple(set(pattern.sessions)),
            )
            row = cursor.fetchone()
            return row["avg_duration"] or 0.0
        finally:
            conn.close()

    def enrich_pattern(self, pattern: ToolPattern) -> ToolPattern:
        """
        Enrich pattern with success rate and duration data.

        Args:
            pattern: Pattern to enrich

        Returns:
            Enriched pattern with calculated metrics
        """
        pattern.success_rate = self.calculate_success_rate(pattern)
        pattern.avg_duration_seconds = self.calculate_avg_duration(pattern)
        return pattern

    def generate_insights(self, patterns: list[ToolPattern]) -> list[PatternInsight]:
        """
        Generate actionable insights from patterns.

        Args:
            patterns: List of detected patterns

        Returns:
            List of insights with recommendations
        """
        insights = []

        # Enrich patterns with metrics
        enriched = [self.enrich_pattern(p) for p in patterns]

        # Find high-success patterns (recommendations)
        for pattern in enriched:
            if pattern.success_rate >= 80 and pattern.frequency >= 5:
                insight = PatternInsight(
                    insight_id=f"insight-{pattern.pattern_id}",
                    insight_type="recommendation",
                    title=f"High Success Pattern: {' → '.join(pattern.sequence)}",
                    description=(
                        f"This pattern has a {pattern.success_rate:.1f}% success rate "
                        f"across {pattern.frequency} occurrences. "
                        f"Consider using this workflow for similar tasks."
                    ),
                    impact_score=pattern.success_rate * (pattern.frequency / 10),
                    patterns=[pattern.pattern_id],
                )
                insights.append(insight)

        # Find low-success patterns (anti-patterns)
        for pattern in enriched:
            if pattern.success_rate < 50 and pattern.frequency >= 5:
                insight = PatternInsight(
                    insight_id=f"anti-{pattern.pattern_id}",
                    insight_type="anti-pattern",
                    title=f"Low Success Pattern: {' → '.join(pattern.sequence)}",
                    description=(
                        f"This pattern has only a {pattern.success_rate:.1f}% success rate "
                        f"across {pattern.frequency} occurrences. "
                        f"Consider alternative approaches."
                    ),
                    impact_score=100 - pattern.success_rate,
                    patterns=[pattern.pattern_id],
                )
                insights.append(insight)

        # Find repeated Read patterns (optimization opportunity)
        for pattern in enriched:
            if pattern.sequence.count("Read") >= 2:
                insight = PatternInsight(
                    insight_id=f"opt-{pattern.pattern_id}",
                    insight_type="optimization",
                    title="Multiple Read Operations Detected",
                    description=(
                        f"Pattern '{' → '.join(pattern.sequence)}' contains "
                        f"{pattern.sequence.count('Read')} Read operations. "
                        f"Consider delegating exploration to a subagent to reduce context usage."
                    ),
                    impact_score=pattern.frequency * 10,
                    patterns=[pattern.pattern_id],
                )
                insights.append(insight)

        # Sort by impact score
        insights.sort(key=lambda i: i.impact_score, reverse=True)
        return insights


class LearningLoop:
    """
    Stores patterns and refines recommendations based on user feedback.

    Maintains a persistent store of patterns and their effectiveness,
    allowing the system to improve recommendations over time.
    """

    def __init__(self, db_path: Path | str):
        """
        Initialize learning loop.

        Args:
            db_path: Path to HtmlGraph database
        """
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")

        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        """Create tool_patterns table if it doesn't exist."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    tool_sequence TEXT NOT NULL,
                    frequency INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    avg_duration_seconds REAL DEFAULT 0.0,
                    last_seen TIMESTAMP,
                    sessions TEXT,
                    user_feedback INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def store_pattern(self, pattern: ToolPattern) -> None:
        """
        Store or update a pattern in the database.

        Args:
            pattern: Pattern to store
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO tool_patterns (
                    pattern_id,
                    tool_sequence,
                    frequency,
                    success_rate,
                    avg_duration_seconds,
                    last_seen,
                    sessions,
                    user_feedback,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    pattern.pattern_id,
                    "->".join(pattern.sequence),
                    pattern.frequency,
                    pattern.success_rate,
                    pattern.avg_duration_seconds,
                    pattern.last_seen.isoformat() if pattern.last_seen else None,
                    json.dumps(pattern.sessions),
                    pattern.user_feedback,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_pattern(self, pattern_id: str) -> ToolPattern | None:
        """
        Retrieve a pattern by ID.

        Args:
            pattern_id: Pattern ID to retrieve

        Returns:
            Pattern or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tool_patterns WHERE pattern_id = ?", (pattern_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return ToolPattern(
                pattern_id=row["pattern_id"],
                sequence=row["tool_sequence"].split("->"),
                frequency=row["frequency"],
                success_rate=row["success_rate"],
                avg_duration_seconds=row["avg_duration_seconds"],
                last_seen=datetime.fromisoformat(row["last_seen"])
                if row["last_seen"]
                else None,
                sessions=json.loads(row["sessions"]) if row["sessions"] else [],
                user_feedback=row["user_feedback"],
            )
        finally:
            conn.close()

    def update_feedback(self, pattern_id: str, feedback: int) -> None:
        """
        Update user feedback for a pattern.

        Args:
            pattern_id: Pattern ID
            feedback: Feedback score (1=helpful, 0=neutral, -1=unhelpful)
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE tool_patterns
                SET user_feedback = ?, updated_at = ?
                WHERE pattern_id = ?
            """,
                (feedback, datetime.now().isoformat(), pattern_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_patterns(self) -> list[ToolPattern]:
        """
        Get all stored patterns.

        Returns:
            List of all patterns
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tool_patterns ORDER BY frequency DESC")

            patterns = []
            for row in cursor.fetchall():
                pattern = ToolPattern(
                    pattern_id=row["pattern_id"],
                    sequence=row["tool_sequence"].split("->"),
                    frequency=row["frequency"],
                    success_rate=row["success_rate"],
                    avg_duration_seconds=row["avg_duration_seconds"],
                    last_seen=datetime.fromisoformat(row["last_seen"])
                    if row["last_seen"]
                    else None,
                    sessions=json.loads(row["sessions"]) if row["sessions"] else [],
                    user_feedback=row["user_feedback"],
                )
                patterns.append(pattern)

            return patterns
        finally:
            conn.close()


class PatternLearner:
    """
    Main interface for pattern learning.

    Combines pattern detection, insight generation, and learning loop
    into a single API for AI agents.

    Example:
        >>> learner = PatternLearner()
        >>> patterns = learner.detect_patterns(min_frequency=5)
        >>> insights = learner.generate_insights()
        >>> recommendations = learner.get_recommendations()
    """

    def __init__(self, graph_dir: Path | None = None):
        """
        Initialize pattern learner.

        Args:
            graph_dir: Root directory for HtmlGraph (defaults to .htmlgraph)
        """
        if graph_dir is None:
            graph_dir = Path.cwd() / ".htmlgraph"

        self.graph_dir = Path(graph_dir)
        self.db_path = self.graph_dir / "htmlgraph.db"

        # Lazy initialization - only initialize components if database exists
        # This prevents failures in tests with temporary directories
        self._matcher: PatternMatcher | None = None
        self._insight_generator: InsightGenerator | None = None
        self._learning_loop: LearningLoop | None = None

    @property
    def matcher(self) -> PatternMatcher:
        """Lazily initialize matcher."""
        if self._matcher is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Database not found at {self.db_path}")
            self._matcher = PatternMatcher(self.db_path)
        return self._matcher

    @property
    def insight_generator(self) -> InsightGenerator:
        """Lazily initialize insight generator."""
        if self._insight_generator is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Database not found at {self.db_path}")
            self._insight_generator = InsightGenerator(self.db_path)
        return self._insight_generator

    @property
    def learning_loop(self) -> LearningLoop:
        """Lazily initialize learning loop."""
        if self._learning_loop is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Database not found at {self.db_path}")
            self._learning_loop = LearningLoop(self.db_path)
        return self._learning_loop

    def detect_patterns(
        self, window_size: int = 3, min_frequency: int = 5
    ) -> list[ToolPattern]:
        """
        Detect tool call patterns from event history.

        Args:
            window_size: Size of tool sequence window (default: 3)
            min_frequency: Minimum occurrences to be considered a pattern

        Returns:
            List of detected patterns
        """
        patterns = self.matcher.find_patterns(
            window_size=window_size, min_frequency=min_frequency
        )

        # Store patterns in learning loop
        for pattern in patterns:
            enriched = self.insight_generator.enrich_pattern(pattern)
            self.learning_loop.store_pattern(enriched)

        return patterns

    def generate_insights(self) -> list[PatternInsight]:
        """
        Generate insights from detected patterns.

        Returns:
            List of actionable insights
        """
        patterns = self.learning_loop.get_all_patterns()
        return self.insight_generator.generate_insights(patterns)

    def get_recommendations(self, limit: int = 3) -> list[PatternInsight]:
        """
        Get top recommendations based on impact.

        Args:
            limit: Maximum number of recommendations (default: 3)

        Returns:
            Top recommendations sorted by impact
        """
        insights = self.generate_insights()
        recommendations = [i for i in insights if i.insight_type == "recommendation"]
        return recommendations[:limit]

    def get_anti_patterns(self) -> list[PatternInsight]:
        """
        Get detected anti-patterns.

        Returns:
            List of anti-pattern insights
        """
        insights = self.generate_insights()
        return [i for i in insights if i.insight_type == "anti-pattern"]

    def export_learnings(self, output_path: Path | str) -> None:
        """
        Export learnings to markdown for team sharing.

        Args:
            output_path: Path to output markdown file
        """
        insights = self.generate_insights()
        patterns = self.learning_loop.get_all_patterns()

        output_path = Path(output_path)

        with open(output_path, "w") as f:
            f.write("# Pattern Learning Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            f.write("## Recommendations\n\n")
            recommendations = [
                i for i in insights if i.insight_type == "recommendation"
            ]
            for insight in recommendations[:5]:
                f.write(f"### {insight.title}\n\n")
                f.write(f"{insight.description}\n\n")
                f.write(f"**Impact Score**: {insight.impact_score:.1f}\n\n")

            f.write("## Anti-Patterns\n\n")
            anti_patterns = [i for i in insights if i.insight_type == "anti-pattern"]
            for insight in anti_patterns[:5]:
                f.write(f"### {insight.title}\n\n")
                f.write(f"{insight.description}\n\n")
                f.write(f"**Impact Score**: {insight.impact_score:.1f}\n\n")

            f.write("## Optimization Opportunities\n\n")
            optimizations = [i for i in insights if i.insight_type == "optimization"]
            for insight in optimizations[:5]:
                f.write(f"### {insight.title}\n\n")
                f.write(f"{insight.description}\n\n")
                f.write(f"**Impact Score**: {insight.impact_score:.1f}\n\n")

            f.write("## All Detected Patterns\n\n")
            for pattern in patterns[:20]:
                f.write(f"- **{' → '.join(pattern.sequence)}** ")
                f.write(f"(frequency: {pattern.frequency}, ")
                f.write(f"success: {pattern.success_rate:.1f}%)\n")
