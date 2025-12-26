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
from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph.models import Node, Step
from htmlgraph.graph import HtmlGraph
from htmlgraph.agents import AgentInterface
from htmlgraph.track_builder import TrackCollection
from htmlgraph.collections import BaseCollection, FeatureCollection, SpikeCollection
from htmlgraph.analytics import Analytics, DependencyAnalytics
from htmlgraph.session_manager import SessionManager
from htmlgraph.context_analytics import ContextAnalytics, ContextUsage
from htmlgraph.agent_detection import detect_agent_name


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

    def __init__(
        self,
        directory: Path | str | None = None,
        agent: str | None = None
    ):
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
            self._directory / "features",
            agent_id=agent
        )

        # Collection interfaces - all work item types
        self.features = FeatureCollection(self)
        self.bugs = BaseCollection(self, "bugs", "bug")
        self.chores = BaseCollection(self, "chores", "chore")
        self.spikes = SpikeCollection(self)
        self.epics = BaseCollection(self, "epics", "epic")
        self.phases = BaseCollection(self, "phases", "phase")

        # Non-work collections
        self.sessions = BaseCollection(self, "sessions", "session")
        self.tracks = TrackCollection(self)  # Use specialized collection with builder support
        self.agents = BaseCollection(self, "agents", "agent")

        # Analytics interface (Phase 2: Work Type Analytics)
        self.analytics = Analytics(self)

        # Dependency analytics interface (Advanced graph analytics)
        self.dep_analytics = DependencyAnalytics(self._graph)

        # Context analytics interface (Context usage tracking)
        self.context = ContextAnalytics(self)

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
        self,
        priority: str | None = None,
        auto_claim: bool = True
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
            auto_claim=auto_claim
        )

    def set_session_handoff(
        self,
        handoff_notes: str | None = None,
        recommended_next: str | None = None,
        blockers: list[str] | None = None,
        session_id: str | None = None,
    ):
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
                active = self.session_manager.get_active_session_for_agent(self._agent_id)
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
        agent: str | None = None
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
            session_id=session_id,
            agent=agent or self._agent_id or "cli",
            title=title
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
            blockers=blockers
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
                raise ValueError("No active session. Start one with sdk.start_session()")
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

    def find_bottlenecks(self, top_n: int = 5) -> list[dict[str, Any]]:
        """
        Identify tasks blocking the most downstream work.

        Args:
            top_n: Maximum number of bottlenecks to return

        Returns:
            List of bottleneck tasks with impact metrics

        Example:
            >>> sdk = SDK(agent="claude")
            >>> bottlenecks = sdk.find_bottlenecks(top_n=3)
            >>> for bn in bottlenecks:
            ...     print(f"{bn['title']} blocks {bn['blocks_count']} tasks")
        """
        return self._agent_interface.find_bottlenecks(top_n=top_n)

    def get_parallel_work(self, max_agents: int = 5) -> dict[str, Any]:
        """
        Find tasks that can be worked on simultaneously.

        Args:
            max_agents: Maximum number of parallel agents to plan for

        Returns:
            Dict with parallelization opportunities

        Example:
            >>> sdk = SDK(agent="claude")
            >>> parallel = sdk.get_parallel_work(max_agents=3)
            >>> print(f"Can work on {parallel['max_parallelism']} tasks at once")
            >>> print(f"Ready now: {parallel['ready_now']}")
        """
        return self._agent_interface.get_parallel_work(max_agents=max_agents)

    def recommend_next_work(self, agent_count: int = 1) -> list[dict[str, Any]]:
        """
        Get smart recommendations for what to work on next.

        Considers priority, dependencies, and transitive impact.

        Args:
            agent_count: Number of agents/tasks to recommend

        Returns:
            List of recommended tasks with reasoning

        Example:
            >>> sdk = SDK(agent="claude")
            >>> recs = sdk.recommend_next_work(agent_count=3)
            >>> for rec in recs:
            ...     print(f"{rec['title']} (score: {rec['score']})")
            ...     print(f"  Reasons: {rec['reasons']}")
        """
        return self._agent_interface.recommend_next_work(agent_count=agent_count)

    def assess_risks(self) -> dict[str, Any]:
        """
        Assess dependency-related risks in the project.

        Identifies single points of failure, circular dependencies,
        and orphaned tasks.

        Returns:
            Dict with risk assessment results

        Example:
            >>> sdk = SDK(agent="claude")
            >>> risks = sdk.assess_risks()
            >>> if risks['high_risk_count'] > 0:
            ...     print(f"Warning: {risks['high_risk_count']} high-risk tasks")
        """
        return self._agent_interface.assess_risks()

    def analyze_impact(self, node_id: str) -> dict[str, Any]:
        """
        Analyze the impact of completing a specific task.

        Args:
            node_id: Task to analyze

        Returns:
            Dict with impact analysis

        Example:
            >>> sdk = SDK(agent="claude")
            >>> impact = sdk.analyze_impact("feature-001")
            >>> print(f"Completing this unlocks {impact['unlocks_count']} tasks")
        """
        return self._agent_interface.analyze_impact(node_id)

    # =========================================================================
    # Planning Workflow Integration
    # =========================================================================

    def start_planning_spike(
        self,
        title: str,
        context: str = "",
        timebox_hours: float = 4.0,
        auto_start: bool = True
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
        from htmlgraph.models import Spike, SpikeType
        from htmlgraph.ids import generate_id

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
                Step(description="Create implementation plan")
            ],
            content=f"<p>{context}</p>" if context else "",
            edges={},
            properties={}
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
        phases: list[tuple[str, list[str]]] | None = None
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
        from htmlgraph.track_builder import TrackBuilder

        builder = self.tracks.builder() \
            .title(title) \
            .description(description) \
            .priority(priority)

        # Add reference to planning spike if provided
        if spike_id:
            builder._data["properties"]["planning_spike"] = spike_id

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
                context=f"Track created from planning spike: {spike_id}" if spike_id else "",
                requirements=req_list,
                acceptance_criteria=[]
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
            "priority": priority
        }

    def smart_plan(
        self,
        description: str,
        create_spike: bool = True,
        timebox_hours: float = 4.0,
        research_completed: bool = False,
        research_findings: dict[str, Any] | None = None
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
            "description": description
        }

        # Build context string with research info
        context_str = f"Project context:\n- {len(bottlenecks)} bottlenecks\n- {risks['high_risk_count']} high-risk items\n- {parallel['max_parallelism']} parallel capacity"

        if research_completed and research_findings:
            context_str += f"\n\nResearch completed:\n- Topic: {research_findings.get('topic', description)}"
            if 'sources_count' in research_findings:
                context_str += f"\n- Sources: {research_findings['sources_count']}"
            if 'recommended_library' in research_findings:
                context_str += f"\n- Recommended: {research_findings['recommended_library']}"

        # Validation: warn if complex work planned without research
        is_complex = any([
            "auth" in description.lower(),
            "security" in description.lower(),
            "real-time" in description.lower(),
            "websocket" in description.lower(),
            "oauth" in description.lower(),
            "performance" in description.lower(),
            "integration" in description.lower(),
        ])

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
                timebox_hours=timebox_hours
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
                    "Research and design the solution" if not research_completed else "Design solution using research findings",
                    "Complete spike steps",
                    "Use SDK.create_track_from_plan() to create track"
                ]
            }

            if warnings:
                result["warnings"] = warnings

            return result
        else:
            # Direct track creation (for when you already know what to do)
            track_info = self.create_track_from_plan(
                title=description,
                description=f"Planned with context: {context}"
            )

            result = {
                "type": "track",
                **track_info,
                "project_context": context,
                "research_informed": research_completed,
                "next_steps": [
                    "Create features from track plan",
                    "Link features to track",
                    "Start implementation"
                ]
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
    # Session Management Optimization
    # =========================================================================

    def get_session_start_info(
        self,
        include_git_log: bool = True,
        git_log_count: int = 5,
        analytics_top_n: int = 3,
        analytics_max_agents: int = 3
    ) -> dict[str, Any]:
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

        Example:
            >>> sdk = SDK(agent="claude")
            >>> info = sdk.get_session_start_info()
            >>> print(f"Project: {info['status']['total_nodes']} nodes")
            >>> print(f"WIP: {info['status']['in_progress_count']}")
            >>> if info['active_work']:
            ...     print(f"Active: {info['active_work']['title']}")
            >>> for bn in info['analytics']['bottlenecks']:
            ...     print(f"Bottleneck: {bn['title']}")
        """
        import subprocess

        result = {}

        # 1. Project status
        result["status"] = self.get_status()

        # 2. Active work item (validation status)
        result["active_work"] = self.get_active_work_item()

        # 3. Features list (simplified)
        features_list = []
        for feature in self.features.all():
            features_list.append({
                "id": feature.id,
                "title": feature.title,
                "status": feature.status,
                "priority": feature.priority,
                "steps_total": len(feature.steps),
                "steps_completed": sum(1 for s in feature.steps if s.completed)
            })
        result["features"] = features_list

        # 4. Sessions list (recent 20)
        sessions_list = []
        for session in self.sessions.all()[:20]:
            sessions_list.append({
                "id": session.id,
                "status": session.status,
                "agent": session.properties.get("agent", "unknown"),
                "event_count": session.properties.get("event_count", 0),
                "started": session.created.isoformat() if hasattr(session, "created") else None
            })
        result["sessions"] = sessions_list

        # 5. Git log (if requested)
        if include_git_log:
            try:
                git_result = subprocess.run(
                    ["git", "log", f"--oneline", f"-{git_log_count}"],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=self._directory.parent
                )
                result["git_log"] = git_result.stdout.strip().split("\n")
            except (subprocess.CalledProcessError, FileNotFoundError):
                result["git_log"] = []

        # 6. Strategic analytics
        result["analytics"] = {
            "bottlenecks": self.find_bottlenecks(top_n=analytics_top_n),
            "recommendations": self.recommend_next_work(agent_count=analytics_top_n),
            "parallel": self.get_parallel_work(max_agents=analytics_max_agents)
        }

        return result

    def get_active_work_item(
        self,
        agent: str | None = None,
        filter_by_agent: bool = False,
        work_types: list[str] | None = None
    ) -> dict[str, Any] | None:
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
                    "steps_completed": sum(1 for s in item.steps if s.completed) if hasattr(item, "steps") else 0
                }

                # Add spike-specific fields for auto-spike detection
                if item.type == "spike":
                    item_dict["auto_generated"] = getattr(item, "auto_generated", False)
                    item_dict["spike_subtype"] = getattr(item, "spike_subtype", None)

                active_items.append(item_dict)

        # Return first active item (primary work item)
        # TODO: In future, could support multiple active items or prioritization
        if active_items:
            return active_items[0]

        return None
