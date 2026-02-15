"""
Activity tracking, drift detection, and graph linking.

Provides:
- ActivityTracker: record tool use, attribute to features, log events
- detect_drift: pure function to detect when work diverges from feature scope
- LinkingOps: bidirectional links between features, sessions, and transcripts

Uses SessionConverter for persistence and scoring functions from features.py
for attribution.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from htmlgraph.converter import SessionConverter
from htmlgraph.event_log import EventRecord, JsonlEventLog
from htmlgraph.graph import HtmlGraph
from htmlgraph.ids import generate_id
from htmlgraph.models import ActivityEntry, Edge, Node, Session
from htmlgraph.sessions.features import attribute_activity, is_system_overhead

logger = logging.getLogger(__name__)


# =========================================================================
# Activity Tracking
# =========================================================================


class ActivityTracker:
    """Tracks activities, attributes them to features, and persists events."""

    def __init__(
        self,
        graph_dir: Path,
        session_converter: SessionConverter,
        event_log: JsonlEventLog,
    ):
        self.graph_dir = graph_dir
        self.session_converter = session_converter
        self.event_log = event_log

    def track_activity(
        self,
        session: Session,
        session_id: str,
        tool: str,
        summary: str,
        file_paths: list[str] | None = None,
        success: bool = True,
        feature_id: str | None = None,
        parent_activity_id: str | None = None,
        payload: dict[str, Any] | None = None,
        active_features: list[Node] | None = None,
        get_active_auto_spike: Any = None,
        linking: LinkingOps | None = None,
        get_session: Any = None,
        check_completion: Any = None,
    ) -> ActivityEntry:
        """
        Track an activity and attribute it to a feature.

        Args:
            session: Session object (already loaded)
            session_id: Session ID
            tool: Tool name (Edit, Bash, Read, etc.)
            summary: Human-readable summary
            file_paths: Files involved in this activity
            success: Whether the tool call succeeded
            feature_id: Explicit feature ID (skips attribution)
            parent_activity_id: ID of parent activity
            payload: Optional rich payload data
            active_features: List of active feature nodes
            get_active_auto_spike: Callable to find active auto-spike
            linking: LinkingOps instance for bidirectional links
            get_session: Callable to get session by ID
            check_completion: Callable to check auto-completion

        Returns:
            Created ActivityEntry with attribution
        """
        active_features = active_features or []

        attributed_feature = feature_id
        drift_score = None
        attribution_reason = None

        if parent_activity_id:
            if not attributed_feature and active_features:
                primary = next(
                    (f for f in active_features if f.properties.get("is_primary")),
                    None,
                )
                attributed_feature = (
                    (primary or active_features[0]).id if active_features else None
                )
            drift_score = None
            attribution_reason = "child_activity"
        elif is_system_overhead(tool, summary, file_paths or []):
            if not attributed_feature and active_features:
                primary = next(
                    (f for f in active_features if f.properties.get("is_primary")),
                    None,
                )
                attributed_feature = (
                    (primary or active_features[0]).id if active_features else None
                )
            drift_score = None
            attribution_reason = "system_overhead"
        elif not attributed_feature and active_features:
            attribution = attribute_activity(
                tool=tool,
                summary=summary,
                file_paths=file_paths or [],
                active_features=active_features,
                agent=session.agent,
                get_active_auto_spike=get_active_auto_spike,
            )
            attributed_feature = attribution["feature_id"]
            drift_score = attribution["drift_score"]
            attribution_reason = attribution["reason"]

        event_id = generate_id(
            node_type="event",
            title=f"{tool}:{summary[:50]}",
        )

        entry = ActivityEntry(
            id=event_id,
            timestamp=datetime.now(),
            tool=tool,
            summary=summary,
            success=success,
            feature_id=attributed_feature,
            drift_score=drift_score,
            parent_activity_id=parent_activity_id,
            payload={
                **(payload or {}),
                "file_paths": file_paths,
                "attribution_reason": attribution_reason,
                "session_id": session_id,
            }
            if file_paths or attribution_reason or session_id
            else payload,
        )

        # Append to JSONL event log
        self._append_to_event_log(entry, session, session_id, file_paths, payload)

        # Update SQLite index if present
        self._update_sqlite_index(entry, session, session_id, file_paths, payload)

        # Add to session
        session.add_activity(entry)

        # Add bidirectional link: feature -> session
        if attributed_feature and linking and get_session:
            linking.add_session_link_to_feature(
                attributed_feature, session_id, get_session
            )
            if check_completion:
                check_completion(attributed_feature, tool, success)

        # Save session
        self.session_converter.save(session)

        return entry

    def _append_to_event_log(
        self,
        entry: ActivityEntry,
        session: Session,
        session_id: str,
        file_paths: list[str] | None,
        payload: dict[str, Any] | None,
    ) -> None:
        """Append activity to JSONL event log."""
        try:
            from htmlgraph.work_type_utils import infer_work_type_from_id

            work_type = infer_work_type_from_id(entry.feature_id)

            self.event_log.append(
                EventRecord(
                    event_id=entry.id or "",
                    timestamp=entry.timestamp,
                    session_id=session_id,
                    agent=session.agent,
                    tool=entry.tool,
                    summary=entry.summary,
                    success=entry.success,
                    feature_id=entry.feature_id,
                    drift_score=entry.drift_score,
                    start_commit=session.start_commit,
                    continued_from=session.continued_from,
                    work_type=work_type,
                    session_status=session.status,
                    file_paths=file_paths,
                    parent_session_id=session.parent_session,
                    payload=entry.payload
                    if isinstance(entry.payload, dict)
                    else payload,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to append to event log: {e}")

    def _update_sqlite_index(
        self,
        entry: ActivityEntry,
        session: Session,
        session_id: str,
        file_paths: list[str] | None,
        payload: dict[str, Any] | None,
    ) -> None:
        """Update SQLite analytics index if it exists."""
        try:
            index_path = self.graph_dir / "index.sqlite"
            if index_path.exists():
                from htmlgraph.analytics_index import AnalyticsIndex

                idx = AnalyticsIndex(index_path)
                idx.ensure_schema()
                idx.upsert_session(
                    {
                        "session_id": session_id,
                        "agent": session.agent,
                        "start_commit": session.start_commit,
                        "continued_from": session.continued_from,
                        "status": session.status,
                        "started_at": session.started_at.isoformat(),
                        "ended_at": session.ended_at.isoformat()
                        if session.ended_at
                        else None,
                    }
                )
                idx.upsert_event(
                    {
                        "event_id": entry.id,
                        "timestamp": entry.timestamp.isoformat(),
                        "session_id": session_id,
                        "tool": entry.tool,
                        "summary": entry.summary,
                        "success": entry.success,
                        "feature_id": entry.feature_id,
                        "drift_score": entry.drift_score,
                        "file_paths": file_paths or [],
                        "payload": entry.payload
                        if isinstance(entry.payload, dict)
                        else payload,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to update SQLite index: {e}")

    def track_user_query(
        self,
        session: Session,
        session_id: str,
        prompt: str,
        feature_id: str | None = None,
        active_features: list[Node] | None = None,
        get_active_auto_spike: Any = None,
        linking: Any = None,
        get_session: Any = None,
        check_completion: Any = None,
    ) -> ActivityEntry:
        """Track a user query/prompt."""
        preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
        preview = preview.replace("\n", " ")

        return self.track_activity(
            session=session,
            session_id=session_id,
            tool="UserQuery",
            summary=f'"{preview}"',
            feature_id=feature_id,
            payload={"prompt": prompt, "prompt_length": len(prompt)},
            active_features=active_features,
            get_active_auto_spike=get_active_auto_spike,
            linking=linking,
            get_session=get_session,
            check_completion=check_completion,
        )


# =========================================================================
# Drift Detection
# =========================================================================

# Drift thresholds
DRIFT_TIME_THRESHOLD = timedelta(minutes=15)


def detect_drift(session: Session, feature_id: str) -> dict[str, Any]:
    """
    Detect if current work is drifting from a feature.

    Args:
        session: Session to analyze
        feature_id: Feature to check drift against

    Returns:
        Dict with is_drifting, drift_score, reasons, indicators
    """
    reasons: list[str] = []
    drift_indicators = 0

    feature_activities = [
        a for a in session.activity_log[-20:] if a.feature_id == feature_id
    ]

    if not feature_activities:
        return {
            "is_drifting": False,
            "drift_score": 0,
            "reasons": ["no_recent_activity"],
        }

    # 1. Check time since last meaningful progress
    last_activity = feature_activities[-1]
    time_since = datetime.now() - last_activity.timestamp
    if time_since > DRIFT_TIME_THRESHOLD:
        drift_indicators += 1
        reasons.append(f"stalled_{int(time_since.total_seconds() / 60)}min")

    # 2. Check for repeated tool patterns (loops)
    recent_tools = [a.tool for a in feature_activities[-10:]]
    if len(recent_tools) >= 6:
        tool_counts: dict[str, int] = {}
        for t in recent_tools:
            tool_counts[t] = tool_counts.get(t, 0) + 1
        max_repeat = max(tool_counts.values())
        if max_repeat >= 5:
            drift_indicators += 1
            reasons.append("repetitive_pattern")

    # 3. Check average drift scores
    drift_scores = [
        a.drift_score for a in feature_activities if a.drift_score is not None
    ]
    if drift_scores:
        avg_drift = sum(drift_scores) / len(drift_scores)
        if avg_drift > 0.6:
            drift_indicators += 1
            reasons.append(f"high_avg_drift_{avg_drift:.2f}")

    # 4. Check for failed tool calls
    failures = sum(1 for a in feature_activities[-10:] if not a.success)
    if failures >= 3:
        drift_indicators += 1
        reasons.append(f"failures_{failures}")

    is_drifting = drift_indicators >= 2
    drift_score_val = min(drift_indicators / 4, 1.0)

    return {
        "is_drifting": is_drifting,
        "drift_score": drift_score_val,
        "reasons": reasons,
        "indicators": drift_indicators,
    }


# =========================================================================
# Graph Linking
# =========================================================================


class LinkingOps:
    """Manages bidirectional links between graph entities."""

    def __init__(
        self,
        session_converter: SessionConverter,
        features_graph: HtmlGraph,
        bugs_graph: HtmlGraph,
    ):
        self.session_converter = session_converter
        self.features_graph = features_graph
        self.bugs_graph = bugs_graph

    def add_session_link_to_feature(
        self,
        feature_id: str,
        session_id: str,
        get_session: Any,
    ) -> None:
        """
        Add a bidirectional link between feature and session.

        Creates:
        1. "implemented-in" edge on the feature pointing to the session
        2. "worked-on" entry on the session pointing to the feature
        """
        feature_node = self.features_graph.get(feature_id) or self.bugs_graph.get(
            feature_id
        )
        if not feature_node:
            return

        existing_sessions = feature_node.edges.get("implemented-in", [])
        feature_already_linked = any(
            edge.target_id == session_id for edge in existing_sessions
        )

        if not feature_already_linked:
            edge = Edge(
                target_id=session_id,
                relationship="implemented-in",
                title=session_id,
                since=datetime.now(),
            )
            feature_node.add_edge(edge)
            graph = self._get_graph_for_node(feature_node)
            graph.update(feature_node)

        session = get_session(session_id)
        if not session:
            return
        if feature_id not in session.worked_on:
            session.worked_on.append(feature_id)
            self.session_converter.save(session)

    def link_transcript_to_feature(
        self,
        node: Node,
        transcript_id: str,
        graph: HtmlGraph,
    ) -> None:
        """Link a Claude Code transcript to a feature with analytics."""
        existing_transcripts = node.edges.get("implemented-by", [])
        already_linked = any(
            edge.target_id == transcript_id for edge in existing_transcripts
        )
        if already_linked:
            return

        tool_count = 0
        duration_seconds = 0
        tool_breakdown: dict[str, Any] = {}

        try:
            from htmlgraph.transcript import TranscriptReader

            reader = TranscriptReader()
            transcript = reader.read_session(transcript_id)
            if transcript:
                tool_count = transcript.tool_call_count
                duration_seconds = int(transcript.duration_seconds or 0)
                tool_breakdown = transcript.tool_breakdown
        except Exception as e:
            logger.warning(
                f"Failed to get transcript analytics for {transcript_id}: {e}"
            )

        edge = Edge(
            target_id=transcript_id,
            relationship="implemented-by",
            title=transcript_id,
            since=datetime.now(),
            properties={
                "tool_count": tool_count,
                "duration_seconds": duration_seconds,
                "tool_breakdown": tool_breakdown,
            },
        )
        node.add_edge(edge)

        if tool_count > 0:
            node.properties["transcript_tool_count"] = tool_count
            node.properties["transcript_duration_seconds"] = duration_seconds

    def _get_graph_for_node(self, node: Node) -> HtmlGraph:
        """Get the graph that contains a node."""
        if node.type == "bug":
            return self.bugs_graph
        return self.features_graph
