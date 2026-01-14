"""
Analytics submodule for SDK.

Provides lazy-loaded analytics interfaces:
- Analytics: Work type distribution and session analytics
- DependencyAnalytics: Graph-based dependency analysis
- CrossSessionAnalytics: Git commit-based cross-session tracking
- ContextAnalytics: Context usage tracking

Exported for backward compatibility.
"""

from htmlgraph.sdk.analytics.engine import AnalyticsEngine
from htmlgraph.sdk.analytics.registry import AnalyticsRegistry

__all__ = [
    "AnalyticsEngine",
    "AnalyticsRegistry",
]
