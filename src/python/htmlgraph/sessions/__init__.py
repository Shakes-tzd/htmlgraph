"""
Session management and continuity.

Provides session lifecycle, handoff, and resumption features.
"""

from htmlgraph.sessions.handoff import (
    ContextRecommender,
    HandoffBuilder,
    HandoffMetrics,
    HandoffTracker,
    SessionResume,
    SessionResumeInfo,
)

__all__ = [
    "HandoffBuilder",
    "SessionResume",
    "SessionResumeInfo",
    "HandoffTracker",
    "HandoffMetrics",
    "ContextRecommender",
]
