"""
Operations mixin for SDK - server, hooks, events, analytics operations.

Provides infrastructure operations for running HtmlGraph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class OperationsMixin:
    """
    Mixin providing operations capabilities to SDK.

    Adds methods for server, hooks, events, and analytics operations.
    Requires SDK instance with _directory attribute.
    """

    _directory: Path

    # =========================================================================
    # Server Operations
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
            >>> logger.info(f"Server running at {result.handle.url}")
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
            >>> logger.info(f"Running: {status.running}")
        """
        from htmlgraph.operations import server

        return server.get_server_status(handle)

    # =========================================================================
    # Hook Operations
    # =========================================================================

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
            >>> logger.info(f"Installed: {result.installed}")
            >>> logger.info(f"Skipped: {result.skipped}")
            >>> if result.warnings:
            ...     logger.info(f"Warnings: {result.warnings}")

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
            >>> logger.info(f"Enabled: {result.enabled}")
            >>> logger.info(f"Disabled: {result.disabled}")
            >>> logger.info(f"Missing: {result.missing}")
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
            ...     logger.info(f"Errors: {result.errors}")
            >>> if result.warnings:
            ...     logger.info(f"Warnings: {result.warnings}")
        """
        from htmlgraph.operations import hooks

        return hooks.validate_hook_config(project_dir=self._directory.parent)

    # =========================================================================
    # Event Operations
    # =========================================================================

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
            >>> logger.info(f"Exported {result.written} sessions")
            >>> logger.info(f"Skipped {result.skipped} (already exist)")
            >>> if result.failed > 0:
            ...     logger.info(f"Failed {result.failed} sessions")

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
            >>> logger.info(f"Rebuilt index: {result.db_path}")
            >>> logger.info(f"Inserted {result.inserted} events")
            >>> logger.info(f"Skipped {result.skipped} (duplicates)")

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
            >>> logger.info(f"Found {result.total} events")
            >>>
            >>> # Get recent Bash events
            >>> result = sdk.query_events(
            ...     tool="Bash",
            ...     since="2025-01-01T00:00:00Z",
            ...     limit=10
            ... )
            >>> for event in result.events:
            ...     logger.info(f"{event['timestamp']}: {event['summary']}")

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
            >>> logger.info(f"Total events: {stats.total_events}")
            >>> logger.info(f"Sessions: {stats.session_count}")
            >>> logger.info(f"JSONL files: {stats.file_count}")
        """
        from htmlgraph.operations import events

        return events.get_event_stats(graph_dir=self._directory)

    # =========================================================================
    # Analytics Operations
    # =========================================================================

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
            >>> logger.info(f"Primary work type: {result.metrics['primary_work_type']}")
            >>> logger.info(f"Total events: {result.metrics['total_events']}")
            >>> logger.info(f"Work distribution: {result.metrics['work_distribution']}")
            >>> if result.warnings:
            ...     logger.info(f"Warnings: {result.warnings}")

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
            >>> logger.info(f"Total sessions: {result.metrics['total_sessions']}")
            >>> logger.info(f"Work distribution: {result.metrics['work_distribution']}")
            >>> logger.info(f"Spike-to-feature ratio: {result.metrics['spike_to_feature_ratio']}")
            >>> logger.info(f"Session types: {result.metrics['session_types']}")
            >>> for session in result.metrics['recent_sessions']:
            ...     logger.info(f"  {session['session_id']}: {session['primary_work_type']}")

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
            ...     logger.info(f"{rec['title']} (score: {rec['score']})")
            ...     logger.info(f"  Reasons: {rec['reasons']}")
            ...     logger.info(f"  Unlocks: {rec['unlocks']}")
            >>> logger.info(f"Reasoning: {result.reasoning}")

        See also:
            recommend_next_work: Legacy method (backward compatibility)
            get_work_queue: Get prioritized work queue
        """
        from htmlgraph.operations import analytics

        return analytics.get_recommendations(graph_dir=self._directory)
