from __future__ import annotations

"""
Context Analytics for HtmlGraph

Provides hierarchical context usage tracking and analytics:
  Activity → Session → Feature → Track

Enables drill-down analysis of where context was consumed.
"""


from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK


@dataclass
class ContextUsage:
    """Aggregated context usage at any level of the hierarchy."""

    tokens_used: int = 0
    peak_tokens: int = 0
    cost_usd: float = 0.0
    output_tokens: int = 0

    # Breakdown by child entities
    by_feature: dict[str, int] = field(default_factory=dict)
    by_session: dict[str, int] = field(default_factory=dict)
    by_tool: dict[str, int] = field(default_factory=dict)

    # Metadata
    entity_type: str = ""  # "track", "feature", "session", "activity"
    entity_id: str = ""
    entity_title: str = ""

    def add_child(self, child_id: str, child_usage: ContextUsage) -> None:
        """Add a child's usage to this aggregate."""
        self.tokens_used += child_usage.tokens_used
        self.peak_tokens = max(self.peak_tokens, child_usage.peak_tokens)
        self.cost_usd += child_usage.cost_usd
        self.output_tokens += child_usage.output_tokens

        # Track by child entity
        if child_usage.entity_type == "feature":
            self.by_feature[child_id] = child_usage.tokens_used
        elif child_usage.entity_type == "session":
            self.by_session[child_id] = child_usage.tokens_used

        # Merge tool breakdown
        for tool, count in child_usage.by_tool.items():
            self.by_tool[tool] = self.by_tool.get(tool, 0) + count

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_title": self.entity_title,
            "tokens_used": self.tokens_used,
            "peak_tokens": self.peak_tokens,
            "cost_usd": self.cost_usd,
            "output_tokens": self.output_tokens,
            "by_feature": self.by_feature,
            "by_session": self.by_session,
            "by_tool": self.by_tool,
        }


class ContextAnalytics:
    """
    Hierarchical context usage analytics.

    Provides drill-down from Track → Feature → Session → Activity.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> ctx = ContextAnalytics(sdk)
        >>>
        >>> # Get track-level usage
        >>> track_usage = ctx.get_track_usage("track-auth")
        >>> print(f"Total: {track_usage.tokens_used:,} tokens")
        >>>
        >>> # Drill down to features
        >>> for feat_id, tokens in track_usage.by_feature.items():
        ...     print(f"  {feat_id}: {tokens:,}")
        >>>
        >>> # Get detailed feature breakdown
        >>> feat_usage = ctx.get_feature_usage("feat-login")
        >>> print(f"Peak: {feat_usage.peak_tokens:,}")
    """

    def __init__(self, sdk: SDK):
        """Initialize with SDK reference."""
        self._sdk = sdk

    def get_session_usage(self, session_id: str) -> ContextUsage:
        """
        Get context usage for a specific session.

        Args:
            session_id: Session ID to analyze

        Returns:
            ContextUsage with session-level metrics
        """
        session = self._sdk.session_manager.get_session(session_id)
        if not session:
            return ContextUsage(entity_type="session", entity_id=session_id)

        usage = ContextUsage(
            entity_type="session",
            entity_id=session.id,
            entity_title=session.title,
            tokens_used=0,
            peak_tokens=session.peak_context_tokens,
            cost_usd=session.total_cost_usd,
            output_tokens=session.total_tokens_generated,
        )

        # Aggregate from context snapshots
        for snapshot in session.context_snapshots:
            usage.tokens_used = max(usage.tokens_used, snapshot.current_tokens)
            if snapshot.feature_id:
                prev = usage.by_feature.get(snapshot.feature_id, 0)
                usage.by_feature[snapshot.feature_id] = max(
                    prev, snapshot.current_tokens
                )

        # Also use context_by_feature from session
        for feat_id, tokens in session.context_by_feature.items():
            usage.by_feature[feat_id] = max(usage.by_feature.get(feat_id, 0), tokens)

        # Get tool breakdown from activity log
        for activity in session.activity_log:
            usage.by_tool[activity.tool] = usage.by_tool.get(activity.tool, 0) + 1

        return usage

    def get_feature_usage(self, feature_id: str) -> ContextUsage:
        """
        Get context usage for a specific feature.

        Aggregates from all sessions that worked on this feature.

        Args:
            feature_id: Feature ID to analyze

        Returns:
            ContextUsage with feature-level metrics
        """
        feature = self._sdk.features.get(feature_id)
        if not feature:
            return ContextUsage(entity_type="feature", entity_id=feature_id)

        usage = ContextUsage(
            entity_type="feature",
            entity_id=feature.id,
            entity_title=feature.title,
            tokens_used=feature.context_tokens_used,
            peak_tokens=feature.context_peak_tokens,
            cost_usd=feature.context_cost_usd,
        )

        # Get usage from each session that worked on this feature
        for session_id in feature.context_sessions:
            session_usage = self.get_session_usage(session_id)
            usage.by_session[session_id] = session_usage.tokens_used

            # Merge tool breakdown
            for tool, count in session_usage.by_tool.items():
                usage.by_tool[tool] = usage.by_tool.get(tool, 0) + count

        return usage

    def get_track_usage(self, track_id: str) -> ContextUsage:
        """
        Get context usage for a track (aggregate of all features).

        Args:
            track_id: Track ID to analyze

        Returns:
            ContextUsage with track-level metrics
        """
        # Get all features in this track
        features = self._sdk.features.where(track_id=track_id)

        usage = ContextUsage(
            entity_type="track",
            entity_id=track_id,
        )

        # Aggregate from each feature
        for feature in features:
            feat_usage = self.get_feature_usage(feature.id)
            usage.add_child(feature.id, feat_usage)

        return usage

    def get_all_tracks_usage(self) -> list[ContextUsage]:
        """
        Get context usage for all tracks.

        Returns:
            List of ContextUsage objects, one per track
        """
        # Find all unique track IDs
        track_ids: set[str] = set()
        for feature in self._sdk.features.all():
            if feature.track_id:
                track_ids.add(feature.track_id)

        return [self.get_track_usage(tid) for tid in sorted(track_ids)]

    def get_total_usage(self) -> ContextUsage:
        """
        Get total context usage across all sessions.

        Returns:
            ContextUsage with project-wide metrics
        """
        usage = ContextUsage(
            entity_type="project",
            entity_id="total",
            entity_title="All Sessions",
        )

        # Get all sessions
        sessions = self._sdk.sessions.all()
        for session in sessions:
            session_usage = self.get_session_usage(session.id)
            usage.add_child(session.id, session_usage)

        return usage

    def get_usage_by_work_type(self) -> dict[str, ContextUsage]:
        """
        Get context usage grouped by work type.

        Returns:
            Dictionary mapping work type to ContextUsage
        """
        by_work_type: dict[str, ContextUsage] = {}

        for feature in self._sdk.features.all():
            # Infer work type from feature
            work_type = feature.properties.get("work_type", "feature")

            if work_type not in by_work_type:
                by_work_type[work_type] = ContextUsage(
                    entity_type="work_type",
                    entity_id=work_type,
                    entity_title=work_type.replace("-", " ").title(),
                )

            feat_usage = self.get_feature_usage(feature.id)
            by_work_type[work_type].add_child(feature.id, feat_usage)

        return by_work_type

    def context_efficiency_report(self) -> dict[str, Any]:
        """
        Generate a context efficiency report.

        Identifies:
        - Features with highest context consumption
        - Sessions with highest peak usage
        - Cost breakdown by feature/track

        Returns:
            Report dictionary with efficiency metrics
        """
        total = self.get_total_usage()

        # Get top features by context usage
        feature_usages = []
        for feature in self._sdk.features.all():
            feat_usage = self.get_feature_usage(feature.id)
            feature_usages.append((feature.id, feature.title, feat_usage))

        # Sort by tokens used descending
        feature_usages.sort(key=lambda x: x[2].tokens_used, reverse=True)

        top_features = [
            {
                "id": fid,
                "title": title,
                "tokens": usage.tokens_used,
                "cost": usage.cost_usd,
                "sessions": len(usage.by_session),
            }
            for fid, title, usage in feature_usages[:10]
        ]

        # Cost per feature
        total_cost = total.cost_usd
        cost_efficiency = []
        for fid, title, usage in feature_usages:
            if usage.cost_usd > 0:
                cost_efficiency.append(
                    {
                        "id": fid,
                        "title": title,
                        "cost": usage.cost_usd,
                        "percent_of_total": (usage.cost_usd / total_cost * 100)
                        if total_cost > 0
                        else 0,
                    }
                )

        return {
            "total_tokens": total.tokens_used,
            "total_cost": total.cost_usd,
            "total_output_tokens": total.output_tokens,
            "peak_tokens": total.peak_tokens,
            "features_count": len(feature_usages),
            "sessions_count": len(total.by_session),
            "top_features_by_context": top_features,
            "cost_by_feature": cost_efficiency[:10],
            "by_tool": total.by_tool,
        }

    def drill_down(self, entity_type: str, entity_id: str) -> ContextUsage:
        """
        Drill down into a specific entity.

        Args:
            entity_type: "track", "feature", or "session"
            entity_id: Entity ID

        Returns:
            ContextUsage for the entity
        """
        if entity_type == "track":
            return self.get_track_usage(entity_id)
        elif entity_type == "feature":
            return self.get_feature_usage(entity_id)
        elif entity_type == "session":
            return self.get_session_usage(entity_id)
        else:
            return ContextUsage(entity_type=entity_type, entity_id=entity_id)
