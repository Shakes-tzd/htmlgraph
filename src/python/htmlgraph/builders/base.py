"""
Base builder class for fluent node creation.

Provides common builder patterns shared across all node types.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, TypeVar, Generic
from datetime import datetime

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK
    from htmlgraph.models import Node

from htmlgraph.models import Step, Edge
from htmlgraph.ids import generate_id

# Generic type for the builder subclass
BuilderT = TypeVar('BuilderT', bound='BaseBuilder')


class BaseBuilder(Generic[BuilderT]):
    """
    Base builder for creating nodes with fluent interface.

    Provides common methods shared across all node types:
    - Priority and status management
    - Step management
    - Relationship management (blocks, blocked_by)
    - Description/content
    - Save functionality

    Subclasses should:
    1. Set `node_type` class attribute
    2. Override `__init__` to set node-specific defaults
    3. Add node-specific builder methods
    """

    node_type: str = "node"  # Override in subclasses

    def __init__(self, sdk: 'SDK', title: str, **kwargs):
        """
        Initialize builder.

        Args:
            sdk: Parent SDK instance
            title: Node title
            **kwargs: Additional node data
        """
        self._sdk = sdk
        self._data: dict[str, Any] = {
            "title": title,
            "type": self.node_type,
            "status": "todo",
            "priority": "medium",
            "steps": [],
            "edges": {},
            "properties": {},
            **kwargs
        }

    def set_priority(self, priority: str) -> BuilderT:
        """Set node priority (low, medium, high, critical)."""
        self._data["priority"] = priority
        return self  # type: ignore

    def set_status(self, status: str) -> BuilderT:
        """Set node status (todo, in-progress, blocked, done, etc.)."""
        self._data["status"] = status
        return self  # type: ignore

    def add_step(self, description: str) -> BuilderT:
        """Add a single implementation step."""
        self._data["steps"].append(Step(description=description))
        return self  # type: ignore

    def add_steps(self, descriptions: list[str]) -> BuilderT:
        """Add multiple implementation steps."""
        for desc in descriptions:
            self._data["steps"].append(Step(description=desc))
        return self  # type: ignore

    def set_description(self, description: str) -> BuilderT:
        """Set node description/content."""
        self._data["content"] = f"<p>{description}</p>"
        return self  # type: ignore

    def blocks(self, node_id: str) -> BuilderT:
        """Add blocking relationship (this node blocks another)."""
        if "blocks" not in self._data["edges"]:
            self._data["edges"]["blocks"] = []
        self._data["edges"]["blocks"].append(
            Edge(target_id=node_id, relationship="blocks")
        )
        return self  # type: ignore

    def blocked_by(self, node_id: str) -> BuilderT:
        """Add blocked-by relationship (this node is blocked by another)."""
        if "blocked_by" not in self._data["edges"]:
            self._data["edges"]["blocked_by"] = []
        self._data["edges"]["blocked_by"].append(
            Edge(target_id=node_id, relationship="blocked_by")
        )
        return self  # type: ignore

    def set_track(self, track_id: str) -> BuilderT:
        """Link to a track."""
        self._data["track_id"] = track_id
        return self  # type: ignore

    def complete_and_handoff(
        self,
        reason: str,
        notes: str | None = None,
        next_agent: str | None = None,
    ) -> BuilderT:
        """
        Mark as complete and create handoff for next agent.

        Args:
            reason: Reason for handoff
            notes: Detailed handoff context/decisions
            next_agent: Next agent to claim (optional)

        Returns:
            Self for method chaining
        """
        self._data["handoff_required"] = True
        self._data["handoff_reason"] = reason
        self._data["handoff_notes"] = notes
        self._data["handoff_timestamp"] = datetime.now()
        return self  # type: ignore

    def save(self) -> 'Node':
        """
        Save the node and return the Node instance.

        Generates ID if not provided, creates Node instance,
        and adds to the correct collection's graph.

        Returns:
            Created Node instance
        """
        # Generate collision-resistant ID if not provided
        if "id" not in self._data:
            self._data["id"] = generate_id(
                node_type=self._data.get("type", self.node_type),
                title=self._data.get("title", ""),
            )

        # Import Node here to avoid circular imports
        from htmlgraph.models import Node
        from htmlgraph.graph import HtmlGraph

        node = Node(**self._data)

        # Save to the correct collection directory based on node type
        # Use the collection's graph, not SDK._graph (which is features-only)
        collection_name = self._data.get("type", self.node_type) + "s"
        graph_path = self._sdk._directory / collection_name
        graph = HtmlGraph(graph_path, auto_load=False)
        graph.add(node)

        # Log creation event if SessionManager is available and agent is set
        if hasattr(self._sdk, 'session_manager') and self._sdk.agent:
            try:
                self._sdk.session_manager._maybe_log_work_item_action(
                    agent=self._sdk.agent,
                    tool="FeatureCreate",
                    summary=f"Created: {collection_name}/{node.id}",
                    feature_id=node.id,
                    payload={"collection": collection_name, "action": "create", "title": node.title},
                )
            except Exception:
                # Never break save because of logging
                pass

        return node
