from __future__ import annotations

"""
Computational Reflection Module.

Pre-computes actionable context from session history for injection into
orchestrator prompts. Addresses the LLM limitation where models can only
effectively track 5-10 variables in working memory.

Design Principles:
1. COMPUTE, don't prompt - Do the synthesis work here, not in prompts
2. LIMIT to 5 items - Respect LLM working memory constraints
3. PRIORITIZE by recency and relevance - Most actionable items first
4. CONNECT the dots - Surface relationships the model would miss

Usage:
    from htmlgraph.reflection import ComputationalReflection

    reflection = ComputationalReflection(sdk)
    context = reflection.get_actionable_context()
    # Returns: {
    #     "summary": "3 blockers, 1 recent failure, avoid Read-Read-Read pattern",
    #     "items": [...],  # Max 5 items
    #     "injected_at": "2025-01-04T12:00:00"
    # }
"""


from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK


@dataclass
class ReflectionItem:
    """A single actionable reflection item."""

    category: str  # "blocker", "failure", "anti_pattern", "spike", "recommendation"
    priority: int  # 1-5, higher = more important
    title: str  # Brief title
    detail: str  # One-line actionable detail
    source_id: str | None = None  # ID of source item (feature, spike, etc.)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "detail": self.detail,
            "source_id": self.source_id,
        }


class ComputationalReflection:
    """
    Computes actionable context from HtmlGraph history.

    This class addresses the core problem: LLMs can retrieve data but
    struggle to synthesize insights from complex graph structures.
    We do the synthesis here and inject computed results.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> reflection = ComputationalReflection(sdk)
        >>> context = reflection.get_actionable_context()
        >>> print(context["summary"])
        "2 blockers | Avoid: Edit-Edit-Edit | Related: spk-abc123"
    """

    MAX_ITEMS = 5  # LLM working memory limit
    LOOKBACK_HOURS = 48  # How far back to look for patterns

    def __init__(self, sdk: SDK):
        self.sdk = sdk
        self._cache: dict[str, Any] = {}
        self._cache_time: datetime | None = None
        self._cache_ttl = timedelta(minutes=5)

    def get_actionable_context(
        self,
        current_feature_id: str | None = None,
        current_track: str | None = None,
    ) -> dict[str, Any]:
        """
        Get pre-computed actionable context for injection.

        This is the main entry point. Returns a structured dict
        suitable for injection into SessionStart or PreToolUse hooks.

        Args:
            current_feature_id: ID of feature being worked on (if any)
            current_track: Track name for filtering relevant history

        Returns:
            Dict with summary string and list of max 5 items
        """
        # Check cache
        if self._cache_time and datetime.now() - self._cache_time < self._cache_ttl:
            return self._cache

        items: list[ReflectionItem] = []

        # 1. Get blocking items (highest priority)
        items.extend(self._get_blockers(current_feature_id))

        # 2. Get recent failures
        items.extend(self._get_recent_failures(current_track))

        # 3. Get anti-patterns to avoid
        items.extend(self._get_anti_patterns())

        # 4. Get related spikes (investigations)
        items.extend(self._get_related_spikes(current_feature_id, current_track))

        # 5. Get strategic recommendations
        items.extend(self._get_recommendations())

        # Sort by priority (highest first) and limit to MAX_ITEMS
        items.sort(key=lambda x: x.priority, reverse=True)
        items = items[: self.MAX_ITEMS]

        # Build summary string
        summary = self._build_summary(items)

        result = {
            "summary": summary,
            "items": [item.to_dict() for item in items],
            "injected_at": datetime.now().isoformat(),
            "item_count": len(items),
        }

        # Cache result
        self._cache = result
        self._cache_time = datetime.now()

        return result

    def _get_blockers(self, feature_id: str | None) -> list[ReflectionItem]:
        """Get items blocking current work."""
        items = []

        try:
            # Use SDK's find_bottlenecks
            bottlenecks = self.sdk.find_bottlenecks(top_n=3)

            for bn in bottlenecks[:2]:  # Max 2 blockers
                items.append(
                    ReflectionItem(
                        category="blocker",
                        priority=5,  # Highest priority
                        title=f"Blocker: {bn.get('title', 'Unknown')[:40]}",
                        detail=f"Blocks {bn.get('blocks_count', 0)} items. Resolve first.",
                        source_id=bn.get("id"),
                    )
                )
        except Exception:
            pass

        # Also check for features marked as blocking
        try:
            blocked = self.sdk.features.where(status="blocked")
            for feat in blocked[:1]:  # Max 1 blocked feature
                items.append(
                    ReflectionItem(
                        category="blocker",
                        priority=4,
                        title=f"Blocked: {feat.title[:40]}",
                        detail="Feature is blocked. Check dependencies.",
                        source_id=feat.id,
                    )
                )
        except Exception:
            pass

        return items

    def _get_recent_failures(self, track: str | None) -> list[ReflectionItem]:
        """Get recent failures from session history."""
        items = []

        try:
            # Get recent sessions
            sessions = self.sdk.sessions.all()
            cutoff = datetime.now() - timedelta(hours=self.LOOKBACK_HOURS)

            recent_sessions = [
                s
                for s in sessions
                if hasattr(s, "started_at") and s.started_at and s.started_at > cutoff
            ]

            # Look for error patterns in session activity
            for session in recent_sessions[-3:]:  # Last 3 sessions
                if hasattr(session, "activity_log") and session.activity_log:
                    for activity in session.activity_log:
                        success = (
                            activity.success
                            if not isinstance(activity, dict)
                            else activity.get("success", True)
                        )
                        if not success:
                            tool = (
                                activity.tool
                                if not isinstance(activity, dict)
                                else activity.get("tool", "")
                            )
                            summary = (
                                activity.summary
                                if not isinstance(activity, dict)
                                else activity.get("summary", "")
                            )

                            items.append(
                                ReflectionItem(
                                    category="failure",
                                    priority=4,
                                    title=f"Recent failure: {tool}",
                                    detail=summary[:60]
                                    if summary
                                    else "Check session log",
                                    source_id=session.id,
                                )
                            )
                            break  # One failure per session max
        except Exception:
            pass

        return items[:2]  # Max 2 failures

    def _get_anti_patterns(self) -> list[ReflectionItem]:
        """Get anti-patterns to avoid from recent sessions."""
        items = []

        try:
            # Import learning module for pattern analysis
            from htmlgraph.learning import LearningPersistence

            learning = LearningPersistence(self.sdk)

            # Get active session for analysis
            active_sessions = [
                s for s in self.sdk.sessions.all() if s.status == "active"
            ]

            if active_sessions:
                # Analyze most recent active session
                session = active_sessions[-1]
                analysis = learning.analyze_for_orchestrator(session.id)

                # Extract anti-patterns
                for pattern in analysis.get("anti_patterns", [])[:1]:
                    seq = pattern.get("sequence", [])
                    desc = pattern.get("description", "")
                    items.append(
                        ReflectionItem(
                            category="anti_pattern",
                            priority=3,
                            title=f"Avoid: {' → '.join(seq)}",
                            detail=desc[:60]
                            if desc
                            else "Detected inefficient pattern",
                            source_id=session.id,
                        )
                    )
        except Exception:
            pass

        return items[:1]  # Max 1 anti-pattern

    def _get_related_spikes(
        self, feature_id: str | None, track: str | None
    ) -> list[ReflectionItem]:
        """Get related investigation spikes."""
        items = []

        try:
            spikes = self.sdk.spikes.all()

            # Find spikes with findings that might be relevant
            relevant_spikes = []

            for spike in spikes:
                # Check if spike has findings
                if not hasattr(spike, "findings") or not spike.findings:
                    continue

                # Check if spike is related to current feature
                if feature_id and hasattr(spike, "edges") and spike.edges:
                    for edge_type, edges in spike.edges.items():
                        for edge in edges:
                            if edge.target_id == feature_id:
                                relevant_spikes.append((spike, 5))  # High relevance
                                break

                # Check if spike mentions the track
                if track and track.lower() in (spike.title or "").lower():
                    relevant_spikes.append((spike, 3))  # Medium relevance

                # Check for recent completed spikes with findings
                if spike.status == "done" and spike.findings:
                    if hasattr(spike, "updated") and spike.updated:
                        cutoff = datetime.now() - timedelta(hours=24)
                        if spike.updated > cutoff:
                            relevant_spikes.append((spike, 2))  # Lower relevance

            # Sort by relevance and take top
            relevant_spikes.sort(key=lambda x: x[1], reverse=True)

            for spike, relevance in relevant_spikes[:1]:
                findings_preview = spike.findings[:60] if spike.findings else ""
                items.append(
                    ReflectionItem(
                        category="spike",
                        priority=2,
                        title=f"Related: {spike.title[:35]}",
                        detail=findings_preview or "See spike for details",
                        source_id=spike.id,
                    )
                )
        except Exception:
            pass

        return items[:1]  # Max 1 spike

    def _get_recommendations(self) -> list[ReflectionItem]:
        """Get strategic recommendations."""
        items = []

        try:
            recs = self.sdk.recommend_next_work(agent_count=1)

            if recs and len(recs) > 0:
                rec = recs[0]
                reasons = rec.get("reasons", [])
                reason_str = reasons[0] if reasons else "Recommended next"

                items.append(
                    ReflectionItem(
                        category="recommendation",
                        priority=2,
                        title=f"Next: {rec.get('title', 'Unknown')[:35]}",
                        detail=reason_str[:60],
                        source_id=rec.get("id"),
                    )
                )
        except Exception:
            pass

        return items[:1]  # Max 1 recommendation

    def _build_summary(self, items: list[ReflectionItem]) -> str:
        """Build a one-line summary from items."""
        if not items:
            return "No actionable context found."

        parts = []

        # Count by category
        blockers = [i for i in items if i.category == "blocker"]
        failures = [i for i in items if i.category == "failure"]
        anti_patterns = [i for i in items if i.category == "anti_pattern"]
        spikes = [i for i in items if i.category == "spike"]

        if blockers:
            parts.append(f"{len(blockers)} blocker{'s' if len(blockers) > 1 else ''}")

        if failures:
            parts.append(
                f"{len(failures)} recent failure{'s' if len(failures) > 1 else ''}"
            )

        if anti_patterns:
            pattern = anti_patterns[0]
            parts.append(f"Avoid: {pattern.title.replace('Avoid: ', '')}")

        if spikes:
            spike = spikes[0]
            parts.append(f"See: {spike.source_id}")

        return " | ".join(parts) if parts else "Session context loaded."

    def format_for_injection(self, context: dict[str, Any] | None = None) -> str:
        """
        Format context for injection into hooks.

        Returns a markdown-formatted string suitable for additionalContext.
        """
        if context is None:
            context = self.get_actionable_context()

        if not context.get("items"):
            return ""

        lines = ["## Computed Reflections", ""]
        lines.append(f"**Summary:** {context.get('summary', 'N/A')}")
        lines.append("")

        for item in context.get("items", []):
            icon = {
                "blocker": "🚫",
                "failure": "❌",
                "anti_pattern": "⚠️",
                "spike": "🔍",
                "recommendation": "💡",
            }.get(item.get("category", ""), "•")

            lines.append(f"{icon} **{item.get('title', 'Unknown')}**")
            lines.append(f"   {item.get('detail', '')}")
            if item.get("source_id"):
                lines.append(f"   _Source: {item.get('source_id')}_")
            lines.append("")

        lines.append("---")
        lines.append("")

        return "\n".join(lines)


def get_reflection_context(
    sdk: SDK,
    feature_id: str | None = None,
    track: str | None = None,
) -> str:
    """
    Convenience function to get formatted reflection context.

    This is the main entry point for hooks.

    Args:
        sdk: HtmlGraph SDK instance
        feature_id: Current feature ID (optional)
        track: Current track name (optional)

    Returns:
        Formatted string for injection into hook context
    """
    reflection = ComputationalReflection(sdk)
    context = reflection.get_actionable_context(feature_id, track)
    return reflection.format_for_injection(context)
