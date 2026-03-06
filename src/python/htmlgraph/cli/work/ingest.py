from __future__ import annotations

"""HtmlGraph CLI - Ingest commands.

Commands for ingesting sessions from external AI tool formats:
- ingest claude-code: Import Claude Code native JSONL sessions
- ingest gemini:      Import Gemini CLI sessions
- ingest opencode:   Import OpenCode sessions
- ingest cursor:     Import Cursor AI conversations
- ingest copilot:    Import GitHub Copilot CLI sessions
- ingest codex:      Import OpenAI Codex CLI sessions
"""

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.table import Table

from htmlgraph.cli.base import BaseCommand, CommandError, CommandResult
from htmlgraph.cli.constants import DEFAULT_GRAPH_DIR

if TYPE_CHECKING:
    from argparse import _SubParsersAction

console = Console()


def register_ingest_commands(subparsers: _SubParsersAction) -> None:
    """Register ingest commands with the argument parser."""
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest sessions from external AI tools (Claude Code, etc.)",
    )
    ingest_subparsers = ingest_parser.add_subparsers(
        dest="ingest_command",
        help="Ingest source",
    )

    # ingest claude-code
    cc_parser = ingest_subparsers.add_parser(
        "claude-code",
        help="Ingest Claude Code native JSONL session files",
    )
    cc_parser.add_argument(
        "--path",
        "-p",
        help=(
            "Path to a directory containing *.jsonl files, or a single *.jsonl file. "
            "Defaults to the Claude Code project directory for the current working "
            "directory (~/.claude/projects/[encoded-cwd]/)."
        ),
    )
    cc_parser.add_argument(
        "--project",
        help=(
            "Project directory to look up in ~/.claude/projects/. "
            "Defaults to the current working directory."
        ),
    )
    cc_parser.add_argument(
        "--agent",
        default="claude-code",
        help="Agent name to assign to ingested sessions (default: claude-code)",
    )
    cc_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of sessions to ingest (newest first)",
    )
    cc_parser.add_argument(
        "--since",
        help="Only ingest sessions started after this date (ISO format, e.g. 2026-01-01)",
    )
    cc_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-ingest sessions that were already imported",
    )
    cc_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report sessions without writing to HtmlGraph",
    )
    cc_parser.add_argument(
        "--graph-dir",
        "-g",
        default=DEFAULT_GRAPH_DIR,
        help="HtmlGraph directory (default: .htmlgraph)",
    )
    cc_parser.set_defaults(func=IngestClaudeCodeCommand.from_args)

    # ingest gemini
    gemini_parser = ingest_subparsers.add_parser(
        "gemini",
        help="Ingest Gemini CLI session files (~/.gemini/tmp/)",
    )
    gemini_parser.add_argument(
        "--path",
        "-p",
        help=(
            "Path to Gemini session storage directory. "
            "Defaults to ~/.gemini/tmp/ or ~/.config/gemini/tmp/."
        ),
    )
    gemini_parser.add_argument(
        "--agent",
        default="gemini",
        help="Agent name to assign to ingested sessions (default: gemini)",
    )
    gemini_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of sessions to ingest",
    )
    gemini_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report sessions without writing to HtmlGraph",
    )
    gemini_parser.add_argument(
        "--graph-dir",
        "-g",
        default=DEFAULT_GRAPH_DIR,
        help="HtmlGraph directory (default: .htmlgraph)",
    )
    gemini_parser.set_defaults(func=IngestGeminiCommand.from_args)

    # ingest opencode
    opencode_parser = ingest_subparsers.add_parser(
        "opencode",
        help="Ingest OpenCode session files (~/.local/share/opencode/)",
    )
    opencode_parser.add_argument(
        "--path",
        "-p",
        help=(
            "Path to OpenCode storage root directory. "
            "Defaults to ~/.local/share/opencode/storage/."
        ),
    )
    opencode_parser.add_argument(
        "--agent",
        default="opencode",
        help="Agent name to assign to ingested sessions (default: opencode)",
    )
    opencode_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of sessions to ingest",
    )
    opencode_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report sessions without writing to HtmlGraph",
    )
    opencode_parser.add_argument(
        "--graph-dir",
        "-g",
        default=DEFAULT_GRAPH_DIR,
        help="HtmlGraph directory (default: .htmlgraph)",
    )
    opencode_parser.set_defaults(func=IngestOpenCodeCommand.from_args)

    # ingest cursor
    cursor_parser = ingest_subparsers.add_parser(
        "cursor",
        help="Ingest Cursor AI conversations from its SQLite tracking database",
    )
    cursor_parser.add_argument(
        "--path",
        "-p",
        help=(
            "Path to Cursor's AI tracking database file. "
            "Defaults to the platform-specific Cursor data directory."
        ),
    )
    cursor_parser.add_argument(
        "--agent",
        default="cursor",
        help="Agent name to assign to ingested sessions (default: cursor)",
    )
    cursor_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of conversations to ingest",
    )
    cursor_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report conversations without writing to HtmlGraph",
    )
    cursor_parser.add_argument(
        "--graph-dir",
        "-g",
        default=DEFAULT_GRAPH_DIR,
        help="HtmlGraph directory (default: .htmlgraph)",
    )
    cursor_parser.set_defaults(func=IngestCursorCommand.from_args)

    # ingest copilot
    copilot_parser = ingest_subparsers.add_parser(
        "copilot",
        help="Ingest GitHub Copilot CLI session files",
    )
    copilot_parser.add_argument(
        "--path",
        "-p",
        help=(
            "Path to Copilot CLI session storage directory. "
            "Defaults to the platform-specific Copilot data directory."
        ),
    )
    copilot_parser.add_argument(
        "--agent",
        default="copilot",
        help="Agent name to assign to ingested sessions (default: copilot)",
    )
    copilot_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of sessions to ingest",
    )
    copilot_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report sessions without writing to HtmlGraph",
    )
    copilot_parser.add_argument(
        "--graph-dir",
        "-g",
        default=DEFAULT_GRAPH_DIR,
        help="HtmlGraph directory (default: .htmlgraph)",
    )
    copilot_parser.set_defaults(func=IngestCopilotCommand.from_args)

    # ingest codex
    codex_parser = ingest_subparsers.add_parser(
        "codex",
        help="Ingest OpenAI Codex CLI session files (~/.codex/)",
    )
    codex_parser.add_argument(
        "--path",
        "-p",
        help=("Path to Codex session storage directory. Defaults to ~/.codex/."),
    )
    codex_parser.add_argument(
        "--agent",
        default="codex",
        help="Agent name to assign to ingested sessions (default: codex)",
    )
    codex_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of sessions to ingest",
    )
    codex_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report sessions without writing to HtmlGraph",
    )
    codex_parser.add_argument(
        "--graph-dir",
        "-g",
        default=DEFAULT_GRAPH_DIR,
        help="HtmlGraph directory (default: .htmlgraph)",
    )
    codex_parser.set_defaults(func=IngestCodexCommand.from_args)


# ============================================================================
# Command classes
# ============================================================================


class IngestClaudeCodeCommand(BaseCommand):
    """Ingest Claude Code native JSONL session files into HtmlGraph."""

    def __init__(
        self,
        *,
        path: str | None,
        project: str | None,
        agent: str,
        limit: int | None,
        since: str | None,
        overwrite: bool,
        dry_run: bool = False,
    ) -> None:
        super().__init__()
        self.path = path
        self.project = project
        self.agent = agent
        self.limit = limit
        self.since_str = since
        self.overwrite = overwrite
        self.dry_run = dry_run

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> IngestClaudeCodeCommand:
        return cls(
            path=getattr(args, "path", None),
            project=getattr(args, "project", None),
            agent=args.agent,
            limit=getattr(args, "limit", None),
            overwrite=args.overwrite,
            since=getattr(args, "since", None),
            dry_run=getattr(args, "dry_run", False),
        )

    def execute(self) -> CommandResult:
        """Execute the Claude Code ingest command."""
        from datetime import datetime, timezone

        from htmlgraph.cli.base import TextOutputBuilder
        from htmlgraph.ingest.claude_code import ClaudeCodeIngester

        if self.graph_dir is None:
            raise CommandError("Missing graph directory")

        graph_dir = Path(self.graph_dir)
        if not graph_dir.exists():
            raise CommandError(
                f"HtmlGraph directory not found: {graph_dir}. "
                "Run 'htmlgraph init' first."
            )

        # Parse --since date
        since: datetime | None = None
        if self.since_str:
            try:
                since = datetime.fromisoformat(self.since_str).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                raise CommandError(
                    f"Invalid --since date: {self.since_str!r}. "
                    "Use ISO format, e.g. 2026-01-01 or 2026-01-01T10:00:00"
                )

        ingester = ClaudeCodeIngester(
            graph_dir=graph_dir,
            agent=self.agent or "claude-code",
            overwrite=self.overwrite,
        )

        with console.status("[blue]Ingesting Claude Code sessions...", spinner="dots"):
            if self.path:
                summary = ingester.ingest_from_path(
                    path=Path(self.path),
                    limit=self.limit,
                    since=since,
                )
            else:
                project_path = Path(self.project) if self.project else None
                summary = ingester.ingest_project(
                    project_path=project_path,
                    limit=self.limit,
                    since=since,
                )

        # Build text output
        output = TextOutputBuilder()

        if summary.sessions_processed == 0 and not summary.errors:
            output.add_warning(
                "No Claude Code sessions found to ingest. "
                "Check that ~/.claude/projects/ contains sessions for this project, "
                "or specify --path to a directory of JSONL files."
            )
            return CommandResult(
                text=output.build(),
                json_data=self._summary_to_dict(summary),
            )

        output.add_success(
            f"Ingested {summary.sessions_processed} session(s) from Claude Code"
        )
        output.add_field("Created", summary.sessions_created)
        output.add_field("Updated", summary.sessions_updated)
        output.add_field("Skipped", summary.sessions_skipped)
        output.add_field("Total events imported", summary.total_events_imported)

        if summary.errors:
            output.add_warning(f"{len(summary.errors)} error(s) encountered")
            for err in summary.errors[:5]:
                output.add_line(f"  - {err}")

        # Build results table
        if summary.results:
            table = Table(
                title="Ingested Sessions",
                show_header=True,
                header_style="bold magenta",
                box=box.ROUNDED,
            )
            table.add_column("Claude Code ID", style="cyan", max_width=20)
            table.add_column("HtmlGraph ID", style="green", width=18)
            table.add_column("Status", style="yellow", width=10)
            table.add_column("Events", justify="right", style="blue", width=8)
            table.add_column("Branch", style="white", max_width=20)

            for result in summary.results:
                status = "updated" if result.was_existing else "created"
                # Truncate session_id for display
                cc_id = (
                    result.session_id[:16] + "..."
                    if len(result.session_id) > 16
                    else result.session_id
                )

                # Get branch from the session file if possible
                branch = "-"
                if result.output_path and result.output_path.exists():
                    try:
                        from htmlgraph.converter import html_to_session

                        sess = html_to_session(result.output_path)
                        branch = sess.transcript_git_branch or "-"
                    except Exception:
                        pass

                table.add_row(
                    cc_id,
                    result.htmlgraph_session_id,
                    status,
                    str(result.imported),
                    branch,
                )

            return CommandResult(
                data=table,
                text=output.build(),
                json_data=self._summary_to_dict(summary),
            )

        return CommandResult(
            text=output.build(),
            json_data=self._summary_to_dict(summary),
        )

    @staticmethod
    def _summary_to_dict(summary: object) -> dict:
        """Convert IngestSummary to a plain dict for JSON output."""
        from htmlgraph.ingest.claude_code import IngestSummary

        if not isinstance(summary, IngestSummary):
            return {}

        return {
            "sessions_processed": summary.sessions_processed,
            "sessions_created": summary.sessions_created,
            "sessions_updated": summary.sessions_updated,
            "sessions_skipped": summary.sessions_skipped,
            "total_events_imported": summary.total_events_imported,
            "errors": summary.errors,
            "results": [
                {
                    "session_id": r.session_id,
                    "htmlgraph_session_id": r.htmlgraph_session_id,
                    "imported": r.imported,
                    "skipped": r.skipped,
                    "total_entries": r.total_entries,
                    "was_existing": r.was_existing,
                    "output_path": str(r.output_path) if r.output_path else None,
                    "errors": r.errors,
                }
                for r in summary.results
            ],
        }


def _ingest_result_to_dict(result: object) -> dict:
    """Convert a generic IngestResult (gemini/opencode/cursor/copilot/codex) to a dict."""
    return {
        "ingested": getattr(result, "ingested", 0),
        "skipped": getattr(result, "skipped", 0),
        "errors": getattr(result, "errors", 0),
        "total": getattr(result, "total", 0),
    }


def _print_ingest_result(output: object, tool_name: str, result: object) -> None:
    """Print a summary for a simple IngestResult."""
    from htmlgraph.cli.base import TextOutputBuilder

    assert isinstance(output, TextOutputBuilder)
    ingested = getattr(result, "ingested", 0)
    skipped = getattr(result, "skipped", 0)
    errors = getattr(result, "errors", 0)
    total = getattr(result, "total", 0)

    if total == 0:
        output.add_warning(
            f"No {tool_name} sessions found. "
            "Check that the tool is installed and has session files, "
            "or specify --path to the session directory."
        )
    else:
        output.add_success(f"Ingested {ingested} session(s) from {tool_name}")
        output.add_field("Ingested", ingested)
        output.add_field("Skipped", skipped)
        if errors:
            output.add_warning(f"{errors} error(s) encountered")


# ============================================================================
# Gemini
# ============================================================================


class IngestGeminiCommand(BaseCommand):
    """Ingest Gemini CLI session files into HtmlGraph."""

    def __init__(
        self,
        *,
        path: str | None,
        agent: str,
        limit: int | None,
        dry_run: bool,
    ) -> None:
        super().__init__()
        self.path = path
        self.agent = agent
        self.limit = limit
        self.dry_run = dry_run

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> IngestGeminiCommand:
        return cls(
            path=getattr(args, "path", None),
            agent=args.agent,
            limit=getattr(args, "limit", None),
            dry_run=getattr(args, "dry_run", False),
        )

    def execute(self) -> CommandResult:
        from htmlgraph.cli.base import TextOutputBuilder
        from htmlgraph.ingest.gemini import ingest_gemini_sessions

        output = TextOutputBuilder()
        result = ingest_gemini_sessions(
            graph_dir=self.graph_dir,
            agent=self.agent or "gemini",
            base_path=Path(self.path) if self.path else None,
            limit=self.limit,
            dry_run=self.dry_run,
        )
        _print_ingest_result(output, "Gemini", result)
        return CommandResult(
            text=output.build(), json_data=_ingest_result_to_dict(result)
        )


# ============================================================================
# OpenCode
# ============================================================================


class IngestOpenCodeCommand(BaseCommand):
    """Ingest OpenCode session files into HtmlGraph."""

    def __init__(
        self,
        *,
        path: str | None,
        agent: str,
        limit: int | None,
        dry_run: bool,
    ) -> None:
        super().__init__()
        self.path = path
        self.agent = agent
        self.limit = limit
        self.dry_run = dry_run

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> IngestOpenCodeCommand:
        return cls(
            path=getattr(args, "path", None),
            agent=args.agent,
            limit=getattr(args, "limit", None),
            dry_run=getattr(args, "dry_run", False),
        )

    def execute(self) -> CommandResult:
        from htmlgraph.cli.base import TextOutputBuilder
        from htmlgraph.ingest.opencode import ingest_opencode_sessions

        output = TextOutputBuilder()
        result = ingest_opencode_sessions(
            graph_dir=self.graph_dir,
            agent=self.agent or "opencode",
            base_path=Path(self.path) if self.path else None,
            limit=self.limit,
            dry_run=self.dry_run,
        )
        _print_ingest_result(output, "OpenCode", result)
        return CommandResult(
            text=output.build(), json_data=_ingest_result_to_dict(result)
        )


# ============================================================================
# Cursor
# ============================================================================


class IngestCursorCommand(BaseCommand):
    """Ingest Cursor AI conversations into HtmlGraph."""

    def __init__(
        self,
        *,
        path: str | None,
        agent: str,
        limit: int | None,
        dry_run: bool,
    ) -> None:
        super().__init__()
        self.path = path
        self.agent = agent
        self.limit = limit
        self.dry_run = dry_run

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> IngestCursorCommand:
        return cls(
            path=getattr(args, "path", None),
            agent=args.agent,
            limit=getattr(args, "limit", None),
            dry_run=getattr(args, "dry_run", False),
        )

    def execute(self) -> CommandResult:
        from htmlgraph.cli.base import TextOutputBuilder
        from htmlgraph.ingest.cursor import ingest_cursor_sessions

        output = TextOutputBuilder()
        result = ingest_cursor_sessions(
            graph_dir=self.graph_dir,
            agent=self.agent or "cursor",
            db_path=Path(self.path) if self.path else None,
            limit=self.limit,
            dry_run=self.dry_run,
        )
        _print_ingest_result(output, "Cursor", result)
        return CommandResult(
            text=output.build(), json_data=_ingest_result_to_dict(result)
        )


# ============================================================================
# Copilot
# ============================================================================


class IngestCopilotCommand(BaseCommand):
    """Ingest GitHub Copilot CLI sessions into HtmlGraph."""

    def __init__(
        self,
        *,
        path: str | None,
        agent: str,
        limit: int | None,
        dry_run: bool,
    ) -> None:
        super().__init__()
        self.path = path
        self.agent = agent
        self.limit = limit
        self.dry_run = dry_run

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> IngestCopilotCommand:
        return cls(
            path=getattr(args, "path", None),
            agent=args.agent,
            limit=getattr(args, "limit", None),
            dry_run=getattr(args, "dry_run", False),
        )

    def execute(self) -> CommandResult:
        from htmlgraph.cli.base import TextOutputBuilder
        from htmlgraph.ingest.copilot import ingest_copilot_sessions

        output = TextOutputBuilder()
        result = ingest_copilot_sessions(
            graph_dir=self.graph_dir,
            agent=self.agent or "copilot",
            base_path=Path(self.path) if self.path else None,
            limit=self.limit,
            dry_run=self.dry_run,
        )
        _print_ingest_result(output, "Copilot", result)
        return CommandResult(
            text=output.build(), json_data=_ingest_result_to_dict(result)
        )


# ============================================================================
# Codex
# ============================================================================


class IngestCodexCommand(BaseCommand):
    """Ingest OpenAI Codex CLI sessions into HtmlGraph."""

    def __init__(
        self,
        *,
        path: str | None,
        agent: str,
        limit: int | None,
        dry_run: bool,
    ) -> None:
        super().__init__()
        self.path = path
        self.agent = agent
        self.limit = limit
        self.dry_run = dry_run

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> IngestCodexCommand:
        return cls(
            path=getattr(args, "path", None),
            agent=args.agent,
            limit=getattr(args, "limit", None),
            dry_run=getattr(args, "dry_run", False),
        )

    def execute(self) -> CommandResult:
        from htmlgraph.cli.base import TextOutputBuilder
        from htmlgraph.ingest.codex import ingest_codex_sessions

        output = TextOutputBuilder()
        result = ingest_codex_sessions(
            graph_dir=self.graph_dir,
            agent=self.agent or "codex",
            base_path=Path(self.path) if self.path else None,
            limit=self.limit,
            dry_run=self.dry_run,
        )
        _print_ingest_result(output, "Codex", result)
        return CommandResult(
            text=output.build(), json_data=_ingest_result_to_dict(result)
        )
