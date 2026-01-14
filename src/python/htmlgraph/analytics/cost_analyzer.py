import logging

logger = logging.getLogger(__name__)

"""
CostAnalyzer for OTEL ROI Analysis - Phase 1.

Analyzes cost attribution of Task() delegations vs direct tool execution.
Provides insights into which delegations are most expensive and their ROI.

Components:
1. get_task_delegations() - Query all task_delegation events with hierarchy
2. calculate_task_cost(event_id) - Sum token costs of all child tool calls
3. get_cost_by_subagent_type() - Group costs by subagent type
4. get_cost_by_tool_type() - Show which tools cost most
5. get_roi_stats() - Calculate parallelization savings and benefits

Usage:
    from htmlgraph.analytics.cost_analyzer import CostAnalyzer
    analyzer = CostAnalyzer()
    delegations = analyzer.get_task_delegations_with_costs()
    logger.info(f"Total delegation cost: ${delegations['total_cost_usd']:.2f}")
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph.cigs.cost import CostCalculator


@dataclass
class TaskDelegation:
    """Represents a single Task delegation with cost analysis."""

    event_id: str
    session_id: str
    timestamp: datetime
    subagent_type: str
    parent_event_id: str | None
    tool_count: int = 0
    total_cost_tokens: int = 0
    child_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "subagent_type": self.subagent_type,
            "parent_event_id": self.parent_event_id,
            "tool_count": self.tool_count,
            "total_cost_tokens": self.total_cost_tokens,
            "child_events": self.child_events,
        }


@dataclass
class CostBreakdown:
    """Cost breakdown analysis."""

    by_subagent: dict[str, int] = field(default_factory=dict)
    by_tool: dict[str, int] = field(default_factory=dict)
    total_cost_tokens: int = 0
    total_delegations: int = 0
    avg_cost_per_delegation: float = 0.0


@dataclass
class ROIStats:
    """Return-on-Investment statistics."""

    total_delegation_cost: int = 0
    estimated_direct_cost: int = 0
    estimated_savings: int = 0
    savings_percentage: float = 0.0
    avg_parallelization_factor: float = 1.0
    context_preservation_benefit: float = 0.0
    total_delegations: int = 0
    avg_cost_per_delegation: float = 0.0


class CostAnalyzer:
    """
    Analyze cost attribution of Task delegations.

    Queries the agent_events database to calculate:
    - Total cost of each Task delegation (sum of child tool calls)
    - Cost breakdown by subagent type and tool type
    - ROI statistics comparing direct vs delegated execution
    """

    def __init__(self, graph_dir: Path | None = None):
        """
        Initialize CostAnalyzer.

        Args:
            graph_dir: Root directory for HtmlGraph (defaults to .htmlgraph)
        """
        if graph_dir is None:
            graph_dir = Path.cwd() / ".htmlgraph"

        self.graph_dir = Path(graph_dir)
        self.db_path = self.graph_dir / "htmlgraph.db"
        self.cost_calculator = CostCalculator()

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_task_delegations(self) -> list[TaskDelegation]:
        """
        Query all task_delegation events from the database.

        Returns:
            List of TaskDelegation objects ordered by timestamp (newest first)
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    event_id,
                    session_id,
                    timestamp,
                    subagent_type,
                    parent_event_id
                FROM agent_events
                WHERE event_type = 'task_delegation'
                ORDER BY timestamp DESC
                """
            )

            delegations = []
            for row in cursor.fetchall():
                timestamp = (
                    datetime.fromisoformat(row["timestamp"])
                    if isinstance(row["timestamp"], str)
                    else row["timestamp"]
                )
                delegations.append(
                    TaskDelegation(
                        event_id=row["event_id"],
                        session_id=row["session_id"],
                        timestamp=timestamp,
                        subagent_type=row["subagent_type"] or "unknown",
                        parent_event_id=row["parent_event_id"],
                    )
                )

            return delegations
        finally:
            conn.close()

    def calculate_task_cost(self, event_id: str) -> tuple[int, list[dict[str, Any]]]:
        """
        Calculate total cost of a Task delegation.

        Sums all token costs of child tool calls using cost_tokens field.
        Falls back to CIGS cost estimation if cost_tokens is not available.

        Args:
            event_id: Task delegation event ID

        Returns:
            Tuple of (total_cost_tokens, child_events_list)
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Get all children of this task
            cursor.execute(
                """
                SELECT
                    event_id,
                    tool_name,
                    cost_tokens,
                    input_summary,
                    output_summary,
                    timestamp
                FROM agent_events
                WHERE parent_event_id = ?
                AND event_type IN ('tool_call', 'tool_result')
                ORDER BY timestamp ASC
                """,
                (event_id,),
            )

            total_cost = 0
            child_events = []

            for row in cursor.fetchall():
                cost = row["cost_tokens"] if row["cost_tokens"] else 0

                # If no stored cost, estimate based on tool type
                if cost == 0 and row["tool_name"]:
                    cost = self.cost_calculator.predict_cost(row["tool_name"], {})

                total_cost += cost

                child_events.append(
                    {
                        "event_id": row["event_id"],
                        "tool_name": row["tool_name"],
                        "cost_tokens": cost,
                        "timestamp": row["timestamp"],
                    }
                )

            return total_cost, child_events
        finally:
            conn.close()

    def get_task_delegations_with_costs(self) -> dict[str, Any]:
        """
        Get all task delegations with calculated costs.

        Returns:
            Dictionary with:
            - delegations: List of TaskDelegation with costs
            - total_cost_tokens: Sum of all delegation costs
            - total_delegations: Count of delegations
            - by_subagent_type: Cost breakdown by subagent
            - by_tool_type: Cost breakdown by tool
        """
        delegations = self.get_task_delegations()

        total_cost = 0
        by_subagent: dict[str, int] = {}
        by_tool: dict[str, int] = {}

        for delegation in delegations:
            cost, child_events = self.calculate_task_cost(delegation.event_id)
            delegation.total_cost_tokens = cost
            delegation.child_events = child_events
            delegation.tool_count = len(child_events)

            total_cost += cost

            # Track by subagent type
            subagent = delegation.subagent_type
            by_subagent[subagent] = by_subagent.get(subagent, 0) + cost

            # Track by tool type
            for child in child_events:
                tool = child["tool_name"] or "unknown"
                by_tool[tool] = by_tool.get(tool, 0) + child["cost_tokens"]

        # Convert to USD (approximation: 1M tokens ~ $3 for input, $6 for output)
        # Average: ~$4.50 per 1M tokens
        total_cost_usd = total_cost * 0.0000045

        return {
            "delegations": delegations,
            "total_cost_tokens": total_cost,
            "total_cost_usd": total_cost_usd,
            "total_delegations": len(delegations),
            "avg_cost_per_delegation": (
                total_cost / len(delegations) if delegations else 0
            ),
            "by_subagent_type": by_subagent,
            "by_tool_type": by_tool,
        }

    def get_cost_by_subagent_type(self) -> dict[str, int]:
        """
        Group delegation costs by subagent type.

        Returns:
            Dictionary mapping subagent_type to total tokens spent
        """
        data = self.get_task_delegations_with_costs()
        result = data.get("by_subagent_type", {})
        if isinstance(result, dict):
            return result
        return {}

    def get_cost_by_tool_type(self) -> dict[str, int]:
        """
        Show which tools cost most across all delegations.

        Returns:
            Dictionary mapping tool_name to total tokens spent
        """
        data = self.get_task_delegations_with_costs()
        result = data.get("by_tool_type", {})
        if isinstance(result, dict):
            return result
        return {}

    def get_roi_stats(self) -> ROIStats:
        """
        Calculate ROI statistics comparing delegation vs direct execution.

        Assumptions:
        - Direct execution: Tokens spent directly on main agent
        - Delegated execution: Tokens in child subagents (already counted)
        - Savings: Context preservation + parallelization benefits
        - Parallelization factor: 1.2-1.5x (subagents can work more efficiently)
        - Context preservation: ~30% token savings from better focus

        Returns:
            ROIStats with cost and savings analysis
        """
        data = self.get_task_delegations_with_costs()

        total_delegation_cost = data["total_cost_tokens"]
        total_delegations = data["total_delegations"]

        # Estimate direct execution cost
        # Assumption: direct execution would cost 2.5x due to context overhead
        estimated_direct_cost = int(total_delegation_cost * 2.5)

        # Estimate savings
        # Parallelization benefit: 1.2x efficiency
        # Context preservation: 30% savings
        parallelization_factor = 1.2
        context_benefit = 0.30

        estimated_savings = int(
            estimated_direct_cost
            - (total_delegation_cost * parallelization_factor * (1.0 - context_benefit))
        )

        savings_percentage = (
            (estimated_savings / estimated_direct_cost * 100)
            if estimated_direct_cost > 0
            else 0.0
        )

        return ROIStats(
            total_delegation_cost=total_delegation_cost,
            estimated_direct_cost=estimated_direct_cost,
            estimated_savings=estimated_savings,
            savings_percentage=savings_percentage,
            avg_parallelization_factor=parallelization_factor,
            context_preservation_benefit=context_benefit,
            total_delegations=total_delegations,
            avg_cost_per_delegation=(
                total_delegation_cost / total_delegations
                if total_delegations > 0
                else 0.0
            ),
        )

    def get_top_delegations(self, limit: int = 10) -> list[TaskDelegation]:
        """
        Get the most expensive Task delegations.

        Args:
            limit: Number of delegations to return (default: 10)

        Returns:
            List of TaskDelegation sorted by cost (descending)
        """
        data = self.get_task_delegations_with_costs()
        delegations = data["delegations"]

        # Sort by cost descending
        sorted_delegations = sorted(
            delegations, key=lambda d: d.total_cost_tokens, reverse=True
        )

        return sorted_delegations[:limit]

    def get_cost_breakdown(self) -> CostBreakdown:
        """
        Get comprehensive cost breakdown.

        Returns:
            CostBreakdown with by_subagent and by_tool analysis
        """
        data = self.get_task_delegations_with_costs()

        return CostBreakdown(
            by_subagent=data["by_subagent_type"],
            by_tool=data["by_tool_type"],
            total_cost_tokens=data["total_cost_tokens"],
            total_delegations=data["total_delegations"],
            avg_cost_per_delegation=data["avg_cost_per_delegation"],
        )
