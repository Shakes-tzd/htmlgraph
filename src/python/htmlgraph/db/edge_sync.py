"""
HTML <-> SQLite edge synchronization.

Provides idempotent sync between HTML file edges (in <nav data-graph-edges>)
and the SQLite graph_edges table. Ensures both stores stay consistent.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.db.schema import HtmlGraphDB
    from htmlgraph.graph import HtmlGraph

logger = logging.getLogger(__name__)


def sync_html_edges_to_sqlite(graph_dir: Path, db: HtmlGraphDB) -> int:
    """
    Scan all HTML nodes and upsert their edges into the SQLite graph_edges table.

    Reads edges from <nav data-graph-edges> sections in HTML files across
    features/, bugs/, and spikes/ subdirectories. For each edge found,
    inserts into graph_edges if not already present (idempotent).

    Args:
        graph_dir: Path to .htmlgraph directory
        db: HtmlGraphDB instance with active connection

    Returns:
        Number of edges synced (inserted, not counting skipped duplicates)
    """
    from htmlgraph.ids import PREFIX_TO_TYPE
    from htmlgraph.parser import HtmlParser

    synced = 0
    subdirs = ["features", "bugs", "spikes"]

    for subdir in subdirs:
        subdir_path = graph_dir / subdir
        if not subdir_path.is_dir():
            continue

        for html_file in subdir_path.glob("*.html"):
            try:
                parser = HtmlParser.from_file(html_file)
                node_id = parser.get_node_id()
                if not node_id:
                    continue

                # Infer source node type from ID prefix
                prefix = node_id.split("-")[0] if "-" in node_id else ""
                from_type = PREFIX_TO_TYPE.get(prefix, "feature")

                edges = parser.get_edges()
                for rel_type, edge_list in edges.items():
                    for edge_data in edge_list:
                        target_id = edge_data.get("target_id", "")
                        if not target_id:
                            continue

                        # Infer target node type
                        target_prefix = (
                            target_id.split("-")[0] if "-" in target_id else ""
                        )
                        to_type = PREFIX_TO_TYPE.get(target_prefix, "feature")

                        relationship = edge_data.get("relationship", rel_type)

                        # Check if this edge already exists to avoid duplicates
                        existing = db.get_graph_edges(
                            node_id,
                            direction="outgoing",
                            relationship_type=relationship,
                        )
                        already_exists = any(
                            e["to_node_id"] == target_id for e in existing
                        )
                        if already_exists:
                            continue

                        # Insert the edge
                        edge_id = db.insert_graph_edge(
                            from_node_id=node_id,
                            from_node_type=from_type,
                            to_node_id=target_id,
                            to_node_type=to_type,
                            relationship_type=relationship,
                        )
                        if edge_id:
                            synced += 1

            except Exception as e:
                logger.debug(f"Error syncing edges from {html_file}: {e}")
                continue

    logger.info(f"Synced {synced} edges from HTML to SQLite")
    return synced


def sync_sqlite_edge_to_html(
    db: HtmlGraphDB,
    graph: HtmlGraph,
    from_id: str,
    to_id: str,
    relationship: str,
    title: str | None = None,
) -> bool:
    """
    Ensure an edge created via SDK/API also appears in the source HTML file.

    Loads the source node from the graph, adds the edge if not already present,
    and saves the updated HTML.

    Args:
        db: HtmlGraphDB instance (unused but kept for API symmetry)
        graph: HtmlGraph instance containing the source node
        from_id: Source node ID
        to_id: Target node ID
        relationship: Relationship type
        title: Optional human-readable title

    Returns:
        True if edge was added to HTML, False if node not found or edge exists
    """
    from htmlgraph.models import Edge

    node = graph.get(from_id)
    if not node:
        logger.debug(f"Node {from_id} not found in graph for edge sync")
        return False

    # Check if edge already exists in HTML
    existing_edges = node.edges.get(relationship, [])
    for existing in existing_edges:
        if existing.target_id == to_id:
            return False  # Already exists

    # Add the edge and save
    edge = Edge(target_id=to_id, relationship=relationship, title=title)
    node.add_edge(edge)
    graph.update(node)

    logger.debug(f"Synced edge {from_id} --{relationship}--> {to_id} to HTML")
    return True
