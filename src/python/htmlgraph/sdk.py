"""
HtmlGraph SDK - AI-Friendly Interface

Provides a fluent, ergonomic API for AI agents with:
- Auto-discovery of .htmlgraph directory
- Method chaining for all operations
- Context managers for auto-save
- Batch operations
- Minimal boilerplate

Example:
    from htmlgraph import SDK

    # Auto-discovers .htmlgraph directory
    sdk = SDK(agent="claude")

    # Fluent feature creation
    feature = sdk.features.create(
        title="User Authentication",
        track="auth"
    ).add_steps([
        "Create login endpoint",
        "Add JWT middleware",
        "Write tests"
    ]).set_priority("high").save()

    # Work on a feature
    with sdk.features.get("feature-001") as feature:
        feature.start()
        feature.complete_step(0)
        # Auto-saves on exit

    # Query
    todos = sdk.features.where(status="todo", priority="high")

    # Batch operations
    sdk.features.mark_done(["feat-001", "feat-002", "feat-003"])
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from htmlgraph.agent_detection import detect_agent_name
from htmlgraph.agents import AgentInterface
from htmlgraph.analytics import Analytics, DependencyAnalytics
from htmlgraph.collections import (
    BaseCollection,
    BugCollection,
    ChoreCollection,
    EpicCollection,
    FeatureCollection,
    PhaseCollection,
    SpikeCollection,
)
from htmlgraph.collections.insight import InsightCollection
from htmlgraph.collections.metric import MetricCollection
from htmlgraph.collections.pattern import PatternCollection
from htmlgraph.context_analytics import ContextAnalytics
from htmlgraph.graph import HtmlGraph
from htmlgraph.models import Node, Step
from htmlgraph.session_manager import SessionManager
from htmlgraph.track_builder import TrackCollection
from htmlgraph.types import (
    ActiveWorkItem,
    BottleneckDict,
    SessionStartInfo,
)


class SDK:
    """
    Main SDK interface for AI agents.

    Auto-discovers .htmlgraph directory and provides fluent API for all collections.

    Available Collections:
        - features: Feature work items with builder support
        - bugs: Bug reports
        - chores: Maintenance and chore tasks
        - spikes: Investigation and research spikes
        - epics: Large bodies of work
        - phases: Project phases
        - sessions: Agent sessions
        - tracks: Work tracks
        - agents: Agent information

    Error Handling Patterns
    =======================

    SDK methods follow consistent error handling patterns by operation type:

    LOOKUP OPERATIONS (Return None):
        Single-item lookups return None when not found.
        Always check the result before using.

        >>> feature = sdk.features.get("nonexistent")
        >>> if feature:
        ...     print(feature.title)
        ... else:
        ...     print("Not found")

    QUERY OPERATIONS (Return Empty List):
        Queries return empty list when no matches or on error.
        Safe to iterate without checking.

        >>> results = sdk.features.where(status="impossible")
        >>> for r in results:  # Empty iteration is safe
        ...     print(r.title)

    EDIT OPERATIONS (Raise Exception):
        Edit operations raise NodeNotFoundError when target missing.
        Use try/except to handle gracefully.

        >>> from htmlgraph.exceptions import NodeNotFoundError
        >>> try:
        ...     with sdk.features.edit("nonexistent") as f:
        ...         f.status = "done"
        ... except NodeNotFoundError:
        ...     print("Feature not found")

    CREATE OPERATIONS (Raise on Validation):
        Create operations raise ValidationError on invalid input.

        >>> try:
        ...     sdk.features.create("")  # Empty title
        ... except ValidationError:
        ...     print("Title required")

    BATCH OPERATIONS (Return Count):
        Batch operations return count of successful items.
        Silently skip items that fail.

        >>> count = sdk.features.mark_done(["feat-1", "missing", "feat-2"])
        >>> print(f"Completed {count} of 3")  # Outputs: Completed 2 of 3

    Pattern Summary:
        | Operation Type | Error Behavior      | Example Method        |
        |----------------|--------------------|-----------------------|
        | Lookup         | Return None        | .get(id)              |
        | Query          | Return []          | .where(), .all()      |
        | Edit           | Raise Exception    | .edit(id)             |
        | Create         | Raise on Invalid   | .create(title)        |
        | Batch          | Return Count       | .mark_done([ids])     |
        | Delete         | Return Bool        | .delete(id)           |

    Available Exceptions:
        - NodeNotFoundError: Node with ID not found
        - ValidationError: Invalid input parameters
        - ClaimConflictError: Node already claimed by another agent

    Example:
        sdk = SDK(agent="claude")

        # Work with features (has builder support)
        feature = sdk.features.create("User Auth")
            .set_priority("high")
            .add_steps(["Login", "Logout"])
            .save()

        # Work with bugs
        high_bugs = sdk.bugs.where(status="todo", priority="high")
        with sdk.bugs.edit("bug-001") as bug:
            bug.status = "in-progress"

        # Work with any collection
        all_spikes = sdk.spikes.all()
        sdk.chores.mark_done(["chore-001", "chore-002"])
        sdk.epics.assign(["epic-001"], agent="claude")
    """

    def __init__(self, directory: Path | str | None = None, agent: str | None = None):
        """
        Initialize SDK.

        Args:
            directory: Path to .htmlgraph directory (auto-discovered if not provided)
            agent: Agent identifier for operations
        """
        if directory is None:
            directory = self._discover_htmlgraph()

        if agent is None:
            agent = detect_agent_name()

        self._directory = Path(directory)
        self._agent_id = agent

        # Initialize SessionManager for smart tracking and attribution
        self.session_manager = SessionManager(self._directory)

        # Initialize underlying components (for backward compatibility)
        self._graph = HtmlGraph(self._directory / "features")
        self._agent_interface = AgentInterface(
            self._directory / "features", agent_id=agent
        )

        # Collection interfaces - all work item types (all with builder support)
        self.features = FeatureCollection(self)
        self.bugs = BugCollection(self)
        self.chores = ChoreCollection(self)
        self.spikes = SpikeCollection(self)
        self.epics = EpicCollection(self)
        self.phases = PhaseCollection(self)

        # Non-work collections
        self.sessions: BaseCollection = BaseCollection(self, "sessions", "session")
        self.tracks: TrackCollection = TrackCollection(
            self
        )  # Use specialized collection with builder support
        self.agents: BaseCollection = BaseCollection(self, "agents", "agent")

        # Learning collections (Active Learning Persistence)
        self.patterns = PatternCollection(self)
        self.insights = InsightCollection(self)
        self.metrics = MetricCollection(self)

        # Create learning directories if needed
        (self._directory / "patterns").mkdir(exist_ok=True)
        (self._directory / "insights").mkdir(exist_ok=True)
        (self._directory / "metrics").mkdir(exist_ok=True)

        # Analytics interface (Phase 2: Work Type Analytics)
        self.analytics = Analytics(self)

        # Dependency analytics interface (Advanced graph analytics)
        self.dep_analytics = DependencyAnalytics(self._graph)

        # Context analytics interface (Context usage tracking)
        self.context = ContextAnalytics(self)

        # Lazy-loaded orchestrator for subagent management
        self._orchestrator = None

    @staticmethod
    def _discover_htmlgraph() -> Path:
        """
        Auto-discover .htmlgraph directory.

        Searches current directory and parents.
        """
        current = Path.cwd()

        # Check current directory
        if (current / ".htmlgraph").exists():
            return current / ".htmlgraph"

        # Check parent directories
        for parent in current.parents:
            if (parent / ".htmlgraph").exists():
                return parent / ".htmlgraph"

        # Default to current directory
        return current / ".htmlgraph"

    @property
    def agent(self) -> str | None:
        """Get current agent ID."""
        return self._agent_id

    def reload(self) -> None:
        """Reload all data from disk."""
        self._graph.reload()
        self._agent_interface.reload()
        # SessionManager reloads implicitly on access via its converters/graphs

    def summary(self, max_items: int = 10) -> str:
        """
        Get project summary.

        Returns:
            Compact overview for AI agent orientation
        """
        return self._agent_interface.get_summary(max_items)

    def my_work(self) -> dict[str, Any]:
        """
        Get current agent's workload.

        Returns:
            Dict with in_progress, completed counts
        """
        if not self._agent_id:
            raise ValueError("No agent ID set")
        return self._agent_interface.get_workload(self._agent_id)

    def next_task(
        self, priority: str | None = None, auto_claim: bool = True
    ) -> Node | None:
        """
        Get next available task for this agent.

        Args:
            priority: Optional priority filter
            auto_claim: Automatically claim the task

        Returns:
            Next available Node or None
        """
        return self._agent_interface.get_next_task(
            agent_id=self._agent_id,
            priority=priority,
            node_type="feature",
            auto_claim=auto_claim,
        )

    def set_session_handoff(
        self,
        handoff_notes: str | None = None,
        recommended_next: str | None = None,
        blockers: list[str] | None = None,
        session_id: str | None = None,
    ) -> Any:
        """
        Set handoff context on a session.

        Args:
            handoff_notes: Notes for next session/agent
            recommended_next: Suggested next steps
            blockers: List of blockers
            session_id: Specific session ID (defaults to active session)

        Returns:
            Updated Session or None if not found
        """
        if not session_id:
            if self._agent_id:
                active = self.session_manager.get_active_session_for_agent(
                    self._agent_id
                )
            else:
                active = self.session_manager.get_active_session()
            if not active:
                return None
            session_id = active.id

        return self.session_manager.set_session_handoff(
            session_id=session_id,
            handoff_notes=handoff_notes,
            recommended_next=recommended_next,
            blockers=blockers,
        )

    def start_session(
        self,
        session_id: str | None = None,
        title: str | None = None,
        agent: str | None = None,
    ) -> Any:
        """
        Start a new session.

        Args:
            session_id: Optional session ID
            title: Optional session title
            agent: Optional agent override (defaults to SDK agent)

        Returns:
            New Session instance
        """
        return self.session_manager.start_session(
            session_id=session_id, agent=agent or self._agent_id or "cli", title=title
        )

    def end_session(
        self,
        session_id: str,
        handoff_notes: str | None = None,
        recommended_next: str | None = None,
        blockers: list[str] | None = None,
    ) -> Any:
        """
        End a session.

        Args:
            session_id: Session ID to end
            handoff_notes: Optional handoff notes
            recommended_next: Optional recommendations
            blockers: Optional blockers

        Returns:
            Ended Session instance
        """
        return self.session_manager.end_session(
            session_id=session_id,
            handoff_notes=handoff_notes,
            recommended_next=recommended_next,
            blockers=blockers,
        )

    def get_status(self) -> dict[str, Any]:
        """
        Get project status.

        Returns:
            Dict with status metrics (WIP, counts, etc.)
        """
        return self.session_manager.get_status()

    def dedupe_sessions(
        self,
        max_events: int = 1,
        move_dir_name: str = "_orphans",
        dry_run: bool = False,
        stale_extra_active: bool = True,
    ) -> dict[str, int]:
        """
        Move low-signal sessions (e.g. SessionStart-only) out of the main sessions dir.

        Args:
            max_events: Maximum events threshold (sessions with <= this many events are moved)
            move_dir_name: Directory name to move orphaned sessions to
            dry_run: If True, only report what would be done without actually moving files
            stale_extra_active: If True, also mark extra active sessions as stale

        Returns:
            Dict with counts: {"scanned": int, "moved": int, "missing": int, "staled_active": int, "kept_active": int}

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.dedupe_sessions(max_events=1, dry_run=False)
            >>> print(f"Scanned: {result['scanned']}, Moved: {result['moved']}")
        """
        return self.session_manager.dedupe_orphan_sessions(
            max_events=max_events,
            move_dir_name=move_dir_name,
            dry_run=dry_run,
            stale_extra_active=stale_extra_active,
        )

    def track_activity(
        self,
        tool: str,
        summary: str,
        file_paths: list[str] | None = None,
        success: bool = True,
        feature_id: str | None = None,
        session_id: str | None = None,
        parent_activity_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        """
        Track an activity in the current or specified session.

        Args:
            tool: Tool name (Edit, Bash, Read, etc.)
            summary: Human-readable summary of the activity
            file_paths: Files involved in this activity
            success: Whether the tool call succeeded
            feature_id: Explicit feature ID (skips attribution if provided)
            session_id: Session ID (defaults to active session for current agent)
            parent_activity_id: ID of parent activity (e.g., Skill/Task invocation)
            payload: Optional rich payload data

        Returns:
            Created ActivityEntry with attribution

        Example:
            >>> sdk = SDK(agent="claude")
            >>> entry = sdk.track_activity(
            ...     tool="CustomTool",
            ...     summary="Performed custom analysis",
            ...     file_paths=["src/main.py"],
            ...     success=True
            ... )
            >>> print(f"Tracked: [{entry.tool}] {entry.summary}")
        """
        # Find active session if not specified
        if not session_id:
            active = self.session_manager.get_active_session(agent=self._agent_id)
            if not active:
                raise ValueError(
                    "No active session. Start one with sdk.start_session()"
                )
            session_id = active.id

        return self.session_manager.track_activity(
            session_id=session_id,
            tool=tool,
            summary=summary,
            file_paths=file_paths,
            success=success,
            feature_id=feature_id,
            parent_activity_id=parent_activity_id,
            payload=payload,
        )

    # =========================================================================
    # Strategic Planning & Analytics (Agent-Friendly Interface)
    # =========================================================================

    def find_bottlenecks(self, top_n: int = 5) -> list[BottleneckDict]:
        """
        Identify tasks blocking the most downstream work.

        Note: Prefer using sdk.dep_analytics.find_bottlenecks() directly.
        This method exists for backward compatibility.

        Args:
            top_n: Maximum number of bottlenecks to return

        Returns:
            List of bottleneck tasks with impact metrics

        Example:
            >>> sdk = SDK(agent="claude")
            >>> # Preferred approach
            >>> bottlenecks = sdk.dep_analytics.find_bottlenecks(top_n=3)
            >>> # Or via SDK (backward compatibility)
            >>> bottlenecks = sdk.find_bottlenecks(top_n=3)
            >>> for bn in bottlenecks:
            ...     print(f"{bn['title']} blocks {bn['blocks_count']} tasks")
        """
        bottlenecks = self.dep_analytics.find_bottlenecks(top_n=top_n)

        # Convert to agent-friendly dict format for backward compatibility
        return [
            {
                "id": bn.id,
                "title": bn.title,
                "status": bn.status,
                "priority": bn.priority,
                "blocks_count": bn.transitive_blocking,
                "impact_score": bn.weighted_impact,
                "blocked_tasks": bn.blocked_nodes[:5],
            }
            for bn in bottlenecks
        ]

    def get_parallel_work(self, max_agents: int = 5) -> dict[str, Any]:
        """
        Find tasks that can be worked on simultaneously.

        Note: Prefer using sdk.dep_analytics.find_parallelizable_work() directly.
        This method exists for backward compatibility.

        Args:
            max_agents: Maximum number of parallel agents to plan for

        Returns:
            Dict with parallelization opportunities

        Example:
            >>> sdk = SDK(agent="claude")
            >>> # Preferred approach
            >>> report = sdk.dep_analytics.find_parallelizable_work(status="todo")
            >>> # Or via SDK (backward compatibility)
            >>> parallel = sdk.get_parallel_work(max_agents=3)
            >>> print(f"Can work on {parallel['max_parallelism']} tasks at once")
            >>> print(f"Ready now: {parallel['ready_now']}")
        """
        report = self.dep_analytics.find_parallelizable_work(status="todo")

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

    def recommend_next_work(self, agent_count: int = 1) -> list[dict[str, Any]]:
        """
        Get smart recommendations for what to work on next.

        Note: Prefer using sdk.dep_analytics.recommend_next_tasks() directly.
        This method exists for backward compatibility.

        Considers priority, dependencies, and transitive impact.

        Args:
            agent_count: Number of agents/tasks to recommend

        Returns:
            List of recommended tasks with reasoning

        Example:
            >>> sdk = SDK(agent="claude")
            >>> # Preferred approach
            >>> recs = sdk.dep_analytics.recommend_next_tasks(agent_count=3)
            >>> # Or via SDK (backward compatibility)
            >>> recs = sdk.recommend_next_work(agent_count=3)
            >>> for rec in recs:
            ...     print(f"{rec['title']} (score: {rec['score']})")
            ...     print(f"  Reasons: {rec['reasons']}")
        """
        recommendations = self.dep_analytics.recommend_next_tasks(
            agent_count=agent_count, lookahead=5
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
                "unlocks": rec.unlocks[:3],
            }
            for rec in recommendations.recommendations
        ]

    def assess_risks(self) -> dict[str, Any]:
        """
        Assess dependency-related risks in the project.

        Note: Prefer using sdk.dep_analytics.assess_dependency_risk() directly.
        This method exists for backward compatibility.

        Identifies single points of failure, circular dependencies,
        and orphaned tasks.

        Returns:
            Dict with risk assessment results

        Example:
            >>> sdk = SDK(agent="claude")
            >>> # Preferred approach
            >>> risk = sdk.dep_analytics.assess_dependency_risk()
            >>> # Or via SDK (backward compatibility)
            >>> risks = sdk.assess_risks()
            >>> if risks['high_risk_count'] > 0:
            ...     print(f"Warning: {risks['high_risk_count']} high-risk tasks")
        """
        risk = self.dep_analytics.assess_dependency_risk()

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
            "orphaned_tasks": risk.orphaned_nodes[:5],
            "recommendations": risk.recommendations,
        }

    def analyze_impact(self, node_id: str) -> dict[str, Any]:
        """
        Analyze the impact of completing a specific task.

        Note: Prefer using sdk.dep_analytics.impact_analysis() directly.
        This method exists for backward compatibility.

        Args:
            node_id: Task to analyze

        Returns:
            Dict with impact analysis

        Example:
            >>> sdk = SDK(agent="claude")
            >>> # Preferred approach
            >>> impact = sdk.dep_analytics.impact_analysis("feature-001")
            >>> # Or via SDK (backward compatibility)
            >>> impact = sdk.analyze_impact("feature-001")
            >>> print(f"Completing this unlocks {impact['unlocks_count']} tasks")
        """
        impact = self.dep_analytics.impact_analysis(node_id)

        return {
            "node_id": node_id,
            "direct_dependents": impact.direct_dependents,
            "total_impact": impact.transitive_dependents,
            "completion_impact": impact.completion_impact,
            "unlocks_count": len(impact.affected_nodes),
            "affected_tasks": impact.affected_nodes[:10],
        }

    def get_work_queue(
        self, agent_id: str | None = None, limit: int = 10, min_score: float = 0.0
    ) -> list[dict[str, Any]]:
        """
        Get prioritized work queue showing recommended work, active work, and dependencies.

        This method provides a comprehensive view of:
        1. Recommended next work (using smart analytics)
        2. Active work by all agents
        3. Blocked items and what's blocking them
        4. Priority-based scoring

        Args:
            agent_id: Agent to get queue for (defaults to SDK agent)
            limit: Maximum number of items to return (default: 10)
            min_score: Minimum score threshold (default: 0.0)

        Returns:
            List of work queue items with scoring and metadata:
                - task_id: Work item ID
                - title: Work item title
                - status: Current status
                - priority: Priority level
                - score: Routing score
                - complexity: Complexity level (if set)
                - effort: Estimated effort (if set)
                - blocks_count: Number of tasks this blocks (if any)
                - blocked_by: List of blocking task IDs (if blocked)
                - agent_assigned: Current assignee (if any)
                - type: Work item type (feature, bug, spike, etc.)

        Example:
            >>> sdk = SDK(agent="claude")
            >>> queue = sdk.get_work_queue(limit=5)
            >>> for item in queue:
            ...     print(f"{item['score']:.1f} - {item['title']}")
            ...     if item.get('blocked_by'):
            ...         print(f"  ⚠️  Blocked by: {', '.join(item['blocked_by'])}")
        """
        from htmlgraph.routing import AgentCapabilityRegistry, CapabilityMatcher

        agent = agent_id or self._agent_id or "cli"

        # Get all work item types
        all_work = []
        for collection_name in ["features", "bugs", "spikes", "chores", "epics"]:
            collection = getattr(self, collection_name, None)
            if collection:
                # Get todo and blocked items
                for item in collection.where(status="todo"):
                    all_work.append(item)
                for item in collection.where(status="blocked"):
                    all_work.append(item)

        if not all_work:
            return []

        # Get recommendations from analytics (uses strategic scoring)
        recommendations = self.recommend_next_work(agent_count=limit * 2)
        rec_scores = {rec["id"]: rec["score"] for rec in recommendations}

        # Build routing registry
        registry = AgentCapabilityRegistry()

        # Register current agent
        registry.register_agent(agent, capabilities=[], wip_limit=5)

        # Get current WIP count for agent
        wip_count = len(self.features.where(status="in-progress", agent_assigned=agent))
        registry.set_wip(agent, wip_count)

        # Score each work item
        queue_items = []
        for item in all_work:
            # Use strategic score if available, otherwise use routing score
            if item.id in rec_scores:
                score = rec_scores[item.id]
            else:
                # Fallback to routing score
                agent_profile = registry.get_agent(agent)
                if agent_profile:
                    score = CapabilityMatcher.score_agent_task_fit(agent_profile, item)
                else:
                    score = 0.0

            # Apply minimum score filter
            if score < min_score:
                continue

            # Build queue item
            queue_item = {
                "task_id": item.id,
                "title": item.title,
                "status": item.status,
                "priority": item.priority,
                "score": score,
                "type": item.type,
                "complexity": getattr(item, "complexity", None),
                "effort": getattr(item, "estimated_effort", None),
                "agent_assigned": getattr(item, "agent_assigned", None),
                "blocks_count": 0,
                "blocked_by": [],
            }

            # Add dependency information
            if hasattr(item, "edges"):
                # Check if this item blocks others
                blocks = item.edges.get("blocks", [])
                queue_item["blocks_count"] = len(blocks)

                # Check if this item is blocked
                blocked_by = item.edges.get("blocked_by", [])
                queue_item["blocked_by"] = blocked_by

            queue_items.append(queue_item)

        # Sort by score (descending)
        queue_items.sort(key=lambda x: x["score"], reverse=True)

        # Limit results
        return queue_items[:limit]

    def work_next(
        self,
        agent_id: str | None = None,
        auto_claim: bool = False,
        min_score: float = 0.0,
    ) -> Node | None:
        """
        Get the next best task for an agent using smart routing.

        Uses both strategic analytics and capability-based routing to find
        the optimal next task.

        Args:
            agent_id: Agent to get task for (defaults to SDK agent)
            auto_claim: Automatically claim the task (default: False)
            min_score: Minimum score threshold (default: 0.0)

        Returns:
            Next best Node or None if no suitable task found

        Example:
            >>> sdk = SDK(agent="claude")
            >>> task = sdk.work_next(auto_claim=True)
            >>> if task:
            ...     print(f"Working on: {task.title}")
            ...     # Task is automatically claimed and assigned
        """
        agent = agent_id or self._agent_id or "cli"

        # Get work queue
        queue = self.get_work_queue(agent_id=agent, limit=1, min_score=min_score)

        if not queue:
            return None

        # Get the top task
        top_item = queue[0]

        # Fetch the actual node
        task = None
        for collection_name in ["features", "bugs", "spikes", "chores", "epics"]:
            collection = getattr(self, collection_name, None)
            if collection:
                try:
                    task = collection.get(top_item["task_id"])
                    if task:
                        break
                except (ValueError, FileNotFoundError):
                    continue

        if not task:
            return None

        # Auto-claim if requested
        if auto_claim and task.status == "todo" and collection is not None:
            # Claim the task
            # collection.edit returns context manager or None
            task_editor: Any = collection.edit(task.id)
            if task_editor is not None:
                # collection.edit returns context manager
                with task_editor as t:
                    t.status = "in-progress"
                    t.agent_assigned = agent

        result: Node | None = task
        return result

    # =========================================================================
    # Planning Workflow Integration
    # =========================================================================

    def start_planning_spike(
        self,
        title: str,
        context: str = "",
        timebox_hours: float = 4.0,
        auto_start: bool = True,
    ) -> Node:
        """
        Create a planning spike to research and design before implementation.

        This is for timeboxed investigation before creating a full track.

        Args:
            title: Spike title (e.g., "Plan User Authentication System")
            context: Background information
            timebox_hours: Time limit for spike (default: 4 hours)
            auto_start: Automatically start the spike (default: True)

        Returns:
            Created spike Node

        Example:
            >>> sdk = SDK(agent="claude")
            >>> spike = sdk.start_planning_spike(
            ...     "Plan Real-time Notifications",
            ...     context="Users need live updates. Research options.",
            ...     timebox_hours=3.0
            ... )
        """
        from htmlgraph.ids import generate_id
        from htmlgraph.models import Spike, SpikeType

        # Create spike directly (SpikeBuilder doesn't exist yet)
        spike_id = generate_id(node_type="spike", title=title)
        spike = Spike(
            id=spike_id,
            title=title,
            type="spike",
            status="in-progress" if auto_start and self._agent_id else "todo",
            spike_type=SpikeType.ARCHITECTURAL,
            timebox_hours=int(timebox_hours),
            agent_assigned=self._agent_id if auto_start and self._agent_id else None,
            steps=[
                Step(description="Research existing solutions and patterns"),
                Step(description="Define requirements and constraints"),
                Step(description="Design high-level architecture"),
                Step(description="Identify dependencies and risks"),
                Step(description="Create implementation plan"),
            ],
            content=f"<p>{context}</p>" if context else "",
            edges={},
            properties={},
        )

        self._graph.add(spike)
        return spike

    def create_track_from_plan(
        self,
        title: str,
        description: str,
        spike_id: str | None = None,
        priority: str = "high",
        requirements: list[str | tuple[str, str]] | None = None,
        phases: list[tuple[str, list[str]]] | None = None,
    ) -> dict[str, Any]:
        """
        Create a track with spec and plan from planning results.

        Args:
            title: Track title
            description: Track description
            spike_id: Optional spike ID that led to this track
            priority: Track priority (default: "high")
            requirements: List of requirements (strings or (req, priority) tuples)
            phases: List of (phase_name, tasks) tuples for the plan

        Returns:
            Dict with track, spec, and plan details

        Example:
            >>> sdk = SDK(agent="claude")
            >>> track_info = sdk.create_track_from_plan(
            ...     title="User Authentication System",
            ...     description="OAuth 2.0 with JWT tokens",
            ...     requirements=[
            ...         ("OAuth 2.0 integration", "must-have"),
            ...         ("JWT token management", "must-have"),
            ...         "Password reset flow"
            ...     ],
            ...     phases=[
            ...         ("Phase 1: OAuth", ["Setup providers (2h)", "Callback (2h)"]),
            ...         ("Phase 2: JWT", ["Token signing (2h)", "Refresh (1.5h)"])
            ...     ]
            ... )
        """

        builder = (
            self.tracks.builder()
            .title(title)
            .description(description)
            .priority(priority)
        )

        # Add reference to planning spike if provided
        if spike_id:
            # Access internal data for track builder
            data: dict[str, Any] = builder._data  # type: ignore[attr-defined]
            data["properties"]["planning_spike"] = spike_id

        # Add spec if requirements provided
        if requirements:
            # Convert simple strings to (requirement, "must-have") tuples
            req_list = []
            for req in requirements:
                if isinstance(req, str):
                    req_list.append((req, "must-have"))
                else:
                    req_list.append(req)

            builder.with_spec(
                overview=description,
                context=f"Track created from planning spike: {spike_id}"
                if spike_id
                else "",
                requirements=req_list,
                acceptance_criteria=[],
            )

        # Add plan if phases provided
        if phases:
            builder.with_plan_phases(phases)

        track = builder.create()

        return {
            "track_id": track.id,
            "title": track.title,
            "has_spec": bool(requirements),
            "has_plan": bool(phases),
            "spike_id": spike_id,
            "priority": priority,
        }

    def smart_plan(
        self,
        description: str,
        create_spike: bool = True,
        timebox_hours: float = 4.0,
        research_completed: bool = False,
        research_findings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Smart planning workflow: analyzes project context and creates spike or track.

        This is the main entry point for planning new work. It:
        1. Checks current project state
        2. Provides context from strategic analytics
        3. Creates a planning spike or track as appropriate

        **IMPORTANT: Research Phase Required**
        For complex features, you should complete research BEFORE planning:
        1. Use /htmlgraph:research or WebSearch to gather best practices
        2. Document findings (libraries, patterns, anti-patterns)
        3. Pass research_completed=True and research_findings to this method
        4. This ensures planning is informed by industry best practices

        Research-first workflow:
            1. /htmlgraph:research "{topic}" → Gather external knowledge
            2. sdk.smart_plan(..., research_completed=True) → Plan with context
            3. Complete spike steps → Design solution
            4. Create track from plan → Structure implementation

        Args:
            description: What you want to plan (e.g., "User authentication system")
            create_spike: Create a spike for research (default: True)
            timebox_hours: If creating spike, time limit (default: 4 hours)
            research_completed: Whether research was performed (default: False)
            research_findings: Structured research findings (optional)

        Returns:
            Dict with planning context and created spike/track info

        Example:
            >>> sdk = SDK(agent="claude")
            >>> # WITH research (recommended for complex work)
            >>> research = {
            ...     "topic": "OAuth 2.0 best practices",
            ...     "sources_count": 5,
            ...     "recommended_library": "authlib",
            ...     "key_insights": ["Use PKCE", "Implement token rotation"]
            ... }
            >>> plan = sdk.smart_plan(
            ...     "User authentication system",
            ...     create_spike=True,
            ...     research_completed=True,
            ...     research_findings=research
            ... )
            >>> print(f"Created: {plan['spike_id']}")
            >>> print(f"Research informed: {plan['research_informed']}")
        """
        # Get project context from strategic analytics
        bottlenecks = self.find_bottlenecks(top_n=3)
        risks = self.assess_risks()
        parallel = self.get_parallel_work(max_agents=5)

        context = {
            "bottlenecks_count": len(bottlenecks),
            "high_risk_count": risks["high_risk_count"],
            "parallel_capacity": parallel["max_parallelism"],
            "description": description,
        }

        # Build context string with research info
        context_str = f"Project context:\n- {len(bottlenecks)} bottlenecks\n- {risks['high_risk_count']} high-risk items\n- {parallel['max_parallelism']} parallel capacity"

        if research_completed and research_findings:
            context_str += f"\n\nResearch completed:\n- Topic: {research_findings.get('topic', description)}"
            if "sources_count" in research_findings:
                context_str += f"\n- Sources: {research_findings['sources_count']}"
            if "recommended_library" in research_findings:
                context_str += (
                    f"\n- Recommended: {research_findings['recommended_library']}"
                )

        # Validation: warn if complex work planned without research
        is_complex = any(
            [
                "auth" in description.lower(),
                "security" in description.lower(),
                "real-time" in description.lower(),
                "websocket" in description.lower(),
                "oauth" in description.lower(),
                "performance" in description.lower(),
                "integration" in description.lower(),
            ]
        )

        warnings = []
        if is_complex and not research_completed:
            warnings.append(
                "⚠️  Complex feature detected without research. "
                "Consider using /htmlgraph:research first to gather best practices."
            )

        if create_spike:
            spike = self.start_planning_spike(
                title=f"Plan: {description}",
                context=context_str,
                timebox_hours=timebox_hours,
            )

            # Store research metadata in spike properties if provided
            if research_completed and research_findings:
                spike.properties["research_completed"] = True
                spike.properties["research_findings"] = research_findings
                self._graph.update(spike)

            result = {
                "type": "spike",
                "spike_id": spike.id,
                "title": spike.title,
                "status": spike.status,
                "timebox_hours": timebox_hours,
                "project_context": context,
                "research_informed": research_completed,
                "next_steps": [
                    "Research and design the solution"
                    if not research_completed
                    else "Design solution using research findings",
                    "Complete spike steps",
                    "Use SDK.create_track_from_plan() to create track",
                ],
            }

            if warnings:
                result["warnings"] = warnings

            return result
        else:
            # Direct track creation (for when you already know what to do)
            track_info = self.create_track_from_plan(
                title=description, description=f"Planned with context: {context}"
            )

            result = {
                "type": "track",
                **track_info,
                "project_context": context,
                "research_informed": research_completed,
                "next_steps": [
                    "Create features from track plan",
                    "Link features to track",
                    "Start implementation",
                ],
            }

            if warnings:
                result["warnings"] = warnings

            return result

    def plan_parallel_work(
        self,
        max_agents: int = 5,
        shared_files: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Plan and prepare parallel work execution.

        This integrates with smart_plan to enable parallel agent dispatch.
        Uses the 6-phase ParallelWorkflow:
        1. Pre-flight analysis (dependencies, risks)
        2. Context preparation (shared file caching)
        3. Prompt generation (for Task tool)

        Args:
            max_agents: Maximum parallel agents (default: 5)
            shared_files: Files to pre-cache for all agents

        Returns:
            Dict with parallel execution plan:
                - can_parallelize: Whether parallelization is recommended
                - analysis: Pre-flight analysis results
                - prompts: Ready-to-use Task tool prompts
                - recommendations: Optimization suggestions

        Example:
            >>> sdk = SDK(agent="orchestrator")
            >>> plan = sdk.plan_parallel_work(max_agents=3)
            >>> if plan["can_parallelize"]:
            ...     # Use prompts with Task tool
            ...     for p in plan["prompts"]:
            ...         Task(prompt=p["prompt"], description=p["description"])
        """
        from htmlgraph.parallel import ParallelWorkflow

        workflow = ParallelWorkflow(self)

        # Phase 1: Pre-flight analysis
        analysis = workflow.analyze(max_agents=max_agents)

        result = {
            "can_parallelize": analysis.can_parallelize,
            "max_parallelism": analysis.max_parallelism,
            "ready_tasks": analysis.ready_tasks,
            "blocked_tasks": analysis.blocked_tasks,
            "speedup_factor": analysis.speedup_factor,
            "recommendation": analysis.recommendation,
            "warnings": analysis.warnings,
            "prompts": [],
        }

        if not analysis.can_parallelize:
            result["reason"] = analysis.recommendation
            return result

        # Phase 2 & 3: Prepare tasks and generate prompts
        tasks = workflow.prepare_tasks(
            analysis.ready_tasks[:max_agents],
            shared_files=shared_files,
        )
        prompts = workflow.generate_prompts(tasks)

        result["prompts"] = prompts
        result["task_count"] = len(prompts)

        # Add efficiency guidelines
        result["guidelines"] = {
            "dispatch": "Send ALL Task calls in a SINGLE message for true parallelism",
            "patterns": [
                "Grep → Read (search before reading)",
                "Read → Edit → Bash (read, modify, test)",
                "Glob → Read (find files first)",
            ],
            "avoid": [
                "Sequential Task calls (loses parallelism)",
                "Read → Read → Read (cache instead)",
                "Edit → Edit → Edit (batch edits)",
            ],
        }

        return result

    def aggregate_parallel_results(
        self,
        agent_ids: list[str],
    ) -> dict[str, Any]:
        """
        Aggregate results from parallel agent execution.

        Call this after parallel agents complete to:
        - Collect health metrics
        - Detect anti-patterns
        - Identify conflicts
        - Generate recommendations

        Args:
            agent_ids: List of agent/transcript IDs to analyze

        Returns:
            Dict with aggregated results and validation

        Example:
            >>> # After parallel work completes
            >>> results = sdk.aggregate_parallel_results([
            ...     "agent-abc123",
            ...     "agent-def456",
            ...     "agent-ghi789",
            ... ])
            >>> print(f"Health: {results['avg_health_score']:.0%}")
            >>> print(f"Conflicts: {results['conflicts']}")
        """
        from htmlgraph.parallel import ParallelWorkflow

        workflow = ParallelWorkflow(self)

        # Phase 5: Aggregate
        aggregate = workflow.aggregate(agent_ids)

        # Phase 6: Validate
        validation = workflow.validate(aggregate)

        return {
            "total_agents": aggregate.total_agents,
            "successful": aggregate.successful,
            "failed": aggregate.failed,
            "total_duration_seconds": aggregate.total_duration_seconds,
            "parallel_speedup": aggregate.parallel_speedup,
            "avg_health_score": aggregate.avg_health_score,
            "total_anti_patterns": aggregate.total_anti_patterns,
            "files_modified": aggregate.files_modified,
            "conflicts": aggregate.conflicts,
            "recommendations": aggregate.recommendations,
            "validation": validation,
            "all_passed": all(validation.values()),
        }

    # =========================================================================
    # Subagent Orchestration
    # =========================================================================

    @property
    def orchestrator(self) -> Any:
        """
        Get the subagent orchestrator for spawning explorer/coder agents.

        Lazy-loaded on first access.

        Returns:
            SubagentOrchestrator instance

        Example:
            >>> sdk = SDK(agent="claude")
            >>> explorer = sdk.orchestrator.spawn_explorer(
            ...     task="Find all API endpoints",
            ...     scope="src/"
            ... )
        """
        if self._orchestrator is None:
            from htmlgraph.orchestrator import SubagentOrchestrator

            self._orchestrator = SubagentOrchestrator(self)  # type: ignore[assignment]
        return self._orchestrator

    def spawn_explorer(
        self,
        task: str,
        scope: str | None = None,
        patterns: list[str] | None = None,
        questions: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Spawn an explorer subagent for codebase discovery.

        Explorer agents are optimized for finding files, searching patterns,
        and mapping code without modifying anything.

        Args:
            task: What to explore/discover
            scope: Directory scope (e.g., "src/")
            patterns: Glob patterns to focus on
            questions: Specific questions to answer

        Returns:
            Dict with prompt ready for Task tool

        Note:
            Returns dict with 'prompt', 'description', 'subagent_type' keys.
            Returns empty dict if spawning fails.

        Example:
            >>> prompt = sdk.spawn_explorer(
            ...     task="Find all database models",
            ...     scope="src/models/",
            ...     questions=["What ORM is used?"]
            ... )
            >>> # Execute with Task tool
            >>> Task(prompt=prompt["prompt"], description=prompt["description"])

        See also:
            spawn_coder: Spawn implementation agent with feature context
            orchestrate: Full exploration + implementation workflow
        """
        subagent_prompt = self.orchestrator.spawn_explorer(
            task=task,
            scope=scope,
            patterns=patterns,
            questions=questions,
        )
        result: dict[str, Any] = subagent_prompt.to_task_kwargs()
        return result

    def spawn_coder(
        self,
        feature_id: str,
        context: str | None = None,
        files_to_modify: list[str] | None = None,
        test_command: str | None = None,
    ) -> dict[str, Any]:
        """
        Spawn a coder subagent for implementing changes.

        Coder agents are optimized for reading, modifying, and testing code.

        Args:
            feature_id: Feature being implemented
            context: Results from explorer (string summary)
            files_to_modify: Specific files to change
            test_command: Command to verify changes

        Returns:
            Dict with prompt ready for Task tool

        Note:
            Returns dict with 'prompt', 'description', 'subagent_type' keys.
            Requires valid feature_id. Returns empty dict if feature not found.

        Example:
            >>> prompt = sdk.spawn_coder(
            ...     feature_id="feat-add-auth",
            ...     context=explorer_results,
            ...     test_command="uv run pytest tests/auth/"
            ... )
            >>> Task(prompt=prompt["prompt"], description=prompt["description"])

        See also:
            spawn_explorer: Explore codebase before implementation
            orchestrate: Full exploration + implementation workflow
        """
        subagent_prompt = self.orchestrator.spawn_coder(
            feature_id=feature_id,
            context=context,
            files_to_modify=files_to_modify,
            test_command=test_command,
        )
        result: dict[str, Any] = subagent_prompt.to_task_kwargs()
        return result

    def orchestrate(
        self,
        feature_id: str,
        exploration_scope: str | None = None,
        test_command: str | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrate full feature implementation with explorer and coder.

        Generates prompts for a two-phase workflow:
        1. Explorer discovers relevant code and patterns
        2. Coder implements the feature based on explorer findings

        Args:
            feature_id: Feature to implement
            exploration_scope: Directory to explore
            test_command: Test command for verification

        Returns:
            Dict with explorer and coder prompts

        Example:
            >>> prompts = sdk.orchestrate(
            ...     "feat-add-caching",
            ...     exploration_scope="src/cache/",
            ...     test_command="uv run pytest tests/cache/"
            ... )
            >>> # Phase 1: Run explorer
            >>> Task(prompt=prompts["explorer"]["prompt"], ...)
            >>> # Phase 2: Run coder with explorer results
            >>> Task(prompt=prompts["coder"]["prompt"], ...)

        See also:
            spawn_explorer: Just the exploration phase
            spawn_coder: Just the implementation phase
        """
        prompts = self.orchestrator.orchestrate_feature(
            feature_id=feature_id,
            exploration_scope=exploration_scope,
            test_command=test_command,
        )
        return {
            "explorer": prompts["explorer"].to_task_kwargs(),
            "coder": prompts["coder"].to_task_kwargs(),
            "workflow": [
                "1. Execute explorer Task and collect results",
                "2. Parse explorer results for files and patterns",
                "3. Execute coder Task with explorer context",
                "4. Verify coder results and update feature status",
            ],
        }

    # =========================================================================
    # Session Management Optimization
    # =========================================================================

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
            >>> print(f"Project: {info['status']['total_nodes']} nodes")
            >>> print(f"WIP: {info['status']['in_progress_count']}")
            >>> if info.get('active_work'):
            ...     print(f"Active: {info['active_work']['title']}")
            >>> for bn in info['analytics']['bottlenecks']:
            ...     print(f"Bottleneck: {bn['title']}")
        """
        import subprocess

        result = {}

        # 1. Project status
        result["status"] = self.get_status()

        # 2. Active work item (validation status) - always include, even if None
        result["active_work"] = self.get_active_work_item()  # type: ignore[assignment]

        # 3. Features list (simplified)
        features_list: list[dict[str, object]] = []
        for feature in self.features.all():
            features_list.append(
                {
                    "id": feature.id,
                    "title": feature.title,
                    "status": feature.status,
                    "priority": feature.priority,
                    "steps_total": len(feature.steps),
                    "steps_completed": sum(1 for s in feature.steps if s.completed),
                }
            )
        result["features"] = features_list  # type: ignore[assignment]

        # 4. Sessions list (recent 20)
        sessions_list: list[dict[str, Any]] = []
        for session in self.sessions.all()[:20]:
            sessions_list.append(
                {
                    "id": session.id,
                    "status": session.status,
                    "agent": session.properties.get("agent", "unknown"),
                    "event_count": session.properties.get("event_count", 0),
                    "started": session.created.isoformat()
                    if hasattr(session, "created")
                    else None,
                }
            )
        result["sessions"] = sessions_list  # type: ignore[assignment]

        # 5. Git log (if requested)
        if include_git_log:
            try:
                git_result = subprocess.run(
                    ["git", "log", "--oneline", f"-{git_log_count}"],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=self._directory.parent,
                )
                git_lines: list[str] = git_result.stdout.strip().split("\n")
                result["git_log"] = git_lines  # type: ignore[assignment]
            except (subprocess.CalledProcessError, FileNotFoundError):
                empty_list: list[str] = []
                result["git_log"] = empty_list  # type: ignore[assignment]

        # 6. Strategic analytics
        result["analytics"] = {
            "bottlenecks": self.find_bottlenecks(top_n=analytics_top_n),
            "recommendations": self.recommend_next_work(agent_count=analytics_top_n),
            "parallel": self.get_parallel_work(max_agents=analytics_max_agents),
        }

        return result  # type: ignore[return-value]

    def get_active_work_item(
        self,
        agent: str | None = None,
        filter_by_agent: bool = False,
        work_types: list[str] | None = None,
    ) -> ActiveWorkItem | None:
        """
        Get the currently active work item (in-progress status).

        This is used by the PreToolUse validation hook to check if code changes
        have an active work item for attribution.

        Args:
            agent: Agent ID for filtering (optional)
            filter_by_agent: If True, filter by agent. If False (default), return any active work item
            work_types: Work item types to check (defaults to all: features, bugs, spikes, chores, epics)

        Returns:
            Dict with work item details or None if no active work item found:
                - id: Work item ID
                - title: Work item title
                - type: Work item type (feature, bug, spike, chore, epic)
                - status: Should be "in-progress"
                - agent: Assigned agent
                - steps_total: Total steps
                - steps_completed: Completed steps
                - auto_generated: (spikes only) True if auto-generated spike
                - spike_subtype: (spikes only) "session-init" or "transition"

        Example:
            >>> sdk = SDK(agent="claude")
            >>> # Get any active work item
            >>> active = sdk.get_active_work_item()
            >>> if active:
            ...     print(f"Working on: {active['title']}")
            ...
            >>> # Get only this agent's active work item
            >>> active = sdk.get_active_work_item(filter_by_agent=True)
        """
        # Default to all work item types
        if work_types is None:
            work_types = ["features", "bugs", "spikes", "chores", "epics"]

        # Search across all work item types
        active_items = []

        for work_type in work_types:
            collection = getattr(self, work_type, None)
            if collection is None:
                continue

            # Query for in-progress items
            in_progress = collection.where(status="in-progress")

            for item in in_progress:
                # Filter by agent if requested
                if filter_by_agent:
                    agent_id = agent or self._agent_id
                    if agent_id and hasattr(item, "agent_assigned"):
                        if item.agent_assigned != agent_id:
                            continue

                item_dict = {
                    "id": item.id,
                    "title": item.title,
                    "type": item.type,
                    "status": item.status,
                    "agent": getattr(item, "agent_assigned", None),
                    "steps_total": len(item.steps) if hasattr(item, "steps") else 0,
                    "steps_completed": sum(1 for s in item.steps if s.completed)
                    if hasattr(item, "steps")
                    else 0,
                }

                # Add spike-specific fields for auto-spike detection
                if item.type == "spike":
                    item_dict["auto_generated"] = getattr(item, "auto_generated", False)
                    item_dict["spike_subtype"] = getattr(item, "spike_subtype", None)

                active_items.append(item_dict)

        # Return first active item (primary work item)
        # TODO: In future, could support multiple active items or prioritization
        if active_items:
            return active_items[0]  # type: ignore[return-value]

        return None

    # =========================================================================
    # Help & Documentation
    # =========================================================================

    def help(self, topic: str | None = None) -> str:
        """
        Get help on SDK usage.

        Args:
            topic: Optional topic (e.g., 'features', 'sessions', 'analytics', 'orchestration')

        Returns:
            Formatted help text

        Example:
            >>> sdk = SDK(agent="claude")
            >>> print(sdk.help())  # List all topics
            >>> print(sdk.help('features'))  # Feature collection help
            >>> print(sdk.help('analytics'))  # Analytics help

        See also:
            Python's built-in help(sdk) for full API documentation
            sdk.features, sdk.bugs, sdk.spikes for work item managers
        """
        if topic is None:
            return self._help_index()
        return self._help_topic(topic)

    def _help_index(self) -> str:
        """Return overview of all available methods/collections."""
        return """HtmlGraph SDK - Quick Reference

COLLECTIONS (Work Items):
  sdk.features     - Feature work items with builder support
  sdk.bugs         - Bug reports
  sdk.spikes       - Investigation and research spikes
  sdk.chores       - Maintenance and chore tasks
  sdk.epics        - Large bodies of work
  sdk.phases       - Project phases

COLLECTIONS (Non-Work):
  sdk.sessions     - Agent sessions
  sdk.tracks       - Work tracks with builder support
  sdk.agents       - Agent information

LEARNING (Active Learning):
  sdk.patterns     - Workflow patterns (optimal/anti-pattern)
  sdk.insights     - Session health insights
  sdk.metrics      - Aggregated time-series metrics

CORE METHODS:
  sdk.summary()           - Get project summary
  sdk.my_work()           - Get current agent's workload
  sdk.next_task()         - Get next available task
  sdk.reload()            - Reload all data from disk

SESSION MANAGEMENT:
  sdk.start_session()     - Start a new session
  sdk.end_session()       - End a session
  sdk.track_activity()    - Track activity in session
  sdk.dedupe_sessions()   - Clean up low-signal sessions
  sdk.get_status()        - Get project status

STRATEGIC ANALYTICS:
  sdk.find_bottlenecks()     - Identify blocking tasks
  sdk.recommend_next_work()  - Get smart recommendations
  sdk.get_parallel_work()    - Find parallelizable work
  sdk.assess_risks()         - Assess dependency risks
  sdk.analyze_impact()       - Analyze task impact

WORK QUEUE:
  sdk.get_work_queue()    - Get prioritized work queue
  sdk.work_next()         - Get next best task (smart routing)

PLANNING WORKFLOW:
  sdk.smart_plan()              - Smart planning with research
  sdk.start_planning_spike()    - Create planning spike
  sdk.create_track_from_plan()  - Create track from plan
  sdk.plan_parallel_work()      - Plan parallel execution
  sdk.aggregate_parallel_results() - Aggregate parallel results

ORCHESTRATION:
  sdk.spawn_explorer()    - Spawn explorer subagent
  sdk.spawn_coder()       - Spawn coder subagent
  sdk.orchestrate()       - Orchestrate feature implementation

SESSION OPTIMIZATION:
  sdk.get_session_start_info() - Get comprehensive session start info
  sdk.get_active_work_item()   - Get currently active work item

ANALYTICS INTERFACES:
  sdk.analytics        - Work type analytics
  sdk.dep_analytics    - Dependency analytics
  sdk.context          - Context analytics

ERROR HANDLING:
  Lookup (.get)      - Returns None if not found
  Query (.where)     - Returns empty list on no matches
  Edit (.edit)       - Raises NodeNotFoundError if missing
  Batch (.mark_done) - Returns count of successful operations

For detailed help on a topic:
  sdk.help('features')      - Feature collection methods
  sdk.help('analytics')     - Analytics methods
  sdk.help('sessions')      - Session management
  sdk.help('orchestration') - Subagent orchestration
  sdk.help('planning')      - Planning workflow
"""

    def __dir__(self) -> list[str]:
        """Return attributes with most useful ones first for discoverability."""
        priority = [
            # Work item managers
            "features",
            "bugs",
            "spikes",
            "chores",
            "epics",
            "phases",
            # Non-work collections
            "tracks",
            "sessions",
            "agents",
            # Learning collections
            "patterns",
            "insights",
            "metrics",
            # Orchestration
            "spawn_explorer",
            "spawn_coder",
            "orchestrate",
            # Session management
            "get_session_start_info",
            "start_session",
            "end_session",
            # Strategic analytics
            "find_bottlenecks",
            "recommend_next_work",
            "get_parallel_work",
            # Work queue
            "get_work_queue",
            "work_next",
            # Help
            "help",
        ]
        # Get all attributes
        all_attrs = object.__dir__(self)
        # Separate into priority, regular, and dunder attributes
        regular = [a for a in all_attrs if not a.startswith("_") and a not in priority]
        dunder = [a for a in all_attrs if a.startswith("_")]
        # Return priority items first, then regular, then dunder
        return priority + regular + dunder

    def _help_topic(self, topic: str) -> str:
        """Return specific help for topic."""
        topic = topic.lower()

        if topic in ["feature", "features"]:
            return """FEATURES COLLECTION

Create and manage feature work items with builder support.

COMMON METHODS:
  sdk.features.create(title)     - Create new feature (returns builder)
  sdk.features.get(id)           - Get feature by ID
  sdk.features.all()             - Get all features
  sdk.features.where(**filters)  - Query features
  sdk.features.edit(id)          - Edit feature (context manager)
  sdk.features.mark_done(ids)    - Mark features as done
  sdk.features.assign(ids, agent) - Assign features to agent

BUILDER PATTERN:
  feature = (sdk.features.create("User Auth")
    .set_priority("high")
    .add_steps(["Login", "Logout", "Reset password"])
    .add_edge("blocked_by", "feat-database")
    .save())

QUERIES:
  high_priority = sdk.features.where(status="todo", priority="high")
  my_features = sdk.features.where(agent_assigned="claude")
  blocked = sdk.features.where(status="blocked")

CONTEXT MANAGER:
  with sdk.features.edit("feat-001") as f:
      f.status = "in-progress"
      f.complete_step(0)
      # Auto-saves on exit

See also: sdk.help('bugs'), sdk.help('spikes'), sdk.help('chores')
"""

        elif topic in ["bug", "bugs"]:
            return """BUGS COLLECTION

Create and manage bug reports.

COMMON METHODS:
  sdk.bugs.create(title)         - Create new bug (returns builder)
  sdk.bugs.get(id)               - Get bug by ID
  sdk.bugs.all()                 - Get all bugs
  sdk.bugs.where(**filters)      - Query bugs
  sdk.bugs.edit(id)              - Edit bug (context manager)

BUILDER PATTERN:
  bug = (sdk.bugs.create("Login fails on Safari")
    .set_priority("critical")
    .add_steps(["Reproduce", "Fix", "Test"])
    .save())

QUERIES:
  critical = sdk.bugs.where(priority="critical", status="todo")
  my_bugs = sdk.bugs.where(agent_assigned="claude")

See also: sdk.help('features'), sdk.help('spikes')
"""

        elif topic in ["spike", "spikes"]:
            return """SPIKES COLLECTION

Create and manage investigation/research spikes.

COMMON METHODS:
  sdk.spikes.create(title)       - Create new spike (returns builder)
  sdk.spikes.get(id)             - Get spike by ID
  sdk.spikes.all()               - Get all spikes
  sdk.spikes.where(**filters)    - Query spikes

BUILDER PATTERN:
  spike = (sdk.spikes.create("Research OAuth providers")
    .set_priority("high")
    .add_steps(["Research", "Document findings"])
    .save())

PLANNING SPIKES:
  spike = sdk.start_planning_spike(
      "Plan User Auth",
      context="Users need login",
      timebox_hours=4.0
  )

See also: sdk.help('planning'), sdk.help('features')
"""

        elif topic in ["chore", "chores"]:
            return """CHORES COLLECTION

Create and manage maintenance and chore tasks.

COMMON METHODS:
  sdk.chores.create(title)       - Create new chore (returns builder)
  sdk.chores.get(id)             - Get chore by ID
  sdk.chores.all()               - Get all chores
  sdk.chores.where(**filters)    - Query chores

BUILDER PATTERN:
  chore = (sdk.chores.create("Update dependencies")
    .set_priority("medium")
    .add_steps(["Run uv update", "Test", "Commit"])
    .save())

See also: sdk.help('features'), sdk.help('bugs')
"""

        elif topic in ["epic", "epics"]:
            return """EPICS COLLECTION

Create and manage large bodies of work.

COMMON METHODS:
  sdk.epics.create(title)        - Create new epic (returns builder)
  sdk.epics.get(id)              - Get epic by ID
  sdk.epics.all()                - Get all epics
  sdk.epics.where(**filters)     - Query epics

BUILDER PATTERN:
  epic = (sdk.epics.create("Authentication System")
    .set_priority("critical")
    .add_steps(["Design", "Implement", "Test", "Deploy"])
    .save())

See also: sdk.help('features'), sdk.help('tracks')
"""

        elif topic in ["track", "tracks"]:
            return """TRACKS COLLECTION

Create and manage work tracks with builder support.

COMMON METHODS:
  sdk.tracks.create(title)       - Create new track (returns builder)
  sdk.tracks.builder()           - Get track builder
  sdk.tracks.get(id)             - Get track by ID
  sdk.tracks.all()               - Get all tracks
  sdk.tracks.where(**filters)    - Query tracks

BUILDER PATTERN:
  track = (sdk.tracks.builder()
    .title("User Authentication")
    .description("OAuth 2.0 system")
    .priority("high")
    .with_spec(
        overview="OAuth integration",
        requirements=[("OAuth 2.0", "must-have")],
        acceptance_criteria=["Login works"]
    )
    .with_plan_phases([
        ("Phase 1", ["Setup (2h)", "Config (1h)"]),
        ("Phase 2", ["Testing (2h)"])
    ])
    .create())

FROM PLANNING:
  track_info = sdk.create_track_from_plan(
      title="User Auth",
      description="OAuth system",
      requirements=[("OAuth", "must-have")],
      phases=[("Phase 1", ["Setup", "Config"])]
  )

See also: sdk.help('planning'), sdk.help('features')
"""

        elif topic in ["session", "sessions"]:
            return """SESSION MANAGEMENT

Create and manage agent sessions.

SESSION METHODS:
  sdk.start_session(title=...)   - Start new session
  sdk.end_session(id)            - End session
  sdk.track_activity(...)        - Track activity in session
  sdk.dedupe_sessions(...)       - Clean up low-signal sessions
  sdk.get_status()               - Get project status

SESSION COLLECTION:
  sdk.sessions.get(id)           - Get session by ID
  sdk.sessions.all()             - Get all sessions
  sdk.sessions.where(**filters)  - Query sessions

TYPICAL WORKFLOW:
  # Session start hook handles this automatically
  session = sdk.start_session(title="Fix login bug")

  # Track activities (handled by hooks)
  sdk.track_activity(
      tool="Edit",
      summary="Fixed auth logic",
      file_paths=["src/auth.py"],
      success=True
  )

  # End session
  sdk.end_session(
      session.id,
      handoff_notes="Login bug fixed, needs testing"
  )

CLEANUP:
  # Remove orphaned sessions (<=1 event)
  result = sdk.dedupe_sessions(max_events=1, dry_run=False)

See also: sdk.help('analytics')
"""

        elif topic in ["analytic", "analytics", "strategic"]:
            return """STRATEGIC ANALYTICS

Find bottlenecks, recommend work, and assess risks.

DEPENDENCY ANALYTICS:
  bottlenecks = sdk.find_bottlenecks(top_n=5)
  # Returns tasks blocking the most work

  parallel = sdk.get_parallel_work(max_agents=5)
  # Returns tasks that can run simultaneously

  recs = sdk.recommend_next_work(agent_count=3)
  # Returns smart recommendations with scoring

  risks = sdk.assess_risks()
  # Returns high-risk tasks and circular deps

  impact = sdk.analyze_impact("feat-001")
  # Returns what unlocks if you complete this task

DIRECT ACCESS (preferred):
  sdk.dep_analytics.find_bottlenecks(top_n=5)
  sdk.dep_analytics.recommend_next_tasks(agent_count=3)
  sdk.dep_analytics.find_parallelizable_work(status="todo")
  sdk.dep_analytics.assess_dependency_risk()
  sdk.dep_analytics.impact_analysis("feat-001")

WORK TYPE ANALYTICS:
  sdk.analytics.get_wip_by_type()
  sdk.analytics.get_completion_rates()
  sdk.analytics.get_agent_workload()

CONTEXT ANALYTICS:
  sdk.context.track_usage(...)
  sdk.context.get_usage_report()

See also: sdk.help('planning'), sdk.help('work_queue')
"""

        elif topic in ["queue", "work_queue", "routing"]:
            return """WORK QUEUE & ROUTING

Get prioritized work using smart routing.

WORK QUEUE:
  queue = sdk.get_work_queue(limit=10, min_score=0.0)
  # Returns prioritized list with scores

  for item in queue:
      print(f"{item['score']:.1f} - {item['title']}")
      if item.get('blocked_by'):
          print(f"  Blocked by: {item['blocked_by']}")

SMART ROUTING:
  task = sdk.work_next(auto_claim=True, min_score=0.5)
  # Returns next best task using analytics + capabilities

  if task:
      print(f"Working on: {task.title}")
      # Task is auto-claimed and assigned

SIMPLE NEXT TASK:
  task = sdk.next_task(priority="high", auto_claim=True)
  # Simpler version without smart routing

See also: sdk.help('analytics')
"""

        elif topic in ["plan", "planning", "workflow"]:
            return """PLANNING WORKFLOW

Research, plan, and create tracks for new work.

SMART PLANNING:
  plan = sdk.smart_plan(
      "User authentication system",
      create_spike=True,
      timebox_hours=4.0,
      research_completed=True,  # IMPORTANT: Do research first!
      research_findings={
          "topic": "OAuth 2.0 best practices",
          "recommended_library": "authlib",
          "key_insights": ["Use PKCE", "Token rotation"]
      }
  )

PLANNING SPIKE:
  spike = sdk.start_planning_spike(
      "Plan Real-time Notifications",
      context="Users need live updates",
      timebox_hours=3.0
  )

CREATE TRACK FROM PLAN:
  track_info = sdk.create_track_from_plan(
      title="User Authentication",
      description="OAuth 2.0 with JWT",
      requirements=[
          ("OAuth 2.0 integration", "must-have"),
          ("JWT token management", "must-have")
      ],
      phases=[
          ("Phase 1: OAuth", ["Setup (2h)", "Callback (2h)"]),
          ("Phase 2: JWT", ["Token signing (2h)"])
      ]
  )

PARALLEL PLANNING:
  plan = sdk.plan_parallel_work(max_agents=3)
  if plan["can_parallelize"]:
      for p in plan["prompts"]:
          Task(prompt=p["prompt"])

  # After parallel work completes
  results = sdk.aggregate_parallel_results([
      "agent-1", "agent-2", "agent-3"
  ])

See also: sdk.help('tracks'), sdk.help('spikes')
"""

        elif topic in ["orchestration", "orchestrate", "subagent", "subagents"]:
            return """SUBAGENT ORCHESTRATION

Spawn explorer and coder subagents for complex work.

EXPLORER (Discovery):
  prompt = sdk.spawn_explorer(
      task="Find all API endpoints",
      scope="src/api/",
      patterns=["*.py"],
      questions=["What framework is used?"]
  )
  # Execute with Task tool
  Task(prompt=prompt["prompt"], description=prompt["description"])

CODER (Implementation):
  prompt = sdk.spawn_coder(
      feature_id="feat-add-auth",
      context=explorer_results,
      files_to_modify=["src/auth.py"],
      test_command="uv run pytest tests/auth/"
  )
  Task(prompt=prompt["prompt"], description=prompt["description"])

FULL ORCHESTRATION:
  prompts = sdk.orchestrate(
      "feat-add-caching",
      exploration_scope="src/cache/",
      test_command="uv run pytest tests/cache/"
  )

  # Phase 1: Explorer
  Task(prompt=prompts["explorer"]["prompt"])

  # Phase 2: Coder (with explorer results)
  Task(prompt=prompts["coder"]["prompt"])

WORKFLOW:
  1. Explorer discovers code patterns and files
  2. Coder implements changes using explorer findings
  3. Both agents auto-track in sessions
  4. Feature gets updated with progress

See also: sdk.help('planning')
"""

        elif topic in ["optimization", "session_start", "active_work"]:
            return """SESSION OPTIMIZATION

Reduce context usage with optimized methods.

SESSION START INFO:
  info = sdk.get_session_start_info(
      include_git_log=True,
      git_log_count=5,
      analytics_top_n=3
  )

  # Single call returns:
  # - status: Project status
  # - active_work: Current work item
  # - features: All features
  # - sessions: Recent sessions
  # - git_log: Recent commits
  # - analytics: Bottlenecks, recommendations, parallel

ACTIVE WORK ITEM:
  active = sdk.get_active_work_item()
  if active:
      print(f"Working on: {active['title']}")
      print(f"Progress: {active['steps_completed']}/{active['steps_total']}")

  # Filter by agent
  active = sdk.get_active_work_item(filter_by_agent=True)

BENEFITS:
  - 6+ tool calls → 1 method call
  - Reduced token usage
  - Faster session initialization
  - All context in one place

See also: sdk.help('sessions')
"""

        else:
            return f"""Unknown topic: '{topic}'

Available topics:
  - features, bugs, spikes, chores, epics (work collections)
  - tracks, sessions, agents (non-work collections)
  - analytics, strategic (dependency and work analytics)
  - work_queue, routing (smart task routing)
  - planning, workflow (planning and track creation)
  - orchestration, subagents (explorer/coder spawning)
  - optimization, session_start (context optimization)

Try: sdk.help() for full overview
"""
