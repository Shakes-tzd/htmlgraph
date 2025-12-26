"""
Collection classes for managing nodes by type.

Provides specialized collections for each node type with
common functionality inherited from BaseCollection.
"""

from htmlgraph.collections.base import BaseCollection
from htmlgraph.collections.feature import FeatureCollection
from htmlgraph.collections.spike import SpikeCollection
from htmlgraph.collections.bug import BugCollection
from htmlgraph.collections.chore import ChoreCollection
from htmlgraph.collections.epic import EpicCollection
from htmlgraph.collections.phase import PhaseCollection

__all__ = [
    "BaseCollection",
    "FeatureCollection",
    "SpikeCollection",
    "BugCollection",
    "ChoreCollection",
    "EpicCollection",
    "PhaseCollection",
]
