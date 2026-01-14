"""
CLI Analytics Command - Beautiful work type analytics with rich formatting.

This module provides the `htmlgraph analytics` command for analyzing work patterns.
"""

import argparse
from collections.abc import Iterator
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from htmlgraph import SDK, WorkType
from htmlgraph.converter import html_to_session


def cmd_analytics(args: argparse.Namespace) -> int:
    """Display work type analytics with beautiful rich formatting."""
    console = Console()
    quiet = getattr(args, "quiet", False)

    try:
        sdk = SDK(agent=args.agent or "cli")
    except Exception as e:
        console.print(f"[red]Error initializing SDK: {e}[/red]")
        return 1

    # Get session files
    sessions_dir = Path(args.graph_dir) / "sessions"

    if not sessions_dir.exists():
        console.print(
            "[yellow]No sessions found. Run some work to generate analytics![/yellow]"
        )
        return 0

    session_files = sorted(
        sessions_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if not session_files:
        console.print("[yellow]No session files found![/yellow]")
        return 0

    # Determine scope
    if args.session_id:
        # Single session analysis
        _display_session_analytics(
            console, sdk, args.session_id, args.graph_dir, quiet=quiet
        )
    elif args.recent:
        # Recent sessions
        _display_recent_sessions(
            console, sdk, session_files[: args.recent], args.graph_dir, quiet=quiet
        )
    else:
        # Project-wide overview
        _display_project_analytics(
            console, sdk, session_files, args.graph_dir, quiet=quiet
        )

    return 0


def _status_context(
    console: Console, quiet: bool, message: str
) -> AbstractContextManager[object]:
    if quiet:
        return nullcontext()
    return console.status(message)


def _iter_with_progress(
    console: Console, quiet: bool, items: list[Path], description: str
) -> Iterator[Path]:
    if quiet:
        for item in items:
            yield item
        return
    try:
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TextColumn,
            TimeElapsedColumn,
        )
    except Exception:
        for item in items:
            yield item
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task(description, total=len(items))
        for item in items:
            yield item
            progress.advance(task_id)


def _display_session_analytics(
    console: Console, sdk: "SDK", session_id: str, graph_dir: str, quiet: bool
) -> None:
    """Display analytics for a single session."""
    from htmlgraph.converter import html_to_session

    session_path = Path(graph_dir) / "sessions" / f"{session_id}.html"

    if not session_path.exists():
        console.print(f"[red]Session {session_id} not found![/red]")
        return

    try:
        with _status_context(console, quiet, "Loading session data..."):
            session = html_to_session(session_path)
    except Exception as e:
        console.print(f"[red]Error loading session: {e}[/red]")
        return

    # Get analytics
    with _status_context(console, quiet, "Computing session analytics..."):
        dist = sdk.analytics.work_type_distribution(session_id=session_id)
        ratio = sdk.analytics.spike_to_feature_ratio(session_id=session_id)
        burden = sdk.analytics.maintenance_burden(session_id=session_id)
        primary = sdk.analytics.calculate_session_primary_work_type(session_id)
        breakdown = sdk.analytics.calculate_session_work_breakdown(session_id)
        total_events = sum(breakdown.values()) if breakdown else session.event_count
        transition_metrics = sdk.analytics.transition_time_metrics(
            session_id=session_id
        )

    # Header panel
    header = Panel(
        f"[bold cyan]{session_id}[/bold cyan]\n"
        f"Agent: {session.agent} | Status: {session.status}\n"
        f"Started: {session.started_at.strftime('%Y-%m-%d %H:%M')} | Events: {total_events}",
        title="📊 Session Analytics",
        border_style="cyan",
    )
    console.print(header)
    console.print()

    # Work distribution table
    if dist:
        table = Table(title="Work Type Distribution", box=box.ROUNDED, show_header=True)
        table.add_column("Work Type", style="cyan", no_wrap=True)
        table.add_column("Percentage", justify="right", style="green")
        table.add_column("Events", justify="right", style="blue")
        table.add_column("Bar", style="magenta")

        for work_type, pct in sorted(dist.items(), key=lambda x: x[1], reverse=True):
            count = breakdown.get(work_type, 0)
            bar_length = int(pct / 2)  # Scale to 50 chars max
            bar = "█" * bar_length
            table.add_row(work_type, f"{pct:.1f}%", str(count), bar)

        console.print(table)
        console.print()

    # Metrics panel
    metrics = Table.grid(padding=1)
    metrics.add_column(style="bold cyan")
    metrics.add_column()

    if primary:
        metrics.add_row("Primary Work Type:", f"[yellow]{primary}[/yellow]")

    if ratio > 0:
        ratio_text = f"{ratio:.2f}"
        if ratio > 0.5:
            ratio_label = "[blue]Research-Heavy[/blue]"
        elif ratio > 0.2:
            ratio_label = "[green]Balanced[/green]"
        else:
            ratio_label = "[cyan]Implementation-Heavy[/cyan]"
        metrics.add_row("Spike-to-Feature Ratio:", f"{ratio_text} {ratio_label}")

    if burden > 0:
        burden_text = f"{burden:.1f}%"
        if burden > 40:
            burden_label = "[red]⚠️  HIGH[/red]"
        elif burden > 20:
            burden_label = "[yellow]Moderate[/yellow]"
        else:
            burden_label = "[green]Low[/green]"
        metrics.add_row("Maintenance Burden:", f"{burden_text} {burden_label}")

    # Add transition time metrics
    if transition_metrics.get("total_minutes", 0) > 0:
        trans_pct = transition_metrics["transition_percent"]
        trans_mins = transition_metrics["transition_minutes"]
        feat_mins = transition_metrics["feature_minutes"]

        # Format transition time
        if trans_pct > 30:
            trans_label = "[yellow]High - Lots of context switching[/yellow]"
        elif trans_pct > 15:
            trans_label = "[cyan]Moderate - Normal transitions[/cyan]"
        else:
            trans_label = "[green]Low - Focused work[/green]"

        metrics.add_row("", "")
        metrics.add_row(
            "Transition Time:",
            f"{trans_pct:.1f}% ({trans_mins:.0f} min) - {trans_label}",
        )
        metrics.add_row("Feature Work Time:", f"{feat_mins:.0f} minutes")

    console.print(Panel(metrics, title="📈 Key Metrics", border_style="green"))


def _display_recent_sessions(
    console: Console,
    sdk: "SDK",
    session_files: list[Path],
    graph_dir: str,
    quiet: bool,
) -> None:
    """Display analytics for recent sessions."""
    console.print(
        Panel(
            f"[bold cyan]Analyzing {len(session_files)} Recent Sessions[/bold cyan]",
            title="📊 Recent Sessions Analytics",
            border_style="cyan",
        )
    )
    console.print()

    # Sessions table
    table = Table(title="Session Summary", box=box.ROUNDED, show_header=True)
    table.add_column("Session ID", style="cyan", no_wrap=False, max_width=30)
    table.add_column("Agent", style="blue")
    table.add_column("Started", style="dim")
    table.add_column("Events", justify="right")
    table.add_column("Primary Type", style="yellow")
    table.add_column("Spike Ratio", justify="right")

    for session_path in _iter_with_progress(
        console, quiet, session_files, "Processing sessions"
    ):
        try:
            session = html_to_session(session_path)
            session_id = session.id

            # Get metrics
            primary = (
                sdk.analytics.calculate_session_primary_work_type(session_id) or "-"
            )
            ratio = sdk.analytics.spike_to_feature_ratio(session_id=session_id)
            breakdown = sdk.analytics.calculate_session_work_breakdown(session_id)
            total_events = sum(breakdown.values()) if breakdown else session.event_count

            # Format primary type
            if primary and len(primary) > 20:
                primary = primary.replace("-implementation", "").replace(
                    "-investigation", ""
                )

            # Format ratio
            ratio_str = f"{ratio:.2f}" if ratio > 0 else "-"

            table.add_row(
                session_id[:30] + "..." if len(session_id) > 30 else session_id,
                session.agent,
                session.started_at.strftime("%m-%d %H:%M"),
                str(total_events),
                primary,
                ratio_str,
            )
        except Exception as e:
            console.print(f"[dim red]Error loading {session_path.name}: {e}[/dim red]")
            continue

    console.print(table)


def _display_project_analytics(
    console: Console,
    sdk: "SDK",
    session_files: list[Path],
    graph_dir: str,
    quiet: bool,
) -> None:
    """Display project-wide analytics."""
    console.print(
        Panel(
            f"[bold cyan]Project-Wide Analytics[/bold cyan]\n"
            f"Analyzing {len(session_files)} total sessions",
            title="📊 HtmlGraph Project Analytics",
            border_style="cyan",
        )
    )
    console.print()

    # Get project-wide metrics
    with _status_context(console, quiet, "Computing project analytics..."):
        all_dist = sdk.analytics.work_type_distribution()
        all_ratio = sdk.analytics.spike_to_feature_ratio()
        all_burden = sdk.analytics.maintenance_burden()
        all_transition = sdk.analytics.transition_time_metrics()

    # Work distribution table
    if all_dist:
        table = Table(title="Project Work Distribution", box=box.ROUNDED)
        table.add_column("Work Type", style="cyan", no_wrap=True)
        table.add_column("Percentage", justify="right", style="green")
        table.add_column("Bar", style="magenta", min_width=50)

        for work_type, pct in sorted(
            all_dist.items(), key=lambda x: x[1], reverse=True
        ):
            bar_length = int(pct / 2)  # Scale to 50 chars max
            bar = "█" * bar_length
            table.add_row(work_type, f"{pct:.1f}%", bar)

        console.print(table)
        console.print()

    # Key metrics
    metrics = Table.grid(padding=1)
    metrics.add_column(style="bold cyan", min_width=30)
    metrics.add_column()

    # Spike-to-Feature Ratio
    ratio_text = f"{all_ratio:.2f}"
    if all_ratio > 0.5:
        ratio_desc = "[blue]Research-Heavy Project[/blue]"
        ratio_note = "Lots of exploration and investigation"
    elif all_ratio > 0.2:
        ratio_desc = "[green]Balanced Project[/green]"
        ratio_note = "Healthy mix of exploration and implementation"
    else:
        ratio_desc = "[cyan]Implementation-Heavy Project[/cyan]"
        ratio_note = "Focused on building features"

    metrics.add_row("Spike-to-Feature Ratio:", f"{ratio_text} - {ratio_desc}")
    metrics.add_row("", f"[dim]{ratio_note}[/dim]")
    metrics.add_row("", "")

    # Maintenance Burden
    burden_text = f"{all_burden:.1f}%"
    if all_burden > 40:
        burden_desc = "[red]⚠️  HIGH - Address Technical Debt[/red]"
    elif all_burden > 20:
        burden_desc = "[yellow]Moderate - Healthy Balance[/yellow]"
    else:
        burden_desc = "[green]Low - Mostly New Development[/green]"

    metrics.add_row("Maintenance Burden:", f"{burden_text} - {burden_desc}")
    metrics.add_row("", "")

    # Transition Time metrics
    if all_transition.get("total_minutes", 0) > 0:
        trans_pct = all_transition["transition_percent"]
        trans_mins = all_transition["transition_minutes"]
        all_transition["feature_minutes"]
        total_mins = all_transition["total_minutes"]

        if trans_pct > 30:
            trans_desc = "[yellow]⚠️  High Context Switching Overhead[/yellow]"
        elif trans_pct > 15:
            trans_desc = "[cyan]Moderate Transition Time[/cyan]"
        else:
            trans_desc = "[green]Low - Focused Development[/green]"

        metrics.add_row(
            "Transition Time:",
            f"{trans_pct:.1f}% ({trans_mins:.0f}m of {total_mins:.0f}m) - {trans_desc}",
        )

    console.print(
        Panel(metrics, title="📈 Project Health Metrics", border_style="green")
    )
    console.print()

    # Session type breakdown
    spike_sessions = sdk.analytics.get_sessions_by_work_type(WorkType.SPIKE.value)
    feature_sessions = sdk.analytics.get_sessions_by_work_type(WorkType.FEATURE.value)
    maintenance_sessions = sdk.analytics.get_sessions_by_work_type(
        WorkType.MAINTENANCE.value
    )

    session_table = Table(title="Session Types", box=box.SIMPLE)
    session_table.add_column("Session Type", style="cyan")
    session_table.add_column("Count", justify="right", style="green")

    session_table.add_row("Exploratory (Spike)", str(len(spike_sessions)))
    session_table.add_row("Implementation (Feature)", str(len(feature_sessions)))
    session_table.add_row("Maintenance", str(len(maintenance_sessions)))

    console.print(session_table)
    console.print()

    # Recent sessions summary
    console.print("[bold]Recent Sessions:[/bold]")
    recent_files = session_files[:5]

    for session_path in _iter_with_progress(
        console, quiet, recent_files, "Loading recent sessions"
    ):
        try:
            session = html_to_session(session_path)
            primary = (
                sdk.analytics.calculate_session_primary_work_type(session.id)
                or "unknown"
            )

            # Shorten work type
            if primary != "unknown":
                primary = primary.replace("-implementation", "").replace(
                    "-investigation", ""
                )

            console.print(
                f"  • [cyan]{session.id[:40]}[/cyan] - {session.agent} - [yellow]{primary}[/yellow]"
            )
        except Exception:
            continue

    console.print()
    console.print(
        "[dim]Run 'htmlgraph analytics --recent 10' for detailed recent session analysis[/dim]"
    )
