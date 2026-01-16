"""
PatternDetector - Detects tool sequences, delegation chains, and error patterns.

This module provides comprehensive pattern detection for learning from agent behavior:
1. Tool sequence patterns - Common sequences of tool calls (Read → Edit → Run)
2. Delegation chains - Which agent types work well together
3. Error patterns - Common failure modes and their solutions
4. Context patterns - What context leads to successful outcomes

Usage:
    from htmlgraph.analytics.strategic import PatternDetector

    detector = PatternDetector(db_path)

    # Detect all patterns
    patterns = detector.detect_all_patterns()

    # Detect specific pattern types
    tool_patterns = detector.detect_tool_sequences(min_frequency=5)
    delegation_patterns = detector.detect_delegation_chains()
    error_patterns = detector.detect_error_patterns()
"""

import hashlib
import json
import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of patterns that can be detected."""

    TOOL_SEQUENCE = "tool_sequence"
    DELEGATION_CHAIN = "delegation_chain"
    ERROR_PATTERN = "error_pattern"
    CONTEXT_PATTERN = "context_pattern"


@dataclass
class Pattern:
    """
    Base pattern dataclass with frequency/confidence scoring.

    Attributes:
        pattern_id: Unique identifier (hash-based)
        pattern_type: Type of pattern (tool_sequence, delegation_chain, etc.)
        frequency: Number of times this pattern occurs
        confidence: Confidence score (0.0-1.0) based on frequency and success rate
        success_rate: Percentage of times pattern led to successful outcomes
        avg_duration_seconds: Average time taken for this pattern
        last_seen: When this pattern was last observed
        sessions: List of session IDs where pattern occurred
        metadata: Additional pattern-specific data
    """

    pattern_id: str
    pattern_type: PatternType
    frequency: int = 0
    confidence: float = 0.0
    success_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    last_seen: datetime | None = None
    sessions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert pattern to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "success_rate": self.success_rate,
            "avg_duration_seconds": self.avg_duration_seconds,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "sessions": self.sessions[:10],  # Limit for serialization
            "metadata": self.metadata,
        }

    def calculate_confidence(self) -> float:
        """
        Calculate confidence score based on frequency and success rate.

        Formula: confidence = (frequency_factor * 0.4) + (success_rate * 0.6)
        where frequency_factor = min(frequency / 20, 1.0)
        """
        frequency_factor = min(self.frequency / 20, 1.0)
        self.confidence = (frequency_factor * 0.4) + ((self.success_rate / 100) * 0.6)
        return self.confidence


@dataclass
class ToolSequencePattern(Pattern):
    """
    Pattern representing a sequence of tool calls.

    Example: ["Read", "Grep", "Edit", "Bash"]
    """

    sequence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Set pattern type."""
        self.pattern_type = PatternType.TOOL_SEQUENCE

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary including sequence."""
        data = super().to_dict()
        data["sequence"] = self.sequence
        return data

    @staticmethod
    def generate_id(sequence: list[str]) -> str:
        """Generate unique pattern ID from sequence."""
        seq_str = "->".join(sequence)
        hash_obj = hashlib.md5(seq_str.encode())
        return f"tsp-{hash_obj.hexdigest()[:8]}"


@dataclass
class DelegationChain(Pattern):
    """
    Pattern representing a delegation chain between agents.

    Tracks which subagent types work well together and their success rates.
    Example: orchestrator -> researcher -> coder -> tester
    """

    agents: list[str] = field(default_factory=list)
    delegation_types: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Set pattern type."""
        self.pattern_type = PatternType.DELEGATION_CHAIN

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary including agent chain."""
        data = super().to_dict()
        data["agents"] = self.agents
        data["delegation_types"] = self.delegation_types
        return data

    @staticmethod
    def generate_id(agents: list[str]) -> str:
        """Generate unique pattern ID from agent chain."""
        chain_str = "->".join(agents)
        hash_obj = hashlib.md5(chain_str.encode())
        return f"dcp-{hash_obj.hexdigest()[:8]}"


@dataclass
class ErrorPattern(Pattern):
    """
    Pattern representing common error scenarios.

    Tracks error types, their frequency, and successful resolution strategies.
    """

    error_type: str = ""
    error_message_pattern: str = ""
    tool_context: list[str] = field(default_factory=list)
    resolution_strategies: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Set pattern type."""
        self.pattern_type = PatternType.ERROR_PATTERN

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary including error details."""
        data = super().to_dict()
        data["error_type"] = self.error_type
        data["error_message_pattern"] = self.error_message_pattern
        data["tool_context"] = self.tool_context
        data["resolution_strategies"] = self.resolution_strategies
        return data

    @staticmethod
    def generate_id(error_type: str, message_pattern: str) -> str:
        """Generate unique pattern ID from error details."""
        err_str = f"{error_type}:{message_pattern}"
        hash_obj = hashlib.md5(err_str.encode())
        return f"erp-{hash_obj.hexdigest()[:8]}"


class PatternDetector:
    """
    Detects patterns from agent event history.

    Analyzes agent_events table to identify:
    1. Tool sequence patterns - Common tool call sequences
    2. Delegation chains - Agent collaboration patterns
    3. Error patterns - Common failure modes
    4. Context patterns - Conditions leading to success/failure
    """

    def __init__(self, db_path: Path | str | None = None):
        """
        Initialize pattern detector.

        Args:
            db_path: Path to HtmlGraph database. If None, uses default location.
        """
        if db_path is None:
            from htmlgraph.config import get_database_path

            db_path = get_database_path()

        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def detect_all_patterns(
        self,
        min_frequency: int = 3,
        days_back: int = 30,
    ) -> list[Pattern]:
        """
        Detect all pattern types from event history.

        Args:
            min_frequency: Minimum occurrences to be considered a pattern
            days_back: Number of days of history to analyze

        Returns:
            List of all detected patterns, sorted by confidence
        """
        patterns: list[Pattern] = []

        # Detect each pattern type
        patterns.extend(
            self.detect_tool_sequences(min_frequency=min_frequency, days_back=days_back)
        )
        patterns.extend(
            self.detect_delegation_chains(
                min_frequency=min_frequency, days_back=days_back
            )
        )
        patterns.extend(
            self.detect_error_patterns(min_frequency=min_frequency, days_back=days_back)
        )

        # Sort by confidence
        patterns.sort(key=lambda p: p.confidence, reverse=True)

        return patterns

    def detect_tool_sequences(
        self,
        window_size: int = 3,
        min_frequency: int = 3,
        days_back: int = 30,
    ) -> list[ToolSequencePattern]:
        """
        Detect common tool call sequence patterns.

        Uses sliding window approach to find frequently occurring sequences.

        Args:
            window_size: Number of consecutive tools in each sequence
            min_frequency: Minimum occurrences to be considered a pattern
            days_back: Number of days of history to analyze

        Returns:
            List of tool sequence patterns sorted by frequency
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Query tool calls ordered by timestamp, grouped by session
            cursor.execute(
                """
                SELECT tool_name, session_id, timestamp, status
                FROM agent_events
                WHERE event_type = 'tool_call'
                AND tool_name IS NOT NULL
                AND timestamp > datetime('now', ?)
                ORDER BY session_id, timestamp ASC
            """,
                (f"-{days_back} days",),
            )

            # Group by session and extract sequences
            session_tools: dict[str, list[tuple[str, datetime, str]]] = defaultdict(
                list
            )
            for row in cursor.fetchall():
                tool = row["tool_name"]
                sess_id = row["session_id"]
                timestamp = (
                    datetime.fromisoformat(row["timestamp"])
                    if isinstance(row["timestamp"], str)
                    else row["timestamp"]
                )
                status = row["status"] or "recorded"
                session_tools[sess_id].append((tool, timestamp, status))

            # Extract sliding windows and count frequencies
            sequence_data: dict[
                tuple[str, ...], list[tuple[str, datetime, list[str]]]
            ] = defaultdict(list)

            for sess_id, tools in session_tools.items():
                for i in range(len(tools) - window_size + 1):
                    window = tools[i : i + window_size]
                    sequence = tuple(t[0] for t in window)
                    timestamp = window[-1][1]
                    statuses = [t[2] for t in window]
                    sequence_data[sequence].append((sess_id, timestamp, statuses))

            # Build patterns from sequences meeting minimum frequency
            patterns: list[ToolSequencePattern] = []

            for seq_tuple, occurrences in sequence_data.items():
                if len(occurrences) >= min_frequency:
                    seq_list: list[str] = list(seq_tuple)
                    pattern_id = ToolSequencePattern.generate_id(seq_list)

                    # Calculate success rate (recorded status = success)
                    total = len(occurrences)
                    successes = sum(
                        1
                        for _, _, statuses in occurrences
                        if all(s == "recorded" for s in statuses)
                    )
                    success_rate = (successes / total) * 100 if total > 0 else 0.0

                    sessions = list(set(occ[0] for occ in occurrences))
                    last_seen = max(occ[1] for occ in occurrences)

                    pattern = ToolSequencePattern(
                        pattern_id=pattern_id,
                        pattern_type=PatternType.TOOL_SEQUENCE,
                        sequence=seq_list,
                        frequency=len(occurrences),
                        success_rate=success_rate,
                        last_seen=last_seen,
                        sessions=sessions,
                    )
                    pattern.calculate_confidence()
                    patterns.append(pattern)

            # Sort by frequency
            patterns.sort(key=lambda p: p.frequency, reverse=True)
            return patterns

        except sqlite3.Error as e:
            logger.error(f"Error detecting tool sequences: {e}")
            return []

    def detect_delegation_chains(
        self,
        min_frequency: int = 2,
        days_back: int = 30,
    ) -> list[DelegationChain]:
        """
        Detect common delegation chain patterns.

        Analyzes agent_collaboration table to find successful agent combinations.

        Args:
            min_frequency: Minimum occurrences to be considered a pattern
            days_back: Number of days of history to analyze

        Returns:
            List of delegation chain patterns sorted by frequency
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Query delegations ordered by timestamp
            cursor.execute(
                """
                SELECT from_agent, to_agent, handoff_type, status, session_id, timestamp
                FROM agent_collaboration
                WHERE handoff_type = 'delegation'
                AND timestamp > datetime('now', ?)
                ORDER BY session_id, timestamp ASC
            """,
                (f"-{days_back} days",),
            )

            # Group by session and build chains
            session_delegations: dict[
                str, list[tuple[str, str, str, str, datetime]]
            ] = defaultdict(list)
            for row in cursor.fetchall():
                sess_id = row["session_id"]
                timestamp = (
                    datetime.fromisoformat(row["timestamp"])
                    if isinstance(row["timestamp"], str)
                    else row["timestamp"]
                )
                session_delegations[sess_id].append(
                    (
                        row["from_agent"],
                        row["to_agent"],
                        row["handoff_type"],
                        row["status"] or "pending",
                        timestamp,
                    )
                )

            # Build chains from consecutive delegations
            chain_data: dict[tuple[str, ...], list[tuple[str, datetime, list[str]]]] = (
                defaultdict(list)
            )

            for sess_id, delegations in session_delegations.items():
                if len(delegations) < 2:
                    # Single delegation - create 2-agent chain
                    if delegations:
                        d = delegations[0]
                        chain = (d[0], d[1])
                        chain_data[chain].append((sess_id, d[4], [d[3]]))
                    continue

                # Build chains of 2-3 consecutive delegations
                for i in range(len(delegations) - 1):
                    # 2-agent chain
                    chain2 = (delegations[i][0], delegations[i][1])
                    statuses2 = [delegations[i][3]]
                    chain_data[chain2].append((sess_id, delegations[i][4], statuses2))

                    # 3-agent chain if possible
                    if i < len(delegations) - 1:
                        if delegations[i][1] == delegations[i + 1][0]:
                            chain3 = (
                                delegations[i][0],
                                delegations[i][1],
                                delegations[i + 1][1],
                            )
                            statuses3 = [delegations[i][3], delegations[i + 1][3]]
                            chain_data[chain3].append(
                                (sess_id, delegations[i + 1][4], statuses3)
                            )

            # Build patterns from chains meeting minimum frequency
            patterns: list[DelegationChain] = []

            for chain_tuple, occurrences in chain_data.items():
                if len(occurrences) >= min_frequency:
                    agents = list(chain_tuple)
                    pattern_id = DelegationChain.generate_id(agents)

                    # Calculate success rate (completed status = success)
                    total = len(occurrences)
                    successes = sum(
                        1
                        for _, _, statuses in occurrences
                        if all(s == "completed" for s in statuses)
                    )
                    success_rate = (successes / total) * 100 if total > 0 else 0.0

                    sessions = list(set(occ[0] for occ in occurrences))
                    last_seen = max(occ[1] for occ in occurrences)

                    pattern = DelegationChain(
                        pattern_id=pattern_id,
                        pattern_type=PatternType.DELEGATION_CHAIN,
                        agents=agents,
                        delegation_types=["delegation"] * (len(agents) - 1),
                        frequency=len(occurrences),
                        success_rate=success_rate,
                        last_seen=last_seen,
                        sessions=sessions,
                    )
                    pattern.calculate_confidence()
                    patterns.append(pattern)

            # Sort by frequency
            patterns.sort(key=lambda p: p.frequency, reverse=True)
            return patterns

        except sqlite3.Error as e:
            logger.error(f"Error detecting delegation chains: {e}")
            return []

    def detect_error_patterns(
        self,
        min_frequency: int = 2,
        days_back: int = 30,
    ) -> list[ErrorPattern]:
        """
        Detect common error patterns and their resolutions.

        Analyzes error events to identify failure modes and successful recovery strategies.

        Args:
            min_frequency: Minimum occurrences to be considered a pattern
            days_back: Number of days of history to analyze

        Returns:
            List of error patterns sorted by frequency
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Query error events with surrounding context
            cursor.execute(
                """
                SELECT
                    ae.event_id,
                    ae.session_id,
                    ae.tool_name,
                    ae.output_summary,
                    ae.timestamp,
                    (
                        SELECT GROUP_CONCAT(prev.tool_name, ',')
                        FROM agent_events prev
                        WHERE prev.session_id = ae.session_id
                        AND prev.timestamp < ae.timestamp
                        AND prev.event_type = 'tool_call'
                        ORDER BY prev.timestamp DESC
                        LIMIT 3
                    ) as prev_tools,
                    (
                        SELECT GROUP_CONCAT(next.tool_name, ',')
                        FROM agent_events next
                        WHERE next.session_id = ae.session_id
                        AND next.timestamp > ae.timestamp
                        AND next.event_type = 'tool_call'
                        ORDER BY next.timestamp ASC
                        LIMIT 3
                    ) as next_tools
                FROM agent_events ae
                WHERE ae.event_type = 'error'
                AND ae.timestamp > datetime('now', ?)
                ORDER BY ae.timestamp DESC
            """,
                (f"-{days_back} days",),
            )

            # Categorize errors by type and message pattern
            error_data: dict[
                tuple[str, str], list[tuple[str, datetime, list[str], list[str]]]
            ] = defaultdict(list)

            for row in cursor.fetchall():
                sess_id = row["session_id"]
                row["tool_name"] or "unknown"
                output = row["output_summary"] or ""
                timestamp = (
                    datetime.fromisoformat(row["timestamp"])
                    if isinstance(row["timestamp"], str)
                    else row["timestamp"]
                )

                # Extract error type from output
                error_type = self._categorize_error(output)
                message_pattern = self._extract_message_pattern(output)

                prev_tools = row["prev_tools"].split(",") if row["prev_tools"] else []
                next_tools = row["next_tools"].split(",") if row["next_tools"] else []

                key = (error_type, message_pattern)
                error_data[key].append((sess_id, timestamp, prev_tools, next_tools))

            # Build patterns from errors meeting minimum frequency
            patterns: list[ErrorPattern] = []

            for (error_type, message_pattern), occurrences in error_data.items():
                if len(occurrences) >= min_frequency:
                    pattern_id = ErrorPattern.generate_id(error_type, message_pattern)

                    # Collect tool context and resolution strategies
                    all_prev_tools: list[str] = []
                    all_next_tools: list[str] = []
                    for _, _, prev, next_t in occurrences:
                        all_prev_tools.extend(prev)
                        all_next_tools.extend(next_t)

                    # Most common tools before and after error
                    tool_context = list(set(all_prev_tools))[:5]
                    resolution_strategies = list(set(all_next_tools))[:5]

                    # Calculate success rate (has resolution = success)
                    total = len(occurrences)
                    successes = sum(1 for _, _, _, next_t in occurrences if next_t)
                    success_rate = (successes / total) * 100 if total > 0 else 0.0

                    sessions = list(set(occ[0] for occ in occurrences))
                    last_seen = max(occ[1] for occ in occurrences)

                    pattern = ErrorPattern(
                        pattern_id=pattern_id,
                        pattern_type=PatternType.ERROR_PATTERN,
                        error_type=error_type,
                        error_message_pattern=message_pattern,
                        tool_context=tool_context,
                        resolution_strategies=resolution_strategies,
                        frequency=len(occurrences),
                        success_rate=success_rate,
                        last_seen=last_seen,
                        sessions=sessions,
                    )
                    pattern.calculate_confidence()
                    patterns.append(pattern)

            # Sort by frequency
            patterns.sort(key=lambda p: p.frequency, reverse=True)
            return patterns

        except sqlite3.Error as e:
            logger.error(f"Error detecting error patterns: {e}")
            return []

    def _categorize_error(self, output: str) -> str:
        """
        Categorize error by type based on output content.

        Args:
            output: Error output/message

        Returns:
            Error type category
        """
        output_lower = output.lower()

        if "permission" in output_lower or "access denied" in output_lower:
            return "permission_error"
        if "not found" in output_lower or "no such file" in output_lower:
            return "not_found_error"
        if "syntax" in output_lower or "parse" in output_lower:
            return "syntax_error"
        if "timeout" in output_lower or "timed out" in output_lower:
            return "timeout_error"
        if "memory" in output_lower or "oom" in output_lower:
            return "memory_error"
        if "network" in output_lower or "connection" in output_lower:
            return "network_error"
        if "type" in output_lower and "error" in output_lower:
            return "type_error"
        if "import" in output_lower:
            return "import_error"
        if "test" in output_lower and (
            "fail" in output_lower or "error" in output_lower
        ):
            return "test_failure"

        return "general_error"

    def _extract_message_pattern(self, output: str) -> str:
        """
        Extract a generalized message pattern from error output.

        Removes specific file names, line numbers, etc. to create a matchable pattern.

        Args:
            output: Error output/message

        Returns:
            Generalized message pattern
        """
        import re

        # Limit length
        pattern = output[:200]

        # Remove line numbers
        pattern = re.sub(r"line \d+", "line N", pattern)

        # Remove file paths
        pattern = re.sub(r"[/\\][\w/\\.-]+\.\w+", "<file>", pattern)

        # Remove numbers (preserve error codes)
        pattern = re.sub(r"(?<!\w)\d+(?!\w)", "N", pattern)

        # Normalize whitespace
        pattern = " ".join(pattern.split())

        return pattern[:100]

    def get_pattern_by_id(self, pattern_id: str) -> Pattern | None:
        """
        Retrieve a stored pattern by ID.

        Args:
            pattern_id: Pattern ID to retrieve

        Returns:
            Pattern or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT * FROM delegation_patterns WHERE pattern_id = ?
            """,
                (pattern_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            # Reconstruct pattern from stored data
            pattern_type = PatternType(row["pattern_type"])
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}

            if pattern_type == PatternType.TOOL_SEQUENCE:
                return ToolSequencePattern(
                    pattern_id=row["pattern_id"],
                    pattern_type=pattern_type,
                    sequence=metadata.get("sequence", []),
                    frequency=row["frequency"],
                    confidence=row["confidence"],
                    success_rate=row["success_rate"],
                    avg_duration_seconds=row["avg_duration_seconds"] or 0.0,
                    last_seen=datetime.fromisoformat(row["last_seen"])
                    if row["last_seen"]
                    else None,
                    sessions=json.loads(row["sessions"]) if row["sessions"] else [],
                    metadata=metadata,
                )
            elif pattern_type == PatternType.DELEGATION_CHAIN:
                return DelegationChain(
                    pattern_id=row["pattern_id"],
                    pattern_type=pattern_type,
                    agents=metadata.get("agents", []),
                    delegation_types=metadata.get("delegation_types", []),
                    frequency=row["frequency"],
                    confidence=row["confidence"],
                    success_rate=row["success_rate"],
                    avg_duration_seconds=row["avg_duration_seconds"] or 0.0,
                    last_seen=datetime.fromisoformat(row["last_seen"])
                    if row["last_seen"]
                    else None,
                    sessions=json.loads(row["sessions"]) if row["sessions"] else [],
                    metadata=metadata,
                )
            elif pattern_type == PatternType.ERROR_PATTERN:
                return ErrorPattern(
                    pattern_id=row["pattern_id"],
                    pattern_type=pattern_type,
                    error_type=metadata.get("error_type", ""),
                    error_message_pattern=metadata.get("error_message_pattern", ""),
                    tool_context=metadata.get("tool_context", []),
                    resolution_strategies=metadata.get("resolution_strategies", []),
                    frequency=row["frequency"],
                    confidence=row["confidence"],
                    success_rate=row["success_rate"],
                    avg_duration_seconds=row["avg_duration_seconds"] or 0.0,
                    last_seen=datetime.fromisoformat(row["last_seen"])
                    if row["last_seen"]
                    else None,
                    sessions=json.loads(row["sessions"]) if row["sessions"] else [],
                    metadata=metadata,
                )
            else:
                return Pattern(
                    pattern_id=row["pattern_id"],
                    pattern_type=pattern_type,
                    frequency=row["frequency"],
                    confidence=row["confidence"],
                    success_rate=row["success_rate"],
                    avg_duration_seconds=row["avg_duration_seconds"] or 0.0,
                    last_seen=datetime.fromisoformat(row["last_seen"])
                    if row["last_seen"]
                    else None,
                    sessions=json.loads(row["sessions"]) if row["sessions"] else [],
                    metadata=metadata,
                )

        except sqlite3.Error as e:
            logger.error(f"Error retrieving pattern: {e}")
            return None

    def store_pattern(self, pattern: Pattern) -> bool:
        """
        Store or update a pattern in the database.

        Args:
            pattern: Pattern to store

        Returns:
            True if stored successfully, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Build metadata based on pattern type
            metadata = pattern.metadata.copy()

            if isinstance(pattern, ToolSequencePattern):
                metadata["sequence"] = pattern.sequence
            elif isinstance(pattern, DelegationChain):
                metadata["agents"] = pattern.agents
                metadata["delegation_types"] = pattern.delegation_types
            elif isinstance(pattern, ErrorPattern):
                metadata["error_type"] = pattern.error_type
                metadata["error_message_pattern"] = pattern.error_message_pattern
                metadata["tool_context"] = pattern.tool_context
                metadata["resolution_strategies"] = pattern.resolution_strategies

            cursor.execute(
                """
                INSERT OR REPLACE INTO delegation_patterns
                (pattern_id, pattern_type, frequency, confidence, success_rate,
                 avg_duration_seconds, last_seen, sessions, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
                (
                    pattern.pattern_id,
                    pattern.pattern_type.value,
                    pattern.frequency,
                    pattern.confidence,
                    pattern.success_rate,
                    pattern.avg_duration_seconds,
                    pattern.last_seen.isoformat() if pattern.last_seen else None,
                    json.dumps(pattern.sessions[:50]),  # Limit stored sessions
                    json.dumps(metadata),
                ),
            )

            conn.commit()
            return True

        except sqlite3.Error as e:
            logger.error(f"Error storing pattern: {e}")
            return False

    def score_pattern(self, pattern: Pattern) -> float:
        """
        Score a pattern for recommendation ranking.

        Score combines:
        - Confidence (40%)
        - Recency (30%) - More recent patterns score higher
        - User feedback (30%) - From preference manager

        Args:
            pattern: Pattern to score

        Returns:
            Score between 0.0 and 1.0
        """
        # Confidence component (40%)
        confidence_score = pattern.confidence * 0.4

        # Recency component (30%)
        recency_score = 0.0
        if pattern.last_seen:
            days_ago = (datetime.now() - pattern.last_seen).days
            recency_factor = max(0, 1 - (days_ago / 30))  # Decay over 30 days
            recency_score = recency_factor * 0.3

        # User feedback component (30%) - Placeholder, actual implementation in PreferenceManager
        feedback_score = 0.15  # Default neutral

        return confidence_score + recency_score + feedback_score
