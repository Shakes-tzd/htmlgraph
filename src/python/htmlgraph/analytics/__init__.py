"""
Analytics modules for HtmlGraph.

Provides work type analysis, dependency analytics, and CLI analytics.
"""

from htmlgraph.analytics.dependency import DependencyAnalytics
from htmlgraph.analytics.work_type import Analytics

__all__ = [
    "Analytics",
    "DependencyAnalytics",
]
