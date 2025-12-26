"""
Transcript Analytics & Learning System.

Extracts patterns, metrics, and insights from Claude Code transcripts
to enable active learning, pattern recognition, and workflow improvements.

Key capabilities:
- Tool transition analysis (which tools follow which)
- Session health scoring (efficiency, retry rates, context rebuilds)
- Workflow pattern detection (common sequences, anti-patterns)
- Cross-session learning (compare and improve over time)
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from htmlgraph.transcript import TranscriptReader, TranscriptSession


@dataclass
class ToolTransition:
    """Represents a transition between two tools."""
    from_tool: str
    to_tool: str
    count: int = 1
    avg_time_between: float = 0.0  # seconds


@dataclass
class WorkflowPattern:
    """A detected workflow pattern."""
    sequence: list[str]
    count: int
    success_rate: float  # 0.0 to 1.0
    avg_duration: float  # seconds
    category: str = "neutral"  # "optimal", "neutral", "anti-pattern"


@dataclass
class SessionHealth:
    """Health metrics for a session."""
    session_id: str
    efficiency_score: float  # 0.0 to 1.0
    retry_rate: float  # proportion of retried operations
    context_rebuild_count: int  # times same files were re-read
    tool_diversity: float  # 0.0 to 1.0 (higher = more varied tools)
    prompt_clarity_score: float  # estimated from iterations needed
    error_recovery_rate: float  # successful recoveries / total errors
    duration_seconds: float
    tools_per_minute: float

    def overall_score(self) -> float:
        """Calculate overall health score."""
        weights = {
            'efficiency': 0.3,
            'low_retry': 0.2,
            'low_rebuilds': 0.15,
            'diversity': 0.1,
            'clarity': 0.15,
            'recovery': 0.1,
        }

        # Normalize rebuild count (lower is better, cap at 10)
        rebuild_score = max(0, 1 - (self.context_rebuild_count / 10))

        return (
            weights['efficiency'] * self.efficiency_score +
            weights['low_retry'] * (1 - self.retry_rate) +
            weights['low_rebuilds'] * rebuild_score +
            weights['diversity'] * self.tool_diversity +
            weights['clarity'] * self.prompt_clarity_score +
            weights['recovery'] * self.error_recovery_rate
        )


@dataclass
class TranscriptInsights:
    """Aggregated insights from transcript analysis."""
    total_sessions: int
    total_user_messages: int
    total_tool_calls: int

    # Tool analysis
    tool_frequency: dict[str, int] = field(default_factory=dict)
    tool_transitions: list[ToolTransition] = field(default_factory=list)

    # Patterns
    common_patterns: list[WorkflowPattern] = field(default_factory=list)
    anti_patterns: list[WorkflowPattern] = field(default_factory=list)

    # Health
    avg_session_health: float = 0.0
    health_trend: str = "stable"  # "improving", "stable", "declining"

    # Recommendations
    recommendations: list[str] = field(default_factory=list)


class TranscriptAnalytics:
    """
    Analytics engine for Claude Code transcripts.

    Extracts patterns, calculates metrics, and generates insights
    for continuous improvement of agent workflows.
    """

    # Known anti-patterns
    ANTI_PATTERNS = [
        (["Grep", "Grep", "Grep"], "Repeated search without reading results"),
        (["Read", "Read", "Read"], "Excessive file reading - consider caching"),
        (["Edit", "Edit", "Edit"], "Multiple edits - consider batching"),
        (["Bash", "Bash", "Bash", "Bash"], "Command loop - check for errors"),
    ]

    # Known optimal patterns
    OPTIMAL_PATTERNS = [
        (["Grep", "Read", "Edit"], "Search → Read → Edit flow"),
        (["Read", "Edit", "Bash"], "Read → Edit → Test flow"),
        (["Glob", "Read", "Edit", "Bash"], "Find → Read → Edit → Verify"),
    ]

    def __init__(self, graph_dir: Path | None = None):
        self.graph_dir = Path(graph_dir) if graph_dir else Path(".htmlgraph")
        self.reader = TranscriptReader()
        self._cache: dict[str, TranscriptSession] = {}

    def get_transcript(self, transcript_id: str) -> TranscriptSession | None:
        """Get transcript, with caching."""
        if transcript_id not in self._cache:
            transcript = self.reader.read_session(transcript_id)
            if transcript:
                self._cache[transcript_id] = transcript
        return self._cache.get(transcript_id)

    def get_tool_transitions(
        self,
        transcript_id: str | None = None,
        feature_id: str | None = None,
    ) -> dict[str, dict[str, int]]:
        """
        Calculate tool transition matrix.

        Returns dict of {from_tool: {to_tool: count}}
        """
        transitions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        transcripts = self._get_transcripts(transcript_id, feature_id)

        for transcript in transcripts:
            tools = [e.tool_name for e in transcript.entries if e.tool_name]

            for i in range(len(tools) - 1):
                from_tool = tools[i]
                to_tool = tools[i + 1]
                transitions[from_tool][to_tool] += 1

        # Convert to regular dict
        return {k: dict(v) for k, v in transitions.items()}

    def get_tool_frequency(
        self,
        transcript_id: str | None = None,
        feature_id: str | None = None,
    ) -> dict[str, int]:
        """Get frequency count for each tool."""
        frequency: Counter[str] = Counter()

        transcripts = self._get_transcripts(transcript_id, feature_id)

        for transcript in transcripts:
            for entry in transcript.entries:
                if entry.tool_name:
                    frequency[entry.tool_name] += 1

        return dict(frequency.most_common())

    def calculate_session_health(self, transcript_id: str) -> SessionHealth | None:
        """Calculate health metrics for a session."""
        transcript = self.get_transcript(transcript_id)
        if not transcript:
            return None

        entries = transcript.entries
        if not entries:
            return SessionHealth(
                session_id=transcript_id,
                efficiency_score=0.0,
                retry_rate=0.0,
                context_rebuild_count=0,
                tool_diversity=0.0,
                prompt_clarity_score=0.0,
                error_recovery_rate=0.0,
                duration_seconds=0.0,
                tools_per_minute=0.0,
            )

        # Calculate metrics
        tools = [e.tool_name for e in entries if e.tool_name]
        user_messages = [e for e in entries if e.entry_type == "user"]
        tool_results = [e for e in entries if e.entry_type == "tool_result"]

        # Duration
        if entries[0].timestamp and entries[-1].timestamp:
            duration = (entries[-1].timestamp - entries[0].timestamp).total_seconds()
        else:
            duration = 0.0

        # Efficiency: tools per user message (higher is better, capped)
        efficiency = min(1.0, len(tools) / max(1, len(user_messages) * 5))

        # Retry rate: consecutive same tools / total tools
        retries = sum(1 for i in range(1, len(tools)) if tools[i] == tools[i-1])
        retry_rate = retries / max(1, len(tools))

        # Context rebuilds: count of repeated Read on same file
        read_files: list[str] = []
        rebuilds = 0
        for e in entries:
            if e.tool_name == "Read" and e.tool_input:
                file_path = e.tool_input.get("file_path", "")
                if file_path in read_files:
                    rebuilds += 1
                else:
                    read_files.append(file_path)

        # Tool diversity
        unique_tools = len(set(tools))
        diversity = min(1.0, unique_tools / 10)  # Cap at 10 unique tools

        # Prompt clarity: fewer user messages per completion = clearer prompts
        clarity = min(1.0, 1 / max(1, len(user_messages) / 5))

        # Error recovery (simplified: assume tool_results with errors)
        # For now, estimate based on session completion
        recovery_rate = 0.8 if duration > 60 else 0.5

        # Tools per minute
        tools_per_min = len(tools) / max(1, duration / 60)

        return SessionHealth(
            session_id=transcript_id,
            efficiency_score=efficiency,
            retry_rate=retry_rate,
            context_rebuild_count=rebuilds,
            tool_diversity=diversity,
            prompt_clarity_score=clarity,
            error_recovery_rate=recovery_rate,
            duration_seconds=duration,
            tools_per_minute=tools_per_min,
        )

    def detect_patterns(
        self,
        transcript_id: str | None = None,
        min_length: int = 3,
        max_length: int = 5,
    ) -> list[WorkflowPattern]:
        """Detect workflow patterns in transcript(s)."""
        patterns: Counter[tuple[str, ...]] = Counter()

        transcripts = self._get_transcripts(transcript_id, None)

        for transcript in transcripts:
            tools = [e.tool_name for e in transcript.entries if e.tool_name]

            # Extract subsequences
            for length in range(min_length, min(max_length + 1, len(tools) + 1)):
                for i in range(len(tools) - length + 1):
                    seq = tuple(tools[i:i + length])
                    patterns[seq] += 1

        # Convert to WorkflowPattern objects
        result = []
        for seq, count in patterns.most_common(20):
            category = self._categorize_pattern(list(seq))
            result.append(WorkflowPattern(
                sequence=list(seq),
                count=count,
                success_rate=0.8 if category == "optimal" else 0.5,
                avg_duration=0.0,
                category=category,
            ))

        return result

    def detect_anti_patterns(
        self,
        transcript_id: str | None = None,
    ) -> list[tuple[WorkflowPattern, str]]:
        """Detect anti-patterns with explanations."""
        results = []
        transcripts = self._get_transcripts(transcript_id, None)

        for transcript in transcripts:
            tools = [e.tool_name for e in transcript.entries if e.tool_name]
            tools_str = ",".join(tools)

            for pattern, explanation in self.ANTI_PATTERNS:
                pattern_str = ",".join(pattern)
                count = tools_str.count(pattern_str)

                if count > 0:
                    results.append((
                        WorkflowPattern(
                            sequence=pattern,
                            count=count,
                            success_rate=0.3,
                            avg_duration=0.0,
                            category="anti-pattern",
                        ),
                        explanation,
                    ))

        return results

    def compare_sessions(
        self,
        session_ids: list[str],
    ) -> dict[str, Any]:
        """Compare multiple sessions."""
        healths = []
        for sid in session_ids:
            health = self.calculate_session_health(sid)
            if health:
                healths.append(health)

        if not healths:
            return {"error": "No valid sessions found"}

        # Find best/worst
        sorted_by_score = sorted(healths, key=lambda h: h.overall_score(), reverse=True)

        return {
            "sessions_compared": len(healths),
            "best_session": {
                "id": sorted_by_score[0].session_id,
                "score": sorted_by_score[0].overall_score(),
            },
            "worst_session": {
                "id": sorted_by_score[-1].session_id,
                "score": sorted_by_score[-1].overall_score(),
            },
            "avg_efficiency": sum(h.efficiency_score for h in healths) / len(healths),
            "avg_retry_rate": sum(h.retry_rate for h in healths) / len(healths),
            "total_context_rebuilds": sum(h.context_rebuild_count for h in healths),
        }

    def generate_recommendations(
        self,
        transcript_id: str | None = None,
    ) -> list[str]:
        """Generate workflow improvement recommendations."""
        recommendations = []

        # Analyze anti-patterns
        anti_patterns = self.detect_anti_patterns(transcript_id)
        for pattern, explanation in anti_patterns:
            if pattern.count >= 2:
                recommendations.append(
                    f"⚠️ Detected: {' → '.join(pattern.sequence)} ({pattern.count}x) - {explanation}"
                )

        # Analyze health if single session
        if transcript_id:
            health = self.calculate_session_health(transcript_id)
            if health:
                if health.retry_rate > 0.3:
                    recommendations.append(
                        "📊 High retry rate detected. Consider reading more context before acting."
                    )
                if health.context_rebuild_count > 5:
                    recommendations.append(
                        "🔄 Many context rebuilds. Consider keeping file content in memory."
                    )
                if health.tool_diversity < 0.3:
                    recommendations.append(
                        "🔧 Low tool diversity. Explore using more specialized tools."
                    )

        # Tool frequency analysis
        freq = self.get_tool_frequency(transcript_id)
        if freq:
            top_tool = max(freq, key=freq.get)
            if freq[top_tool] > 50:
                recommendations.append(
                    f"📈 Heavy use of {top_tool} ({freq[top_tool]}x). Consider if this is optimal."
                )

        if not recommendations:
            recommendations.append("✅ No major issues detected. Workflow looks healthy!")

        return recommendations

    def get_insights(
        self,
        transcript_ids: list[str] | None = None,
    ) -> TranscriptInsights:
        """Generate comprehensive insights from transcripts."""
        if transcript_ids:
            transcripts = [self.get_transcript(tid) for tid in transcript_ids]
            transcripts = [t for t in transcripts if t]
        else:
            transcripts = list(self._get_transcripts(None, None))

        if not transcripts:
            return TranscriptInsights(
                total_sessions=0,
                total_user_messages=0,
                total_tool_calls=0,
            )

        # Aggregate stats
        total_user = sum(
            len([e for e in t.entries if e.entry_type == "user"])
            for t in transcripts
        )
        total_tools = sum(
            len([e for e in t.entries if e.tool_name])
            for t in transcripts
        )

        # Get patterns and anti-patterns
        patterns = self.detect_patterns()
        optimal = [p for p in patterns if p.category == "optimal"]
        anti = [p for p in patterns if p.category == "anti-pattern"]

        # Calculate average health
        healths = []
        for t in transcripts:
            h = self.calculate_session_health(t.session_id)
            if h:
                healths.append(h.overall_score())

        avg_health = sum(healths) / len(healths) if healths else 0.0

        return TranscriptInsights(
            total_sessions=len(transcripts),
            total_user_messages=total_user,
            total_tool_calls=total_tools,
            tool_frequency=self.get_tool_frequency(),
            common_patterns=optimal[:5],
            anti_patterns=anti[:5],
            avg_session_health=avg_health,
            recommendations=self.generate_recommendations(),
        )

    def _get_transcripts(
        self,
        transcript_id: str | None,
        feature_id: str | None,
    ) -> list[TranscriptSession]:
        """Get transcripts to analyze."""
        if transcript_id:
            t = self.get_transcript(transcript_id)
            return [t] if t else []

        # Get all available transcripts
        transcripts = []
        for session in self.reader.list_sessions():
            t = self.get_transcript(session.session_id)
            if t:
                transcripts.append(t)

        return transcripts

    def _categorize_pattern(self, sequence: list[str]) -> str:
        """Categorize a pattern as optimal, anti-pattern, or neutral."""
        for pattern, _ in self.OPTIMAL_PATTERNS:
            if sequence == pattern:
                return "optimal"

        for pattern, _ in self.ANTI_PATTERNS:
            if sequence == pattern:
                return "anti-pattern"

        return "neutral"
