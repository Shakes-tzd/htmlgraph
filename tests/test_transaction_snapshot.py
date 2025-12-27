"""
Tests for transaction and snapshot functionality.

Tests the transaction pattern and snapshot capabilities for high-concurrency scenarios.
"""

import tempfile
from pathlib import Path

import pytest

from htmlgraph.graph import HtmlGraph, GraphSnapshot
from htmlgraph.models import Node


class TestSnapshot:
    """Test GraphSnapshot functionality."""

    @pytest.fixture
    def temp_graph(self):
        """Create a temporary graph with test nodes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            # Add some test nodes
            node1 = Node(id="node-001", title="Node 1", status="todo", priority="high")
            node2 = Node(id="node-002", title="Node 2", status="in-progress", priority="medium")
            node3 = Node(id="node-003", title="Node 3", status="done", priority="low")

            graph.add(node1)
            graph.add(node2)
            graph.add(node3)

            yield graph

    def test_snapshot_creation(self, temp_graph):
        """Test creating a snapshot."""
        snapshot = temp_graph.snapshot()

        assert isinstance(snapshot, GraphSnapshot)
        assert len(snapshot) == 3

    def test_snapshot_is_immutable(self, temp_graph):
        """Test that snapshot doesn't change when graph is modified."""
        snapshot = temp_graph.snapshot()

        # Verify initial state
        node = snapshot.get("node-001")
        assert node is not None
        assert node.status == "todo"

        # Modify graph
        updated_node = temp_graph.get("node-001")
        updated_node.status = "done"
        temp_graph.update(updated_node)

        # Verify snapshot is unchanged
        snapshot_node = snapshot.get("node-001")
        assert snapshot_node.status == "todo"

    def test_snapshot_get(self, temp_graph):
        """Test getting a node from snapshot."""
        snapshot = temp_graph.snapshot()

        node = snapshot.get("node-001")
        assert node is not None
        assert node.id == "node-001"
        assert node.title == "Node 1"

        # Non-existent node
        assert snapshot.get("nonexistent") is None

    def test_snapshot_query(self, temp_graph):
        """Test querying snapshot with CSS selectors."""
        snapshot = temp_graph.snapshot()

        # Query by status
        results = snapshot.query("[data-status='todo']")
        assert len(results) == 1
        assert results[0].id == "node-001"

        # Query by priority
        results = snapshot.query("[data-priority='high']")
        assert len(results) == 1
        assert results[0].id == "node-001"

    def test_snapshot_filter(self, temp_graph):
        """Test filtering snapshot with predicate."""
        snapshot = temp_graph.snapshot()

        # Filter by status
        results = snapshot.filter(lambda n: n.status == "in-progress")
        assert len(results) == 1
        assert results[0].id == "node-002"

        # Filter by priority
        results = snapshot.filter(lambda n: n.priority in ["high", "medium"])
        assert len(results) == 2

    def test_snapshot_contains(self, temp_graph):
        """Test __contains__ operator on snapshot."""
        snapshot = temp_graph.snapshot()

        assert "node-001" in snapshot
        assert "node-002" in snapshot
        assert "nonexistent" not in snapshot

    def test_snapshot_iteration(self, temp_graph):
        """Test iterating over snapshot."""
        snapshot = temp_graph.snapshot()

        nodes = list(snapshot)
        assert len(nodes) == 3

        node_ids = {node.id for node in snapshot}
        assert node_ids == {"node-001", "node-002", "node-003"}

    def test_snapshot_nodes_property(self, temp_graph):
        """Test accessing all nodes via property."""
        snapshot = temp_graph.snapshot()

        nodes = snapshot.nodes
        assert len(nodes) == 3
        assert "node-001" in nodes
        assert "node-002" in nodes
        assert "node-003" in nodes


class TestTransaction:
    """Test transaction functionality."""

    @pytest.fixture
    def temp_graph(self):
        """Create a temporary graph with test nodes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            # Add some test nodes
            node1 = Node(id="node-001", title="Node 1", status="todo")
            node2 = Node(id="node-002", title="Node 2", status="in-progress")

            graph.add(node1)
            graph.add(node2)

            yield graph

    def test_transaction_add(self, temp_graph):
        """Test adding nodes within transaction."""
        with temp_graph.transaction() as tx:
            new_node = Node(id="node-003", title="Node 3", status="todo")
            tx.add(new_node)

        # Verify node was added
        assert "node-003" in temp_graph
        node = temp_graph.get("node-003")
        assert node is not None
        assert node.title == "Node 3"

    def test_transaction_update(self, temp_graph):
        """Test updating nodes within transaction."""
        with temp_graph.transaction() as tx:
            node = temp_graph.get("node-001")
            node.status = "done"
            tx.update(node)

        # Verify node was updated
        updated = temp_graph.get("node-001")
        assert updated.status == "done"

    def test_transaction_delete(self, temp_graph):
        """Test deleting nodes within transaction."""
        with temp_graph.transaction() as tx:
            tx.delete("node-001")

        # Verify node was deleted
        assert "node-001" not in temp_graph
        assert temp_graph.get("node-001") is None

    def test_transaction_multiple_operations(self, temp_graph):
        """Test multiple operations in a single transaction."""
        with temp_graph.transaction() as tx:
            # Add new node
            new_node = Node(id="node-003", title="Node 3", status="todo")
            tx.add(new_node)

            # Update existing node
            node = temp_graph.get("node-001")
            node.status = "done"
            tx.update(node)

            # Delete another node
            tx.delete("node-002")

        # Verify all operations succeeded
        assert "node-003" in temp_graph
        assert temp_graph.get("node-001").status == "done"
        assert "node-002" not in temp_graph

    def test_transaction_rollback_on_error(self, temp_graph):
        """Test that transaction rolls back on error."""
        initial_count = len(temp_graph)
        initial_status = temp_graph.get("node-001").status

        try:
            with temp_graph.transaction() as tx:
                # Add new node
                new_node = Node(id="node-003", title="Node 3", status="todo")
                tx.add(new_node)

                # Update existing node
                node = temp_graph.get("node-001")
                node.status = "done"
                tx.update(node)

                # Raise an error to trigger rollback
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify rollback - no changes should have been persisted
        assert len(temp_graph) == initial_count
        assert "node-003" not in temp_graph
        assert temp_graph.get("node-001").status == initial_status

    def test_transaction_chaining(self, temp_graph):
        """Test chaining transaction operations."""
        with temp_graph.transaction() as tx:
            new_node = Node(id="node-003", title="Node 3", status="todo")
            tx.add(new_node).update(temp_graph.get("node-001"))

        assert "node-003" in temp_graph

    def test_transaction_empty(self, temp_graph):
        """Test transaction with no operations."""
        initial_count = len(temp_graph)

        with temp_graph.transaction() as tx:
            pass  # No operations

        # Graph should be unchanged
        assert len(temp_graph) == initial_count

    def test_transaction_add_duplicate_raises_error(self, temp_graph):
        """Test that adding duplicate node raises error and rolls back."""
        initial_count = len(temp_graph)

        try:
            with temp_graph.transaction() as tx:
                # Try to add node with existing ID
                duplicate_node = Node(id="node-001", title="Duplicate", status="todo")
                tx.add(duplicate_node)
        except ValueError:
            pass

        # Verify rollback
        assert len(temp_graph) == initial_count
        # Original node should be unchanged
        original = temp_graph.get("node-001")
        assert original.title == "Node 1"


class TestConcurrencyScenarios:
    """Test scenarios for high-concurrency usage."""

    @pytest.fixture
    def temp_graph(self):
        """Create a temporary graph with test nodes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            for i in range(10):
                node = Node(id=f"node-{i:03d}", title=f"Node {i}", status="todo")
                graph.add(node)

            yield graph

    def test_snapshot_read_while_writing(self, temp_graph):
        """Test reading from snapshot while graph is being modified."""
        # Agent 1: Take snapshot for reading
        snapshot = temp_graph.snapshot()

        # Agent 2: Modify graph
        for i in range(10):
            node = temp_graph.get(f"node-{i:03d}")
            node.status = "done"
            temp_graph.update(node)

        # Agent 1: Read from snapshot (should see old state)
        for i in range(10):
            node = snapshot.get(f"node-{i:03d}")
            assert node.status == "todo"  # Unchanged in snapshot

        # Verify graph has new state
        for i in range(10):
            node = temp_graph.get(f"node-{i:03d}")
            assert node.status == "done"

    def test_multiple_snapshots(self, temp_graph):
        """Test creating multiple snapshots at different points in time."""
        # Snapshot 1: Initial state
        snapshot1 = temp_graph.snapshot()

        # Modify half the nodes
        for i in range(5):
            node = temp_graph.get(f"node-{i:03d}")
            node.status = "in-progress"
            temp_graph.update(node)

        # Snapshot 2: After first change
        snapshot2 = temp_graph.snapshot()

        # Modify remaining nodes
        for i in range(5, 10):
            node = temp_graph.get(f"node-{i:03d}")
            node.status = "done"
            temp_graph.update(node)

        # Verify snapshots have different states
        assert len(snapshot1.filter(lambda n: n.status == "todo")) == 10
        assert len(snapshot2.filter(lambda n: n.status == "in-progress")) == 5
        assert len(snapshot2.filter(lambda n: n.status == "todo")) == 5

    def test_snapshot_before_transaction(self, temp_graph):
        """Test taking snapshot before transaction for comparison."""
        # Take snapshot before changes
        before = temp_graph.snapshot()

        # Make changes in transaction
        with temp_graph.transaction() as tx:
            for i in range(5):
                node = temp_graph.get(f"node-{i:03d}")
                node.status = "done"
                tx.update(node)

        # Take snapshot after changes
        after = temp_graph.snapshot()

        # Compare snapshots
        assert len(before.filter(lambda n: n.status == "done")) == 0
        assert len(after.filter(lambda n: n.status == "done")) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
