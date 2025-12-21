"""
HtmlGraph - HTML is All You Need

A lightweight graph database framework using HTML files as nodes,
hyperlinks as edges, and CSS selectors as the query language.
"""

from htmlgraph.models import Node, Edge, Step, Graph, Session, ActivityEntry
from htmlgraph.graph import HtmlGraph
from htmlgraph.agents import AgentInterface
from htmlgraph.server import serve
from htmlgraph.session_manager import SessionManager
from htmlgraph.sdk import SDK

__version__ = "0.1.3"
__all__ = [
    "Node",
    "Edge",
    "Step",
    "Graph",
    "Session",
    "ActivityEntry",
    "HtmlGraph",
    "AgentInterface",
    "SessionManager",
    "SDK",
    "serve",
]
