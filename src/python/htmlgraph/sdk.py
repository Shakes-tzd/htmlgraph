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


class FeatureCollection:
    """Collection interface for features."""

    def __init__(self, sdk: 'SDK'):
        self._sdk = sdk
        self._graph = sdk._graph

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

    def get(self, feature_id: str) -> Node | None:
        """Get a feature by ID."""
        return self._graph.get(feature_id)

    @contextmanager
    def edit(self, feature_id: str) -> Iterator[Node]:
        """
        Context manager for editing a feature.

        Auto-saves on exit.

        Example:
            with sdk.features.edit("feat-001") as feature:
                feature.status = "in-progress"
                feature.steps[0].completed = True
        """
        node = self._graph.get(feature_id)
        if not node:
            raise ValueError(f"Feature {feature_id} not found")

        yield node

        # Auto-save on exit
        self._graph.update(node)

    def where(
        self,
        status: str | None = None,
        priority: str | None = None,
        track: str | None = None,
        assigned_to: str | None = None
    ) -> list[Node]:
        """
        Query features with filters.

        Example:
            high_priority_todos = sdk.features.where(
                status="todo",
                priority="high"
            )
        """
        def matches(node: Node) -> bool:
            if node.type != "feature":
                return False
            if status and node.status != status:
                return False
            if priority and node.priority != priority:
                return False
            if track and getattr(node, "track_id", None) != track:
                return False
            if assigned_to and node.agent_assigned != assigned_to:
                return False
            return True

        return self._graph.filter(matches)

    def all(self) -> list[Node]:
        """Get all features."""
        return [n for n in self._graph if n.type == "feature"]

    def mark_done(self, feature_ids: list[str]) -> int:
        """
        Batch mark features as done.

        Returns:
            Number of features updated
        """
        count = 0
        for fid in feature_ids:
            node = self._graph.get(fid)
            if node:
                node.status = "done"
                node.updated = datetime.now()
                self._graph.update(node)
                count += 1
        return count

    def assign(self, feature_ids: list[str], agent: str) -> int:
        """
        Batch assign features to an agent.

        Returns:
            Number of features assigned
        """
        count = 0
        for fid in feature_ids:
            node = self._graph.get(fid)
            if node:
                node.agent_assigned = agent
                node.status = "in-progress"
                node.updated = datetime.now()
                self._graph.update(node)
                count += 1
        return count


class SDK:
    """
    Main SDK interface for AI agents.

    Auto-discovers .htmlgraph directory and provides fluent API.

    Example:
        sdk = SDK(agent="claude")

        # Create a feature
        feature = sdk.features.create("User Auth")
            .set_priority("high")
            .add_steps(["Login", "Logout"])
            .save()

        # Edit a feature
        with sdk.features.edit("feat-001") as f:
            f.status = "done"

        # Query features
        todos = sdk.features.where(status="todo", priority="high")
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

        # Initialize underlying components
        self._graph = HtmlGraph(self._directory / "features")
        self._agent_interface = AgentInterface(
            self._directory / "features",
            agent_id=agent
        )

        # Collection interfaces
        self.features = FeatureCollection(self)

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
