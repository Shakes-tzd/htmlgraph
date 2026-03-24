from __future__ import annotations

"""HtmlGraph CLI - Skill Scout commands.

Commands for project auditing and plugin recommendation:
- audit: Analyze project and recommend Claude Code plugins
- skills-search: Search for Claude Code plugins by keyword
"""


import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from htmlgraph.cli.base import BaseCommand, CommandResult
from htmlgraph.cli.constants import DEFAULT_GRAPH_DIR

if TYPE_CHECKING:
    from argparse import _SubParsersAction

console = Console()


# ============================================================================
# Command Registration
# ============================================================================


def register_commands(subparsers: _SubParsersAction) -> None:
    """Register skill scout commands with the argument parser."""
    # audit command
    audit_parser = subparsers.add_parser(
        "audit",
        help="Analyze project and recommend Claude Code plugins",
    )
    audit_parser.add_argument(
        "--path",
        default=".",
        help="Project path to analyze (default: current directory)",
    )
    audit_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of recommendations (default: 5)",
    )
    audit_parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output as JSON",
    )
    audit_parser.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    audit_parser.set_defaults(func=AuditCommand.from_args)

    # skills-install command
    install_parser = subparsers.add_parser(
        "skills-install",
        help="Install a Claude Code plugin with HtmlGraph tracking",
    )
    install_parser.add_argument("plugin_name", help="Plugin name to install")
    install_parser.add_argument(
        "--marketplace",
        default="",
        help="Optional marketplace qualifier (e.g., anthropics-claude-code)",
    )
    install_parser.add_argument(
        "--path",
        default=".",
        help="Project root for tracking (default: current directory)",
    )
    install_parser.set_defaults(func=SkillsInstallCommand.from_args)

    # skills-search command
    search_parser = subparsers.add_parser(
        "skills-search",
        help="Search for Claude Code plugins by keyword",
    )
    search_parser.add_argument("query", help="Search keyword")
    search_parser.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    search_parser.set_defaults(func=SkillsSearchCommand.from_args)


# ============================================================================
# AuditCommand
# ============================================================================


class AuditCommand(BaseCommand):
    """Analyze project and display plugin recommendations."""

    def __init__(self, path: Path, limit: int, json_output: bool) -> None:
        super().__init__()
        self.path = path
        self.limit = limit
        self.json_output = json_output

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> AuditCommand:
        return cls(
            path=Path(getattr(args, "path", ".")),
            limit=getattr(args, "limit", 5),
            json_output=getattr(args, "json_output", False),
        )

    def execute(self) -> CommandResult:
        from htmlgraph.skill_scout.plugin_index import PluginIndex
        from htmlgraph.skill_scout.project_analyzer import ProjectAnalyzer
        from htmlgraph.skill_scout.recommender import recommend

        analyzer = ProjectAnalyzer(self.path)
        signals = analyzer.analyze()

        index = PluginIndex()
        available = index.load() if not index.is_stale() else []

        recs = recommend(signals, available_plugins=available, limit=self.limit)

        if self.json_output:
            data = [
                {
                    "plugin_name": r.plugin_name,
                    "repo": r.repo,
                    "score": r.score,
                    "description": r.description,
                    "category": r.category,
                    "reasons": r.reasons,
                }
                for r in recs
            ]
            console.print(json.dumps(data, indent=2))
            return CommandResult()

        _print_audit_results(signals, recs)
        return CommandResult()


def _print_audit_results(signals: object, recs: list) -> None:  # type: ignore[type-arg]
    """Print audit results as a rich table."""
    from htmlgraph.skill_scout.project_analyzer import ProjectAnalysis

    assert isinstance(signals, ProjectAnalysis)

    langs = ", ".join(signals.languages) if signals.languages else "none detected"
    fwks = ", ".join(signals.frameworks) if signals.frameworks else "none detected"
    console.print(f"\n[bold]Languages:[/bold] {langs}")
    console.print(f"[bold]Frameworks:[/bold] {fwks}")
    console.print(
        f"[dim]Signals: has_ci={signals.has_ci}, "
        f"has_tests={signals.has_tests}, "
        f"has_docker={signals.has_docker}[/dim]\n"
    )

    if not recs:
        console.print("[yellow]No plugin recommendations found.[/yellow]")
        return

    table = Table(title="Plugin Recommendations")
    table.add_column("Plugin", style="cyan")
    table.add_column("Score", style="yellow", justify="right")
    table.add_column("Reasons")

    for rec in recs:
        table.add_row(rec.plugin_name, str(rec.score), "\n".join(rec.reasons))

    console.print(table)
    console.print("\n[dim]Install: claude plugin install <plugin-name>[/dim]")


# ============================================================================
# SkillsInstallCommand
# ============================================================================


class SkillsInstallCommand(BaseCommand):
    """Install a Claude Code plugin with HtmlGraph tracking."""

    def __init__(self, plugin_name: str, marketplace: str, path: Path) -> None:
        super().__init__()
        self.plugin_name = plugin_name
        self.marketplace = marketplace
        self.path = path

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> SkillsInstallCommand:
        return cls(
            plugin_name=args.plugin_name,
            marketplace=getattr(args, "marketplace", ""),
            path=Path(getattr(args, "path", ".")),
        )

    def execute(self) -> CommandResult:
        from htmlgraph.skill_scout.installer import install_plugin

        console.print(f"[dim]Installing {self.plugin_name}...[/dim]")
        result = install_plugin(self.plugin_name, self.marketplace, self.path)

        if result.success:
            console.print(f"[green]✓[/green] {result.message}")
            console.print("[dim]Tracked in .htmlgraph/installed-plugins.json[/dim]")
        else:
            console.print(f"[red]✗[/red] {result.message}")

        return CommandResult()


# ============================================================================
# SkillsSearchCommand
# ============================================================================


class SkillsSearchCommand(BaseCommand):
    """Search plugin index by keyword."""

    def __init__(self, query: str) -> None:
        super().__init__()
        self.query = query

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> SkillsSearchCommand:
        return cls(query=args.query)

    def execute(self) -> CommandResult:
        from htmlgraph.skill_scout.plugin_index import PluginIndex

        index = PluginIndex()
        if index.is_stale():
            console.print("[dim]Refreshing plugin index...[/dim]")
            index.refresh()

        results = index.search(self.query)

        if not results:
            console.print(f"[yellow]No plugins found matching '{self.query}'[/yellow]")
            return CommandResult()

        table = Table(title=f"Plugins matching '{self.query}'")
        table.add_column("Name", style="cyan")
        table.add_column("Repo", style="dim")
        table.add_column("Description")

        for p in results[:10]:
            table.add_row(p.name, p.repo, p.description)

        console.print(table)
        return CommandResult()
