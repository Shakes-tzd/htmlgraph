from __future__ import annotations

"""Analytics operations for HtmlGraph."""


from dataclasses import dataclass
from pathlib import Path
from typing import Any

from htmlgraph import SDK
from htmlgraph.converter import html_to_session


@dataclass(frozen=True)
class AnalyticsSessionResult:
    """Result of analyzing a single session."""

    session_id: str
    metrics: dict[str, Any]
    warnings: list[str]


@dataclass(frozen=True)
class AnalyticsProjectResult:
    """Result of analyzing project-wide analytics."""

    metrics: dict[str, Any]
    warnings: list[str]


@dataclass(frozen=True)
class RecommendationsResult:
    """Result of getting work recommendations."""

    recommendations: list[dict[str, Any]]
    reasoning: dict[str, Any]
    warnings: list[str]


class AnalyticsOperationError(RuntimeError):
    """Base error for analytics operations."""


def analyze_session(*, graph_dir: Path, session_id: str) -> AnalyticsSessionResult:
    """
    Compute analytics for a single session.

    Args:
        graph_dir: Path to .htmlgraph directory
        session_id: ID of the session to analyze

    Returns:
        AnalyticsSessionResult with session metrics and warnings

    Raises:
        AnalyticsOperationError: If session cannot be analyzed
    """
    warnings: list[str] = []

    # Validate inputs
    if not graph_dir.exists():
        raise AnalyticsOperationError(f"Graph directory does not exist: {graph_dir}")

    session_path = graph_dir / "sessions" / f"{session_id}.html"
    if not session_path.exists():
        raise AnalyticsOperationError(f"Session not found: {session_id}")

    try:
        # Load session
        session = html_to_session(session_path)
    except Exception as e:
        raise AnalyticsOperationError(f"Failed to load session {session_id}: {e}")

    try:
        # Initialize SDK with minimal agent
        sdk = SDK(directory=str(graph_dir), agent="analytics-ops")

        # Compute metrics
        metrics: dict[str, Any] = {}

        # Work distribution
        try:
            work_dist = sdk.analytics.work_type_distribution(session_id=session_id)
            metrics["work_distribution"] = work_dist
        except Exception as e:
            warnings.append(f"Failed to compute work distribution: {e}")
            metrics["work_distribution"] = {}

        # Spike-to-feature ratio
        try:
            spike_ratio = sdk.analytics.spike_to_feature_ratio(session_id=session_id)
            metrics["spike_to_feature_ratio"] = spike_ratio
        except Exception as e:
            warnings.append(f"Failed to compute spike ratio: {e}")
            metrics["spike_to_feature_ratio"] = 0.0

        # Maintenance burden
        try:
            maintenance = sdk.analytics.maintenance_burden(session_id=session_id)
            metrics["maintenance_burden"] = maintenance
        except Exception as e:
            warnings.append(f"Failed to compute maintenance burden: {e}")
            metrics["maintenance_burden"] = 0.0

        # Primary work type
        try:
            primary = sdk.analytics.calculate_session_primary_work_type(session_id)
            metrics["primary_work_type"] = primary
        except Exception as e:
            warnings.append(f"Failed to compute primary work type: {e}")
            metrics["primary_work_type"] = None

        # Work breakdown (event counts)
        try:
            breakdown = sdk.analytics.calculate_session_work_breakdown(session_id)
            metrics["work_breakdown"] = breakdown
            metrics["total_events"] = sum(breakdown.values()) if breakdown else 0
        except Exception as e:
            warnings.append(f"Failed to compute work breakdown: {e}")
            metrics["work_breakdown"] = {}
            metrics["total_events"] = session.event_count

        # Transition time metrics
        try:
            transition = sdk.analytics.transition_time_metrics(session_id=session_id)
            metrics["transition_metrics"] = transition
        except Exception as e:
            warnings.append(f"Failed to compute transition metrics: {e}")
            metrics["transition_metrics"] = {}

        # Session metadata
        metrics["session_id"] = session.id
        metrics["agent"] = session.agent
        metrics["status"] = session.status
        metrics["started_at"] = session.started_at.isoformat()
        if session.ended_at:
            metrics["ended_at"] = session.ended_at.isoformat()

        return AnalyticsSessionResult(
            session_id=session_id, metrics=metrics, warnings=warnings
        )

    except AnalyticsOperationError:
        raise
    except Exception as e:
        raise AnalyticsOperationError(f"Failed to analyze session {session_id}: {e}")


def analyze_project(*, graph_dir: Path) -> AnalyticsProjectResult:
    """
    Compute analytics for the project.

    Args:
        graph_dir: Path to .htmlgraph directory

    Returns:
        AnalyticsProjectResult with project metrics and warnings

    Raises:
        AnalyticsOperationError: If project cannot be analyzed
    """
    warnings: list[str] = []

    # Validate inputs
    if not graph_dir.exists():
        raise AnalyticsOperationError(f"Graph directory does not exist: {graph_dir}")

    sessions_dir = graph_dir / "sessions"
    if not sessions_dir.exists():
        warnings.append("No sessions directory found")
        return AnalyticsProjectResult(metrics={"total_sessions": 0}, warnings=warnings)

    try:
        # Initialize SDK
        sdk = SDK(directory=str(graph_dir), agent="analytics-ops")

        # Get session count
        session_files = sorted(
            sessions_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        total_sessions = len(session_files)

        # Compute metrics
        metrics: dict[str, Any] = {
            "total_sessions": total_sessions,
        }

        if total_sessions == 0:
            warnings.append("No sessions found in project")
            return AnalyticsProjectResult(metrics=metrics, warnings=warnings)

        # Project-wide work distribution
        try:
            work_dist = sdk.analytics.work_type_distribution()
            metrics["work_distribution"] = work_dist
        except Exception as e:
            warnings.append(f"Failed to compute work distribution: {e}")
            metrics["work_distribution"] = {}

        # Project-wide spike-to-feature ratio
        try:
            spike_ratio = sdk.analytics.spike_to_feature_ratio()
            metrics["spike_to_feature_ratio"] = spike_ratio
        except Exception as e:
            warnings.append(f"Failed to compute spike ratio: {e}")
            metrics["spike_to_feature_ratio"] = 0.0

        # Project-wide maintenance burden
        try:
            maintenance = sdk.analytics.maintenance_burden()
            metrics["maintenance_burden"] = maintenance
        except Exception as e:
            warnings.append(f"Failed to compute maintenance burden: {e}")
            metrics["maintenance_burden"] = 0.0

        # Project-wide transition metrics
        try:
            transition = sdk.analytics.transition_time_metrics()
            metrics["transition_metrics"] = transition
        except Exception as e:
            warnings.append(f"Failed to compute transition metrics: {e}")
            metrics["transition_metrics"] = {}

        # Session type breakdown
        try:
            from htmlgraph import WorkType

            spike_sessions = sdk.analytics.get_sessions_by_work_type(
                WorkType.SPIKE.value
            )
            feature_sessions = sdk.analytics.get_sessions_by_work_type(
                WorkType.FEATURE.value
            )
            maintenance_sessions = sdk.analytics.get_sessions_by_work_type(
                WorkType.MAINTENANCE.value
            )

            metrics["session_types"] = {
                "spike": len(spike_sessions),
                "feature": len(feature_sessions),
                "maintenance": len(maintenance_sessions),
            }
        except Exception as e:
            warnings.append(f"Failed to compute session types: {e}")
            metrics["session_types"] = {}

        # Recent sessions (metadata only)
        try:
            recent_sessions = []
            for session_path in session_files[:5]:  # Top 5 most recent
                try:
                    session = html_to_session(session_path)
                    primary = (
                        sdk.analytics.calculate_session_primary_work_type(session.id)
                        or "unknown"
                    )
                    recent_sessions.append(
                        {
                            "session_id": session.id,
                            "agent": session.agent,
                            "started_at": session.started_at.isoformat(),
                            "status": session.status,
                            "primary_work_type": primary,
                        }
                    )
                except Exception as e:
                    warnings.append(f"Failed to load session {session_path.name}: {e}")
                    continue

            metrics["recent_sessions"] = recent_sessions
        except Exception as e:
            warnings.append(f"Failed to load recent sessions: {e}")
            metrics["recent_sessions"] = []

        return AnalyticsProjectResult(metrics=metrics, warnings=warnings)

    except AnalyticsOperationError:
        raise
    except Exception as e:
        raise AnalyticsOperationError(f"Failed to analyze project: {e}")


def get_recommendations(*, graph_dir: Path) -> RecommendationsResult:
    """
    Get work recommendations based on project state.

    Args:
        graph_dir: Path to .htmlgraph directory

    Returns:
        RecommendationsResult with recommendations, reasoning, and warnings

    Raises:
        AnalyticsOperationError: If recommendations cannot be generated
    """
    warnings: list[str] = []

    # Validate inputs
    if not graph_dir.exists():
        raise AnalyticsOperationError(f"Graph directory does not exist: {graph_dir}")

    try:
        # Initialize SDK
        sdk = SDK(directory=str(graph_dir), agent="analytics-ops")

        # Get recommendations
        try:
            task_recs = sdk.dep_analytics.recommend_next_tasks(agent_count=5)
            recommendations = [
                {
                    "id": rec.id,
                    "title": rec.title,
                    "priority": rec.priority,
                    "score": rec.score,
                    "reasons": rec.reasons,
                    "unlocks": rec.unlocks,
                    "estimated_effort": rec.estimated_effort,
                }
                for rec in task_recs.recommendations
            ]
            reasoning = {
                "recommendation_count": len(task_recs.recommendations),
                "parallel_suggestions": task_recs.parallel_suggestions,
            }
        except Exception as e:
            raise AnalyticsOperationError(f"Failed to generate recommendations: {e}")

        # Add contextual warnings based on recommendations
        if not recommendations:
            warnings.append("No recommendations available - project may be empty")

        return RecommendationsResult(
            recommendations=recommendations, reasoning=reasoning, warnings=warnings
        )

    except AnalyticsOperationError:
        raise
    except Exception as e:
        raise AnalyticsOperationError(f"Failed to get recommendations: {e}")
