"""
Active Learning Persistence Module.

Bridges TranscriptAnalytics to the HtmlGraph for persistent learning.
Analyzes sessions and persists patterns, insights, and metrics to the graph.
"""
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from collections import Counter

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK


class LearningPersistence:
    """Persists analytics insights to the HtmlGraph.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> learning = LearningPersistence(sdk)
        >>> learning.persist_session_insight("sess-123")
        >>> learning.persist_patterns()
    """

    def __init__(self, sdk: "SDK"):
        self.sdk = sdk

    def persist_session_insight(self, session_id: str) -> str | None:
        """Analyze a session and persist insight to graph.

        Args:
            session_id: Session to analyze

        Returns:
            Insight ID if created, None if session not found
        """
        session = self.sdk.sessions.get(session_id)
        if not session:
            return None

        # Calculate health metrics from activity log
        health = self._calculate_health(session)

        # Create insight
        insight = self.sdk.insights.create(f"Session Analysis: {session_id}") \
            .for_session(session_id) \
            .set_health_scores(
                efficiency=health.get("efficiency", 0.0),
                retry_rate=health.get("retry_rate", 0.0),
                context_rebuilds=health.get("context_rebuilds", 0),
                tool_diversity=health.get("tool_diversity", 0.0),
                error_recovery=health.get("error_recovery", 0.0),
            ) \
            .save()

        # Add issues
        for issue in health.get("issues", []):
            insight.issues_detected.append(issue)

        # Add recommendations
        for rec in health.get("recommendations", []):
            insight.recommendations.append(rec)

        # Update insight
        if health.get("issues") or health.get("recommendations"):
            self.sdk.insights.update(insight)

        return insight.id

    def _calculate_health(self, session) -> dict:
        """Calculate health metrics from session activity log."""
        health = {
            "efficiency": 0.8,  # Default reasonable value
            "retry_rate": 0.0,
            "context_rebuilds": 0,
            "tool_diversity": 0.5,
            "error_recovery": 1.0,
            "issues": [],
            "recommendations": [],
        }

        if not hasattr(session, 'activity_log') or not session.activity_log:
            return health

        activities = session.activity_log
        total = len(activities)

        if total == 0:
            return health

        # Count tool usage
        tools = [a.tool if hasattr(a, 'tool') else a.get('tool', '') for a in activities]
        tool_counts = Counter(tools)
        unique_tools = len(tool_counts)

        # Tool diversity (0-1, normalized by 10 expected tools)
        health["tool_diversity"] = min(unique_tools / 10.0, 1.0)

        # Detect retries (same tool twice in a row)
        retries = sum(1 for i in range(1, len(tools)) if tools[i] == tools[i-1])
        health["retry_rate"] = retries / total if total > 0 else 0.0

        # Detect context rebuilds (Read same file multiple times)
        reads = [a for a in activities if (hasattr(a, 'tool') and a.tool == 'Read') or (isinstance(a, dict) and a.get('tool') == 'Read')]
        if reads:
            read_targets = [str(getattr(r, 'summary', '') if hasattr(r, 'summary') else r.get('summary', '')) for r in reads]
            rebuild_count = len(read_targets) - len(set(read_targets))
            health["context_rebuilds"] = rebuild_count

        # Calculate efficiency (inverse of wasted operations)
        wasted = retries + health["context_rebuilds"]
        health["efficiency"] = max(0.0, 1.0 - (wasted / total))

        # Generate issues
        if health["retry_rate"] > 0.2:
            health["issues"].append(f"High retry rate: {health['retry_rate']:.0%}")
            health["recommendations"].append("Consider reading more context before acting")

        if health["context_rebuilds"] > 2:
            health["issues"].append(f"Excessive context rebuilds: {health['context_rebuilds']}")
            health["recommendations"].append("Cache file contents or take notes")

        if health["tool_diversity"] < 0.3:
            health["issues"].append("Low tool diversity")
            health["recommendations"].append("Consider using more specialized tools")

        return health

    def persist_patterns(self, min_count: int = 2) -> list[str]:
        """Detect and persist workflow patterns from sessions.

        Args:
            min_count: Minimum occurrences to persist a pattern

        Returns:
            List of persisted pattern IDs
        """
        # Collect tool sequences from all sessions
        sequences = []
        for session in self.sdk.sessions.all():
            if hasattr(session, 'activity_log') and session.activity_log:
                tools = [
                    a.tool if hasattr(a, 'tool') else a.get('tool', '')
                    for a in session.activity_log
                ]
                # Extract 3-tool sequences
                for i in range(len(tools) - 2):
                    seq = tools[i:i+3]
                    if all(seq):  # No empty tools
                        sequences.append(tuple(seq))

        # Count sequences
        seq_counts = Counter(sequences)

        # Persist patterns with min_count
        pattern_ids = []
        for seq, count in seq_counts.items():
            if count >= min_count:
                # Check if pattern already exists
                existing = self.sdk.patterns.find_by_sequence(list(seq))
                if existing:
                    # Update count
                    pattern = existing[0]
                    pattern.detection_count = count
                    pattern.last_detected = datetime.now()
                    self.sdk.patterns.update(pattern)
                    pattern_ids.append(pattern.id)
                else:
                    # Create new pattern
                    pattern_type = self._classify_pattern(list(seq))
                    pattern = self.sdk.patterns.create(f"Pattern: {' -> '.join(seq)}") \
                        .set_sequence(list(seq)) \
                        .set_pattern_type(pattern_type) \
                        .save()
                    pattern.detection_count = count
                    pattern.first_detected = datetime.now()
                    pattern.last_detected = datetime.now()
                    self.sdk.patterns.update(pattern)
                    pattern_ids.append(pattern.id)

        return pattern_ids

    def _classify_pattern(self, sequence: list[str]) -> str:
        """Classify a pattern as optimal, anti-pattern, or neutral."""
        seq = tuple(sequence)

        # Known optimal patterns
        optimal = [
            ("Read", "Edit", "Bash"),  # Read, modify, test
            ("Grep", "Read", "Edit"),  # Search, understand, modify
            ("Glob", "Read", "Edit"),  # Find, understand, modify
        ]

        # Known anti-patterns
        anti = [
            ("Edit", "Edit", "Edit"),  # Too many edits without testing
            ("Bash", "Bash", "Bash"),  # Command spam
            ("Read", "Read", "Read"),  # Excessive reading without action
        ]

        if seq in optimal:
            return "optimal"
        elif seq in anti:
            return "anti-pattern"
        else:
            return "neutral"

    def persist_metrics(self, period: str = "weekly") -> str | None:
        """Aggregate and persist metrics for the current period.

        Args:
            period: "daily", "weekly", or "monthly"

        Returns:
            Metric ID if created
        """
        from datetime import timedelta

        now = datetime.now()

        # Calculate period boundaries
        if period == "daily":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif period == "weekly":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        else:  # monthly
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)

        # Collect insights for this period
        insights = list(self.sdk.insights.all())
        period_insights = [
            i for i in insights
            if hasattr(i, 'analyzed_at') and i.analyzed_at
            and start <= i.analyzed_at <= end
        ]

        if not period_insights:
            # Use all insights if none in period
            period_insights = insights

        if not period_insights:
            return None

        # Calculate aggregate metrics
        efficiency_scores = [
            getattr(i, 'efficiency_score', 0.0)
            for i in period_insights
            if getattr(i, 'efficiency_score', None)
        ]
        avg_efficiency = sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0.0

        # Create metric
        metric = self.sdk.metrics.create(f"Efficiency Metric: {period} ending {end.strftime('%Y-%m-%d')}") \
            .set_scope("session") \
            .set_period(period, start, end) \
            .set_metrics({
                "avg_efficiency": avg_efficiency,
                "sessions_analyzed": len(period_insights),
            }) \
            .save()

        # Note: After save(), metric is a Node object
        # The sessions_in_period is tracked in metric_values
        metric.properties = metric.properties or {}
        metric.properties["data_points_count"] = len(period_insights)
        metric.properties["sessions_in_period"] = [
            getattr(i, 'session_id', i.id) for i in period_insights
            if hasattr(i, 'session_id') or hasattr(i, 'id')
        ]
        self.sdk.metrics.update(metric)

        return metric.id


def auto_persist_on_session_end(sdk: "SDK", session_id: str) -> dict:
    """Convenience function to auto-persist learning data when session ends.

    Returns:
        Dict with insight_id, pattern_ids, metric_id
    """
    learning = LearningPersistence(sdk)

    result = {
        "insight_id": learning.persist_session_insight(session_id),
        "pattern_ids": learning.persist_patterns(),
        "metric_id": learning.persist_metrics(),
    }

    return result
