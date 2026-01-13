"""HtmlGraph CLI - Work management commands.

Commands for managing work items:
- Features: Work item tracking
- Sessions: Session management
- Tracks: Multi-feature planning
- Archives: Archival management
- Orchestrator: Claude Code integration
- Other work-related operations
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import _SubParsersAction


def register_commands(subparsers: _SubParsersAction) -> None:
    """Register work management commands with the argument parser.

    Args:
        subparsers: Subparser action from ArgumentParser.add_subparsers()
    """
    from htmlgraph.cli.work.features import register_feature_commands
    from htmlgraph.cli.work.orchestration import (
        register_archive_commands,
        register_claude_commands,
        register_orchestrator_commands,
    )
    from htmlgraph.cli.work.report import register_report_commands
    from htmlgraph.cli.work.sessions import register_session_commands
    from htmlgraph.cli.work.tracks import register_track_commands

    # Register all command groups
    register_session_commands(subparsers)
    register_feature_commands(subparsers)
    register_track_commands(subparsers)
    register_archive_commands(subparsers)
    register_orchestrator_commands(subparsers)
    register_claude_commands(subparsers)
    register_report_commands(subparsers)


# Re-export all command classes for backward compatibility
from htmlgraph.cli.work.features import (
    FeatureClaimCommand,
    FeatureCompleteCommand,
    FeatureCreateCommand,
    FeatureListCommand,
    FeaturePrimaryCommand,
    FeatureReleaseCommand,
    FeatureStartCommand,
)
from htmlgraph.cli.work.orchestration import (
    ArchiveCreateCommand,
    ArchiveListCommand,
    ClaudeCommand,
    OrchestratorDisableCommand,
    OrchestratorEnableCommand,
    OrchestratorResetViolationsCommand,
    OrchestratorSetLevelCommand,
    OrchestratorStatusCommand,
)
from htmlgraph.cli.work.report import SessionReportCommand
from htmlgraph.cli.work.sessions import (
    SessionEndCommand,
    SessionHandoffCommand,
    SessionListCommand,
    SessionStartCommand,
    SessionStartInfoCommand,
)
from htmlgraph.cli.work.tracks import (
    TrackDeleteCommand,
    TrackListCommand,
    TrackNewCommand,
    TrackPlanCommand,
    TrackSpecCommand,
)

__all__ = [
    "register_commands",
    # Session commands
    "SessionStartCommand",
    "SessionEndCommand",
    "SessionListCommand",
    "SessionHandoffCommand",
    "SessionStartInfoCommand",
    # Report commands
    "SessionReportCommand",
    # Feature commands
    "FeatureListCommand",
    "FeatureCreateCommand",
    "FeatureStartCommand",
    "FeatureCompleteCommand",
    "FeatureClaimCommand",
    "FeatureReleaseCommand",
    "FeaturePrimaryCommand",
    # Track commands
    "TrackNewCommand",
    "TrackListCommand",
    "TrackSpecCommand",
    "TrackPlanCommand",
    "TrackDeleteCommand",
    # Orchestration commands
    "ArchiveCreateCommand",
    "ArchiveListCommand",
    "OrchestratorStatusCommand",
    "OrchestratorEnableCommand",
    "OrchestratorDisableCommand",
    "OrchestratorResetViolationsCommand",
    "OrchestratorSetLevelCommand",
    "ClaudeCommand",
]


# Convenience functions for backward compatibility with tests
def cmd_orchestrator_reset_violations(args: object) -> None:
    """Reset violations command."""
    from argparse import Namespace

    if isinstance(args, Namespace):
        cmd = OrchestratorResetViolationsCommand.from_args(args)
        cmd.graph_dir = (
            str(args.graph_dir) if hasattr(args, "graph_dir") else ".htmlgraph"
        )
        result = cmd.execute()
        from htmlgraph.cli.base import TextFormatter

        formatter = TextFormatter()
        formatter.output(result)


def cmd_orchestrator_set_level(args: object) -> None:
    """Set level command."""
    from argparse import Namespace

    if isinstance(args, Namespace):
        cmd = OrchestratorSetLevelCommand.from_args(args)
        cmd.graph_dir = (
            str(args.graph_dir) if hasattr(args, "graph_dir") else ".htmlgraph"
        )
        result = cmd.execute()
        from htmlgraph.cli.base import TextFormatter

        formatter = TextFormatter()
        formatter.output(result)


def cmd_orchestrator_status(args: object) -> None:
    """Status command."""
    from argparse import Namespace

    if isinstance(args, Namespace):
        cmd = OrchestratorStatusCommand.from_args(args)
        cmd.graph_dir = (
            str(args.graph_dir) if hasattr(args, "graph_dir") else ".htmlgraph"
        )
        result = cmd.execute()
        from htmlgraph.cli.base import TextFormatter

        formatter = TextFormatter()
        formatter.output(result)
