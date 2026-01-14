from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

"""
Task delegation collection for tracking spawned agent work.

Captures observability data for Task() calls:
- Which agent was spawned (gemini-spawner, codex-spawner, copilot-spawner, haiku)
- What task was assigned
- How long it took
- What was the output/result
- Cost (tokens used)
- Success/failure status

This data proves multi-agent orchestration works and enables dashboard attribution.
"""


from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.collections.base import BaseCollection


class TaskDelegationCollection(BaseCollection["TaskDelegationCollection"]):
    """
    Collection interface for task delegations.

    Tracks all spawned agent work with metrics:
    - Agent type (gemini-spawner, codex-spawner, copilot-spawner, haiku)
    - Task description
    - Start and end timestamps
    - Duration in seconds
    - Tokens used
    - Cost in USD
    - Status (success/failure)
    - Result summary

    Example:
        >>> sdk = SDK(agent="orchestrator")
        >>> delegations = sdk.task_delegations.where(agent_type="codex-spawner")
        >>> for d in delegations:
        ...     logger.info(f"{d.agent_type}: {d.task_description} ({d.duration_seconds}s)")
        >>>
        >>> # Get all delegations for a specific agent
        >>> gemini_work = sdk.task_delegations.where(agent_type="gemini-spawner")
        >>>
        >>> # Calculate total cost
        >>> total_cost = sum(float(d.cost_usd or 0) for d in sdk.task_delegations.all())
    """

    _collection_name = "task-delegations"
    _node_type = "task-delegation"

    def __init__(self, sdk: SDK):
        """
        Initialize task delegation collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "task-delegations", "task-delegation")
        self._sdk = sdk

    def create_delegation(
        self,
        agent_type: str,
        task_description: str,
        timestamp_start: datetime | None = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        status: str = "pending",
        result_summary: str = "",
    ) -> Any:
        """
        Record a task delegation.

        Args:
            agent_type: Type of spawned agent (gemini-spawner, codex-spawner, copilot-spawner, haiku)
            task_description: Human-readable task description
            timestamp_start: When delegation started (defaults to now)
            tokens_used: Number of tokens used by the agent
            cost_usd: Cost in USD for this delegation
            status: success/failure/pending
            result_summary: Brief summary of the result

        Returns:
            Created task delegation node
        """
        if timestamp_start is None:
            timestamp_start = datetime.utcnow()

        # Create delegation record via base collection
        return self.create(
            title=f"{agent_type}: {task_description[:50]}...",
        ).set_metadata(
            {
                "agent_type": agent_type,
                "task_description": task_description,
                "timestamp_start": timestamp_start.isoformat(),
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "status": status,
                "result_summary": result_summary,
            }
        )

    def update_delegation(
        self,
        delegation_id: str,
        timestamp_end: datetime | None = None,
        tokens_used: int | None = None,
        cost_usd: float | None = None,
        status: str | None = None,
        result_summary: str | None = None,
    ) -> Any:
        """
        Update a delegation record with completion info.

        Args:
            delegation_id: ID of the delegation to update
            timestamp_end: When delegation completed
            tokens_used: Updated token count
            cost_usd: Updated cost
            status: Updated status
            result_summary: Updated result summary

        Returns:
            Updated delegation node
        """
        if timestamp_end is None:
            timestamp_end = datetime.utcnow()

        with self.edit(delegation_id) as delegation:
            if timestamp_end:
                delegation.timestamp_end = timestamp_end.isoformat()  # type: ignore[attr-defined]

            # Calculate duration if we have start time
            if hasattr(delegation, "timestamp_start") and timestamp_end:
                start = datetime.fromisoformat(str(delegation.timestamp_start))
                duration = (timestamp_end - start).total_seconds()
                delegation.duration_seconds = int(duration)  # type: ignore[attr-defined]

            if tokens_used is not None:
                delegation.tokens_used = tokens_used  # type: ignore[attr-defined]
            if cost_usd is not None:
                delegation.cost_usd = cost_usd  # type: ignore[attr-defined]
            if status is not None:
                delegation.status = status  # type: ignore[assignment]
            if result_summary is not None:
                delegation.result_summary = result_summary  # type: ignore[attr-defined]

        return delegation

    def get_by_agent_type(self, agent_type: str) -> list:
        """
        Get all delegations for a specific agent type.

        Args:
            agent_type: Type of agent (gemini-spawner, codex-spawner, etc.)

        Returns:
            List of delegations for that agent type
        """
        return self.where(agent_type=agent_type)

    def get_by_status(self, status: str) -> list:
        """
        Get all delegations with a specific status.

        Args:
            status: Status to filter by (success/failure/pending)

        Returns:
            List of delegations with that status
        """
        return self.where(status=status)

    def get_stats(self) -> dict:
        """
        Get aggregated statistics about delegations.

        Returns:
            Dictionary with:
            - total_delegations: Count of all delegations
            - by_agent_type: Count per agent type
            - by_status: Count per status
            - total_tokens: Sum of all tokens used
            - total_cost: Sum of all costs in USD
            - average_duration: Average duration in seconds
        """
        all_delegations = self.all()

        if not all_delegations:
            return {
                "total_delegations": 0,
                "by_agent_type": {},
                "by_status": {},
                "total_tokens": 0,
                "total_cost": 0.0,
                "average_duration": 0.0,
            }

        # Count by agent type
        by_agent_type: dict[str, int] = {}
        for d in all_delegations:
            agent = getattr(d, "agent_type", "unknown")
            by_agent_type[agent] = by_agent_type.get(agent, 0) + 1

        # Count by status
        by_status: dict[str, int] = {}
        for d in all_delegations:
            status = getattr(d, "status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        # Sum tokens and cost
        total_tokens = sum(getattr(d, "tokens_used", 0) for d in all_delegations)
        total_cost = sum(float(getattr(d, "cost_usd", 0) or 0) for d in all_delegations)

        # Average duration
        durations = [
            getattr(d, "duration_seconds", 0)
            for d in all_delegations
            if hasattr(d, "duration_seconds")
        ]
        average_duration = sum(durations) / len(durations) if durations else 0.0

        return {
            "total_delegations": len(all_delegations),
            "by_agent_type": by_agent_type,
            "by_status": by_status,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "average_duration": round(average_duration, 2),
        }
