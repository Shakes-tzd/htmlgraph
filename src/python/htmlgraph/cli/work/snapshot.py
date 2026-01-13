"""HtmlGraph CLI - Snapshot command for graph state visualization."""

from __future__ import annotations

import argparse
import json
from typing import Any

from htmlgraph.cli.base import BaseCommand, CommandResult


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
    """

    def __init__(
        self,
        *,
        output_format: str = "refs",
        node_type: str | None = None,
        status: str | None = None,
    ) -> None:
        """Initialize snapshot command.

        Args:
            output_format: Output format (refs, json, text)
            node_type: Filter by type (feature, track, bug, spike, chore, epic, all)
            status: Filter by status (todo, in_progress, blocked, done, all)
        """
        super().__init__()
        self.output_format = output_format
        self.node_type = node_type
        self.status = status

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> SnapshotCommand:
        """Create command instance from argparse arguments."""
        return cls(
            output_format=args.output_format
            if hasattr(args, "output_format")
            else "refs",
            node_type=args.type if hasattr(args, "type") else None,
            status=args.status if hasattr(args, "status") else None,
        )

    def execute(self) -> CommandResult:
        """Execute snapshot command."""
        sdk = self.get_sdk()

        # Gather all work items
        items = self._gather_items(sdk)

        # Format output
        if self.output_format == "json":
            output = self._format_json(items)
        elif self.output_format == "refs":
            output = self._format_refs(items)
        else:  # text
            output = self._format_text(items)

        return CommandResult(
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

                items.append(self._node_to_dict(sdk, node))

        # Sort by type, status, then ref
        return sorted(items, key=lambda x: (x["type"], x["status"], x["ref"] or ""))

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
        """Format as readable list with refs.

        Args:
            items: List of item dicts

        Returns:
            Formatted string with refs
        """
        output = []
        output.append("SNAPSHOT - Current Graph State")
        output.append("=" * 50)

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
            output.append(f"\n{node_type.upper()}S ({len(type_items)})")
            output.append("-" * 40)

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

                output.append(f"\n  {status.upper().replace('-', '_')}:")
                for item in by_status[status]:
                    ref_str = f"{item['ref']:4s}" if item["ref"] else "    "
                    title = (
                        item["title"][:40] if len(item["title"]) > 40 else item["title"]
                    )
                    prio = item["priority"] or "-"
                    output.append(f"    {ref_str} | {title:40s} | {prio}")

        return "\n".join(output)

    def _format_json(self, items: list[dict]) -> str:
        """Format as JSON.

        Args:
            items: List of item dicts

        Returns:
            JSON string
        """
        return json.dumps(items, indent=2, default=str)

    def _format_text(self, items: list[dict]) -> str:
        """Format as simple text (no refs).

        Args:
            items: List of item dicts

        Returns:
            Plain text string
        """
        output = []
        for item in items:
            title = item["title"][:40] if len(item["title"]) > 40 else item["title"]
            output.append(f"{item['type']:8s} | {title:40s} | {item['status']}")
        return "\n".join(output)
