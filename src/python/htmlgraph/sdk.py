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

import os
from pathlib import Path
from typing import Any

from htmlgraph.agent_detection import detect_agent_name
from htmlgraph.agents import AgentInterface
from htmlgraph.analytics import Analytics, CrossSessionAnalytics, DependencyAnalytics
from htmlgraph.collections import (
    BaseCollection,
    BugCollection,
    ChoreCollection,
    EpicCollection,
    FeatureCollection,
    PhaseCollection,
    SpikeCollection,
    TaskDelegationCollection,
    TodoCollection,
)
from htmlgraph.collections.insight import InsightCollection
from htmlgraph.collections.metric import MetricCollection
from htmlgraph.collections.pattern import PatternCollection
from htmlgraph.collections.session import SessionCollection
from htmlgraph.context_analytics import ContextAnalytics
from htmlgraph.db.schema import HtmlGraphDB
from htmlgraph.graph import HtmlGraph
from htmlgraph.models import Node, Step
from htmlgraph.session_manager import SessionManager
from htmlgraph.session_warning import check_and_show_warning
from htmlgraph.system_prompts import SystemPromptManager
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
        - todos: Persistent task tracking (mirrors TodoWrite API)
        - patterns: Workflow patterns (optimal/anti-pattern)
        - insights: Session health insights
        - metrics: Aggregated time-series metrics

    System Prompt Management:
        sdk.system_prompts - Manage system prompts
            .get_active() - Get active prompt (project override OR plugin default)
            .get_default() - Get plugin default system prompt
            .get_project() - Get project-level override if exists
            .create(template) - Create project-level override
            .validate() - Validate prompt token count
            .delete() - Delete project override (fall back to default)
            .get_stats() - Get prompt statistics

    Analytics & Decision Support:
        sdk.dep_analytics - Dependency analysis
            .find_bottlenecks(top_n=5) - Find blocking tasks
            .get_parallel_work(max_agents=5) - Find parallelizable work
            .recommend_next_tasks(agent_count=1) - Smart recommendations
            .assess_dependency_risk() - Check for circular deps
            .impact_analysis(node_id) - See what task unlocks

        sdk.analytics - Work analytics
            .get_work_type_distribution() - Breakdown by type
            .get_spike_to_feature_ratio() - Investigation vs implementation
            .get_maintenance_burden() - Chore vs feature ratio

        sdk.context - Context tracking
            .get_context_usage() - Session context metrics
            .get_context_efficiency() - Efficiency score

    Discovery & Help:
        sdk.help() - Get structured help for all operations
        sdk.help('analytics') - Get analytics-specific help
        sdk.help('features') - Get feature collection help

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

    BATCH OPERATIONS (Return Results Dict):
        Batch operations return dict with success_count, failed_ids, and warnings.
        Provides detailed feedback for partial failures.

        >>> result = sdk.features.mark_done(["feat-1", "missing", "feat-2"])
        >>> print(f"Completed {result['success_count']} of 3")
        >>> if result['failed_ids']:
        ...     print(f"Failed: {result['failed_ids']}")
        ...     print(f"Reasons: {result['warnings']}")

    Pattern Summary:
        | Operation Type | Error Behavior      | Example Method        |
        |----------------|--------------------|-----------------------|
        | Lookup         | Return None        | .get(id)              |
        | Query          | Return []          | .where(), .all()      |
        | Edit           | Raise Exception    | .edit(id)             |
        | Create         | Raise on Invalid   | .create(title)        |
        | Batch          | Return Results Dict| .mark_done([ids])     |
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

    def __init__(
        self,
        directory: Path | str | None = None,
        agent: str | None = None,
        parent_session: str | None = None,
        db_path: str | None = None,
    ):
        """
        Initialize SDK.

        Args:
            directory: Path to .htmlgraph directory (auto-discovered if not provided)
            agent: REQUIRED - Agent identifier for operations.
                Used to attribute work items (features, spikes, bugs, etc) to the agent.
                Examples: agent='explorer', agent='coder', agent='tester'
                Critical for: Work attribution, result retrieval, orchestrator tracking
                Falls back to: CLAUDE_AGENT_NAME env var, then detect_agent_name()
                Raises ValueError if not provided and cannot be detected
            parent_session: Parent session ID to log activities to (for nested contexts)
            db_path: Path to SQLite database file (optional, defaults to ~/.htmlgraph/htmlgraph.db)
        """
        if directory is None:
            directory = self._discover_htmlgraph()

        if agent is None:
            # Try environment variable fallback
            agent = os.getenv("CLAUDE_AGENT_NAME")

        if agent is None:
            # Try automatic detection
            detected = detect_agent_name()
            if detected and detected != "cli":
                # Only accept detected if it's not the default fallback
                agent = detected
            else:
                # No valid agent found - fail fast with helpful error message
                raise ValueError(
                    "Agent identifier is required for work attribution. "
                    "Pass agent='name' to SDK() initialization. "
                    "Examples: SDK(agent='explorer'), SDK(agent='coder'), SDK(agent='tester')\n"
                    "Alternatively, set CLAUDE_AGENT_NAME environment variable.\n"
                    "Critical for: Work attribution, result retrieval, orchestrator tracking"
                )

        self._directory = Path(directory)
        self._agent_id = agent
        self._parent_session = parent_session or os.getenv("HTMLGRAPH_PARENT_SESSION")

        # Initialize SQLite database (Phase 2)
        self._db = HtmlGraphDB(
            db_path or str(Path.home() / ".htmlgraph" / "htmlgraph.db")
        )
        self._db.connect()
        self._db.create_tables()

        # Initialize underlying HtmlGraphs first (for backward compatibility and sharing)
        # These are shared with SessionManager to avoid double-loading features
        self._graph = HtmlGraph(self._directory / "features")
        self._bugs_graph = HtmlGraph(self._directory / "bugs")

        # Initialize SessionManager with shared graph instances to avoid double-loading
        self.session_manager = SessionManager(
            self._directory,
            features_graph=self._graph,
            bugs_graph=self._bugs_graph,
        )

        # Agent interface (for backward compatibility)
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
        self.sessions: SessionCollection = SessionCollection(self)
        self.tracks: TrackCollection = TrackCollection(
            self
        )  # Use specialized collection with builder support
        self.agents: BaseCollection = BaseCollection(self, "agents", "agent")

        # Learning collections (Active Learning Persistence)
        self.patterns = PatternCollection(self)
        self.insights = InsightCollection(self)
        self.metrics = MetricCollection(self)

        # Todo collection (persistent task tracking)
        self.todos = TodoCollection(self)

        # Task delegation collection (observability for spawned agents)
        self.task_delegations = TaskDelegationCollection(self)

        # Create learning directories if needed
        (self._directory / "patterns").mkdir(exist_ok=True)
        (self._directory / "insights").mkdir(exist_ok=True)
        (self._directory / "metrics").mkdir(exist_ok=True)
        (self._directory / "todos").mkdir(exist_ok=True)
        (self._directory / "task-delegations").mkdir(exist_ok=True)

        # Analytics interface (Phase 2: Work Type Analytics)
        self.analytics = Analytics(self)

        # Dependency analytics interface (Advanced graph analytics)
        self.dep_analytics = DependencyAnalytics(self._graph)

        # Cross-session analytics interface (Git commit-based analytics)
        self.cross_session_analytics = CrossSessionAnalytics(self)

        # Context analytics interface (Context usage tracking)
        self.context = ContextAnalytics(self)

        # Pattern learning interface (Phase 2: Behavior Pattern Learning)
        from htmlgraph.analytics.pattern_learning import PatternLearner

        self.pattern_learning = PatternLearner(self._directory)

        # Lazy-loaded orchestrator for subagent management
        self._orchestrator: Any = None

        # System prompt manager (lazy-loaded)
        self._system_prompts: SystemPromptManager | None = None

        # Session warning system (workaround for Claude Code hook bug #10373)
        # Shows orchestrator instructions on first SDK usage per session
        self._session_warning = check_and_show_warning(
            self._directory,
            agent=self._agent_id,
            session_id=None,  # Will be set by session manager if available
        )

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

    @property
    def system_prompts(self) -> SystemPromptManager:
        """
        Access system prompt management.

        Provides methods to:
        - Get active prompt (project override OR plugin default)
        - Create/delete project-level overrides
        - Validate token counts
        - Get prompt statistics

        Lazy-loaded on first access.

        Returns:
            SystemPromptManager instance

        Example:
            >>> sdk = SDK(agent="claude")

            # Get active prompt
            >>> prompt = sdk.system_prompts.get_active()

            # Create project override
            >>> sdk.system_prompts.create("## Custom prompt\\n...")

            # Validate token count
            >>> result = sdk.system_prompts.validate()
            >>> print(result['message'])

            # Get statistics
            >>> stats = sdk.system_prompts.get_stats()
            >>> print(f"Source: {stats['source']}")
        """
        if self._system_prompts is None:
            self._system_prompts = SystemPromptManager(self._directory)
        return self._system_prompts

    def dismiss_session_warning(self) -> bool:
        """
        Dismiss the session warning after reading it.

        IMPORTANT: Call this as your FIRST action after seeing the orchestrator
        warning. This confirms you've read the instructions.

        Returns:
            True if warning was dismissed, False if already dismissed

        Example:
            sdk = SDK(agent="claude")
            # Warning shown automatically...

            # First action: dismiss to confirm you read it
            sdk.dismiss_session_warning()

            # Now proceed with orchestration
            sdk.spawn_coder(feature_id="feat-123", ...)
        """
        if self._session_warning:
            return self._session_warning.dismiss(
                agent=self._agent_id,
                session_id=None,
            )
        return False

    def get_warning_status(self) -> dict[str, Any]:
        """
        Get current session warning status.

        Returns:
            Dict with dismissed status, timestamp, and show count
        """
        if self._session_warning:
            return self._session_warning.get_status()
        return {"dismissed": True, "show_count": 0}

    # =========================================================================
    # SQLite Database Integration (Phase 2)
    # =========================================================================

    def db(self) -> HtmlGraphDB:
        """
        Get the SQLite database instance.

        Returns:
            HtmlGraphDB instance for executing queries

        Example:
            >>> sdk = SDK(agent="claude")
            >>> db = sdk.db()
            >>> events = db.get_session_events("sess-123")
            >>> features = db.get_features_by_status("todo")
        """
        return self._db

    def query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """
        Execute a raw SQL query on the SQLite database.

        Args:
            sql: SQL query string
            params: Query parameters (for safe parameterized queries)

        Returns:
            List of result dictionaries

        Example:
            >>> sdk = SDK(agent="claude")
            >>> results = sdk.query(
            ...     "SELECT * FROM features WHERE status = ? AND priority = ?",
            ...     ("todo", "high")
            ... )
            >>> for row in results:
            ...     print(row["title"])
        """
        if not self._db.connection:
            self._db.connect()

        cursor = self._db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def execute_query_builder(
        self, sql: str, params: tuple = ()
    ) -> list[dict[str, Any]]:
        """
        Execute a query using the Queries builder.

        Args:
            sql: SQL query from Queries builder
            params: Parameters from Queries builder

        Returns:
            List of result dictionaries

        Example:
            >>> sdk = SDK(agent="claude")
            >>> sql, params = Queries.get_features_by_status("todo", limit=5)
            >>> results = sdk.execute_query_builder(sql, params)
        """
        return self.query(sql, params)

    def export_to_html(
        self,
        output_dir: str | None = None,
        include_features: bool = True,
        include_sessions: bool = True,
        include_events: bool = False,
    ) -> dict[str, int]:
        """
        Export SQLite data to HTML files for backward compatibility.

        Args:
            output_dir: Directory to export to (defaults to .htmlgraph)
            include_features: Export features
            include_sessions: Export sessions
            include_events: Export events (detailed, use with care)

        Returns:
            Dict with export counts: {"features": int, "sessions": int, "events": int}

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.export_to_html()
            >>> print(f"Exported {result['features']} features")
        """
        if output_dir is None:
            output_dir = str(self._directory)

        output_path = Path(output_dir)
        counts = {"features": 0, "sessions": 0, "events": 0}

        if include_features:
            # Export all features from SQLite to HTML
            features_dir = output_path / "features"
            features_dir.mkdir(parents=True, exist_ok=True)

            try:
                cursor = self._db.connection.cursor()  # type: ignore[union-attr]
                cursor.execute("SELECT * FROM features")
                rows = cursor.fetchall()

                for row in rows:
                    feature_dict = dict(row)
                    feature_id = feature_dict["id"]
                    # Write HTML file (simplified export)
                    html_file = features_dir / f"{feature_id}.html"
                    html_file.write_text(
                        f"<h1>{feature_dict['title']}</h1>"
                        f"<p>Status: {feature_dict['status']}</p>"
                        f"<p>Type: {feature_dict['type']}</p>"
                    )
                    counts["features"] += 1
            except Exception as e:
                import logging

                logging.error(f"Error exporting features: {e}")

        if include_sessions:
            # Export all sessions from SQLite to HTML
            sessions_dir = output_path / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)

            try:
                cursor = self._db.connection.cursor()  # type: ignore[union-attr]
                cursor.execute("SELECT * FROM sessions")
                rows = cursor.fetchall()

                for row in rows:
                    session_dict = dict(row)
                    session_id = session_dict["session_id"]
                    # Write HTML file (simplified export)
                    html_file = sessions_dir / f"{session_id}.html"
                    html_file.write_text(
                        f"<h1>Session {session_id}</h1>"
                        f"<p>Agent: {session_dict['agent_assigned']}</p>"
                        f"<p>Status: {session_dict['status']}</p>"
                    )
                    counts["sessions"] += 1
            except Exception as e:
                import logging

                logging.error(f"Error exporting sessions: {e}")

        return counts

    def _log_event(
        self,
        event_type: str,
        tool_name: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        context: dict[str, Any] | None = None,
        cost_tokens: int = 0,
    ) -> bool:
        """
        Log an event to the SQLite database with parent-child linking.

        Internal method used by collections to track operations.
        Automatically creates a session if one doesn't exist.
        Reads parent event ID from HTMLGRAPH_PARENT_ACTIVITY env var for hierarchical tracking.

        Args:
            event_type: Type of event (tool_call, completion, error, etc.)
            tool_name: Tool that was called
            input_summary: Summary of input
            output_summary: Summary of output
            context: Additional context metadata
            cost_tokens: Token cost estimate

        Returns:
            True if logged successfully, False otherwise

        Example (internal use):
            >>> sdk._log_event(
            ...     event_type="tool_call",
            ...     tool_name="Edit",
            ...     input_summary="Edit file.py",
            ...     cost_tokens=100
            ... )
        """
        from uuid import uuid4

        event_id = f"evt-{uuid4().hex[:12]}"
        session_id = self._parent_session or "cli-session"

        # Read parent event ID from environment variable for hierarchical linking
        parent_event_id = os.getenv("HTMLGRAPH_PARENT_ACTIVITY")

        # Ensure session exists before logging event
        try:
            self._ensure_session_exists(session_id, parent_event_id=parent_event_id)
        except Exception as e:
            import logging

            logging.debug(f"Failed to ensure session exists: {e}")
            # Continue anyway - session creation failure shouldn't block event logging

        return self._db.insert_event(
            event_id=event_id,
            agent_id=self._agent_id,
            event_type=event_type,
            session_id=session_id,
            tool_name=tool_name,
            input_summary=input_summary,
            output_summary=output_summary,
            context=context,
            parent_event_id=parent_event_id,
            cost_tokens=cost_tokens,
        )

    def _ensure_session_exists(
        self, session_id: str, parent_event_id: str | None = None
    ) -> None:
        """
        Create a session record if it doesn't exist.

        Args:
            session_id: Session ID to ensure exists
            parent_event_id: Event that spawned this session (optional)
        """
        if not self._db.connection:
            self._db.connect()

        cursor = self._db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE session_id = ?", (session_id,)
        )
        exists = cursor.fetchone()[0] > 0

        if not exists:
            # Create session record
            self._db.insert_session(
                session_id=session_id,
                agent_assigned=self._agent_id,
                is_subagent=self._parent_session is not None,
                parent_session_id=self._parent_session,
                parent_event_id=parent_event_id,
            )

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

    def continue_from_last(
        self,
        agent: str | None = None,
        auto_create_session: bool = True,
    ) -> tuple[Any, Any]:
        """
        Continue work from the last completed session.

        Loads context from previous session including handoff notes,
        recommended files, blockers, and recent commits.

        Args:
            agent: Filter by agent (None = current SDK agent)
            auto_create_session: Create new session if True

        Returns:
            Tuple of (new_session, resume_info) or (None, None)

        Example:
            >>> sdk = SDK(agent="claude")
            >>> session, resume = sdk.continue_from_last()
            >>> if resume:
            ...     print(resume.summary)
            ...     print(resume.next_focus)
            ...     for file in resume.recommended_files:
            ...         print(f"  - {file}")
        """
        if not agent:
            agent = self._agent_id

        return self.session_manager.continue_from_last(
            agent=agent,
            auto_create_session=auto_create_session,
        )

    def end_session_with_handoff(
        self,
        session_id: str | None = None,
        summary: str | None = None,
        next_focus: str | None = None,
        blockers: list[str] | None = None,
        keep_context: list[str] | None = None,
        auto_recommend_context: bool = True,
    ) -> Any:
        """
        End session with handoff information for next session.

        Args:
            session_id: Session to end (None = active session)
            summary: What was accomplished
            next_focus: What should be done next
            blockers: List of blockers
            keep_context: List of files to keep context for
            auto_recommend_context: Auto-recommend files from git

        Returns:
            Updated Session or None

        Example:
            >>> sdk.end_session_with_handoff(
            ...     summary="Completed OAuth integration",
            ...     next_focus="Implement JWT token refresh",
            ...     blockers=["Waiting for security review"],
            ...     keep_context=["src/auth/oauth.py"]
            ... )
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

        return self.session_manager.end_session_with_handoff(
            session_id=session_id,
            summary=summary,
            next_focus=next_focus,
            blockers=blockers,
            keep_context=keep_context,
            auto_recommend_context=auto_recommend_context,
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
            session_id=session_id,
            agent=agent or self._agent_id or "cli",
            title=title,
            parent_session_id=self._parent_session,
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
            session_id: Session ID (defaults to parent session if available, then active session)
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
        # Determine target session: explicit parameter > parent_session > active > none
        if not session_id:
            # Priority 1: Parent session (explicitly provided or from env var)
            if self._parent_session:
                session_id = self._parent_session
            else:
                # Priority 2: Active session for this agent
                active = self.session_manager.get_active_session(agent=self._agent_id)
                if active:
                    session_id = active.id
                else:
                    raise ValueError(
                        "No active session. Start one with sdk.start_session()"
                    )

        # Get parent activity ID from environment if not provided
        if not parent_activity_id:
            parent_activity_id = os.getenv("HTMLGRAPH_PARENT_ACTIVITY")

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

        # Get work queue - get more items since we filter for actionable (todo) only
        queue = self.get_work_queue(agent_id=agent, limit=20, min_score=min_score)

        if not queue:
            return None

        # Find the first actionable (todo) task - blocked tasks are not actionable
        top_item = None
        for item in queue:
            if item["status"] == "todo":
                top_item = item
                break

        if top_item is None:
            return None

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
        # Separate real work items from auto-generated spikes
        real_work_items = []
        auto_spikes = []

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

                    # Separate auto-spikes from real work
                    # Auto-spikes are temporary tracking items (session-init, transition, conversation-init)
                    is_auto_spike = item_dict["auto_generated"] and item_dict[
                        "spike_subtype"
                    ] in ("session-init", "transition", "conversation-init")

                    if is_auto_spike:
                        auto_spikes.append(item_dict)
                    else:
                        # Real user-created spike
                        real_work_items.append(item_dict)
                else:
                    # Features, bugs, chores, epics are always real work
                    real_work_items.append(item_dict)

        # Prioritize real work items over auto-spikes
        # Auto-spikes should only show if there's NO other active work item
        if real_work_items:
            return real_work_items[0]  # type: ignore[return-value]

        if auto_spikes:
            return auto_spikes[0]  # type: ignore[return-value]

        return None

    # =========================================================================
    # Operations Layer - Server, Hooks, Events, Analytics
    # =========================================================================

    def start_server(
        self,
        port: int = 8080,
        host: str = "localhost",
        watch: bool = True,
        auto_port: bool = False,
    ) -> Any:
        """
        Start HtmlGraph server for browsing graph via web UI.

        Args:
            port: Port to listen on (default: 8080)
            host: Host to bind to (default: "localhost")
            watch: Enable file watching for auto-reload (default: True)
            auto_port: Automatically find available port if specified port is in use (default: False)

        Returns:
            ServerStartResult with handle, warnings, and config used

        Raises:
            PortInUseError: If port is in use and auto_port=False
            ServerStartError: If server fails to start

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.start_server(port=8080, watch=True)
            >>> print(f"Server running at {result.handle.url}")
            >>> # Open browser to http://localhost:8080
            >>>
            >>> # Stop server when done
            >>> sdk.stop_server(result.handle)

        See also:
            stop_server: Stop running server
            get_server_status: Check if server is running
        """
        from htmlgraph.operations import server

        return server.start_server(
            port=port,
            graph_dir=self._directory,
            static_dir=self._directory.parent,  # Project root for index.html
            host=host,
            watch=watch,
            auto_port=auto_port,
        )

    def stop_server(self, handle: Any) -> None:
        """
        Stop a running HtmlGraph server.

        Args:
            handle: ServerHandle returned from start_server()

        Raises:
            ServerStartError: If shutdown fails

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.start_server()
            >>> # Work with server...
            >>> sdk.stop_server(result.handle)
        """
        from htmlgraph.operations import server

        server.stop_server(handle)

    def get_server_status(self, handle: Any | None = None) -> Any:
        """
        Check server status.

        Args:
            handle: Optional ServerHandle to check

        Returns:
            ServerStatus indicating whether server is running

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.start_server()
            >>> status = sdk.get_server_status(result.handle)
            >>> print(f"Running: {status.running}")
        """
        from htmlgraph.operations import server

        return server.get_server_status(handle)

    def install_hooks(self, use_copy: bool = False) -> Any:
        """
        Install Git hooks for automatic tracking.

        Installs hooks that automatically track sessions, activities, and features
        as you work.

        Args:
            use_copy: Force copy instead of symlink (default: False)

        Returns:
            HookInstallResult with installation details

        Raises:
            HookInstallError: If installation fails
            HookConfigError: If configuration is invalid

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.install_hooks()
            >>> print(f"Installed: {result.installed}")
            >>> print(f"Skipped: {result.skipped}")
            >>> if result.warnings:
            ...     print(f"Warnings: {result.warnings}")

        See also:
            list_hooks: List installed hooks
            validate_hook_config: Validate hook configuration
        """
        from htmlgraph.operations import hooks

        return hooks.install_hooks(
            project_dir=self._directory.parent,
            use_copy=use_copy,
        )

    def list_hooks(self) -> Any:
        """
        List Git hooks status (enabled/disabled/missing).

        Returns:
            HookListResult with enabled, disabled, and missing hooks

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.list_hooks()
            >>> print(f"Enabled: {result.enabled}")
            >>> print(f"Disabled: {result.disabled}")
            >>> print(f"Missing: {result.missing}")
        """
        from htmlgraph.operations import hooks

        return hooks.list_hooks(project_dir=self._directory.parent)

    def validate_hook_config(self) -> Any:
        """
        Validate hook configuration.

        Returns:
            HookValidationResult with validation status

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.validate_hook_config()
            >>> if not result.valid:
            ...     print(f"Errors: {result.errors}")
            >>> if result.warnings:
            ...     print(f"Warnings: {result.warnings}")
        """
        from htmlgraph.operations import hooks

        return hooks.validate_hook_config(project_dir=self._directory.parent)

    def export_sessions(self, overwrite: bool = False) -> Any:
        """
        Export legacy session HTML logs to JSONL events.

        Converts HTML session files to JSONL format for efficient querying.

        Args:
            overwrite: Whether to overwrite existing JSONL files (default: False)

        Returns:
            EventExportResult with counts of written, skipped, failed files

        Raises:
            EventOperationError: If export fails

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.export_sessions()
            >>> print(f"Exported {result.written} sessions")
            >>> print(f"Skipped {result.skipped} (already exist)")
            >>> if result.failed > 0:
            ...     print(f"Failed {result.failed} sessions")

        See also:
            rebuild_event_index: Rebuild SQLite index from JSONL
            query_events: Query exported events
        """
        from htmlgraph.operations import events

        return events.export_sessions(
            graph_dir=self._directory,
            overwrite=overwrite,
        )

    def rebuild_event_index(self) -> Any:
        """
        Rebuild SQLite analytics index from JSONL events.

        Creates an optimized SQLite index for fast analytics queries.

        Returns:
            EventRebuildResult with db_path and counts of inserted/skipped events

        Raises:
            EventOperationError: If rebuild fails

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.rebuild_event_index()
            >>> print(f"Rebuilt index: {result.db_path}")
            >>> print(f"Inserted {result.inserted} events")
            >>> print(f"Skipped {result.skipped} (duplicates)")

        See also:
            export_sessions: Export HTML sessions to JSONL first
        """
        from htmlgraph.operations import events

        return events.rebuild_index(graph_dir=self._directory)

    def query_events(
        self,
        session_id: str | None = None,
        tool: str | None = None,
        feature_id: str | None = None,
        since: str | None = None,
        limit: int | None = None,
    ) -> Any:
        """
        Query events from JSONL logs with optional filters.

        Args:
            session_id: Filter by session ID (None = all sessions)
            tool: Filter by tool name (e.g., 'Bash', 'Edit')
            feature_id: Filter by attributed feature ID
            since: Only events after this timestamp (ISO string)
            limit: Maximum number of events to return

        Returns:
            EventQueryResult with matching events and total count

        Raises:
            EventOperationError: If query fails

        Example:
            >>> sdk = SDK(agent="claude")
            >>> # Get all events for a session
            >>> result = sdk.query_events(session_id="sess-123")
            >>> print(f"Found {result.total} events")
            >>>
            >>> # Get recent Bash events
            >>> result = sdk.query_events(
            ...     tool="Bash",
            ...     since="2025-01-01T00:00:00Z",
            ...     limit=10
            ... )
            >>> for event in result.events:
            ...     print(f"{event['timestamp']}: {event['summary']}")

        See also:
            export_sessions: Export sessions to JSONL first
            get_event_stats: Get event statistics
        """
        from htmlgraph.operations import events

        return events.query_events(
            graph_dir=self._directory,
            session_id=session_id,
            tool=tool,
            feature_id=feature_id,
            since=since,
            limit=limit,
        )

    def get_event_stats(self) -> Any:
        """
        Get statistics about events in the system.

        Returns:
            EventStats with counts of total events, sessions, and files

        Example:
            >>> sdk = SDK(agent="claude")
            >>> stats = sdk.get_event_stats()
            >>> print(f"Total events: {stats.total_events}")
            >>> print(f"Sessions: {stats.session_count}")
            >>> print(f"JSONL files: {stats.file_count}")
        """
        from htmlgraph.operations import events

        return events.get_event_stats(graph_dir=self._directory)

    def analyze_session(self, session_id: str) -> Any:
        """
        Compute detailed analytics for a single session.

        Analyzes work distribution, spike-to-feature ratio, maintenance burden,
        transition metrics, and more.

        Args:
            session_id: ID of the session to analyze

        Returns:
            AnalyticsSessionResult with session metrics and warnings

        Raises:
            AnalyticsOperationError: If session cannot be analyzed

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.analyze_session("sess-123")
            >>> print(f"Primary work type: {result.metrics['primary_work_type']}")
            >>> print(f"Total events: {result.metrics['total_events']}")
            >>> print(f"Work distribution: {result.metrics['work_distribution']}")
            >>> if result.warnings:
            ...     print(f"Warnings: {result.warnings}")

        See also:
            analyze_project: Analyze entire project
        """
        from htmlgraph.operations import analytics

        return analytics.analyze_session(
            graph_dir=self._directory,
            session_id=session_id,
        )

    def analyze_project(self) -> Any:
        """
        Compute project-wide analytics.

        Analyzes all sessions, work distribution, spike-to-feature ratios,
        maintenance burden, and session types across the entire project.

        Returns:
            AnalyticsProjectResult with project metrics and warnings

        Raises:
            AnalyticsOperationError: If project cannot be analyzed

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.analyze_project()
            >>> print(f"Total sessions: {result.metrics['total_sessions']}")
            >>> print(f"Work distribution: {result.metrics['work_distribution']}")
            >>> print(f"Spike-to-feature ratio: {result.metrics['spike_to_feature_ratio']}")
            >>> print(f"Session types: {result.metrics['session_types']}")
            >>> for session in result.metrics['recent_sessions']:
            ...     print(f"  {session['session_id']}: {session['primary_work_type']}")

        See also:
            analyze_session: Analyze a single session
            get_work_recommendations: Get work recommendations
        """
        from htmlgraph.operations import analytics

        return analytics.analyze_project(graph_dir=self._directory)

    def get_work_recommendations(self) -> Any:
        """
        Get smart work recommendations based on project state.

        Uses dependency analytics to recommend next tasks based on priority,
        dependencies, and impact.

        Returns:
            RecommendationsResult with recommendations, reasoning, and warnings

        Raises:
            AnalyticsOperationError: If recommendations cannot be generated

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.get_work_recommendations()
            >>> for rec in result.recommendations:
            ...     print(f"{rec['title']} (score: {rec['score']})")
            ...     print(f"  Reasons: {rec['reasons']}")
            ...     print(f"  Unlocks: {rec['unlocks']}")
            >>> print(f"Reasoning: {result.reasoning}")

        See also:
            recommend_next_work: Legacy method (backward compatibility)
            get_work_queue: Get prioritized work queue
        """
        from htmlgraph.operations import analytics

        return analytics.get_recommendations(graph_dir=self._directory)

    # =========================================================================
    # Task Attribution - Subagent Work Tracking
    # =========================================================================

    def get_task_attribution(self, task_id: str) -> dict[str, Any]:
        """
        Get attribution - which subagent did what work in this task?

        Queries the database to find all events associated with a Claude Code task,
        showing which subagent executed each tool call.

        Args:
            task_id: Claude Code's internal task ID (available from Task() response)

        Returns:
            Dictionary with task_id, by_subagent mapping, and total_events count

        Example:
            >>> sdk = SDK(agent="claude")
            >>> result = sdk.get_task_attribution("task-abc123-xyz789")
            >>> for subagent, events in result['by_subagent'].items():
            ...     print(f"{subagent}:")
            ...     for event in events:
            ...         print(f"  - {event['tool']}: {event['summary']}")
            >>> print(f"Total events: {result['total_events']}")

        See also:
            get_subagent_work: Get all work grouped by subagent in a session
        """
        from htmlgraph.config import get_database_path
        from htmlgraph.db.schema import HtmlGraphDB

        try:
            db = HtmlGraphDB(str(get_database_path()))
            events = db.get_events_for_task(task_id)

            # Group by subagent_type
            by_subagent: dict[str, list[dict[str, Any]]] = {}
            for event in events:
                agent = event.get("subagent_type", "orchestrator")
                if agent not in by_subagent:
                    by_subagent[agent] = []
                by_subagent[agent].append(
                    {
                        "tool": event.get("tool_name"),
                        "summary": event.get("input_summary"),
                        "timestamp": event.get("created_at"),
                        "event_id": event.get("event_id"),
                        "success": not event.get("is_error", False),
                    }
                )

            return {
                "task_id": task_id,
                "by_subagent": by_subagent,
                "total_events": len(events),
            }
        except Exception as e:
            return {
                "task_id": task_id,
                "by_subagent": {},
                "total_events": 0,
                "error": str(e),
            }

    def get_subagent_work(self, session_id: str) -> dict[str, list[dict[str, Any]]]:
        """
        Get all work grouped by which subagent did it in a session.

        Shows which subagent (researcher, general-purpose, etc.) executed each
        tool call within a session.

        Args:
            session_id: Session ID to analyze

        Returns:
            Dictionary mapping subagent_type to list of events they executed.
            Each event includes: tool_name, input_summary, output_summary, created_at, event_id

        Example:
            >>> sdk = SDK(agent="claude")
            >>> work = sdk.get_subagent_work("sess-123")
            >>> for subagent, events in work.items():
            ...     print(f"{subagent} ({len(events)} events):")
            ...     for event in events:
            ...         print(f"  - {event['tool_name']}: {event['input_summary']}")

        See also:
            get_task_attribution: Get work for a specific Claude Code task
            analyze_session: Get session metrics and analytics
        """
        from htmlgraph.config import get_database_path
        from htmlgraph.db.schema import HtmlGraphDB

        try:
            db = HtmlGraphDB(str(get_database_path()))
            return db.get_subagent_work(session_id)
        except Exception:
            return {}

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

OPERATIONS (Server, Hooks, Events):
  sdk.start_server()         - Start web server for graph browsing
  sdk.stop_server()          - Stop running server
  sdk.install_hooks()        - Install Git hooks for tracking
  sdk.list_hooks()           - List Git hooks status
  sdk.export_sessions()      - Export HTML sessions to JSONL
  sdk.rebuild_event_index()  - Rebuild SQLite index from events
  sdk.query_events()         - Query JSONL event logs
  sdk.get_event_stats()      - Get event statistics
  sdk.analyze_session()      - Analyze single session metrics
  sdk.analyze_project()      - Analyze project-wide metrics
  sdk.get_work_recommendations() - Get work recommendations

ERROR HANDLING:
  Lookup (.get)      - Returns None if not found
  Query (.where)     - Returns empty list on no matches
  Edit (.edit)       - Raises NodeNotFoundError if missing
  Batch (.mark_done) - Returns dict with success_count, failed_ids, warnings

For detailed help on a topic:
  sdk.help('features')      - Feature collection methods
  sdk.help('analytics')     - Analytics methods
  sdk.help('sessions')      - Session management
  sdk.help('orchestration') - Subagent orchestration
  sdk.help('planning')      - Planning workflow
  sdk.help('operations')    - Server, hooks, events operations
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
            # Operations
            "start_server",
            "install_hooks",
            "export_sessions",
            "analyze_project",
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

BATCH OPERATIONS:
  result = sdk.features.mark_done(["feat-001", "feat-002"])
  print(f"Completed {result['success_count']} features")
  if result['failed_ids']:
      print(f"Failed: {result['failed_ids']}")

COMMON MISTAKES:
  ❌ sdk.features.mark_complete([ids])  → ✅ sdk.features.mark_done([ids])
  ❌ sdk.feature.create(...)            → ✅ sdk.features.create(...)
  ❌ claim(id, agent_id=...)            → ✅ claim(id, agent=...)
  ❌ builder.status = "done"            → ✅ builder.save(); then edit()

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

        elif topic in ["operation", "operations", "server", "hooks", "events"]:
            return """OPERATIONS - Server, Hooks, Events

Infrastructure operations for running HtmlGraph.

SERVER OPERATIONS:
  # Start server for web UI
  result = sdk.start_server(port=8080, watch=True)
  print(f"Server at {result.handle.url}")

  # Stop server
  sdk.stop_server(result.handle)

  # Check status
  status = sdk.get_server_status(result.handle)

HOOK OPERATIONS:
  # Install Git hooks for automatic tracking
  result = sdk.install_hooks()
  print(f"Installed: {result.installed}")

  # List hook status
  result = sdk.list_hooks()
  print(f"Enabled: {result.enabled}")
  print(f"Missing: {result.missing}")

  # Validate configuration
  result = sdk.validate_hook_config()
  if not result.valid:
      print(f"Errors: {result.errors}")

EVENT OPERATIONS:
  # Export HTML sessions to JSONL
  result = sdk.export_sessions()
  print(f"Exported {result.written} sessions")

  # Rebuild SQLite index
  result = sdk.rebuild_event_index()
  print(f"Inserted {result.inserted} events")

  # Query events
  result = sdk.query_events(
      session_id="sess-123",
      tool="Bash",
      limit=10
  )
  for event in result.events:
      print(f"{event['timestamp']}: {event['summary']}")

  # Get statistics
  stats = sdk.get_event_stats()
  print(f"Total events: {stats.total_events}")

ANALYTICS OPERATIONS:
  # Analyze session
  result = sdk.analyze_session("sess-123")
  print(f"Primary work: {result.metrics['primary_work_type']}")

  # Analyze project
  result = sdk.analyze_project()
  print(f"Total sessions: {result.metrics['total_sessions']}")
  print(f"Work distribution: {result.metrics['work_distribution']}")

  # Get recommendations
  result = sdk.get_work_recommendations()
  for rec in result.recommendations:
      print(f"{rec['title']} (score: {rec['score']})")

See also: sdk.help('analytics'), sdk.help('sessions')
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
