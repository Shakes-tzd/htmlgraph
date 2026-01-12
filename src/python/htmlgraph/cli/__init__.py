"""HtmlGraph CLI - Modular command-line interface.

Architecture:
- base.py: Base classes, formatters, error handling
- constants.py: Single source of truth for all configuration
- main.py: Entry point, argument parsing
- core.py: Infrastructure commands (serve, init, status, etc.)
- work.py: Work management (features, sessions, tracks, etc.)
- analytics.py: Reporting and analytics commands

Usage:
    from htmlgraph.cli.main import main
    main()
"""

from htmlgraph.cli.base import (
    BaseCommand,
    CommandError,
    CommandResult,
    JsonFormatter,
    TextFormatter,
    get_formatter,
)
from htmlgraph.cli.main import main
from htmlgraph.cli.work import (
    cmd_orchestrator_reset_violations,
    cmd_orchestrator_set_level,
    cmd_orchestrator_status,
)

__all__ = [
    "main",
    "BaseCommand",
    "CommandError",
    "CommandResult",
    "JsonFormatter",
    "TextFormatter",
    "get_formatter",
    "cmd_orchestrator_reset_violations",
    "cmd_orchestrator_set_level",
    "cmd_orchestrator_status",
]
