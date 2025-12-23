"""
HtmlGraph - HTML is All You Need

A lightweight graph database framework using HTML files as nodes,
hyperlinks as edges, and CSS selectors as the query language.
"""

from htmlgraph.models import (
    Node,
    Edge,
    Step,
    Graph,
    Session,
    ActivityEntry,
    Spike,
    Chore,
    WorkType,
    SpikeType,
    MaintenanceType,
)
from htmlgraph.graph import HtmlGraph
from htmlgraph.edge_index import EdgeIndex, EdgeRef
from htmlgraph.query_builder import QueryBuilder, Condition, Operator
from htmlgraph.find_api import FindAPI, find, find_all
from htmlgraph.agents import AgentInterface
from htmlgraph.server import serve
from htmlgraph.session_manager import SessionManager
from htmlgraph.sdk import SDK
from htmlgraph.analytics import Analytics
from htmlgraph.dependency_analytics import DependencyAnalytics
from htmlgraph.ids import generate_id, generate_hierarchical_id, parse_id, is_valid_id, is_legacy_id
from htmlgraph.work_type_utils import infer_work_type, infer_work_type_from_id

__version__ = "0.7.2"
__all__ = [
    # Core models
    "Node",
    "Edge",
    "Step",
    "Graph",
    "Session",
    "ActivityEntry",
    "Spike",
    "Chore",
    # Work type classification (Phase 1)
    "WorkType",
    "SpikeType",
    "MaintenanceType",
    # Graph operations
    "HtmlGraph",
    "EdgeIndex",
    "EdgeRef",
    "QueryBuilder",
    "Condition",
    "Operator",
    "FindAPI",
    "find",
    "find_all",
    "AgentInterface",
    "SessionManager",
    "SDK",
    "Analytics",  # Phase 2: Work Type Analytics
    "DependencyAnalytics",  # Advanced dependency-aware analytics
    "serve",
    # ID generation (collision-resistant, multi-agent safe)
    "generate_id",
    "generate_hierarchical_id",
    "parse_id",
    "is_valid_id",
    "is_legacy_id",
    # Work type utilities
    "infer_work_type",
    "infer_work_type_from_id",
]
