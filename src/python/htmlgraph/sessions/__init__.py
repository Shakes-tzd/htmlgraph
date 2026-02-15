"""
Session management and continuity.

Consolidated modules:
- lifecycle: Session lifecycle operations + error management
- features: Feature workflow + attribution scoring
- activity: Activity tracking + drift detection + graph linking
- transcripts: Transcript operations
- handoff: Session handoff and resumption
- spikes: Auto-generated spike management
"""

from htmlgraph.sessions.activity import ActivityTracker, LinkingOps, detect_drift
from htmlgraph.sessions.features import (
    FeatureWorkflow,
    attribute_activity,
    is_system_overhead,
)
from htmlgraph.sessions.handoff import (
    ContextRecommender,
    HandoffBuilder,
    HandoffMetrics,
    HandoffTracker,
    SessionResume,
    SessionResumeInfo,
)
from htmlgraph.sessions.lifecycle import ErrorManager, SessionLifecycleOps
from htmlgraph.sessions.spikes import SpikeManager
from htmlgraph.sessions.transcripts import TranscriptOps

__all__ = [
    # Lifecycle
    "SessionLifecycleOps",
    "ErrorManager",
    # Features
    "FeatureWorkflow",
    "attribute_activity",
    "is_system_overhead",
    # Activity
    "ActivityTracker",
    "LinkingOps",
    "detect_drift",
    # Transcripts
    "TranscriptOps",
    # Handoff
    "HandoffBuilder",
    "SessionResume",
    "SessionResumeInfo",
    "HandoffTracker",
    "HandoffMetrics",
    "ContextRecommender",
    # Spikes
    "SpikeManager",
]
