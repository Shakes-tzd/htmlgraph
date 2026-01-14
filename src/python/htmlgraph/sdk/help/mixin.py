"""
Help mixin for SDK - documentation and discoverability.

Provides comprehensive help system for SDK methods and collections.
"""

from __future__ import annotations


class HelpMixin:
    """
    Mixin providing help and documentation capabilities to SDK.

    Adds methods for getting help on SDK usage and improved discoverability.
    """

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
  logger.info(f"Completed {result['success_count']} features")
  if result['failed_ids']:
      logger.info(f"Failed: {result['failed_ids']}")

COMMON MISTAKES:
  sdk.features.mark_complete([ids])  -> sdk.features.mark_done([ids])
  sdk.feature.create(...)            -> sdk.features.create(...)
  claim(id, agent_id=...)            -> claim(id, agent=...)
  builder.status = "done"            -> builder.save(); then edit()

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
      logger.info(f"{item['score']:.1f} - {item['title']}")
      if item.get('blocked_by'):
          logger.info(f"  Blocked by: {item['blocked_by']}")

SMART ROUTING:
  task = sdk.work_next(auto_claim=True, min_score=0.5)
  # Returns next best task using analytics + capabilities

  if task:
      logger.info(f"Working on: {task.title}")
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
      logger.info(f"Working on: {active['title']}")
      logger.info(f"Progress: {active['steps_completed']}/{active['steps_total']}")

  # Filter by agent
  active = sdk.get_active_work_item(filter_by_agent=True)

BENEFITS:
  - 6+ tool calls -> 1 method call
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
  logger.info(f"Server at {result.handle.url}")

  # Stop server
  sdk.stop_server(result.handle)

  # Check status
  status = sdk.get_server_status(result.handle)

HOOK OPERATIONS:
  # Install Git hooks for automatic tracking
  result = sdk.install_hooks()
  logger.info(f"Installed: {result.installed}")

  # List hook status
  result = sdk.list_hooks()
  logger.info(f"Enabled: {result.enabled}")
  logger.info(f"Missing: {result.missing}")

  # Validate configuration
  result = sdk.validate_hook_config()
  if not result.valid:
      logger.info(f"Errors: {result.errors}")

EVENT OPERATIONS:
  # Export HTML sessions to JSONL
  result = sdk.export_sessions()
  logger.info(f"Exported {result.written} sessions")

  # Rebuild SQLite index
  result = sdk.rebuild_event_index()
  logger.info(f"Inserted {result.inserted} events")

  # Query events
  result = sdk.query_events(
      session_id="sess-123",
      tool="Bash",
      limit=10
  )
  for event in result.events:
      logger.info(f"{event['timestamp']}: {event['summary']}")

  # Get statistics
  stats = sdk.get_event_stats()
  logger.info(f"Total events: {stats.total_events}")

ANALYTICS OPERATIONS:
  # Analyze session
  result = sdk.analyze_session("sess-123")
  logger.info(f"Primary work: {result.metrics['primary_work_type']}")

  # Analyze project
  result = sdk.analyze_project()
  logger.info(f"Total sessions: {result.metrics['total_sessions']}")
  logger.info(f"Work distribution: {result.metrics['work_distribution']}")

  # Get recommendations
  result = sdk.get_work_recommendations()
  for rec in result.recommendations:
      logger.info(f"{rec['title']} (score: {rec['score']})")

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
