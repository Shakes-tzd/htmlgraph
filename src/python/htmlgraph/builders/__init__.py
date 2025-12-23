"""
Builder classes for fluent node creation.

Provides specialized builders for each node type with
common functionality inherited from BaseBuilder.
"""

from htmlgraph.builders.base import BaseBuilder
from htmlgraph.builders.feature import FeatureBuilder
from htmlgraph.builders.spike import SpikeBuilder

__all__ = [
    "BaseBuilder",
    "FeatureBuilder",
    "SpikeBuilder",
]
