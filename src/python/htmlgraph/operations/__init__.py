"""Shared operations layer for HtmlGraph CLI and SDK."""

from .analytics import (
    AnalyticsProjectResult,
    AnalyticsSessionResult,
    analyze_project,
    analyze_session,
)
from .events import (
    EventExportResult,
    EventQueryResult,
    EventRebuildResult,
    EventStats,
    export_sessions,
    get_event_stats,
    query_events,
    rebuild_index,
)
from .hooks import (
    HookInstallResult,
    HookListResult,
    HookValidationResult,
    install_hooks,
    list_hooks,
    validate_hook_config,
)
from .initialization import (
    create_analytics_index,
    create_config_files,
    create_database,
    create_directory_structure,
    initialize_htmlgraph,
    install_git_hooks,
    update_gitignore,
    validate_directory,
)
from .server import (
    ServerHandle,
    ServerStartResult,
    ServerStatus,
    get_server_status,
    start_server,
    stop_server,
)

__all__ = [
    "AnalyticsProjectResult",
    "AnalyticsSessionResult",
    "analyze_project",
    "analyze_session",
    "EventExportResult",
    "EventQueryResult",
    "EventRebuildResult",
    "EventStats",
    "export_sessions",
    "get_event_stats",
    "query_events",
    "rebuild_index",
    "HookInstallResult",
    "HookListResult",
    "HookValidationResult",
    "install_hooks",
    "list_hooks",
    "validate_hook_config",
    "ServerHandle",
    "ServerStartResult",
    "ServerStatus",
    "start_server",
    "stop_server",
    "get_server_status",
    "initialize_htmlgraph",
    "validate_directory",
    "create_directory_structure",
    "create_database",
    "create_analytics_index",
    "create_config_files",
    "update_gitignore",
    "install_git_hooks",
]
