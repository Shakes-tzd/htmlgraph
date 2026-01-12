"""CLI constants and configuration - Single Source of Truth.

Define all constants, defaults, and configuration values here.
Never hardcode these values elsewhere in the CLI code.
"""

from pathlib import Path

# ============================================================================
# Directory and Path Constants
# ============================================================================

DEFAULT_GRAPH_DIR = ".htmlgraph"
DEFAULT_DATABASE_NAME = "htmlgraph.db"
DEFAULT_ANALYTICS_CACHE_NAME = "index.sqlite"

# Plugin paths (relative to project root)
PLUGIN_DIR_NAME = ".claude-plugin"
PLUGIN_SOURCE_DIR = "packages/claude-plugin/.claude-plugin"

# ============================================================================
# Server Configuration
# ============================================================================

DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 8080
SERVER_AUTO_PORT_RANGE = (8080, 8180)  # Try ports in this range if default taken

# ============================================================================
# Session Configuration
# ============================================================================

DEFAULT_SESSION_RETENTION_DAYS = 30
DEFAULT_MAX_SESSIONS = 100
DEFAULT_AUTO_ARCHIVE = True

# ============================================================================
# Output Format Configuration
# ============================================================================

OUTPUT_FORMATS = ["json", "text", "plain"]
DEFAULT_OUTPUT_FORMAT = "text"

# ============================================================================
# Work Item Limits
# ============================================================================

WIP_LIMIT_DEFAULT = 3  # Max concurrent work items
WIP_LIMIT_FEATURES = 3
WIP_LIMIT_SPIKES = 5
WIP_LIMIT_BUGS = 5

# ============================================================================
# Claude Integration
# ============================================================================

CLAUDE_BINARY_NAME = "claude"
CLAUDE_CODE_DOCS_URL = "https://code.claude.com"

# Orchestrator modes
CLAUDE_MODE_INIT = "init"
CLAUDE_MODE_CONTINUE = "continue"
CLAUDE_MODE_DEV = "dev"
CLAUDE_MODE_DEFAULT = "default"

# System prompt files (relative to package root)
ORCHESTRATOR_PROMPT_FILE = "orchestrator-system-prompt-optimized.txt"
ORCHESTRATION_RULES_FILE = "orchestration.md"

# ============================================================================
# Error Messages (Single Source of Truth)
# ============================================================================

ERROR_MESSAGES = {
    "missing_graph_dir": "Error: .htmlgraph directory not found: {path}",
    "missing_claude_cli": "Error: 'claude' command not found.\nPlease install Claude Code CLI: https://code.claude.com",
    "missing_plugin_dir": "Error: Plugin directory not found: {path}\nExpected location: packages/claude-plugin/.claude-plugin",
    "invalid_format": "Error: Unknown output format '{format}'. Valid: {valid_formats}",
    "wip_limit_reached": "WIP limit ({limit}) reached. Complete existing work first.",
    "feature_not_found": "Error: Feature not found: {feature_id}",
    "session_not_found": "Error: Session not found: {session_id}",
    "track_not_found": "Error: Track not found: {track_id}",
}

# ============================================================================
# Success Messages
# ============================================================================

SUCCESS_MESSAGES = {
    "feature_created": "✓ Created feature: {feature_id}",
    "feature_started": "✓ Started feature: {feature_id}",
    "feature_completed": "✓ Completed feature: {feature_id}",
    "session_started": "✓ Started session: {session_id}",
    "session_ended": "✓ Ended session: {session_id}",
    "track_created": "✓ Created track: {track_id}",
    "server_started": "✓ Server started: {url}",
}

# ============================================================================
# Rich Console Styles (Single Source of Truth)
# ============================================================================

CONSOLE_STYLES = {
    "success": "[green]",
    "error": "[red]",
    "warning": "[yellow]",
    "info": "[cyan]",
    "dim": "[dim]",
    "bold": "[bold]",
    "id": "[cyan]",
    "title": "[yellow]",
    "status": "[blue]",
    "path": "[dim]",
}

# ============================================================================
# Collection Names
# ============================================================================

COLLECTIONS = [
    "features",
    "bugs",
    "spikes",
    "chores",
    "epics",
    "sessions",
    "agents",
    "tracks",
    "task-delegations",
]

# ============================================================================
# Feature Priorities
# ============================================================================

FEATURE_PRIORITIES = ["low", "medium", "high", "critical"]
DEFAULT_FEATURE_PRIORITY = "medium"

# ============================================================================
# Session Status Values
# ============================================================================

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_ENDED = "ended"
SESSION_STATUS_ARCHIVED = "archived"

# ============================================================================
# Feature Status Values
# ============================================================================

FEATURE_STATUS_TODO = "todo"
FEATURE_STATUS_IN_PROGRESS = "in_progress"
FEATURE_STATUS_COMPLETED = "completed"
FEATURE_STATUS_BLOCKED = "blocked"

# ============================================================================
# Timeout Configuration
# ============================================================================

DEFAULT_TIMEOUT_SECONDS = 120
LONG_RUNNING_TIMEOUT_SECONDS = 600  # 10 minutes

# ============================================================================
# Helper Functions
# ============================================================================


def get_error_message(key: str, **kwargs: str) -> str:
    """Get error message template and format with kwargs.

    Usage:
        msg = get_error_message('missing_graph_dir', path='/path/to/dir')
    """
    template = ERROR_MESSAGES.get(key, "Error: {key}")
    return template.format(**kwargs)


def get_success_message(key: str, **kwargs: str) -> str:
    """Get success message template and format with kwargs.

    Usage:
        msg = get_success_message('feature_created', feature_id='feat-123')
    """
    template = SUCCESS_MESSAGES.get(key, "Success")
    return template.format(**kwargs)


def get_style(key: str) -> str:
    """Get Rich console style by key.

    Usage:
        style = get_style('success')  # Returns "[green]"
    """
    return CONSOLE_STYLES.get(key, "")


def get_plugin_dir(project_root: Path | str) -> Path:
    """Get plugin directory path from project root.

    Args:
        project_root: Project root directory

    Returns:
        Path to plugin directory
    """
    return Path(project_root) / PLUGIN_SOURCE_DIR
