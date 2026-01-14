"""
Spawner utilities for creating subagent prompts.

Provides session context information needed for orchestration.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.analytics import DependencyAnalytics
    from htmlgraph.collections.feature import FeatureCollection
    from htmlgraph.collections.session import SessionCollection
    from htmlgraph.sdk import SDK as SDK_TYPE
    from htmlgraph.types import SessionStartInfo
else:
    SDK_TYPE = "SDK"  # type: ignore[misc,assignment]
    SessionStartInfo = dict  # type: ignore[misc,assignment]
    FeatureCollection = Any  # type: ignore[misc,assignment]
    SessionCollection = Any  # type: ignore[misc,assignment]
    DependencyAnalytics = Any  # type: ignore[misc,assignment]


class SessionInfoMixin:
    """
    Mixin providing session start information for orchestration.

    Used by orchestrator to gather context for subagent spawning.

    This mixin is used by SDK class which has these attributes.
    """

    _directory: Path
    features: FeatureCollection
    sessions: SessionCollection
    dep_analytics: DependencyAnalytics

    def get_status(self) -> dict[str, Any]:
        """Get project status. Implemented by SDK."""
        raise NotImplementedError("Implemented by SDK")

    def get_active_work_item(self) -> dict[str, Any] | None:
        """Get active work item. Implemented by SDK."""
        raise NotImplementedError("Implemented by SDK")

    def get_session_start_info(
        self,
        include_git_log: bool = True,
        git_log_count: int = 5,
        analytics_top_n: int = 3,
        analytics_max_agents: int = 3,
    ) -> SessionStartInfo:
        """
        Get comprehensive session start information in a single call.

        Consolidates all information needed for session start into one method,
        reducing context usage from 6+ tool calls to 1.

        Args:
            include_git_log: Include recent git commits (default: True)
            git_log_count: Number of recent commits to include (default: 5)
            analytics_top_n: Number of bottlenecks/recommendations (default: 3)
            analytics_max_agents: Max agents for parallel work analysis (default: 3)

        Returns:
            Dict with comprehensive session start context:
                - status: Project status (nodes, collections, WIP)
                - active_work: Current active work item (if any)
                - features: List of features with status
                - sessions: Recent sessions
                - git_log: Recent commits (if include_git_log=True)
                - analytics: Strategic insights (bottlenecks, recommendations, parallel)

        Note:
            Returns empty dict {} if session context unavailable.
            Always check for expected keys before accessing.

        Example:
            >>> sdk = SDK(agent="claude")
            >>> info = sdk.get_session_start_info()
            >>> logger.info(f"Project: {info['status']['total_nodes']} nodes")
            >>> logger.info(f"WIP: {info['status']['in_progress_count']}")
            >>> if info.get('active_work'):
            ...     logger.info(f"Active: {info['active_work']['title']}")

        See also:
            status: Get project status only
            features.list_all: Get all features
            dep_analytics.recommend_next_tasks: Get recommendations only
        """
        # Build result dictionary incrementally, then cast at return
        result: dict[str, Any] = {}

        try:
            # 1. Project status
            status = self.get_status()
            result["status"] = status

            # 2. Active work item
            active_work = self.get_active_work_item()
            if active_work:
                result["active_work"] = active_work

            # 3. All features
            features = self.features.list_all()
            result["features"] = [
                {
                    "id": f.id,
                    "title": f.title,
                    "status": f.status,
                    "priority": getattr(f, "priority", "medium"),
                    "steps_total": len(f.steps) if hasattr(f, "steps") else 0,
                    "steps_completed": sum(1 for s in f.steps if s.completed)
                    if hasattr(f, "steps")
                    else 0,
                }
                for f in features
            ]

            # 4. Recent sessions
            sessions = self.sessions.list_all()
            result["sessions"] = [
                {
                    "id": s.id,
                    "agent": getattr(s, "agent", "unknown"),
                    "status": s.status,
                    "event_count": getattr(s.properties, "event_count", 0)
                    if hasattr(s, "properties")
                    else 0,
                }
                for s in sessions[:5]  # Last 5 sessions
            ]

            # 5. Git log (optional)
            if include_git_log:
                import subprocess

                try:
                    git_output = subprocess.check_output(
                        [
                            "git",
                            "log",
                            f"-{git_log_count}",
                            "--oneline",
                            "--no-decorate",
                        ],
                        cwd=self._directory.parent,
                        stderr=subprocess.DEVNULL,
                        text=True,
                    )
                    result["git_log"] = git_output.strip().split("\n")
                except Exception:
                    # Git not available or not a git repo
                    result["git_log"] = []

            # 6. Strategic analytics
            try:
                bottlenecks = self.dep_analytics.find_bottlenecks(top_n=analytics_top_n)
                recommendations = self.dep_analytics.recommend_next_tasks(
                    agent_count=1, lookahead=analytics_top_n
                )
                parallel_work = self.dep_analytics.find_parallelizable_work()

                # Convert to serializable dicts for JSON response
                result["analytics"] = {
                    "bottlenecks": [
                        {
                            "id": b.id,
                            "title": b.title,
                            "weighted_impact": b.weighted_impact,
                        }
                        for b in bottlenecks
                    ],
                    "recommendations": [
                        {"id": r.id, "title": r.title, "score": r.score}
                        for r in recommendations.recommendations
                    ]
                    if hasattr(recommendations, "recommendations")
                    else [],
                    "parallel": {
                        "max_parallelism": parallel_work.max_parallelism,
                        "levels": len(parallel_work.levels)
                        if hasattr(parallel_work, "levels")
                        else 0,
                    },
                }
            except Exception:
                # Analytics not available
                result["analytics"] = {
                    "bottlenecks": [],
                    "recommendations": [],
                    "parallel": {
                        "max_parallelism": 0,
                        "levels": 0,
                    },
                }

        except Exception:
            # Return empty dict on any error - type ignore since we're returning partial dict
            return {}  # type: ignore[return-value,typeddict-item]

        return result  # type: ignore[return-value,typeddict-item]
