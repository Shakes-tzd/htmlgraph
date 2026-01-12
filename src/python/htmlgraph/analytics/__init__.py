"""
Analytics modules for HtmlGraph.

Provides work type analysis, dependency analytics, cross-session analytics, CLI analytics,
and cost attribution analysis for OTEL ROI.
"""

from htmlgraph.analytics.cost_analyzer import CostAnalyzer
from htmlgraph.analytics.cost_reporter import CostReporter
from htmlgraph.analytics.cross_session import CrossSessionAnalytics
from htmlgraph.analytics.dependency import DependencyAnalytics
from htmlgraph.analytics.work_type import Analytics

__all__ = [
    "Analytics",
    "DependencyAnalytics",
    "CrossSessionAnalytics",
    "CostAnalyzer",
    "CostReporter",
]
