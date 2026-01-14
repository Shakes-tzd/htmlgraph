from __future__ import annotations

"""HtmlGraph CLI - Session report commands.

Commands for generating "What Did Claude Do?" reports:
- report: Show chronological timeline of tool calls in a session

THE killer feature that differentiates HtmlGraph - complete observability
of AI agent activities with cost attribution and tool usage analysis.
"""


import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console

from htmlgraph.cli.base import BaseCommand, CommandError, CommandResult
from htmlgraph.cli.constants import DEFAULT_GRAPH_DIR

if TYPE_CHECKING:
    from argparse import _SubParsersAction

console = Console()


def register_report_commands(subparsers: _SubParsersAction) -> None:
    """Register report commands."""
    report_parser = subparsers.add_parser(
        "report", help="Generate 'What Did Claude Do?' session report"
    )
    report_parser.add_argument(
        "--session",
        help="Session ID (or 'latest', 'today')",
        default="latest",
    )
    report_parser.add_argument(
        "--report-format",
        choices=["terminal", "html", "markdown"],
        default="terminal",
        help="Report output format (terminal=rich formatting, html=self-contained HTML, markdown=markdown file)",
    )
    report_parser.add_argument(
        "--detail",
        choices=["basic", "full"],
        default="basic",
        help="Detail level (basic=summary, full=inputs/outputs)",
    )
    report_parser.add_argument(
        "--output", "-o", help="Output file path (for html/markdown formats)"
    )
    report_parser.add_argument(
        "--graph-dir", "-g", default=DEFAULT_GRAPH_DIR, help="Graph directory"
    )
    report_parser.set_defaults(func=SessionReportCommand.from_args)


class SessionReportCommand(BaseCommand):
    """Generate 'What Did Claude Do?' session report."""

    def __init__(
        self,
        *,
        session: str,
        report_format: str,
        detail: str,
        output: str | None,
    ) -> None:
        super().__init__()
        self.session = session
        self.report_format = report_format
        self.detail = detail
        self.output = output

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> SessionReportCommand:
        return cls(
            session=getattr(args, "session", "latest"),
            report_format=getattr(args, "report_format", "terminal"),
            detail=getattr(args, "detail", "basic"),
            output=getattr(args, "output", None),
        )

    def execute(self) -> CommandResult:
        """Generate and display session report."""
        if not self.graph_dir:
            raise CommandError("Graph directory not specified")

        graph_dir = Path(self.graph_dir)
        db_path = graph_dir / "htmlgraph.db"

        if not db_path.exists():
            console.print(
                f"[yellow]No database found at {db_path}[/yellow]\n"
                "Run some work to generate reports!"
            )
            raise CommandError("No database found", exit_code=1)

        # Resolve session ID
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            session_id = self._resolve_session_id(conn, self.session)
            if not session_id:
                console.print(f"[red]Session not found: {self.session}[/red]")
                raise CommandError("Session not found", exit_code=1)

            # Get session data
            session_data = self._get_session_data(conn, session_id)
            events = self._get_session_events(conn, session_id)

            if not events:
                console.print(
                    f"[yellow]No events found for session {session_id}[/yellow]"
                )
                # Still return success, just no events to report
                return CommandResult(text="")

            # Generate report in requested format
            if self.report_format == "terminal":
                self._render_terminal_report(session_data, events)
            elif self.report_format == "html":
                self._render_html_report(session_data, events)
            elif self.report_format == "markdown":
                self._render_markdown_report(session_data, events)

            # Return empty result to prevent default formatter output
            # (report commands handle their own output)
            return CommandResult(text="")

        finally:
            conn.close()

    def _resolve_session_id(self, conn: sqlite3.Connection, session: str) -> str | None:
        """Resolve session identifier to actual session_id."""
        cursor = conn.cursor()

        if session == "latest":
            # Get most recent session
            cursor.execute(
                """
                SELECT session_id FROM sessions
                ORDER BY created_at DESC
                LIMIT 1
            """
            )
            row = cursor.fetchone()
            return row[0] if row else None

        elif session == "today":
            # Get all sessions from today and combine them
            # For now, just return the most recent today
            today_start = (
                datetime.now()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .isoformat()
            )
            cursor.execute(
                """
                SELECT session_id FROM sessions
                WHERE created_at >= ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                (today_start,),
            )
            row = cursor.fetchone()
            return row[0] if row else None

        else:
            # Assume it's a session ID (or partial match)
            cursor.execute(
                """
                SELECT session_id FROM sessions
                WHERE session_id LIKE ?
                LIMIT 1
            """,
                (f"%{session}%",),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def _get_session_data(
        self, conn: sqlite3.Connection, session_id: str
    ) -> dict[str, Any]:
        """Get session metadata."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                session_id,
                agent_assigned,
                created_at,
                completed_at,
                total_events,
                total_tokens_used,
                status
            FROM sessions
            WHERE session_id = ?
        """,
            (session_id,),
        )

        row = cursor.fetchone()
        if not row:
            return {}

        data = dict(row)

        # Calculate duration (handle both timezone-aware and naive datetimes)
        if data.get("created_at") and data.get("completed_at"):
            start = datetime.fromisoformat(data["created_at"])
            end = datetime.fromisoformat(data["completed_at"])
            # Remove timezone info if present to avoid comparison issues
            if start.tzinfo is not None:
                start = start.replace(tzinfo=None)
            if end.tzinfo is not None:
                end = end.replace(tzinfo=None)
            duration = end - start
        elif data.get("created_at"):
            start = datetime.fromisoformat(data["created_at"])
            # Remove timezone info if present
            if start.tzinfo is not None:
                start = start.replace(tzinfo=None)
            duration = datetime.now() - start
        else:
            duration = timedelta(0)

        data["duration"] = duration
        return data

    def _get_session_events(
        self, conn: sqlite3.Connection, session_id: str
    ) -> list[dict[str, Any]]:
        """Get all tool_call events for a session in chronological order."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                event_id,
                tool_name,
                timestamp,
                input_summary,
                output_summary,
                status,
                parent_event_id,
                cost_tokens,
                execution_duration_seconds,
                subagent_type
            FROM agent_events
            WHERE session_id = ? AND event_type = 'tool_call'
            ORDER BY timestamp ASC
        """,
            (session_id,),
        )

        events = []
        for row in cursor.fetchall():
            event = dict(row)
            # Parse timestamp
            if event.get("timestamp"):
                if isinstance(event["timestamp"], str):
                    event["timestamp"] = datetime.fromisoformat(event["timestamp"])
            events.append(event)

        return events

    def _render_terminal_report(
        self, session_data: dict[str, Any], events: list[dict[str, Any]]
    ) -> None:
        """Render report to terminal using Rich."""
        # Header
        session_id = session_data.get("session_id", "unknown")
        agent = session_data.get("agent_assigned", "unknown")
        duration = session_data.get("duration", timedelta(0))
        total_tokens = session_data.get("total_tokens_used", 0)

        # Calculate estimated cost (rough approximation)
        # Average: $4.50 per 1M tokens
        est_cost = (total_tokens / 1_000_000) * 4.5 if total_tokens else 0

        # Format duration
        duration_mins = int(duration.total_seconds() / 60)
        duration_str = f"{duration_mins} minutes" if duration_mins > 0 else "< 1 minute"

        console.print(f"\n[bold cyan]Session Report: {session_id[:16]}...[/bold cyan]")
        console.print(
            f"[dim]Agent: {agent}  |  Duration: {duration_str}  |  "
            f"Tokens: {total_tokens:,}  |  Est. Cost: ${est_cost:.2f}[/dim]\n"
        )

        # Timeline
        console.print("[bold]TIMELINE:[/bold]")
        console.print("─" * 80)

        prev_timestamp = None
        for i, event in enumerate(events, 1):
            timestamp = event.get("timestamp")
            tool_name = event.get("tool_name", "unknown")
            status = event.get("status", "")
            subagent = event.get("subagent_type")

            # Format timestamp
            time_str = timestamp.strftime("%H:%M:%S") if timestamp else "??:??:??"

            # Format status indicator
            if status == "completed" or not status:
                status_icon = "✓"
                status_color = "green"
            elif status == "failed":
                status_icon = "✗"
                status_color = "red"
            else:
                status_icon = "○"
                status_color = "yellow"

            # Calculate time since last event (thinking time)
            think_time = ""
            if prev_timestamp and timestamp:
                delta = (timestamp - prev_timestamp).total_seconds()
                if delta > 5:  # Only show if > 5 seconds
                    think_time = f" [dim](+{int(delta)}s)[/dim]"

            prev_timestamp = timestamp

            # Format tool name with subagent context
            tool_display = tool_name
            if subagent:
                tool_display = f"{tool_name} [dim]({subagent})[/dim]"

            # Get input/output summaries (sanitized)
            input_summary = self._sanitize_summary(event.get("input_summary", ""))
            output_summary = self._sanitize_summary(event.get("output_summary", ""))

            # Basic display
            console.print(
                f"{time_str}  [{status_color}]{status_icon}[/{status_color}] "
                f"[cyan]{tool_display}[/cyan]{think_time}"
            )

            # Full detail mode
            if self.detail == "full":
                if input_summary:
                    console.print(f"         [dim]→ {input_summary[:80]}[/dim]")
                if output_summary:
                    console.print(f"         [dim]← {output_summary[:80]}[/dim]")

        console.print("─" * 80)

        # Summary statistics
        self._render_summary_stats(session_data, events)

    def _render_summary_stats(
        self, session_data: dict[str, Any], events: list[dict[str, Any]]
    ) -> None:
        """Render summary statistics."""
        console.print("\n[bold]SUMMARY:[/bold]")

        # Tool usage counts
        tool_counts: dict[str, int] = {}
        total_cost = 0
        for event in events:
            tool = event.get("tool_name", "unknown")
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
            total_cost += event.get("cost_tokens", 0)

        # Sort by count
        sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)

        console.print(
            f"Tools used: {', '.join(f'{tool}({count})' for tool, count in sorted_tools[:5])}"
        )

        # Files touched (extract from input summaries)
        files_touched = self._extract_files_from_events(events)
        if files_touched:
            console.print(f"Files touched: {', '.join(list(files_touched)[:5])}")
            if len(files_touched) > 5:
                console.print(f"         [dim](+{len(files_touched) - 5} more)[/dim]")

        # Tests run (look for Bash events with pytest/test)
        test_events = [
            e
            for e in events
            if e.get("tool_name") == "Bash"
            and e.get("input_summary")
            and ("pytest" in e["input_summary"] or "test" in e["input_summary"])
        ]
        if test_events:
            console.print(f"Tests run: {len(test_events)}")

        # Cost breakdown
        if total_cost > 0:
            console.print(f"Total cost: {total_cost:,} tokens")

        console.print()

    def _extract_files_from_events(self, events: list[dict[str, Any]]) -> set[str]:
        """Extract file paths from event summaries."""
        files = set()
        for event in events:
            tool = event.get("tool_name", "")
            input_summary = event.get("input_summary", "")

            # Read/Write/Edit events typically have file paths
            if tool in ["Read", "Write", "Edit"] and input_summary:
                # Extract file path (simple heuristic)
                parts = input_summary.split()
                for part in parts:
                    if "/" in part and len(part) > 3:
                        # Extract filename only
                        files.add(part.split("/")[-1])
                        if len(files) >= 10:  # Limit collection
                            break

        return files

    def _sanitize_summary(self, summary: str | None) -> str:
        """Sanitize summary to remove secrets."""
        if not summary:
            return ""

        # Simple sanitization: remove potential secrets
        # (passwords, tokens, keys)
        sensitive_patterns = [
            "password",
            "token",
            "secret",
            "key",
            "api_key",
            "auth",
        ]

        for pattern in sensitive_patterns:
            if pattern.lower() in summary.lower():
                return "[REDACTED - contains sensitive data]"

        return summary

    def _render_html_report(
        self, session_data: dict[str, Any], events: list[dict[str, Any]]
    ) -> None:
        """Render report to HTML file."""
        html_content = self._generate_html(session_data, events)

        # Determine output path
        if self.output:
            output_path = Path(self.output)
        else:
            output_path = Path(self.graph_dir or ".") / "session-report.html"

        output_path.write_text(html_content)
        console.print(f"[green]✓ HTML report saved to: {output_path}[/green]")

    def _generate_html(
        self, session_data: dict[str, Any], events: list[dict[str, Any]]
    ) -> str:
        """Generate self-contained HTML report."""
        session_id = session_data.get("session_id", "unknown")
        agent = session_data.get("agent_assigned", "unknown")
        duration = session_data.get("duration", timedelta(0))
        total_tokens = session_data.get("total_tokens_used", 0)
        est_cost = (total_tokens / 1_000_000) * 4.5 if total_tokens else 0

        duration_mins = int(duration.total_seconds() / 60)

        # Build timeline HTML
        timeline_html = ""
        prev_timestamp = None

        for event in events:
            timestamp = event.get("timestamp")
            tool_name = event.get("tool_name", "unknown")
            status = event.get("status", "")
            input_summary = self._sanitize_summary(event.get("input_summary", ""))
            output_summary = self._sanitize_summary(event.get("output_summary", ""))

            time_str = timestamp.strftime("%H:%M:%S") if timestamp else "??:??:??"

            # Status indicator
            if status == "completed" or not status:
                status_class = "success"
                status_icon = "✓"
            elif status == "failed":
                status_class = "error"
                status_icon = "✗"
            else:
                status_class = "pending"
                status_icon = "○"

            # Calculate thinking time
            think_time = ""
            if prev_timestamp and timestamp:
                delta = (timestamp - prev_timestamp).total_seconds()
                if delta > 5:
                    think_time = f'<span class="think-time">(+{int(delta)}s)</span>'

            prev_timestamp = timestamp

            # Build event row
            timeline_html += f"""
            <div class="event">
                <span class="time">{time_str}</span>
                <span class="status {status_class}">{status_icon}</span>
                <span class="tool">{tool_name}</span>
                {think_time}
            """

            if self.detail == "full":
                if input_summary:
                    timeline_html += (
                        f'<div class="detail input">→ {input_summary[:100]}</div>'
                    )
                if output_summary:
                    timeline_html += (
                        f'<div class="detail output">← {output_summary[:100]}</div>'
                    )

            timeline_html += "</div>\n"

        # Complete HTML document
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Session Report: {session_id[:16]}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .header .meta {{
            color: #666;
            font-size: 14px;
        }}
        .timeline {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .event {{
            padding: 10px;
            border-bottom: 1px solid #eee;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }}
        .event:last-child {{
            border-bottom: none;
        }}
        .time {{
            color: #666;
            margin-right: 10px;
        }}
        .status {{
            margin-right: 10px;
            font-weight: bold;
        }}
        .status.success {{
            color: #28a745;
        }}
        .status.error {{
            color: #dc3545;
        }}
        .status.pending {{
            color: #ffc107;
        }}
        .tool {{
            color: #007bff;
            font-weight: bold;
        }}
        .think-time {{
            color: #999;
            margin-left: 10px;
        }}
        .detail {{
            margin-left: 120px;
            color: #666;
            font-size: 12px;
            margin-top: 5px;
        }}
        .detail.input {{
            color: #666;
        }}
        .detail.output {{
            color: #28a745;
        }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary h2 {{
            margin-top: 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Session Report: {session_id[:16]}...</h1>
        <div class="meta">
            Agent: {agent} | Duration: {duration_mins} minutes |
            Tokens: {total_tokens:,} | Est. Cost: ${est_cost:.2f}
        </div>
    </div>

    <div class="timeline">
        <h2>Timeline</h2>
        {timeline_html}
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <p>Total events: {len(events)}</p>
        <p>Generated by HtmlGraph - "HTML is All You Need"</p>
    </div>
</body>
</html>"""

        return html

    def _render_markdown_report(
        self, session_data: dict[str, Any], events: list[dict[str, Any]]
    ) -> None:
        """Render report to Markdown file."""
        markdown_content = self._generate_markdown(session_data, events)

        # Determine output path
        if self.output:
            output_path = Path(self.output)
        else:
            output_path = Path(self.graph_dir or ".") / "session-report.md"

        output_path.write_text(markdown_content)
        console.print(f"[green]✓ Markdown report saved to: {output_path}[/green]")

    def _generate_markdown(
        self, session_data: dict[str, Any], events: list[dict[str, Any]]
    ) -> str:
        """Generate Markdown report."""
        session_id = session_data.get("session_id", "unknown")
        agent = session_data.get("agent_assigned", "unknown")
        duration = session_data.get("duration", timedelta(0))
        total_tokens = session_data.get("total_tokens_used", 0)
        est_cost = (total_tokens / 1_000_000) * 4.5 if total_tokens else 0

        duration_mins = int(duration.total_seconds() / 60)

        # Build timeline markdown
        timeline_md = ""
        prev_timestamp = None

        for event in events:
            timestamp = event.get("timestamp")
            tool_name = event.get("tool_name", "unknown")
            status = event.get("status", "")
            input_summary = self._sanitize_summary(event.get("input_summary", ""))

            time_str = timestamp.strftime("%H:%M:%S") if timestamp else "??:??:??"

            # Status indicator
            if status == "completed" or not status:
                status_icon = "✓"
            elif status == "failed":
                status_icon = "✗"
            else:
                status_icon = "○"

            # Calculate thinking time
            think_time = ""
            if prev_timestamp and timestamp:
                delta = (timestamp - prev_timestamp).total_seconds()
                if delta > 5:
                    think_time = f" *(+{int(delta)}s)*"

            prev_timestamp = timestamp

            timeline_md += f"**{time_str}** {status_icon} `{tool_name}`{think_time}\n"

            if self.detail == "full" and input_summary:
                timeline_md += f"  → {input_summary[:100]}\n"

            timeline_md += "\n"

        # Complete markdown document
        markdown = f"""# Session Report: {session_id}

**Agent:** {agent}
**Duration:** {duration_mins} minutes
**Tokens:** {total_tokens:,}
**Estimated Cost:** ${est_cost:.2f}

---

## Timeline

{timeline_md}

---

## Summary

Total events: {len(events)}

*Generated by HtmlGraph - "HTML is All You Need"*
"""

        return markdown
