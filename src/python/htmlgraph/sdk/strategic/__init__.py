"""
Strategic Analytics SDK Integration - Phase 3

Provides SDK mixin for accessing strategic analytics capabilities:
- Pattern detection and retrieval
- Suggestion generation
- Preference management
- Cost optimization

Usage:
    from htmlgraph import SDK

    sdk = SDK(agent="claude")

    # Access strategic analytics
    patterns = sdk.strategic.detect_patterns()
    suggestions = sdk.strategic.get_suggestions()
    preferences = sdk.strategic.get_preferences()

    # Record feedback
    sdk.strategic.record_feedback(suggestion_id, accepted=True)
"""

from htmlgraph.sdk.strategic.mixin import StrategicAnalyticsMixin

__all__ = ["StrategicAnalyticsMixin"]
