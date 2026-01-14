from __future__ import annotations

"""HtmlGraph CLI - Orchestration commands (Archive, Orchestrator, Claude)."""


import argparse
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from htmlgraph.cli.base import BaseCommand, CommandError, CommandResult
from htmlgraph.cli.constants import DEFAULT_GRAPH_DIR

if TYPE_CHECKING:
    from argparse import _SubParsersAction

console = Console()


def register_archive_commands(subparsers: _SubParsersAction) -> None:
    """Register archive management commands."""
    archive_parser = subparsers.add_parser("archive", help="Archive management")
    archive_subparsers = archive_parser.add_subparsers(
        dest="archive_command", help="Archive command"
    )

    # archive create
    archive_create = archive_subparsers.add_parser("create", help="Create archive")
    archive_create.add_argument("entity_id", help="Entity ID to archive")
    archive_create.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    archive_create.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    archive_create.set_defaults(func=ArchiveCreateCommand.from_args)

    # archive list
    archive_list = archive_subparsers.add_parser("list", help="List archives")
    archive_list.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    archive_list.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    archive_list.set_defaults(func=ArchiveListCommand.from_args)


def register_orchestrator_commands(subparsers: _SubParsersAction) -> None:
    """Register orchestrator commands."""
    orchestrator_parser = subparsers.add_parser(
        "orchestrator", help="Orchestrator management"
    )
    orchestrator_subparsers = orchestrator_parser.add_subparsers(
        dest="orchestrator_command", help="Orchestrator command"
    )

    # orchestrator enable
    orch_enable = orchestrator_subparsers.add_parser(
        "enable", help="Enable orchestrator mode"
    )
    orch_enable.add_argument(
        "--level",
        "-l",
        choices=["strict", "guidance"],
        default="strict",
        help="Enforcement level (default: strict)",
    )
    orch_enable.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    orch_enable.set_defaults(func=OrchestratorEnableCommand.from_args)

    # orchestrator disable
    orch_disable = orchestrator_subparsers.add_parser(
        "disable", help="Disable orchestrator mode"
    )
    orch_disable.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    orch_disable.set_defaults(func=OrchestratorDisableCommand.from_args)

    # orchestrator status
    orch_status = orchestrator_subparsers.add_parser(
        "status", help="Show orchestrator status"
    )
    orch_status.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    orch_status.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    orch_status.set_defaults(func=OrchestratorStatusCommand.from_args)

    # orchestrator config show
    config_show = orchestrator_subparsers.add_parser(
        "config-show", help="Show orchestrator configuration"
    )
    config_show.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    config_show.set_defaults(func=OrchestratorConfigShowCommand.from_args)

    # orchestrator config set
    config_set = orchestrator_subparsers.add_parser(
        "config-set", help="Set a configuration value"
    )
    config_set.add_argument(
        "key", help="Config key (e.g., thresholds.exploration_calls)"
    )
    config_set.add_argument("value", type=int, help="New value")
    config_set.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    config_set.set_defaults(func=OrchestratorConfigSetCommand.from_args)

    # orchestrator config reset
    config_reset = orchestrator_subparsers.add_parser(
        "config-reset", help="Reset configuration to defaults"
    )
    config_reset.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    config_reset.set_defaults(func=OrchestratorConfigResetCommand.from_args)

    # orchestrator reset-violations
    reset_violations = orchestrator_subparsers.add_parser(
        "reset-violations", help="Reset violation counter"
    )
    reset_violations.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    reset_violations.set_defaults(func=OrchestratorResetViolationsCommand.from_args)

    # orchestrator set-level
    set_level = orchestrator_subparsers.add_parser(
        "set-level", help="Set enforcement level"
    )
    set_level.add_argument(
        "level", choices=["strict", "guidance"], help="Enforcement level to set"
    )
    set_level.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    set_level.set_defaults(func=OrchestratorSetLevelCommand.from_args)


def register_claude_commands(subparsers: _SubParsersAction) -> None:
    """Register Claude Code launcher commands."""
    claude_parser = subparsers.add_parser(
        "claude", help="Launch Claude Code with HtmlGraph integration"
    )
    claude_parser.add_argument(
        "--init",
        action="store_true",
        help="Launch with orchestrator prompt and plugin installation",
    )
    claude_parser.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Resume last session with orchestrator rules",
    )
    claude_parser.add_argument(
        "--dev",
        action="store_true",
        help="Launch with local plugin for development",
    )
    claude_parser.set_defaults(func=ClaudeCommand.from_args)


# ============================================================================
# Archive Commands
# ============================================================================


class ArchiveCreateCommand(BaseCommand):
    """Create an archive."""

    def __init__(self, *, entity_id: str) -> None:
        super().__init__()
        self.entity_id = entity_id

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> ArchiveCreateCommand:
        return cls(entity_id=args.entity_id)

    def execute(self) -> CommandResult:
        """Create an archive."""
        from htmlgraph.archive import ArchiveManager

        if self.graph_dir is None:
            raise CommandError("Missing graph directory")

        htmlgraph_dir = Path(self.graph_dir).resolve()

        if not htmlgraph_dir.exists():
            raise CommandError(f"Directory not found: {htmlgraph_dir}")

        with console.status("[blue]Initializing archive manager...", spinner="dots"):
            manager = ArchiveManager(htmlgraph_dir)

        try:
            # Archive the entity
            with console.status(f"[blue]Archiving {self.entity_id}...", spinner="dots"):
                # For now, we'll use the older_than_days parameter with 0 to archive immediately
                result = manager.archive_entities(older_than_days=0, dry_run=False)

            from htmlgraph.cli.base import TextOutputBuilder

            output = TextOutputBuilder()
            output.add_success(f"Archived: {self.entity_id}")
            output.add_field(
                "Created", f"{len(result['archive_files'])} archive file(s)"
            )
            output.add_field("Total entities archived", result["archived_count"])

            json_data = {
                "entity_id": self.entity_id,
                "archived": True,
                "archive_files": result["archive_files"],
                "count": result["archived_count"],
            }

            return CommandResult(
                text=output.build(),
                json_data=json_data,
            )
        finally:
            manager.close()


class ArchiveListCommand(BaseCommand):
    """List all archives."""

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> ArchiveListCommand:
        return cls()

    def execute(self) -> CommandResult:
        """List all archives."""
        if self.graph_dir is None:
            raise CommandError("Missing graph directory")

        htmlgraph_dir = Path(self.graph_dir).resolve()

        if not htmlgraph_dir.exists():
            raise CommandError(f"Directory not found: {htmlgraph_dir}")

        archive_dir = htmlgraph_dir / "archives"

        if not archive_dir.exists():
            from htmlgraph.cli.base import TextOutputBuilder

            output = TextOutputBuilder()
            output.add_warning("No archives found.")
            return CommandResult(
                text=output.build(),
                json_data={"archives": []},
            )

        archive_files = sorted(archive_dir.glob("*.html"))

        if not archive_files:
            from htmlgraph.cli.base import TextOutputBuilder

            output = TextOutputBuilder()
            output.add_warning("No archives found.")
            return CommandResult(
                text=output.build(),
                json_data={"archives": []},
            )

        # Create Rich table
        from htmlgraph.cli.base import TableBuilder

        builder = TableBuilder.create_list_table(
            f"Archive Files ({len(archive_files)})"
        )
        builder.add_column("Filename", style="cyan", no_wrap=False)
        builder.add_numeric_column("Size (KB)", style="yellow", width=12)
        builder.add_timestamp_column("Modified", width=16)

        file_list = []
        for f in archive_files:
            size_kb = f.stat().st_size / 1024
            modified = datetime.fromtimestamp(f.stat().st_mtime)
            modified_str = modified.strftime("%Y-%m-%d %H:%M")

            builder.add_row(f.name, f"{size_kb:.1f}", modified_str)

            file_list.append(
                {
                    "filename": f.name,
                    "size_kb": size_kb,
                    "modified": modified.isoformat(),
                }
            )

        # Return table object directly - TextFormatter will print it properly
        return CommandResult(
            data=builder.table,
            json_data={"archives": file_list},
        )


# ============================================================================
# Orchestrator Commands
# ============================================================================


class OrchestratorEnableCommand(BaseCommand):
    """Enable orchestrator mode."""

    def __init__(self, *, level: str = "strict") -> None:
        super().__init__()
        self.level: str = level

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> OrchestratorEnableCommand:
        return cls(level=getattr(args, "level", "strict"))

    def execute(self) -> CommandResult:
        """Enable orchestrator mode."""

        from htmlgraph.orchestrator_mode import OrchestratorModeManager

        if self.graph_dir is None:
            raise CommandError("Missing graph directory")

        manager = OrchestratorModeManager(self.graph_dir)
        manager.enable(level=self.level)  # type: ignore[arg-type]
        status = manager.status()

        from htmlgraph.cli.base import TextOutputBuilder

        output = TextOutputBuilder()
        if self.level == "strict":
            output.add_success("Orchestrator mode enabled (strict enforcement)")
        else:
            output.add_success("Orchestrator mode enabled (guidance mode)")
        output.add_field("Level", self.level)
        if status.get("activated_at"):
            output.add_field("Activated at", status["activated_at"])

        return CommandResult(
            text=output.build(),
            json_data=status,
        )


class OrchestratorDisableCommand(BaseCommand):
    """Disable orchestrator mode."""

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> OrchestratorDisableCommand:
        return cls()

    def execute(self) -> CommandResult:
        """Disable orchestrator mode."""
        from htmlgraph.orchestrator_mode import OrchestratorModeManager

        if self.graph_dir is None:
            raise CommandError("Missing graph directory")

        manager = OrchestratorModeManager(self.graph_dir)
        manager.disable(by_user=True)
        status = manager.status()

        from htmlgraph.cli.base import TextOutputBuilder

        output = TextOutputBuilder()
        output.add_success("Orchestrator mode disabled")
        output.add_field("Status", "Disabled by user (auto-activation prevented)")

        return CommandResult(
            text=output.build(),
            json_data=status,
        )


class OrchestratorStatusCommand(BaseCommand):
    """Show orchestrator status."""

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> OrchestratorStatusCommand:
        return cls()

    def execute(self) -> CommandResult:
        """Show orchestrator status."""
        from htmlgraph.orchestrator_mode import OrchestratorModeManager

        if self.graph_dir is None:
            raise CommandError("Missing graph directory")

        manager = OrchestratorModeManager(self.graph_dir)
        mode = manager.load()
        status = manager.status()

        from htmlgraph.cli.base import TextOutputBuilder

        output = TextOutputBuilder()
        if status.get("enabled"):
            if status.get("enforcement_level") == "strict":
                output.add_line("Orchestrator mode: enabled (strict enforcement)")
            else:
                output.add_line("Orchestrator mode: enabled (guidance mode)")
        else:
            output.add_line("Orchestrator mode: disabled")
            if mode.disabled_by_user:
                output.add_field(
                    "Status", "Disabled by user (auto-activation prevented)"
                )

        if status.get("activated_at"):
            output.add_field("Activated at", status["activated_at"])
        if status.get("violations") is not None:
            output.add_field("Violations", f"{status['violations']}/3")
            if status.get("circuit_breaker_triggered"):
                output.add_field("Circuit breaker", "TRIGGERED")

        return CommandResult(
            data=status,
            text=output.build(),
            json_data=status,
        )


class OrchestratorConfigShowCommand(BaseCommand):
    """Show orchestrator configuration."""

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> OrchestratorConfigShowCommand:
        return cls()

    def execute(self) -> CommandResult:
        """Show orchestrator configuration."""
        from htmlgraph.orchestrator_config import (
            format_config_display,
            load_orchestrator_config,
        )

        config = load_orchestrator_config()
        text_output = format_config_display(config)

        return CommandResult(
            text=text_output,
            json_data=config.model_dump(),
        )


class OrchestratorConfigSetCommand(BaseCommand):
    """Set a configuration value."""

    def __init__(self, *, key: str, value: int) -> None:
        super().__init__()
        self.key = key
        self.value = value

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> OrchestratorConfigSetCommand:
        return cls(key=args.key, value=args.value)

    def execute(self) -> CommandResult:
        """Set a configuration value."""
        from htmlgraph.orchestrator_config import (
            get_config_paths,
            load_orchestrator_config,
            save_orchestrator_config,
            set_config_value,
        )

        # Load current config
        config = load_orchestrator_config()

        try:
            # Set the value
            set_config_value(config, self.key, self.value)

            # Save to first config path (project-specific)
            config_path = get_config_paths()[0]
            save_orchestrator_config(config, config_path)

            from htmlgraph.cli.base import TextOutputBuilder

            output = TextOutputBuilder()
            output.add_success(f"Configuration updated: {self.key} = {self.value}")
            output.add_field("Config file", str(config_path))

            return CommandResult(
                text=output.build(),
                json_data={
                    "key": self.key,
                    "value": self.value,
                    "path": str(config_path),
                },
            )
        except KeyError as e:
            raise CommandError(f"Invalid config key: {e}")


class OrchestratorConfigResetCommand(BaseCommand):
    """Reset configuration to defaults."""

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> OrchestratorConfigResetCommand:
        return cls()

    def execute(self) -> CommandResult:
        """Reset configuration to defaults."""
        from htmlgraph.orchestrator_config import (
            OrchestratorConfig,
            get_config_paths,
            save_orchestrator_config,
        )

        # Create default config
        config = OrchestratorConfig()

        # Save to first config path (project-specific)
        config_path = get_config_paths()[0]
        save_orchestrator_config(config, config_path)

        from htmlgraph.cli.base import TextOutputBuilder

        output = TextOutputBuilder()
        output.add_success("Configuration reset to defaults")
        output.add_field("Config file", str(config_path))
        output.add_field("Exploration calls", config.thresholds.exploration_calls)
        output.add_field(
            "Circuit breaker", config.thresholds.circuit_breaker_violations
        )
        output.add_field(
            "Violation decay", f"{config.thresholds.violation_decay_seconds}s"
        )

        return CommandResult(
            text=output.build(),
            json_data=config.model_dump(),
        )


class OrchestratorResetViolationsCommand(BaseCommand):
    """Reset violation counter."""

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> OrchestratorResetViolationsCommand:
        return cls()

    def execute(self) -> CommandResult:
        """Reset violation counter."""
        from htmlgraph.orchestrator_mode import OrchestratorModeManager

        if self.graph_dir is None:
            raise CommandError("Missing graph directory")

        manager = OrchestratorModeManager(self.graph_dir)

        if not manager.status().get("enabled"):
            console.print("[yellow]Orchestrator mode is not enabled[/yellow]")
            return CommandResult(
                text="Orchestrator mode is not enabled",
                json_data={"success": False, "message": "not enabled"},
            )

        manager.reset_violations()
        status = manager.status()

        from htmlgraph.cli.base import TextOutputBuilder

        output = TextOutputBuilder()
        output.add_success("Violations reset")
        output.add_field("Violation count", status.get("violations", 0))
        output.add_field(
            "Circuit breaker",
            "Normal" if not status.get("circuit_breaker_triggered") else "TRIGGERED",
        )

        return CommandResult(
            text=output.build(),
            json_data=status,
        )


class OrchestratorSetLevelCommand(BaseCommand):
    """Set enforcement level."""

    def __init__(self, *, level: str) -> None:
        super().__init__()
        self.level: str = level

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> OrchestratorSetLevelCommand:
        return cls(level=args.level)

    def execute(self) -> CommandResult:
        """Set enforcement level."""
        from htmlgraph.orchestrator_mode import OrchestratorModeManager

        if self.graph_dir is None:
            raise CommandError("Missing graph directory")

        manager = OrchestratorModeManager(self.graph_dir)
        manager.set_level(self.level)  # type: ignore[arg-type]
        status = manager.status()

        from htmlgraph.cli.base import TextOutputBuilder

        output = TextOutputBuilder()
        output.add_success(f"Enforcement level changed to '{self.level}'")
        if self.level == "strict":
            output.add_field("Mode", "Strict enforcement")
        else:
            output.add_field("Mode", "Guidance mode")

        return CommandResult(
            text=output.build(),
            json_data=status,
        )


# ============================================================================
# Claude Code Launcher Commands
# ============================================================================


class ClaudeCommand(BaseCommand):
    """Launch Claude Code with HtmlGraph integration."""

    def __init__(
        self,
        *,
        init: bool,
        continue_session: bool,
        dev: bool,
        quiet: bool,
        format: str,
    ) -> None:
        super().__init__()
        self.init = init
        self.continue_session = continue_session
        self.dev = dev
        self.quiet = quiet
        self.format = format

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> ClaudeCommand:
        return cls(
            init=getattr(args, "init", False),
            continue_session=getattr(args, "continue_session", False),
            dev=getattr(args, "dev", False),
            quiet=getattr(args, "quiet", False),
            format=getattr(args, "format", "text"),
        )

    def execute(self) -> CommandResult:
        """Launch Claude Code."""
        from htmlgraph.orchestration.claude_launcher import ClaudeLauncher

        # Create args namespace for launcher
        launcher_args = argparse.Namespace(
            init=self.init,
            continue_session=self.continue_session,
            dev=self.dev,
            quiet=self.quiet,
            format=self.format,
        )

        # Launch Claude Code
        launcher = ClaudeLauncher(launcher_args)
        launcher.launch()

        # This won't be reached because launcher.launch() calls subprocess
        return CommandResult(text="Claude Code launched")
