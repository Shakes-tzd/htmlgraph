"""
Agent interface for HtmlGraph.

Provides a simplified API for AI agents with:
- Lightweight context generation
- Task claiming and completion
- Progress tracking
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph.models import Node, Step
from htmlgraph.graph import HtmlGraph


class AgentInterface:
    """
    Simplified interface for AI agent interaction with HtmlGraph.

    Provides token-efficient methods for:
    - Getting available tasks
    - Claiming and releasing tasks
    - Updating progress
    - Getting lightweight context

    Example:
        agent = AgentInterface("features/")
        task = agent.get_next_task(agent_id="claude", priority="high")
        context = agent.get_context(task.id)
        agent.complete_step(task.id, 0, agent_id="claude")
        agent.complete_task(task.id, agent_id="claude")
    """

    def __init__(
        self,
        directory: Path | str,
        agent_id: str | None = None
    ):
        """
        Initialize agent interface.

        Args:
            directory: Directory containing graph HTML files
            agent_id: Default agent identifier for operations
        """
        self.graph = HtmlGraph(directory)
        self.agent_id = agent_id

    def reload(self) -> None:
        """Reload graph from disk."""
        self.graph.reload()

    # =========================================================================
    # Task Discovery
    # =========================================================================

    def get_available_tasks(
        self,
        status: str = "todo",
        priority: str | None = None,
        node_type: str | None = None,
        limit: int = 10
    ) -> list[Node]:
        """
        Get available tasks matching criteria.

        Args:
            status: Filter by status (default: todo)
            priority: Optional priority filter
            node_type: Optional type filter
            limit: Maximum tasks to return

        Returns:
            List of matching nodes, sorted by priority
        """
        def matches(node: Node) -> bool:
            if node.status != status:
                return False
            if priority and node.priority != priority:
                return False
            if node_type and node.type != node_type:
                return False
            # Exclude already assigned tasks
            if node.agent_assigned and node.agent_assigned != self.agent_id:
                return False
            return True

        tasks = self.graph.filter(matches)

        # Sort by priority (critical > high > medium > low)
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        tasks.sort(key=lambda n: priority_order.get(n.priority, 99))

        return tasks[:limit]

    def get_next_task(
        self,
        agent_id: str | None = None,
        priority: str | None = None,
        node_type: str | None = None,
        auto_claim: bool = False
    ) -> Node | None:
        """
        Get the next available task.

        Args:
            agent_id: Agent requesting task (uses default if not specified)
            priority: Optional priority filter
            node_type: Optional type filter
            auto_claim: Whether to automatically claim the task

        Returns:
            Next available Node or None
        """
        agent_id = agent_id or self.agent_id
        tasks = self.get_available_tasks(
            priority=priority,
            node_type=node_type,
            limit=1
        )

        if not tasks:
            return None

        task = tasks[0]

        if auto_claim and agent_id:
            self.claim_task(task.id, agent_id)
            # Reload to get updated state
            task = self.graph.get(task.id)

        return task

    def get_blocked_tasks(self) -> list[Node]:
        """Get all tasks that are currently blocked."""
        return self.graph.by_status("blocked")

    def get_in_progress_tasks(self, agent_id: str | None = None) -> list[Node]:
        """
        Get tasks currently in progress.

        Args:
            agent_id: Optional filter by assigned agent
        """
        tasks = self.graph.by_status("in-progress")

        if agent_id:
            tasks = [t for t in tasks if t.agent_assigned == agent_id]

        return tasks

    # =========================================================================
    # Task Operations
    # =========================================================================

    def claim_task(self, node_id: str, agent_id: str | None = None) -> bool:
        """
        Claim a task for an agent.

        Args:
            node_id: Task to claim
            agent_id: Agent claiming task (uses default if not specified)

        Returns:
            True if claim successful
        """
        agent_id = agent_id or self.agent_id
        if not agent_id:
            raise ValueError("agent_id required for claiming")

        node = self.graph.get(node_id)
        if not node:
            return False

        if node.agent_assigned and node.agent_assigned != agent_id:
            return False  # Already claimed by another agent

        node.agent_assigned = agent_id
        node.claimed_at = datetime.now()
        node.status = "in-progress"
        node.updated = datetime.now()

        self.graph.update(node)
        return True

    def release_task(self, node_id: str, agent_id: str | None = None) -> bool:
        """
        Release a claimed task.

        Args:
            node_id: Task to release
            agent_id: Agent releasing task (verifies ownership)

        Returns:
            True if release successful
        """
        agent_id = agent_id or self.agent_id
        node = self.graph.get(node_id)

        if not node:
            return False

        if node.agent_assigned and node.agent_assigned != agent_id:
            return False  # Can't release someone else's task

        node.agent_assigned = None
        node.claimed_at = None
        node.claimed_by_session = None
        node.status = "todo"
        node.updated = datetime.now()

        self.graph.update(node)
        return True

    def complete_task(self, node_id: str, agent_id: str | None = None) -> bool:
        """
        Mark a task as complete.

        Args:
            node_id: Task to complete
            agent_id: Agent completing task

        Returns:
            True if completion successful
        """
        agent_id = agent_id or self.agent_id
        node = self.graph.get(node_id)

        if not node:
            return False

        node.status = "done"
        node.updated = datetime.now()

        # Mark any remaining steps as complete
        for step in node.steps:
            if not step.completed:
                step.completed = True
                step.agent = agent_id
                step.timestamp = datetime.now()

        self.graph.update(node)
        return True

    def block_task(
        self,
        node_id: str,
        blocked_by: str,
        reason: str | None = None
    ) -> bool:
        """
        Mark a task as blocked.

        Args:
            node_id: Task to block
            blocked_by: ID of blocking task
            reason: Optional reason for blocking

        Returns:
            True if successful
        """
        node = self.graph.get(node_id)
        if not node:
            return False

        node.status = "blocked"
        node.updated = datetime.now()

        # Add blocking edge if not present
        from htmlgraph.models import Edge
        blocking_edge = Edge(
            target_id=blocked_by,
            relationship="blocked_by",
            since=datetime.now(),
            properties={"reason": reason} if reason else {}
        )
        node.add_edge(blocking_edge)

        self.graph.update(node)
        return True

    # =========================================================================
    # Step Operations
    # =========================================================================

    def complete_step(
        self,
        node_id: str,
        step_index: int,
        agent_id: str | None = None
    ) -> bool:
        """
        Mark a step as completed.

        Args:
            node_id: Task containing step
            step_index: Index of step to complete (0-based)
            agent_id: Agent completing step

        Returns:
            True if successful
        """
        agent_id = agent_id or self.agent_id
        node = self.graph.get(node_id)

        if not node:
            return False

        if node.complete_step(step_index, agent_id):
            self.graph.update(node)
            return True

        return False

    def add_step(
        self,
        node_id: str,
        description: str
    ) -> bool:
        """
        Add a new step to a task.

        Args:
            node_id: Task to add step to
            description: Step description

        Returns:
            True if successful
        """
        node = self.graph.get(node_id)
        if not node:
            return False

        node.steps.append(Step(description=description))
        node.updated = datetime.now()

        self.graph.update(node)
        return True

    # =========================================================================
    # Context Generation
    # =========================================================================

    def get_context(self, node_id: str) -> str:
        """
        Get lightweight context for a task.

        Returns ~50-100 tokens of essential information.

        Args:
            node_id: Task to get context for

        Returns:
            Compact string representation
        """
        node = self.graph.get(node_id)
        if not node:
            return f"# {node_id}\nStatus: NOT FOUND"

        return node.to_context()

    def get_full_context(self, node_id: str, include_related: bool = True) -> str:
        """
        Get extended context including related nodes.

        Args:
            node_id: Task to get context for
            include_related: Whether to include related node summaries

        Returns:
            Extended context string
        """
        node = self.graph.get(node_id)
        if not node:
            return f"# {node_id}\nStatus: NOT FOUND"

        lines = [node.to_context()]

        if include_related:
            # Include blocking dependencies
            blocked_by = node.edges.get("blocked_by", [])
            if blocked_by:
                lines.append("\n## Blocking Dependencies")
                for edge in blocked_by:
                    dep = self.graph.get(edge.target_id)
                    if dep:
                        lines.append(f"- {dep.id}: {dep.title} [{dep.status}]")

            # Include related items
            related = node.edges.get("related", [])
            if related:
                lines.append("\n## Related")
                for edge in related[:5]:  # Limit related items
                    rel = self.graph.get(edge.target_id)
                    if rel:
                        lines.append(f"- {rel.id}: {rel.title}")

        return "\n".join(lines)

    def get_summary(self, max_items: int = 10) -> str:
        """
        Get summary of current graph state.

        Returns compact overview for AI agent orientation.
        """
        stats = self.graph.stats()

        lines = [
            "# Project Summary",
            f"Total: {stats['total']} | Done: {stats['completion_rate']}%",
        ]

        # Status breakdown
        status_parts = [f"{s}: {c}" for s, c in stats["by_status"].items()]
        lines.append(f"Status: {' | '.join(status_parts)}")

        # In progress
        in_progress = self.get_in_progress_tasks()
        if in_progress:
            lines.append("\n## In Progress")
            for task in in_progress[:max_items]:
                agent = f" ({task.agent_assigned})" if task.agent_assigned else ""
                lines.append(f"- {task.id}: {task.title}{agent}")

        # Blocked
        blocked = self.get_blocked_tasks()
        if blocked:
            lines.append("\n## Blocked")
            for task in blocked[:max_items]:
                lines.append(f"- {task.id}: {task.title}")

        # Next available
        available = self.get_available_tasks(limit=max_items)
        if available:
            lines.append("\n## Available")
            for task in available:
                lines.append(f"- {task.id}: {task.title} [{task.priority}]")

        return "\n".join(lines)

    # =========================================================================
    # Utility
    # =========================================================================

    def create_task(
        self,
        task_id: str,
        title: str,
        description: str = "",
        priority: str = "medium",
        node_type: str = "task",
        steps: list[str] | None = None
    ) -> Node:
        """
        Create a new task.

        Args:
            task_id: Unique identifier
            title: Task title
            description: Task description
            priority: Priority level
            node_type: Node type
            steps: Optional list of step descriptions

        Returns:
            Created Node
        """
        node = Node(
            id=task_id,
            title=title,
            type=node_type,
            priority=priority,
            content=f"<p>{description}</p>" if description else "",
            steps=[Step(description=s) for s in (steps or [])]
        )

        self.graph.add(node)
        return node

    def get_workload(self, agent_id: str | None = None) -> dict[str, Any]:
        """
        Get workload summary for an agent.

        Args:
            agent_id: Agent to check (uses default if not specified)

        Returns:
            Dict with in_progress count, completed today, etc.
        """
        agent_id = agent_id or self.agent_id

        in_progress = self.get_in_progress_tasks(agent_id)

        # Count completed (could be enhanced with timestamp filtering)
        completed = self.graph.filter(
            lambda n: n.status == "done" and n.agent_assigned == agent_id
        )

        return {
            "agent_id": agent_id,
            "in_progress": len(in_progress),
            "completed": len(completed),
            "tasks": [t.id for t in in_progress]
        }
