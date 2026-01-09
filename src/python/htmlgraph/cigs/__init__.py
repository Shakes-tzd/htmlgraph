"""
Computational Imperative Guidance System (CIGS)

Provides guidance, messaging, and tracking for delegation enforcement in HtmlGraph.

Modules:
- messages_basic: Level 0-1 imperative message templates
- models: Data models for violations, patterns, and autonomy
- tracker: Violation tracking and persistence
- cost: Cost calculation and efficiency metrics
- patterns: Anti-pattern detection and analysis
- autonomy: Autonomy level management
- reporter: Dashboard generation for cost analysis
"""

from htmlgraph.cigs.autonomy import AutonomyRecommender
from htmlgraph.cigs.messages_basic import (
    BasicMessageGenerator,
    MessageTemplateLibrary,
    OperationContext,
    ToolCategory,
    classify_operation,
    estimate_costs,
)
from htmlgraph.cigs.messaging import (
    ImperativeMessageGenerator,
    PositiveReinforcementGenerator,
)
from htmlgraph.cigs.models import (
    AutonomyLevel,
    CostMetrics,
    CostPrediction,
    OperationClassification,
    PatternRecord,
    SessionViolationSummary,
    TokenCost,
    ViolationRecord,
    ViolationType,
)
from htmlgraph.cigs.patterns import (
    DetectionResult,
    PatternDetector,
    detect_patterns,
)
from htmlgraph.cigs.posttool_analyzer import CIGSPostToolAnalyzer
from htmlgraph.cigs.reporter import CostReporter
from htmlgraph.cigs.tracker import ViolationTracker

__all__ = [
    # Messages
    "BasicMessageGenerator",
    "PositiveReinforcementGenerator",
    "ImperativeMessageGenerator",
    "MessageTemplateLibrary",
    "OperationContext",
    "ToolCategory",
    "classify_operation",
    "estimate_costs",
    # Models
    "ViolationType",
    "ViolationRecord",
    "SessionViolationSummary",
    "PatternRecord",
    "TokenCost",
    "CostPrediction",
    "OperationClassification",
    "AutonomyLevel",
    "CostMetrics",
    # Autonomy
    "AutonomyRecommender",
    # Patterns
    "PatternDetector",
    "DetectionResult",
    "detect_patterns",
    # Tracker
    "ViolationTracker",
    # PostTool Analysis
    "CIGSPostToolAnalyzer",
    # Reporter
    "CostReporter",
]
