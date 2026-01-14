from __future__ import annotations

"""HtmlGraph CLI - Snapshot command for graph state visualization."""


import argparse
import json
from typing import Any

from rich.console import Console

from htmlgraph.cli.base import BaseCommand, CommandResult


class SnapshotFormatter:
    """Helper for agent-friendly colored output formatting.

    Uses ANSI color codes that are visible to humans but harmless to agents.
    Avoids box-drawing characters and complex table formatting.
    """

    def __init__(self) -> None:
        """Initialize formatter with Rich console."""
        # Force color output even when not in TTY
        self.console = Console(force_terminal=True, legacy_windows=False)

    def colorize_status(self, status: str) -> str:
        """Return ANSI-colored status string.

        Args:
            status: Status value (todo, in-progress, blocked, done)

        Returns:
            Colored status string with Rich markup
        """
        colors = {
            "todo": "yellow",
            "in-progress": "cyan",
            "blocked": "red",
            "done": "green",
        }
        color = colors.get(status, "white")
        return f"[{color}]{status}[/{color}]"

    def colorize_priority(self, priority: str | None) -> str:
        """Return ANSI-colored priority string.

        Args:
            priority: Priority value (critical, high, medium, low)

        Returns:
            Colored priority string with Rich markup
        """
        if not priority:
            return "[dim]-[/dim]"

        colors = {
            "critical": "red",
            "high": "red",
            "medium": "yellow",
            "low": "dim",
        }
        color = colors.get(priority, "white")
        return f"[{color}]{priority}[/{color}]"

    def colorize_ref(self, ref: str | None) -> str:
        """Return ANSI-colored ref.

        Args:
            ref: Reference string (@f1, @t1, etc.)

        Returns:
            Colored ref string with Rich markup
        """
        if not ref:
            return "    "
        return f"[cyan]{ref}[/cyan]"

    def status_symbol(self, status: str) -> str:
        """Return appropriate Unicode symbol for status.

        Args:
            status: Status value

        Returns:
            Unicode symbol representing status
        """
        symbols = {
            "done": "✓",
            "blocked": "✗",
            "in-progress": "⟳",
            "todo": "●",
        }
        return symbols.get(status, "●")

    def render(self, text: str) -> str:
        """Render Rich markup to ANSI-escaped string.

        Args:
            text: Text with Rich markup

        Returns:
            String with ANSI color codes
        """
        # Use Rich's export_text to get ANSI-formatted output
        from rich.text import Text

        # Parse Rich markup
        rich_text = Text.from_markup(text)

        # Render to string with ANSI codes
        with self.console.capture() as capture:
            self.console.print(rich_text, end="")
        return capture.get()


class SnapshotCommand(BaseCommand):
    """Generate and output a snapshot of the current graph state.

    Outputs all work items organized by type and status, optionally with
    short refs for AI-friendly references.

    Usage:
        htmlgraph snapshot                    # Human-readable with refs
        htmlgraph snapshot --format json      # JSON format
        htmlgraph snapshot --format text      # Simple text (no refs)
        htmlgraph snapshot --type feature     # Only features
        htmlgraph snapshot --status todo      # Only todo items
        htmlgraph snapshot --active           # Only active work (TODO/IN_PROGRESS)
        htmlgraph snapshot --track @t1        # Only items in track
        htmlgraph snapshot --blockers         # Only critical/blocked items
        htmlgraph snapshot --summary          # Summary with counts and progress
        htmlgraph snapshot --my-work          # Only items assigned to current agent
    """

    def __init__(
        self,
        *,
        output_format: str = "refs",
        node_type: str | None = None,
        status: str | None = None,
        track_id: str | None = None,
        active: bool = False,
        blockers: bool = False,
        summary: bool = False,
        my_work: bool = False,
    ) -> None:
        """Initialize snapshot command.

        Args:
            output_format: Output format (refs, json, text)
            node_type: Filter by type (feature, track, bug, spike, chore, epic, all)
            status: Filter by status (todo, in_progress, blocked, done, all)
            track_id: Filter by track ID or ref
            active: Show only TODO/IN_PROGRESS items
            blockers: Show only critical/blocked items
            summary: Show summary format with counts
            my_work: Show only items assigned to current agent
        """
        super().__init__()
        self.output_format = output_format
        self.node_type = node_type
        self.status = status
        self.track_id = track_id
        self.active = active
        self.blockers = blockers
        self.summary = summary
        self.my_work = my_work
        self.formatter = SnapshotFormatter()

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> SnapshotCommand:
        """Create command instance from argparse arguments."""
        cmd = cls(
            output_format=args.output_format
            if hasattr(args, "output_format")
            else "refs",
            node_type=args.type if hasattr(args, "type") else None,
            status=args.status if hasattr(args, "status") else None,
            track_id=args.track if hasattr(args, "track") else None,
            active=args.active if hasattr(args, "active") else False,
            blockers=args.blockers if hasattr(args, "blockers") else False,
            summary=args.summary if hasattr(args, "summary") else False,
            my_work=args.my_work if hasattr(args, "my_work") else False,
        )
        # If snapshot command has its own --output-format, override the global --format
        # This allows "htmlgraph snapshot --output-format json" to work without needing --format json
        if hasattr(args, "output_format"):
            cmd.override_output_format = args.output_format
        return cmd

    def execute(self) -> CommandResult:
        """Execute snapshot command."""
        sdk = self.get_sdk()

        # Gather all work items
        items = self._gather_items(sdk)

        # Format output based on output_format setting
        if self.summary:
            output = self._format_summary(items, sdk)
            return CommandResult(
                json_data=items,  # For JsonFormatter if needed
                data={"snapshot": output, "item_count": len(items)},
                text=output,
            )
        elif self.output_format == "json":
            # For JSON format, return items as both json_data and text
            # This allows both direct result.text access (in tests) and
            # JsonFormatter to work correctly
            json_text = self._format_json(items)
            return CommandResult(
                json_data=items,  # For JsonFormatter
                data=items,  # For backward compatibility
                text=json_text,  # JSON string for direct access
            )
        elif self.output_format == "refs":
            output = self._format_refs(items)
        else:  # text
            output = self._format_text(items)

        return CommandResult(
            json_data=items,  # For JsonFormatter if needed
            data={"snapshot": output, "item_count": len(items)},
            text=output,
        )

    def _gather_items(self, sdk: Any) -> list[dict[str, Any]]:
        """Gather all relevant items from SDK.

        Args:
            sdk: HtmlGraph SDK instance

        Returns:
            List of item dicts with ref, id, type, title, status, priority
        """
        items = []

        # Resolve track_id if provided as ref
        resolved_track_id = None
        if self.track_id:
            if self.track_id.startswith("@"):
                # Resolve ref to track ID
                track_node = sdk.ref(self.track_id)
                if track_node and track_node.type == "track":
                    resolved_track_id = track_node.id
            else:
                resolved_track_id = self.track_id

        # Map collection names to SDK attributes
        collection_map = {
            "feature": "features",
            "track": "tracks",
            "bug": "bugs",
            "spike": "spikes",
            "chore": "chores",
            "epic": "epics",
        }

        for node_type, collection_name in collection_map.items():
            # Apply type filter
            if (
                self.node_type
                and self.node_type != "all"
                and self.node_type != node_type
            ):
                continue

            # Get collection
            collection = getattr(sdk, collection_name, None)
            if not collection:
                continue

            # Get all nodes from collection
            nodes = collection.all()

            for node in nodes:
                # Apply status filter
                if self.status and self.status != "all" and node.status != self.status:
                    continue

                # Apply active filter
                if self.active:
                    if node.status not in ["todo", "in-progress", "blocked"]:
                        continue
                    # Filter out metadata spikes
                    if node.type == "spike" and self._is_metadata_spike(node):
                        continue

                # Apply blockers filter
                if self.blockers:
                    priority = getattr(node, "priority", None)
                    if priority != "critical" and node.status != "blocked":
                        continue

                # Apply track filter
                if resolved_track_id:
                    node_track_id = getattr(node, "track_id", None)
                    if node_track_id != resolved_track_id:
                        continue

                # Apply my_work filter
                if self.my_work:
                    assigned_to = getattr(node, "agent_assigned", None)
                    if assigned_to != sdk.agent:
                        continue

                items.append(self._node_to_dict(sdk, node))

        # Sort by type, status, then ref
        return sorted(items, key=lambda x: (x["type"], x["status"], x["ref"] or ""))

    def _is_metadata_spike(self, node: Any) -> bool:
        """Check if spike is metadata (conversation, transition, etc).

        Args:
            node: Spike node to check

        Returns:
            True if spike is metadata
        """
        title = node.title.lower()
        metadata_keywords = ["conversation", "transition", "handoff", "session"]
        return any(keyword in title for keyword in metadata_keywords)

    def _node_to_dict(self, sdk: Any, node: Any) -> dict[str, Any]:
        """Convert Node to dict with ref.

        Args:
            sdk: HtmlGraph SDK instance
            node: Node object

        Returns:
            Dict with ref, id, type, title, status, priority, assigned_to, track_id
        """
        # Get ref if available (may not exist yet)
        ref = None
        if hasattr(sdk, "refs") and sdk.refs:
            ref = sdk.refs.get_ref(node.id)

        return {
            "ref": ref,
            "id": node.id,
            "type": node.type,
            "title": node.title,
            "status": node.status,
            "priority": getattr(node, "priority", None),
            "assigned_to": getattr(node, "agent_assigned", None),
            "track_id": getattr(node, "track_id", None),
        }

    def _format_refs(self, items: list[dict]) -> str:
        """Format as readable list with refs and ANSI colors.

        Args:
            items: List of item dicts

        Returns:
            Formatted string with refs and ANSI color codes
        """
        lines = []
        lines.append("[bold]SNAPSHOT - Current Graph State[/bold]")
        lines.append("=" * 50)

        # Group by type
        by_type: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            t = item["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(item)

        # Iterate through types in consistent order
        for node_type in ["feature", "track", "bug", "spike", "chore", "epic"]:
            if node_type not in by_type:
                continue

            type_items = by_type[node_type]
            lines.append(f"\n[bold]{node_type.upper()}S ({len(type_items)})[/bold]")
            lines.append("─" * 40)

            # Group by status
            by_status: dict[str, list[dict[str, Any]]] = {}
            for item in type_items:
                status = item["status"]
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(item)

            # Iterate through statuses in consistent order
            for status in ["todo", "in-progress", "blocked", "done"]:
                if status not in by_status:
                    continue

                lines.append(f"\n{status.upper().replace('-', '_')}:")
                for item in by_status[status]:
                    ref = self.formatter.colorize_ref(item["ref"])
                    title = (
                        item["title"][:40] if len(item["title"]) > 40 else item["title"]
                    )
                    prio = self.formatter.colorize_priority(item["priority"])
                    status_colored = self.formatter.colorize_status(item["status"])
                    lines.append(f"  {ref}  {title:40s}  {prio:10s}  {status_colored}")

        # Render all lines with Rich markup to ANSI
        return self.formatter.render("\n".join(lines))

    def _format_json(self, items: list[dict]) -> str:
        """Format as JSON.

        Args:
            items: List of item dicts

        Returns:
            JSON string
        """
        return json.dumps(items, indent=2, default=str)

    def _format_text(self, items: list[dict]) -> str:
        """Format as simple text with colors (no refs).

        Args:
            items: List of item dicts

        Returns:
            Plain text string with ANSI color codes
        """
        lines = []
        for item in items:
            title = item["title"][:40] if len(item["title"]) > 40 else item["title"]
            item_type = item["type"]
            status_colored = self.formatter.colorize_status(item["status"])
            lines.append(f"{item_type:8s}  {title:40s}  {status_colored}")
        return self.formatter.render("\n".join(lines))

    def _format_summary(self, items: list[dict], sdk: Any) -> str:
        """Format as summary with counts, progress, colors, and symbols.

        Args:
            items: List of item dicts
            sdk: HtmlGraph SDK instance

        Returns:
            Summary string with ANSI colors and Unicode symbols
        """
        lines = []
        lines.append("[bold]ACTIVE WORK CONTEXT[/bold]")
        lines.append("═" * 60)
        lines.append("")

        # Show current track if track filter is active
        if self.track_id:
            track_ref = self.track_id if self.track_id.startswith("@") else None
            if not track_ref:
                # Try to get ref from track_id
                track_ref = sdk.refs.get_ref(self.track_id)
            track_ref_colored = self.formatter.colorize_ref(track_ref or self.track_id)
            lines.append(f"Current Track: {track_ref_colored}")
            lines.append("")

        # Group by type
        by_type: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            t = item["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(item)

        # Features summary
        if "feature" in by_type:
            features = by_type["feature"]
            done_count = sum(1 for f in features if f["status"] == "done")
            total_count = len(features)
            progress = int((done_count / total_count) * 100) if total_count > 0 else 0

            lines.append(
                f"[bold]● Active Features ({done_count}/{total_count} complete - {progress}%):[/bold]"
            )
            # Show active features (not done)
            active_features = [f for f in features if f["status"] != "done"]
            for feature in active_features[:5]:  # Limit to 5
                ref = self.formatter.colorize_ref(feature["ref"])
                symbol = self.formatter.status_symbol(feature["status"])
                title = (
                    feature["title"][:40]
                    if len(feature["title"]) > 40
                    else feature["title"]
                )
                prio = self.formatter.colorize_priority(feature["priority"])
                lines.append(f"  {ref}  {symbol} {title:40s}  {prio}")
            if len(active_features) > 5:
                lines.append(f"  ... and {len(active_features) - 5} more")
            lines.append("")

        # Bugs summary
        if "bug" in by_type:
            bugs = by_type["bug"]
            critical_bugs = [b for b in bugs if b["priority"] == "critical"]
            high_bugs = [b for b in bugs if b["priority"] == "high"]

            lines.append(
                f"[bold]✗ Active Bugs ({len(critical_bugs)} critical, {len(high_bugs)} high):[/bold]"
            )
            # Show critical and high priority bugs
            priority_bugs = critical_bugs + high_bugs
            for bug in priority_bugs[:5]:  # Limit to 5
                ref = self.formatter.colorize_ref(bug["ref"])
                symbol = self.formatter.status_symbol(bug["status"])
                title = bug["title"][:40] if len(bug["title"]) > 40 else bug["title"]
                prio = self.formatter.colorize_priority(bug["priority"])
                lines.append(f"  {ref}  {symbol} {title:40s}  {prio}")
            if len(priority_bugs) > 5:
                lines.append(f"  ... and {len(priority_bugs) - 5} more")
            lines.append("")

        # Blockers & Critical summary
        blockers = [
            i for i in items if i["priority"] == "critical" or i["status"] == "blocked"
        ]
        if blockers:
            lines.append(f"[bold]⚠ Blockers & Critical ({len(blockers)} items):[/bold]")
            for item in blockers[:5]:  # Limit to 5
                ref = self.formatter.colorize_ref(item["ref"])
                symbol = self.formatter.status_symbol(item["status"])
                title = item["title"][:40] if len(item["title"]) > 40 else item["title"]
                prio = self.formatter.colorize_priority(item["priority"])
                lines.append(f"  {ref}  {symbol} {title:40s}  {prio}")
            if len(blockers) > 5:
                lines.append(f"  ... and {len(blockers) - 5} more")
            lines.append("")

        # Quick Stats
        lines.append("[bold]Quick Stats:[/bold]")
        if "feature" in by_type:
            features = by_type["feature"]
            done = sum(1 for f in features if f["status"] == "done")
            total = len(features)
            progress = int((done / total) * 100) if total > 0 else 0
            if self.track_id:
                lines.append(f"  Track: {done}/{total} features ({progress}% done)")
            else:
                lines.append(f"  Features: {done}/{total} complete ({progress}% done)")

        if "bug" in by_type:
            bugs = by_type["bug"]
            open_bugs = sum(1 for b in bugs if b["status"] != "done")
            critical = sum(1 for b in bugs if b["priority"] == "critical")
            lines.append(f"  Bugs: {open_bugs} open ({critical} critical)")

        if "spike" in by_type:
            spikes = by_type["spike"]
            lines.append(f"  Spikes: {len(spikes)} active")

        if "track" in by_type:
            tracks = by_type["track"]
            active_tracks = sum(1 for t in tracks if t["status"] == "in-progress")
            lines.append(f"  Tracks: {active_tracks} active")

        return self.formatter.render("\n".join(lines))
