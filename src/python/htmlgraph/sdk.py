"""
HtmlGraph SDK - AI-Friendly Interface

Provides a fluent, ergonomic API for AI agents with:
- Auto-discovery of .htmlgraph directory
- Method chaining for all operations
- Context managers for auto-save
- Batch operations
- Minimal boilerplate

Example:
    from htmlgraph import SDK

    # Auto-discovers .htmlgraph directory
    sdk = SDK(agent="claude")

    # Fluent feature creation
    feature = sdk.features.create(
        title="User Authentication",
        track="auth"
    ).add_steps([
        "Create login endpoint",
        "Add JWT middleware",
        "Write tests"
    ]).set_priority("high").save()

    # Work on a feature
    with sdk.features.get("feature-001") as feature:
        feature.start()
        feature.complete_step(0)
        # Auto-saves on exit

    # Query
    todos = sdk.features.where(status="todo", priority="high")

    # Batch operations
    sdk.features.mark_done(["feat-001", "feat-002", "feat-003"])
"""

from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Literal
from dataclasses import dataclass

from htmlgraph.models import Node, Step, Edge
from htmlgraph.graph import HtmlGraph
from htmlgraph.agents import AgentInterface


@dataclass
class FeatureBuilder:
    """Fluent builder for creating features."""

    _sdk: 'SDK'
    _data: dict[str, Any]

    def __init__(self, sdk: 'SDK', title: str, **kwargs):
        self._sdk = sdk
        self._data = {
            "title": title,
            "type": "feature",
            "status": "todo",
            "priority": "medium",
            "steps": [],
            "edges": {},
            "properties": {},
            **kwargs
        }

    def set_priority(self, priority: Literal["low", "medium", "high", "critical"]) -> FeatureBuilder:
        """Set feature priority."""
        self._data["priority"] = priority
        return self

    def set_status(self, status: str) -> FeatureBuilder:
        """Set feature status."""
        self._data["status"] = status
        return self

    def add_step(self, description: str) -> FeatureBuilder:
        """Add a single step."""
        self._data["steps"].append(Step(description=description))
        return self

    def add_steps(self, descriptions: list[str]) -> FeatureBuilder:
        """Add multiple steps."""
        for desc in descriptions:
            self._data["steps"].append(Step(description=desc))
        return self

    def set_track(self, track_id: str) -> FeatureBuilder:
        """Link to a track."""
        self._data["track_id"] = track_id
        return self

    def set_description(self, description: str) -> FeatureBuilder:
        """Set feature description."""
        self._data["content"] = f"<p>{description}</p>"
        return self

    def blocks(self, feature_id: str) -> FeatureBuilder:
        """Add blocking relationship."""
        if "blocks" not in self._data["edges"]:
            self._data["edges"]["blocks"] = []
        self._data["edges"]["blocks"].append(
            Edge(target_id=feature_id, relationship="blocks")
        )
        return self

    def blocked_by(self, feature_id: str) -> FeatureBuilder:
        """Add blocked-by relationship."""
        if "blocked_by" not in self._data["edges"]:
            self._data["edges"]["blocked_by"] = []
        self._data["edges"]["blocked_by"].append(
            Edge(target_id=feature_id, relationship="blocked_by")
        )
        return self

    def save(self) -> Node:
        """Save the feature and return the Node."""
        # Generate ID if not provided
        if "id" not in self._data:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self._data["id"] = f"feature-{timestamp}"

        node = Node(**self._data)
        self._sdk._graph.add(node)
        return node


class Collection:
    """Generic collection interface for any node type."""

    def __init__(self, sdk: 'SDK', collection_name: str, node_type: str):
        """
        Initialize a collection.

        Args:
            sdk: Parent SDK instance
            collection_name: Name of the collection (e.g., "features", "bugs")
            node_type: Node type to filter by (e.g., "feature", "bug")
        """
        self._sdk = sdk
        self._collection_name = collection_name
        self._node_type = node_type
        self._graph = None  # Lazy-loaded

    def _ensure_graph(self):
        """Lazy-load the graph for this collection."""
        if self._graph is None:
            from htmlgraph.graph import HtmlGraph
            collection_path = self._sdk._directory / self._collection_name
            self._graph = HtmlGraph(collection_path, auto_load=True)
        return self._graph

    def get(self, node_id: str) -> Node | None:
        """Get a node by ID."""
        return self._ensure_graph().get(node_id)

    @contextmanager
    def edit(self, node_id: str) -> Iterator[Node]:
        """
        Context manager for editing a node.

        Auto-saves on exit.

        Example:
            with sdk.bugs.edit("bug-001") as bug:
                bug.status = "in-progress"
        """
        graph = self._ensure_graph()
        node = graph.get(node_id)
        if not node:
            raise ValueError(f"{self._node_type.capitalize()} {node_id} not found")

        yield node

        # Auto-save on exit
        graph.update(node)

    def where(
        self,
        status: str | None = None,
        priority: str | None = None,
        track: str | None = None,
        assigned_to: str | None = None,
        **extra_filters
    ) -> list[Node]:
        """
        Query nodes with filters.

        Example:
            high_bugs = sdk.bugs.where(status="todo", priority="high")
        """
        def matches(node: Node) -> bool:
            if node.type != self._node_type:
                return False
            if status and getattr(node, 'status', None) != status:
                return False
            if priority and getattr(node, 'priority', None) != priority:
                return False
            if track and getattr(node, "track_id", None) != track:
                return False
            if assigned_to and getattr(node, 'agent_assigned', None) != assigned_to:
                return False

            # Check extra filters
            for key, value in extra_filters.items():
                if getattr(node, key, None) != value:
                    return False

            return True

        return self._ensure_graph().filter(matches)

    def all(self) -> list[Node]:
        """Get all nodes of this type."""
        return [n for n in self._ensure_graph() if n.type == self._node_type]

    def delete(self, node_id: str) -> bool:
        """
        Delete a node.

        Returns:
            True if deleted, False if not found
        """
        graph = self._ensure_graph()
        node = graph.get(node_id)
        if not node:
            return False
        graph.delete(node_id)
        return True

    def update(self, node: Node) -> Node:
        """
        Update a node.

        Args:
            node: Node to update

        Returns:
            Updated node
        """
        node.updated = datetime.now()
        self._ensure_graph().update(node)
        return node

    def batch_update(
        self,
        node_ids: list[str],
        updates: dict[str, Any]
    ) -> int:
        """
        Vectorized batch update operation.

        Args:
            node_ids: List of node IDs to update
            updates: Dictionary of attribute: value pairs to update

        Returns:
            Number of nodes successfully updated

        Example:
            sdk.bugs.batch_update(
                ["bug-1", "bug-2"],
                {"status": "done", "agent_assigned": "claude"}
            )
        """
        graph = self._ensure_graph()
        now = datetime.now()
        count = 0

        # Vectorized retrieval
        nodes = [graph.get(nid) for nid in node_ids]

        # Batch update
        for node in nodes:
            if node:
                # Apply all updates
                for attr, value in updates.items():
                    setattr(node, attr, value)
                node.updated = now
                graph.update(node)
                count += 1

        return count

    def mark_done(self, node_ids: list[str]) -> int:
        """
        Batch mark nodes as done.

        Returns:
            Number of nodes updated
        """
        return self.batch_update(node_ids, {"status": "done"})

    def assign(self, node_ids: list[str], agent: str) -> int:
        """
        Batch assign nodes to an agent.

        Returns:
            Number of nodes assigned
        """
        updates = {
            "agent_assigned": agent,
            "status": "in-progress"
        }
        return self.batch_update(node_ids, updates)


class FeatureCollection(Collection):
    """Collection interface for features with builder support."""

    def __init__(self, sdk: 'SDK'):
        super().__init__(sdk, "features", "feature")
        self._sdk = sdk

    def create(self, title: str, **kwargs) -> FeatureBuilder:
        """
        Create a new feature with fluent interface.

        Args:
            title: Feature title
            **kwargs: Additional feature properties

        Returns:
            FeatureBuilder for method chaining

        Example:
            feature = sdk.features.create("User Auth")
                .set_priority("high")
                .add_steps(["Login", "Logout"])
                .save()
        """
        return FeatureBuilder(self._sdk, title, **kwargs)


class SDK:
    """
    Main SDK interface for AI agents.

    Auto-discovers .htmlgraph directory and provides fluent API for all collections.

    Available Collections:
        - features: Feature work items with builder support
        - bugs: Bug reports
        - chores: Maintenance and chore tasks
        - spikes: Investigation and research spikes
        - epics: Large bodies of work
        - phases: Project phases
        - sessions: Agent sessions
        - tracks: Work tracks
        - agents: Agent information

    Example:
        sdk = SDK(agent="claude")

        # Work with features (has builder support)
        feature = sdk.features.create("User Auth")
            .set_priority("high")
            .add_steps(["Login", "Logout"])
            .save()

        # Work with bugs
        high_bugs = sdk.bugs.where(status="todo", priority="high")
        with sdk.bugs.edit("bug-001") as bug:
            bug.status = "in-progress"

        # Work with any collection
        all_spikes = sdk.spikes.all()
        sdk.chores.mark_done(["chore-001", "chore-002"])
        sdk.epics.assign(["epic-001"], agent="claude")
    """

    def __init__(
        self,
        directory: Path | str | None = None,
        agent: str | None = None
    ):
        """
        Initialize SDK.

        Args:
            directory: Path to .htmlgraph directory (auto-discovered if not provided)
            agent: Agent identifier for operations
        """
        if directory is None:
            directory = self._discover_htmlgraph()

        self._directory = Path(directory)
        self._agent_id = agent

        # Initialize underlying components (for backward compatibility)
        self._graph = HtmlGraph(self._directory / "features")
        self._agent_interface = AgentInterface(
            self._directory / "features",
            agent_id=agent
        )

        # Collection interfaces - all work item types
        self.features = FeatureCollection(self)
        self.bugs = Collection(self, "bugs", "bug")
        self.chores = Collection(self, "chores", "chore")
        self.spikes = Collection(self, "spikes", "spike")
        self.epics = Collection(self, "epics", "epic")
        self.phases = Collection(self, "phases", "phase")

        # Non-work collections
        self.sessions = Collection(self, "sessions", "session")
        self.tracks = Collection(self, "tracks", "track")
        self.agents = Collection(self, "agents", "agent")

    @staticmethod
    def _discover_htmlgraph() -> Path:
        """
        Auto-discover .htmlgraph directory.

        Searches current directory and parents.
        """
        current = Path.cwd()

        # Check current directory
        if (current / ".htmlgraph").exists():
            return current / ".htmlgraph"

        # Check parent directories
        for parent in current.parents:
            if (parent / ".htmlgraph").exists():
                return parent / ".htmlgraph"

        # Default to current directory
        return current / ".htmlgraph"

    @property
    def agent(self) -> str | None:
        """Get current agent ID."""
        return self._agent_id

    def reload(self) -> None:
        """Reload all data from disk."""
        self._graph.reload()
        self._agent_interface.reload()

    def summary(self, max_items: int = 10) -> str:
        """
        Get project summary.

        Returns:
            Compact overview for AI agent orientation
        """
        return self._agent_interface.get_summary(max_items)

    def my_work(self) -> dict[str, Any]:
        """
        Get current agent's workload.

        Returns:
            Dict with in_progress, completed counts
        """
        if not self._agent_id:
            raise ValueError("No agent ID set")
        return self._agent_interface.get_workload(self._agent_id)

    def next_task(
        self,
        priority: str | None = None,
        auto_claim: bool = True
    ) -> Node | None:
        """
        Get next available task for this agent.

        Args:
            priority: Optional priority filter
            auto_claim: Automatically claim the task

        Returns:
            Next available Node or None
        """
        return self._agent_interface.get_next_task(
            agent_id=self._agent_id,
            priority=priority,
            node_type="feature",
            auto_claim=auto_claim
        )
