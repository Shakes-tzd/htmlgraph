from __future__ import annotations

"""HtmlGraph CLI - Diagnose delegation enforcement gaps."""


import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console

from htmlgraph.cli.base import BaseCommand, CommandError, CommandResult
from htmlgraph.cli.constants import DEFAULT_GRAPH_DIR

if TYPE_CHECKING:
    from argparse import _SubParsersAction

console = Console()

_QUALITY_GATE_PATTERNS = (
    "%ruff%",
    "%pytest%",
    "%mypy%",
    "%git status%",
    "%git log%",
    "%git diff%",
    "%git show%",
    "%ls %",
)

_GIT_WRITE_KEYWORDS = (
    "git commit",
    "git push",
    "git tag",
    "git merge",
    "git rebase",
    "git reset",
    "git branch -d",
)


def _build_quality_gate_filter() -> str:
    """Build SQL NOT LIKE clause for quality-gate Bash ops."""
    clauses = " AND ".join(
        f"input_summary NOT LIKE '{p}'" for p in _QUALITY_GATE_PATTERNS
    )
    return clauses


def _is_git_write(input_summary: str | None) -> bool:
    """Return True if the Bash command is a git write operation."""
    if not input_summary:
        return False
    return any(kw in input_summary for kw in _GIT_WRITE_KEYWORDS)


def _fmt_time(ts: str | None) -> str:
    """Format a DB timestamp to HH:MM."""
    if not ts:
        return "?"
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M")
    except ValueError:
        return ts[:5]


def _query_session_events(
    conn: sqlite3.Connection, session_id: str
) -> dict[str, list[Any]]:
    """Query all relevant event categories for a session."""
    quality_filter = _build_quality_gate_filter()

    direct_ops: list[Any] = conn.execute(
        f"""
        SELECT event_id, tool_name, input_summary, timestamp
        FROM agent_events
        WHERE session_id = ? AND tool_name = 'Bash'
          AND {quality_filter}
        ORDER BY timestamp
        """,
        (session_id,),
    ).fetchall()

    git_writes = [op for op in direct_ops if _is_git_write(op[2])]

    delegations: list[Any] = conn.execute(
        """
        SELECT event_id, tool_name, input_summary, timestamp
        FROM agent_events
        WHERE session_id = ? AND tool_name IN ('Task', 'Agent')
        ORDER BY timestamp
        """,
        (session_id,),
    ).fetchall()

    direct_impl: list[Any] = conn.execute(
        """
        SELECT event_id, tool_name, input_summary, timestamp
        FROM agent_events
        WHERE session_id = ? AND tool_name IN ('Edit', 'Write')
        ORDER BY timestamp
        """,
        (session_id,),
    ).fetchall()

    return {
        "direct_ops": direct_ops,
        "git_writes": git_writes,
        "delegations": delegations,
        "direct_impl": direct_impl,
    }


def register_diagnose_commands(subparsers: _SubParsersAction) -> None:
    """Register the diagnose command."""
    diagnose_parser = subparsers.add_parser(
        "diagnose",
        help="Diagnose orchestrator delegation enforcement gaps",
    )
    diagnose_parser.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    diagnose_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    diagnose_parser.set_defaults(func=DiagnoseCommand.from_args)


class DiagnoseCommand(BaseCommand):
    """Diagnose orchestrator delegation enforcement gaps."""

    _args_model = None

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> DiagnoseCommand:
        return cls()

    def execute(self) -> CommandResult:
        """Run delegation gap analysis and return a structured report."""
        if self.graph_dir is None:
            raise CommandError("Missing graph directory")

        graph_path = Path(str(self.graph_dir))
        db_path = graph_path / "htmlgraph.db"

        if not db_path.exists():
            raise CommandError(f"Database not found: {db_path}")

        # Orchestrator state
        orch_status = self._get_orchestrator_status(graph_path)

        # Session events
        events = self._get_session_events(db_path)
        session_id = events.get("session_id")

        if session_id is None:
            text = (
                "No events found in the current session.\n"
                "Verify hooks are active with: /hooks"
            )
            return CommandResult(
                text=text,
                json_data={"error": "no_session", "orchestrator": orch_status},
            )

        git_writes = events["git_writes"]
        delegations = events["delegations"]
        direct_impl = events["direct_impl"]

        # Compute delegation score
        impl_total = len(delegations) + len(direct_impl) + len(git_writes)
        score = int(len(delegations) / impl_total * 100) if impl_total > 0 else 100

        json_data: dict[str, Any] = {
            "session_id": session_id,
            "orchestrator": orch_status,
            "delegation_score": score,
            "delegations": len(delegations),
            "implementation_total": impl_total,
            "git_write_gaps": len(git_writes),
            "direct_impl_gaps": len(direct_impl),
        }

        text = self._format_report(
            orch_status=orch_status,
            score=score,
            impl_total=impl_total,
            delegations=delegations,
            git_writes=git_writes,
            direct_impl=direct_impl,
        )

        return CommandResult(text=text, json_data=json_data)

    def _get_orchestrator_status(self, graph_path: Path) -> dict[str, Any]:
        """Load orchestrator mode state."""
        try:
            from htmlgraph.orchestrator_mode import OrchestratorModeManager

            manager = OrchestratorModeManager(graph_path)
            return manager.status()
        except Exception:
            return {"enabled": False, "error": "unavailable"}

    def _get_session_events(self, db_path: Path) -> dict[str, Any]:
        """Query the SQLite DB for current session events."""
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT session_id FROM agent_events ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            if not row:
                return {"session_id": None}

            session_id = row[0]
            events = _query_session_events(conn, session_id)
            events["session_id"] = session_id
            return events
        finally:
            conn.close()

    def _format_report(
        self,
        *,
        orch_status: dict[str, Any],
        score: int,
        impl_total: int,
        delegations: list[Any],
        git_writes: list[Any],
        direct_impl: list[Any],
    ) -> str:
        """Render the diagnostic report as Rich-formatted text."""
        lines: list[str] = []

        # Orchestrator state
        lines.append("[bold]Delegation Diagnostic Report[/bold]\n")
        lines.append("[bold underline]Orchestrator State[/bold underline]")
        enabled = orch_status.get("enabled", False)
        mode_str = "enabled" if enabled else "disabled"
        level = orch_status.get("enforcement_level", "N/A")
        violations = orch_status.get("violations", 0)
        cb = "triggered" if orch_status.get("circuit_breaker_triggered") else "normal"
        lines.append(f"  Mode: {mode_str}")
        lines.append(f"  Enforcement: {level}")
        lines.append(f"  Violations: {violations}/3")
        lines.append(f"  Circuit breaker: {cb}\n")

        # Score
        score_color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
        lines.append(
            f"[bold underline]Delegation Score:[/bold underline] "
            f"[{score_color}]{score}%[/{score_color}] "
            f"({len(delegations)}/{impl_total} actions delegated)\n"
        )

        if score >= 80 and not git_writes and not direct_impl:
            lines.append("[green]No enforcement gaps found in this session.[/green]")
            return "\n".join(lines)

        lines.append("[bold underline]Gaps Found[/bold underline]\n")

        # Git write gaps
        if git_writes:
            lines.append(
                "[yellow]Git Write Operations[/yellow] — should use /htmlgraph:copilot"
            )
            for op in git_writes:
                summary = (op[2] or "")[:60]
                lines.append(f"  [{_fmt_time(op[3])}] {summary}")
            lines.append("")

        # Direct implementation gaps
        if direct_impl:
            lines.append(
                "[yellow]Direct Implementation[/yellow] — should delegate to coder agent"
            )
            for op in direct_impl:
                summary = (op[2] or "")[:60]
                lines.append(f"  [{_fmt_time(op[3])}] {op[1]}: {summary}")
            lines.append("")

        # Recommendations
        lines.append("[bold underline]Recommendations[/bold underline]")
        recs: list[str] = []
        if not enabled:
            recs.append(
                "Enable orchestrator: "
                "`uv run htmlgraph orchestrator enable --level strict`"
            )
        if git_writes:
            recs.append("Use /htmlgraph:copilot skill for git commit/push/tag")
        if direct_impl:
            recs.append(
                "Delegate Edit/Write to coder agents: "
                'Task(subagent_type="general-purpose", model="sonnet", prompt=...)'
            )
        if score < 80:
            recs.append(
                "Review orchestrator directives: /htmlgraph:orchestrator-directives-skill"
            )
        if not recs:
            recs.append("No immediate actions required.")
        for i, rec in enumerate(recs, 1):
            lines.append(f"  {i}. {rec}")

        return "\n".join(lines)
