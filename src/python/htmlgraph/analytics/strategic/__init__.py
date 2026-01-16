"""
Strategic Analytics - Phase 3: Pattern Detection & Smart Suggestions

This module provides intelligent pattern detection and suggestion systems
that learn from user delegation patterns and make smart suggestions.

Key Components:
1. PatternDetector - Detects tool sequences, delegation chains, error patterns
2. SuggestionEngine - Generates context-aware suggestions with ranking
3. PreferenceManager - Learns user preferences from feedback
4. CostOptimizer - Suggests token budgets, parallelization, model selection

Usage:
    from htmlgraph.analytics.strategic import (
        PatternDetector,
        SuggestionEngine,
        PreferenceManager,
        CostOptimizer,
    )

    # Detect patterns from event history
    detector = PatternDetector(db_path)
    patterns = detector.detect_all_patterns()

    # Get suggestions for current context
    engine = SuggestionEngine(db_path)
    suggestions = engine.suggest(context)

    # Learn from feedback
    manager = PreferenceManager(db_path)
    manager.record_feedback(suggestion_id, accepted=True)
"""

from htmlgraph.analytics.strategic.cost_optimizer import (
    CostOptimizer,
    ModelRecommendation,
    ParallelizationStrategy,
    TokenBudget,
)
from htmlgraph.analytics.strategic.pattern_detector import (
    DelegationChain,
    ErrorPattern,
    Pattern,
    PatternDetector,
    PatternType,
    ToolSequencePattern,
)
from htmlgraph.analytics.strategic.preference_manager import (
    Feedback,
    PreferenceManager,
    UserPreferences,
)
from htmlgraph.analytics.strategic.suggestion_engine import (
    Suggestion,
    SuggestionEngine,
    SuggestionType,
)

__all__ = [
    # Pattern Detection
    "PatternDetector",
    "Pattern",
    "PatternType",
    "ToolSequencePattern",
    "DelegationChain",
    "ErrorPattern",
    # Suggestion Engine
    "SuggestionEngine",
    "Suggestion",
    "SuggestionType",
    # Preference Manager
    "PreferenceManager",
    "UserPreferences",
    "Feedback",
    # Cost Optimizer
    "CostOptimizer",
    "TokenBudget",
    "ParallelizationStrategy",
    "ModelRecommendation",
]
