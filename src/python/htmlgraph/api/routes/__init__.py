"""
HtmlGraph API Routes Package.

This package contains modular route handlers organized by domain:
- dashboard: Main dashboard, activity feed, agents, metrics views
- orchestration: Delegation chains, work items, spawners
- analytics: Cost summary, performance metrics, query metrics
- presence: Real-time presence tracking and WebSocket endpoints
"""

from htmlgraph.api.routes.analytics import router as analytics_router
from htmlgraph.api.routes.dashboard import router as dashboard_router
from htmlgraph.api.routes.orchestration import router as orchestration_router
from htmlgraph.api.routes.presence import router as presence_router

__all__ = [
    "dashboard_router",
    "orchestration_router",
    "analytics_router",
    "presence_router",
]
