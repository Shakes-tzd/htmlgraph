from __future__ import annotations

"""
SDK Constants and Settings

Centralized configuration for the HtmlGraph SDK using Pydantic.
"""


from pathlib import Path
from typing import Any

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback if pydantic-settings not available
    _PYDANTIC_AVAILABLE = False
    BaseSettings = object  # type: ignore

    def Field(**kwargs: Any) -> None:  # type: ignore[misc,no-redef]  # noqa: N802
        """Fallback Field for environments without pydantic-settings."""
        return None

    SettingsConfigDict = dict  # type: ignore


if _PYDANTIC_AVAILABLE:

    class SDKSettings(BaseSettings):
        """
            HtmlGraph SDK Configuration.

        Uses Pydantic Settings for configuration from environment variables,
        .env files, and direct instantiation.

        Environment variables are prefixed with HTMLGRAPH_ (e.g., HTMLGRAPH_PROJECT_ROOT).
        """

    # Core paths
    project_root: Path = Field(default_factory=Path.cwd)
    htmlgraph_dir_name: str = ".htmlgraph"

    # Collection directories (relative to .htmlgraph)
    features_dir: str = "features"
    bugs_dir: str = "bugs"
    chores_dir: str = "chores"
    spikes_dir: str = "spikes"
    epics_dir: str = "epics"
    phases_dir: str = "phases"
    sessions_dir: str = "sessions"
    tracks_dir: str = "tracks"
    agents_dir: str = "agents"
    patterns_dir: str = "patterns"
    insights_dir: str = "insights"
    metrics_dir: str = "metrics"
    todos_dir: str = "todos"
    task_delegations_dir: str = "task-delegations"
    archives_dir: str = "archives"

    # Database
    database_filename: str = "htmlgraph.db"
    analytics_cache_filename: str = "index.sqlite"

    # Session management
    max_sessions: int = 100
    session_retention_days: int = 30
    auto_archive_sessions: bool = True

    # Performance
    max_query_results: int = 1000
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600

    # Logging
    log_level: str = "INFO"

    # Agent detection
    agent_env_var: str = "CLAUDE_AGENT_NAME"
    parent_session_env_var: str = "HTMLGRAPH_PARENT_SESSION"

    model_config = SettingsConfigDict(
        env_prefix="HTMLGRAPH_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    def get_htmlgraph_dir(self: SDKSettings) -> Path:  # type: ignore[misc]
        """Get the .htmlgraph directory path."""
        return Path(self.project_root) / self.htmlgraph_dir_name  # type: ignore[no-any-return]

    def get_collection_dir(self: SDKSettings, collection: str) -> Path:
        """
        Get the directory path for a specific collection.

        Args:
            collection: Collection name (e.g., "features", "bugs", "spikes")

        Returns:
            Path to collection directory
        """
        collection_attr = f"{collection}_dir"
        if hasattr(self, collection_attr):
            dir_name = getattr(self, collection_attr)
            return Path(self.get_htmlgraph_dir()) / str(dir_name)
        raise ValueError(f"Unknown collection: {collection}")

    def get_database_path(self: SDKSettings) -> Path:  # type: ignore[misc]
        """Get the unified database path."""
        return Path(self.get_htmlgraph_dir()) / self.database_filename  # type: ignore[no-any-return]

    def get_analytics_cache_path(self: SDKSettings) -> Path:  # type: ignore[misc]
        """Get the analytics cache database path."""
        return Path(self.get_htmlgraph_dir()) / self.analytics_cache_filename  # type: ignore[no-any-return]

    def ensure_directories(self: SDKSettings) -> None:  # type: ignore[misc]
        """Create all collection directories if they don't exist."""
        htmlgraph_dir = self.get_htmlgraph_dir()
        htmlgraph_dir.mkdir(parents=True, exist_ok=True)

        # Create all collection directories
        for collection in [
            "features",
            "bugs",
            "chores",
            "spikes",
            "epics",
            "phases",
            "sessions",
            "tracks",
            "agents",
            "patterns",
            "insights",
            "metrics",
            "todos",
            "task_delegations",
            "archives",
        ]:
            self.get_collection_dir(collection).mkdir(exist_ok=True)

else:
    # Pydantic not available - provide simple fallback
    class SDKSettings:  # type: ignore[no-redef]
        """Fallback settings without Pydantic."""

        def __init__(self) -> None:
            self.project_root = Path.cwd()
            self.htmlgraph_dir_name = ".htmlgraph"
            self.database_filename = "htmlgraph.db"
            self.analytics_cache_filename = "index.sqlite"

        def get_htmlgraph_dir(self) -> Path:
            return self.project_root / self.htmlgraph_dir_name

        def get_database_path(self) -> Path:
            return self.get_htmlgraph_dir() / self.database_filename

        def get_analytics_cache_path(self) -> Path:
            return self.get_htmlgraph_dir() / self.analytics_cache_filename

    default_settings = SDKSettings()


# Error messages (centralized)
ERROR_MESSAGES = {
    "agent_required": (
        "Agent identifier is required for work attribution. "
        "Pass agent='name' to SDK() initialization. "
        "Examples: SDK(agent='explorer'), SDK(agent='coder'), SDK(agent='tester')\n"
        "Alternatively, set CLAUDE_AGENT_NAME environment variable.\n"
        "Critical for: Work attribution, result retrieval, orchestrator tracking"
    ),
    "htmlgraph_not_found": (
        "Could not find .htmlgraph directory in {path} or any parent directory. "
        "Run 'htmlgraph init' to initialize a new project."
    ),
    "invalid_collection": "Unknown collection: {collection}",
    "node_not_found": "Node not found: {node_id}",
    "session_not_found": "Session not found: {session_id}",
}


# Work type constants
WORK_TYPES = [
    "feature",
    "bug",
    "chore",
    "spike",
    "epic",
    "phase",
    "task",
    "pattern",
    "insight",
    "metric",
]


# Status constants
STATUSES = ["todo", "active", "done", "archived", "abandoned"]


# Priority constants
PRIORITIES = ["low", "medium", "high", "critical"]


__all__ = [
    "SDKSettings",
    "default_settings",
    "ERROR_MESSAGES",
    "WORK_TYPES",
    "STATUSES",
    "PRIORITIES",
]
