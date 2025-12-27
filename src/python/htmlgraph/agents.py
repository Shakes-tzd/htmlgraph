"""
Agent interface for simplified task management.

IMPERATIVE USAGE INSTRUCTIONS
=============================

The AgentInterface provides lightweight task claiming and progress tracking.

TASK LIFECYCLE
==============

1. CLAIM A TASK
   ```python
   from htmlgraph.agents import AgentInterface

   agent = AgentInterface("features/")
   task = agent.get_next_task(
       agent_id="claude",
       priority="high",  # Optional filter
       auto_claim=True   # Automatically claim the task
   )
   ```

2. WORK ON TASK
   ```python
   # Get lightweight context for LLM
   context = agent.get_context(task.id)
   # Returns: "# feature-001: Title\\nStatus: in-progress..."

   # Complete steps as you work
   agent.complete_step(task.id, step_index=0, agent_id="claude")
   agent.complete_step(task.id, step_index=1, agent_id="claude")
   ```

3. COMPLETE TASK
   ```python
   agent.complete_task(task.id, agent_id="claude")
   ```

4. IF BLOCKED
   ```python
   agent.release_task(task.id, agent_id="claude")
   # Task becomes available for other agents
   ```

DISCOVERY METHODS
=================

| Method | Purpose |
|--------|---------|
| `get_available_tasks()` | Find all matching tasks |
| `get_next_task()` | Get single next task |
| `get_blocked_tasks()` | Find blocked work |
| `get_in_progress_tasks()` | Get agent's active work |

ANTI-PATTERNS
=============

NEVER:
- Work on unclaimed tasks
- Skip step completion updates
- Leave tasks in-progress when blocked

ALWAYS:
- Claim before working
- Update progress incrementally
- Release if you can't complete

Available Classes
=================

AgentInterface: Simplified interface for task management
AgentRegistry: Capability-based agent routing
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

from htmlgraph.agent_registry import AgentProfile, AgentRegistry
from htmlgraph.graph import HtmlGraph
from htmlgraph.models import Node, Step


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

    def __init__(self, directory: Path | str, agent_id: str | None = None):
        """
        Initialize agent interface.

        Args:
            directory: Directory containing graph HTML files
            agent_id: Default agent identifier for operations
        """
        self.graph = HtmlGraph(directory)
        self.agent_id = agent_id

        # Initialize agent registry for capability-based routing
        # Assumes .htmlgraph is parent of directory
        htmlgraph_dir = (
            Path(directory).parent
            if Path(directory).name == "features"
            else Path(directory)
        )
        self.registry = AgentRegistry(htmlgraph_dir)

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
        limit: int = 10,
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
        auto_claim: bool = False,
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
            priority=priority, node_type=node_type, limit=1
        )

        if not tasks:
            return None

        task = tasks[0]

        if auto_claim and agent_id:
            self.claim_task(task.id, agent_id)
            # Reload to get updated state
            reloaded_task = self.graph.get(task.id)
            if reloaded_task:
                task = reloaded_task

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

    def get_tasks_by_capability(
        self, agent_capabilities: list[str], status: str = "todo", limit: int = 10
    ) -> list[Node]:
        """
        Get tasks that match agent capabilities.

        Filters tasks to those where agent has at least one required capability.

        Args:
            agent_capabilities: List of agent's capabilities
            status: Filter by task status (default: todo)
            limit: Maximum tasks to return

        Returns:
            List of matching nodes, prioritized by exact matches first
        """

        def matches(node: Node) -> bool:
            if node.status != status:
                return False
            # Exclude already assigned tasks
            if node.agent_assigned and node.agent_assigned != self.agent_id:
                return False
            # Tasks with no required capabilities are available to all
            if not node.required_capabilities:
                return True
            # Check if agent has at least one required capability
            return any(cap in agent_capabilities for cap in node.required_capabilities)

        tasks = self.graph.filter(matches)

        # Sort by capability match quality
        agent_caps = set(agent_capabilities)

        def capability_score(node: Node) -> tuple[int, int]:
            """Return (negative_exact_matches, priority_order) for sorting."""
            if not node.required_capabilities:
                priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                return (0, priority_order.get(node.priority, 99))
            exact_matches = len(set(node.required_capabilities) & agent_caps)
            # Sort by exact matches (descending), then by priority
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            return (-exact_matches, priority_order.get(node.priority, 99))

        tasks.sort(key=capability_score)

        return tasks[:limit]

    def get_next_task_by_capability(
        self,
        agent_capabilities: list[str],
        agent_id: str | None = None,
        auto_claim: bool = False,
    ) -> Node | None:
        """
        Get next task matching agent capabilities.

        Args:
            agent_capabilities: List of agent's capabilities
            agent_id: Agent requesting task (uses default if not specified)
            auto_claim: Whether to automatically claim the task

        Returns:
            Next matching Node or None
        """
        agent_id = agent_id or self.agent_id
        tasks = self.get_tasks_by_capability(agent_capabilities, limit=1)

        if not tasks:
            return None

        task = tasks[0]

        if auto_claim and agent_id:
            self.claim_task(task.id, agent_id)
            # Reload to get updated state
            reloaded_task = self.graph.get(task.id)
            if reloaded_task:
                task = reloaded_task

        return task

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
        self, node_id: str, blocked_by: str, reason: str | None = None
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
            properties={"reason": reason} if reason else {},
        )
        node.add_edge(blocking_edge)

        self.graph.update(node)
        return True

    # =========================================================================
    # Step Operations
    # =========================================================================

    def complete_step(
        self, node_id: str, step_index: int, agent_id: str | None = None
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

    def add_step(self, node_id: str, description: str) -> bool:
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
    # Strategic Planning & Analytics
    # =========================================================================

    def find_bottlenecks(
        self, top_n: int = 5, status_filter: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Identify tasks blocking the most downstream work.

        Args:
            top_n: Maximum number of bottlenecks to return
            status_filter: Filter by status (default: ["in-progress", "todo", "blocked"])

        Returns:
            List of bottleneck tasks with impact metrics

        Example:
            >>> bottlenecks = agent.find_bottlenecks(top_n=3)
            >>> for bn in bottlenecks:
            ...     print(f"{bn['title']} blocks {bn['blocks_count']} tasks")
        """
        from htmlgraph.analytics.dependency import DependencyAnalytics

        analytics = DependencyAnalytics(self.graph)
        bottlenecks = analytics.find_bottlenecks(
            status_filter=status_filter, top_n=top_n
        )

        # Convert to agent-friendly dict format
        return [
            {
                "id": bn.id,
                "title": bn.title,
                "status": bn.status,
                "priority": bn.priority,
                "blocks_count": bn.transitive_blocking,
                "impact_score": bn.weighted_impact,
                "blocked_tasks": bn.blocked_nodes[:5],  # Limit for readability
            }
            for bn in bottlenecks
        ]

    def get_parallel_work(
        self, status: str = "todo", max_agents: int = 5
    ) -> dict[str, Any]:
        """
        Find tasks that can be worked on simultaneously.

        Args:
            status: Filter by status (default: "todo")
            max_agents: Maximum number of parallel agents to plan for

        Returns:
            Dict with parallelization opportunities

        Example:
            >>> parallel = agent.get_parallel_work(max_agents=3)
            >>> print(f"Can work on {parallel['max_parallelism']} tasks at once")
            >>> print(f"Ready now: {parallel['ready_now']}")
        """
        from htmlgraph.analytics.dependency import DependencyAnalytics

        analytics = DependencyAnalytics(self.graph)
        report = analytics.find_parallelizable_work(status=status)

        ready_now = (
            report.dependency_levels[0].nodes if report.dependency_levels else []
        )

        return {
            "max_parallelism": report.max_parallelism,
            "ready_now": ready_now[:max_agents],
            "total_ready": len(ready_now),
            "level_count": len(report.dependency_levels),
            "next_level": report.dependency_levels[1].nodes
            if len(report.dependency_levels) > 1
            else [],
        }

    def recommend_next_work(
        self, agent_count: int = 1, lookahead: int = 5
    ) -> list[dict[str, Any]]:
        """
        Get smart recommendations for what to work on next.

        Considers priority, dependencies, and transitive impact.

        Args:
            agent_count: Number of agents/tasks to recommend
            lookahead: How many levels ahead to consider

        Returns:
            List of recommended tasks with reasoning

        Example:
            >>> recs = agent.recommend_next_work(agent_count=3)
            >>> for rec in recs:
            ...     print(f"{rec['title']} (score: {rec['score']})")
            ...     print(f"  Reasons: {rec['reasons']}")
        """
        from htmlgraph.analytics.dependency import DependencyAnalytics

        analytics = DependencyAnalytics(self.graph)
        recommendations = analytics.recommend_next_tasks(
            agent_count=agent_count, lookahead=lookahead
        )

        return [
            {
                "id": rec.id,
                "title": rec.title,
                "priority": rec.priority,
                "score": rec.score,
                "reasons": rec.reasons,
                "estimated_hours": rec.estimated_effort,
                "unlocks_count": len(rec.unlocks),
                "unlocks": rec.unlocks[:3],  # Show first 3
            }
            for rec in recommendations.recommendations
        ]

    def assess_risks(self) -> dict[str, Any]:
        """
        Assess dependency-related risks in the project.

        Identifies single points of failure, circular dependencies,
        and orphaned tasks.

        Returns:
            Dict with risk assessment results

        Example:
            >>> risks = agent.assess_risks()
            >>> if risks['high_risk_count'] > 0:
            ...     print(f"Warning: {risks['high_risk_count']} high-risk tasks")
            >>> if risks['circular_dependencies']:
            ...     print(f"Found {len(risks['circular_dependencies'])} cycles")
        """
        from htmlgraph.analytics.dependency import DependencyAnalytics

        analytics = DependencyAnalytics(self.graph)
        risk = analytics.assess_dependency_risk()

        return {
            "high_risk_count": len(risk.high_risk),
            "high_risk_tasks": [
                {
                    "id": node.id,
                    "title": node.title,
                    "risk_score": node.risk_score,
                    "risk_factors": [f.description for f in node.risk_factors],
                }
                for node in risk.high_risk
            ],
            "circular_dependencies": risk.circular_dependencies,
            "orphaned_count": len(risk.orphaned_nodes),
            "orphaned_tasks": risk.orphaned_nodes[:5],  # First 5
            "recommendations": risk.recommendations,
        }

    def analyze_impact(self, node_id: str) -> dict[str, Any]:
        """
        Analyze the impact of completing a specific task.

        Shows what downstream work will be unblocked.

        Args:
            node_id: Task to analyze

        Returns:
            Dict with impact analysis

        Example:
            >>> impact = agent.analyze_impact("feature-001")
            >>> print(f"Completing this unlocks {impact['unlocks_count']} tasks")
            >>> print(f"Impact: {impact['completion_impact']}% of remaining work")
        """
        from htmlgraph.analytics.dependency import DependencyAnalytics

        analytics = DependencyAnalytics(self.graph)
        impact = analytics.impact_analysis(node_id)

        return {
            "node_id": node_id,
            "direct_dependents": impact.direct_dependents,
            "total_impact": impact.transitive_dependents,
            "completion_impact": impact.completion_impact,
            "unlocks_count": len(impact.affected_nodes),
            "affected_tasks": impact.affected_nodes[:10],  # First 10
        }

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
        steps: list[str] | None = None,
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
            priority=cast(Literal["low", "medium", "high", "critical"], priority),
            content=f"<p>{description}</p>" if description else "",
            steps=[Step(description=s) for s in (steps or [])],
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
            "tasks": [t.id for t in in_progress],
        }

    # =========================================================================
    # Smart Routing & Capability Matching (Phase 3)
    # =========================================================================

    def calculate_task_score(
        self, task: Node, agent: AgentProfile, current_workload: int = 0
    ) -> float:
        """
        Calculate routing score for a task-agent pair.

        Higher score = better match.

        Args:
            task: Task to score
            agent: Agent profile
            current_workload: Current number of tasks assigned to agent

        Returns:
            Score (0-100)
        """
        score = 0.0

        # Priority score (0-30 points)
        priority_scores = {"critical": 30, "high": 20, "medium": 10, "low": 5}
        score += priority_scores.get(task.priority, 5)

        # Capability match score (0-40 points)
        if task.required_capabilities:
            if agent.can_handle(task.required_capabilities):
                # Perfect match gets 40 points
                score += 40
                # Bonus for exact capability match (no extra capabilities)
                matching_caps = sum(
                    1 for cap in task.required_capabilities if cap in agent.capabilities
                )
                score += (matching_caps / len(task.required_capabilities)) * 5
            else:
                # No match = very low score
                score = max(score - 30, 0)

        # Complexity match score (0-20 points)
        task_complexity = getattr(task, "complexity", None)
        if task_complexity:
            if agent.can_handle_complexity(task_complexity):
                score += 20
                # Bonus for preferred complexity
                complexity_preference = {
                    "low": 2,
                    "medium": 5,
                    "high": 3,
                    "very-high": 1,
                }
                score += complexity_preference.get(task_complexity, 0)
            else:
                score = max(score - 15, 0)

        # Workload balancing (0-10 points)
        if current_workload < agent.max_parallel_tasks:
            workload_ratio = current_workload / agent.max_parallel_tasks
            score += (1 - workload_ratio) * 10
        else:
            # Agent is at or over capacity
            score = max(score - 20, 0)

        return score

    def get_agent_workload(self, agent_id: str) -> int:
        """Get current workload (in-progress tasks) for an agent."""
        in_progress = self.get_in_progress_tasks(agent_id)
        return len(in_progress)

    def find_best_match(
        self, task: Node, candidate_agents: list[str] | None = None
    ) -> tuple[str, float] | None:
        """
        Find the best agent for a task using smart routing.

        Args:
            task: Task to match
            candidate_agents: Optional list of agent IDs to consider (defaults to all active)

        Returns:
            Tuple of (agent_id, score) or None if no match
        """
        # Get candidate agents
        agents: list[AgentProfile]
        if candidate_agents:
            agents_maybe = [self.registry.get(aid) for aid in candidate_agents]
            agents = [a for a in agents_maybe if a and a.active]
        else:
            # Find capable agents based on requirements
            required_caps = getattr(task, "required_capabilities", None)
            if required_caps:
                agents = self.registry.find_capable_agents(
                    required_caps, getattr(task, "complexity", None)
                )
            else:
                # No requirements, all active agents
                agents = self.registry.list_agents(active_only=True)

        if not agents:
            return None

        # Score each agent
        best_agent = None
        best_score = 0.0

        for agent in agents:
            workload = self.get_agent_workload(agent.id)
            score = self.calculate_task_score(task, agent, workload)

            if score > best_score:
                best_score = score
                best_agent = agent.id

        if best_agent:
            return (best_agent, best_score)
        return None

    def get_work_queue(
        self, agent_id: str | None = None, limit: int = 10, min_score: float = 20.0
    ) -> list[dict[str, Any]]:
        """
        Get prioritized work queue for an agent using smart routing.

        Args:
            agent_id: Agent to get queue for (uses default if not specified)
            limit: Maximum tasks to return
            min_score: Minimum routing score to include

        Returns:
            List of tasks with routing scores, sorted by score (highest first)
        """
        agent_id = agent_id or self.agent_id
        if not agent_id:
            raise ValueError("agent_id required for work queue")

        agent = self.registry.get(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found in registry")

        # Get available tasks
        available = self.get_available_tasks(status="todo", limit=100)

        # Score each task
        queue = []
        workload = self.get_agent_workload(agent_id)

        for task in available:
            score = self.calculate_task_score(task, agent, workload)

            if score >= min_score:
                queue.append(
                    {
                        "task_id": task.id,
                        "title": task.title,
                        "priority": task.priority,
                        "status": task.status,
                        "score": round(score, 2),
                        "required_capabilities": getattr(
                            task, "required_capabilities", None
                        ),
                        "complexity": getattr(task, "complexity", None),
                        "estimated_effort": getattr(task, "estimated_effort", None),
                    }
                )

        # Sort by score (highest first)
        queue.sort(
            key=lambda x: float(x["score"]) if x["score"] is not None else 0.0,
            reverse=True,
        )

        return queue[:limit]

    def get_next_task_smart(
        self,
        agent_id: str | None = None,
        auto_claim: bool = False,
        min_score: float = 20.0,
    ) -> Node | None:
        """
        Get next task using smart routing based on capabilities.

        Args:
            agent_id: Agent requesting task (uses default if not specified)
            auto_claim: Whether to automatically claim the task
            min_score: Minimum routing score to accept

        Returns:
            Next best task or None
        """
        agent_id = agent_id or self.agent_id
        if not agent_id:
            raise ValueError("agent_id required")

        queue = self.get_work_queue(agent_id, limit=1, min_score=min_score)

        if not queue:
            return None

        task_id = queue[0]["task_id"]
        task = self.graph.get(task_id)

        if task and auto_claim:
            self.claim_task(task_id, agent_id)
            # Reload to get updated state
            task = self.graph.get(task_id)

        return task
