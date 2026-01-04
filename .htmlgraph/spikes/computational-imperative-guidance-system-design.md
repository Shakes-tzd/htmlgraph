# Computational Imperative Guidance System (CIGS)

## Design Document for HtmlGraph Delegation Enforcement

**Version:** 1.0
**Date:** 2026-01-04
**Status:** Design Complete

---

## Executive Summary

This document describes a **Computational Imperative Guidance System** (CIGS) that ensures Claude follows HtmlGraph delegation workflows through imperative (commanding) guidance rather than blocking. The system leverages AI behavioral science research showing AI agents are 6-16x more susceptible to nudges than humans, making well-designed imperative guidance highly effective.

### Key Design Principles

1. **Imperative > Advisory** - Commands ("YOU MUST delegate") not suggestions ("Consider delegating")
2. **Computational > Heuristic** - Data-driven decisions based on tracked metrics
3. **Reinforcing > Restricting** - Positive loops for correct behavior, escalating for violations
4. **Intelligent > Mechanical** - Leverages Claude's reasoning for context-aware decisions

---

## Part 1: System Architecture

### 1.1 Three-Layer Integration Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LAYER 1: System Prompt                          │
│                   (Constitutional Framework Layer)                       │
├─────────────────────────────────────────────────────────────────────────┤
│  • ORCHESTRATOR_DIRECTIVES (session-start.py injection)                 │
│  • Core delegation principles and decision trees                        │
│  • Constitutional-style rules for self-critique                         │
│  • Autonomy level framework                                              │
│  • Cost model education                                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         LAYER 2: Plugin Hooks                           │
│                  (Real-Time Intervention Layer)                          │
├─────────────────────────────────────────────────────────────────────────┤
│  • SessionStart: Initialize tracking, load violation history            │
│  • UserPromptSubmit: Pre-response delegation reminders                  │
│  • PreToolUse: Imperative guidance before tool execution                │
│  • PostToolUse: Cost accounting, reflection, reinforcement              │
│  • Stop: Session summary, pattern report                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      LAYER 3: Python Package                            │
│                  (Analytics & State Management Layer)                    │
├─────────────────────────────────────────────────────────────────────────┤
│  • ViolationTracker: Records violations with context                    │
│  • PatternAnalyzer: Detects anti-patterns and improvements              │
│  • CostCalculator: Computes actual vs optimal costs                     │
│  • AutonomyManager: Recommends autonomy level adjustments               │
│  • ImperativeMessageGenerator: Creates escalating messages              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow Architecture

```
User Request
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      UserPromptSubmit Hook                               │
│  ┌───────────────┐  ┌────────────────┐  ┌─────────────────────────────┐│
│  │ Load Session  │→ │ Load Violation │→ │ Generate Decision Framework ││
│  │   Context     │  │    History     │  │        Reminder             ││
│  └───────────────┘  └────────────────┘  └─────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼ (Claude generates response with tool calls)
     │
┌─────────────────────────────────────────────────────────────────────────┐
│                       PreToolUse Hook                                    │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐ │
│  │ Classify Tool  │→ │ Check Autonomy   │→ │ Generate Imperative     │ │
│  │   Category     │  │    Level         │  │      Message            │ │
│  └────────────────┘  └──────────────────┘  └─────────────────────────┘ │
│                              │                        │                 │
│                              ▼                        ▼                 │
│                    ┌─────────────────┐      ┌─────────────────────┐    │
│                    │  Predict Cost   │      │  Escalation Level   │    │
│                    │   (Waste)       │      │  Based on History   │    │
│                    └─────────────────┘      └─────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼ (Tool executes)
     │
┌─────────────────────────────────────────────────────────────────────────┐
│                      PostToolUse Hook                                    │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐ │
│  │ Record Actual  │→ │ Calculate Cost   │→ │ Generate Feedback       │ │
│  │    Result      │  │    Efficiency    │  │   (Positive/Negative)   │ │
│  └────────────────┘  └──────────────────┘  └─────────────────────────┘ │
│                              │                                          │
│                              ▼                                          │
│                    ┌─────────────────────────────────────────────────┐ │
│                    │        Update Analytics & Learning              │ │
│                    │  • Update violation count (if applicable)       │ │
│                    │  • Record pattern for anti-pattern detection    │ │
│                    │  • Adjust autonomy level recommendation         │ │
│                    └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼ (Session ends)
     │
┌─────────────────────────────────────────────────────────────────────────┐
│                        Stop Hook                                         │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │                    Session Summary Report                          ││
│  │  • Delegation compliance rate                                      ││
│  │  • Cost efficiency score                                           ││
│  │  • Detected patterns (good and bad)                                ││
│  │  • Autonomy level recommendation for next session                  ││
│  └────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Feedback Loop Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    REINFORCEMENT LOOP                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Observation                Intervention              Interpretation     │
│  ───────────                ────────────              ──────────────     │
│                                                                          │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐   │
│  │ Tool Use    │    ─────→ │ Imperative  │    ─────→ │ Track       │   │
│  │ Detection   │           │ Message     │           │ Response    │   │
│  └─────────────┘           └─────────────┘           └─────────────┘   │
│        │                         │                         │            │
│        │                         │                         │            │
│        ▼                         ▼                         ▼            │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐   │
│  │ Context     │           │ Adjust      │           │ Update      │   │
│  │ Analysis    │    ◄───── │ Messaging   │    ◄───── │ Model       │   │
│  └─────────────┘           └─────────────┘           └─────────────┘   │
│                                                                          │
│  ───────────────────────────────────────────────────────────────────────│
│  Correct Delegation → Positive Reinforcement → Lower Guidance Intensity │
│  Violation → Escalated Imperative → Higher Guidance Intensity           │
│  Repeated Violations → Circuit Breaker → Mandatory Acknowledgment       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Hook Specifications

### 2.1 SessionStart Hook Enhancement

**Purpose:** Initialize violation tracking and provide context-aware autonomy level.

```python
# File: src/python/htmlgraph/hooks/session_start_cigs.py

class CIGSSessionInitializer:
    """Initialize CIGS state at session start."""

    def initialize(self, session_id: str, graph_dir: Path) -> dict:
        """
        Initialize CIGS for a new session.

        Returns:
            Context to inject into session including:
            - Previous session violation summary
            - Recommended autonomy level
            - Personalized delegation reminders
        """
        # Load violation history
        tracker = ViolationTracker(graph_dir)
        history = tracker.get_recent_violations(sessions=5)

        # Analyze patterns
        analyzer = PatternAnalyzer(graph_dir)
        patterns = analyzer.detect_patterns(history)

        # Determine autonomy level
        autonomy_mgr = AutonomyManager(graph_dir)
        autonomy = autonomy_mgr.recommend_level(history, patterns)

        # Generate personalized context
        context = self._build_session_context(history, patterns, autonomy)

        return {
            "autonomy_level": autonomy,
            "violation_summary": history.summary(),
            "patterns_detected": patterns,
            "context_injection": context
        }

    def _build_session_context(self, history, patterns, autonomy):
        """Build personalized context based on history."""

        if autonomy.level == "strict":
            return self._strict_mode_context(history)
        elif autonomy.level == "guided":
            return self._guided_mode_context(history, patterns)
        else:
            return self._observer_mode_context()
```

**Output Format:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "## CIGS Status\n\nAutonomy Level: GUIDED\nPrevious Violations: 7 (last 5 sessions)\nPattern: Repeated direct Read operations\n\nIMPERATIVE: You MUST delegate exploration work. Your history shows 70% of Read operations expanded to 3+ calls.\n\n### Personalized Reminders\n- Explorer tasks: spawn_gemini() (FREE)\n- Code changes: spawn_codex() (70% cheaper)\n- Git operations: spawn_copilot() (60% cheaper)"
  }
}
```

### 2.2 UserPromptSubmit Hook Enhancement

**Purpose:** Provide decision framework reminder before Claude generates response.

```python
# File: src/python/htmlgraph/hooks/user_prompt_submit_cigs.py

class CIGSPromptInterceptor:
    """Intercept user prompts and inject delegation reminders."""

    def intercept(self, prompt: str, session_context: dict) -> dict:
        """
        Analyze prompt and provide pre-response guidance.

        Returns:
            Imperative guidance to inject before Claude responds.
        """
        # Classify prompt intent
        classifier = PromptClassifier()
        intent = classifier.classify(prompt)

        # Get violation count for session
        tracker = ViolationTracker()
        violations = tracker.get_session_violations()

        # Generate imperative based on intent and history
        guidance = self._generate_pre_response_guidance(intent, violations)

        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": guidance
            }
        }

    def _generate_pre_response_guidance(self, intent, violations):
        """Generate imperative guidance based on intent."""

        imperatives = []

        if intent.involves_exploration:
            imperatives.append(
                "IMPERATIVE: This request involves exploration. "
                "YOU MUST use spawn_gemini() (FREE). "
                "DO NOT use Read/Grep/Glob directly."
            )

        if intent.involves_code_changes:
            imperatives.append(
                "IMPERATIVE: This request involves code changes. "
                "YOU MUST use spawn_codex() or Task(). "
                "DO NOT use Edit/Write directly."
            )

        if intent.involves_git:
            imperatives.append(
                "IMPERATIVE: This request involves git operations. "
                "YOU MUST use spawn_copilot(). "
                "DO NOT run git commands directly."
            )

        if violations.count > 0:
            imperatives.append(
                f"WARNING: You have {violations.count} violations this session. "
                f"Circuit breaker triggers at 3."
            )

        return "\n\n".join(imperatives) if imperatives else ""
```

### 2.3 PreToolUse Hook Enhancement

**Purpose:** Provide imperative guidance with escalation before tool execution.

```python
# File: src/python/htmlgraph/hooks/pretooluse_cigs.py

class CIGSPreToolEnforcer:
    """Enforce delegation with imperative guidance."""

    # Tool classification categories
    ALWAYS_ALLOWED = {"Task", "AskUserQuestion", "TodoWrite"}
    EXPLORATION_TOOLS = {"Read", "Grep", "Glob"}
    IMPLEMENTATION_TOOLS = {"Edit", "Write", "NotebookEdit", "Delete"}

    def enforce(self, tool: str, params: dict, session_context: dict) -> dict:
        """
        Provide imperative guidance for tool use.

        Returns:
            Hook response with imperative message and decision.
        """
        # Quick allow for orchestrator-core operations
        if tool in self.ALWAYS_ALLOWED:
            return self._allow_with_positive_reinforcement(tool)

        # Load violation tracker
        tracker = ViolationTracker()
        violation_count = tracker.get_session_violations().count

        # Check autonomy level
        autonomy = session_context.get("autonomy_level", "strict")

        # Classify the operation
        classification = self._classify_operation(tool, params)

        # Generate imperative message
        message_gen = ImperativeMessageGenerator()
        message = message_gen.generate(
            tool=tool,
            classification=classification,
            violation_count=violation_count,
            autonomy_level=autonomy
        )

        # Calculate cost prediction
        cost_calc = CostCalculator()
        predicted_cost = cost_calc.predict_cost(tool, params)
        optimal_cost = cost_calc.optimal_cost(classification)
        waste_estimate = predicted_cost - optimal_cost

        if classification.should_delegate:
            # Record violation (but don't block)
            tracker.record_violation(
                tool=tool,
                params=params,
                classification=classification,
                predicted_waste=waste_estimate
            )

            return self._imperative_response(
                message=message,
                classification=classification,
                waste_estimate=waste_estimate,
                violation_count=violation_count + 1
            )
        else:
            return self._allow_response(tool)

    def _classify_operation(self, tool: str, params: dict) -> OperationClassification:
        """Classify operation and determine if delegation is required."""

        # Use OrchestratorValidator for base classification
        validator = OrchestratorValidator()
        result, reason = validator.validate_tool_use(tool, params)

        # Check tool history for patterns
        history = load_tool_history()
        exploration_count = sum(
            1 for h in history[-5:]
            if h["tool"] in self.EXPLORATION_TOOLS
        )

        return OperationClassification(
            tool=tool,
            category=self._get_category(tool),
            should_delegate=result == "block",
            reason=reason,
            is_exploration_sequence=exploration_count >= 2,
            suggested_delegation=self._get_delegation_suggestion(tool, params)
        )

    def _imperative_response(self, message, classification, waste_estimate, violation_count):
        """Generate imperative response for violation."""

        # Escalation based on violation count
        if violation_count >= 3:
            prefix = "🚨 CIRCUIT BREAKER ACTIVE - "
            suffix = "\n\nYou MUST acknowledge this violation before proceeding."
        elif violation_count == 2:
            prefix = "⚠️ FINAL WARNING - "
            suffix = "\n\nNext violation triggers circuit breaker."
        else:
            prefix = "🔴 IMPERATIVE - "
            suffix = ""

        full_message = f"""{prefix}{message}{suffix}

**Cost Impact:**
- Predicted waste: {waste_estimate} tokens
- This session waste: {self._get_session_waste()} tokens total

**YOU MUST delegate this operation:**
{classification.suggested_delegation}
"""

        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",  # Guidance, not blocking
                "additionalContext": full_message
            }
        }
```

### 2.4 PostToolUse Hook Enhancement

**Purpose:** Account for actual cost, provide feedback, update learning model.

```python
# File: src/python/htmlgraph/hooks/posttooluse_cigs.py

class CIGSPostToolAnalyzer:
    """Analyze tool results and provide feedback."""

    def analyze(self, tool: str, params: dict, result: dict) -> dict:
        """
        Analyze tool execution and provide feedback.

        Returns:
            Hook response with cost analysis and reinforcement.
        """
        # Calculate actual cost
        cost_calc = CostCalculator()
        actual_cost = cost_calc.calculate_actual_cost(tool, result)

        # Load prediction from PreToolUse (if available)
        tracker = ViolationTracker()
        prediction = tracker.get_last_prediction(tool)

        # Determine if this was a delegation or direct execution
        was_delegation = tool == "Task" or tool.startswith("spawn_")

        if was_delegation:
            return self._positive_reinforcement(tool, actual_cost)
        else:
            return self._cost_accounting(tool, actual_cost, prediction)

    def _positive_reinforcement(self, tool: str, cost: TokenCost) -> dict:
        """Provide positive reinforcement for correct delegation."""

        message = f"""✅ Correct delegation pattern used.

**Cost Efficiency:**
- Subagent context cost: {cost.subagent_tokens} tokens
- Your context cost: {cost.orchestrator_tokens} tokens (only Task call + summary)
- Savings vs direct execution: ~{cost.estimated_savings}%

Keep delegating! Your delegation compliance this session: {self._get_compliance_rate()}%
"""

        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": message
            }
        }

    def _cost_accounting(self, tool: str, cost: TokenCost, prediction: CostPrediction) -> dict:
        """Account for cost of direct execution."""

        # Record actual cost
        tracker = ViolationTracker()
        tracker.record_actual_cost(tool, cost)

        # Check if we were warned (violation)
        if prediction and prediction.should_delegate:
            # This was a warned violation - update learning model
            analyzer = PatternAnalyzer()
            analyzer.record_ignored_warning(tool, cost)

            message = f"""📊 Direct execution completed.

**Cost Impact (Violation):**
- Actual cost: {cost.total_tokens} tokens
- If delegated: ~{prediction.optimal_cost} tokens
- Waste: {cost.total_tokens - prediction.optimal_cost} tokens ({prediction.waste_percentage}% overhead)

**Session Statistics:**
- Violations: {tracker.get_session_violations().count}
- Total waste: {tracker.get_session_waste()} tokens
- Delegation compliance: {self._get_compliance_rate()}%

REFLECTION: Was this delegation worth the context cost?
The same operation via Task() would have cost ~{prediction.optimal_cost} tokens
with full isolation of tactical details.
"""
        else:
            # Allowed operation - just informational
            message = f"Operation completed. Cost: {cost.total_tokens} tokens."

        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": message
            }
        }
```

### 2.5 Stop Hook Enhancement

**Purpose:** Provide session summary with pattern analysis and autonomy recommendations.

```python
# File: src/python/htmlgraph/hooks/stop_cigs.py

class CIGSSessionSummarizer:
    """Generate session summary with CIGS analytics."""

    def summarize(self, session_id: str) -> dict:
        """
        Generate comprehensive session summary.

        Returns:
            Session summary with metrics and recommendations.
        """
        tracker = ViolationTracker()
        analyzer = PatternAnalyzer()
        autonomy_mgr = AutonomyManager()

        # Gather session metrics
        violations = tracker.get_session_violations()
        patterns = analyzer.analyze_session(session_id)
        costs = tracker.get_session_costs()

        # Generate recommendations
        autonomy_rec = autonomy_mgr.recommend_for_next_session(
            violations=violations,
            patterns=patterns,
            costs=costs
        )

        # Build summary
        summary = self._build_summary(violations, patterns, costs, autonomy_rec)

        # Persist for next session
        self._persist_summary(session_id, summary)

        return {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": summary
            }
        }

    def _build_summary(self, violations, patterns, costs, autonomy_rec) -> str:
        """Build human-readable session summary."""

        return f"""
## 📊 CIGS Session Summary

### Delegation Metrics
- **Compliance Rate:** {self._calc_compliance_rate(violations)}%
- **Violations:** {violations.count} (threshold: 3)
- **Circuit Breaker:** {"Triggered" if violations.count >= 3 else "Not triggered"}

### Cost Analysis
- **Total Context Used:** {costs.total_tokens} tokens
- **Estimated Waste:** {costs.waste_tokens} tokens ({costs.waste_percentage}%)
- **Optimal Path Cost:** {costs.optimal_tokens} tokens
- **Efficiency Score:** {costs.efficiency_score}/100

### Detected Patterns
{self._format_patterns(patterns)}

### Anti-Patterns Identified
{self._format_anti_patterns(patterns)}

### Autonomy Recommendation
**Next Session:** {autonomy_rec.level}
**Reason:** {autonomy_rec.reason}

### Learning Applied
- Violation patterns added to detection model
- Cost predictions updated with actual data
- Messaging intensity adjusted: {autonomy_rec.messaging_intensity}
"""
```

---

## Part 3: Tracking Data Model

### 3.1 Violation Record Schema

```python
# File: src/python/htmlgraph/cigs/models.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class ViolationType(Enum):
    """Types of delegation violations."""
    DIRECT_EXPLORATION = "direct_exploration"      # Read/Grep/Glob when should delegate
    DIRECT_IMPLEMENTATION = "direct_implementation" # Edit/Write when should delegate
    DIRECT_TESTING = "direct_testing"              # pytest/npm test directly
    DIRECT_GIT = "direct_git"                      # git commands directly
    EXPLORATION_SEQUENCE = "exploration_sequence"  # 3+ exploration tools in sequence
    IGNORED_WARNING = "ignored_warning"            # Proceeded after imperative warning

@dataclass
class ViolationRecord:
    """Record of a single delegation violation."""

    id: str                                # Unique violation ID
    session_id: str                        # Session where violation occurred
    timestamp: datetime                    # When violation occurred

    # Violation details
    tool: str                              # Tool that was used directly
    tool_params: dict                      # Parameters passed to tool
    violation_type: ViolationType          # Classification of violation

    # Context
    context_before: Optional[str] = None   # What Claude was trying to do
    should_have_delegated_to: str = ""     # spawn_gemini, spawn_codex, Task, etc.

    # Cost impact
    actual_cost_tokens: int = 0            # Tokens consumed by direct execution
    optimal_cost_tokens: int = 0           # Tokens if delegated properly
    waste_tokens: int = 0                  # actual - optimal

    # Escalation
    warning_level: int = 1                 # 1=first, 2=second, 3=circuit breaker
    was_warned: bool = False               # Whether PreToolUse warned before execution
    warning_ignored: bool = False          # Whether Claude proceeded despite warning

    # Metadata
    agent: str = "claude-code"             # Agent that violated
    feature_id: Optional[str] = None       # Feature being worked on (if any)

@dataclass
class SessionViolationSummary:
    """Summary of violations for a session."""

    session_id: str
    total_violations: int
    violations_by_type: dict[ViolationType, int]
    total_waste_tokens: int
    circuit_breaker_triggered: bool
    compliance_rate: float                 # 0.0 to 1.0

    violations: list[ViolationRecord] = field(default_factory=list)

@dataclass
class PatternRecord:
    """Detected behavioral pattern."""

    id: str
    pattern_type: str                      # "anti-pattern" or "good-pattern"
    name: str                              # Human-readable pattern name
    description: str                       # What the pattern is

    # Detection criteria
    trigger_conditions: list[str]          # Conditions that trigger this pattern
    example_sequence: list[str]            # Example tool sequence

    # Statistics
    occurrence_count: int = 0              # How many times detected
    sessions_affected: list[str] = field(default_factory=list)

    # Remediation (for anti-patterns)
    correct_approach: Optional[str] = None
    delegation_suggestion: Optional[str] = None

@dataclass
class AutonomyLevel:
    """Autonomy level recommendation."""

    level: str                             # "observer", "consultant", "collaborator", "operator"
    messaging_intensity: str               # "minimal", "moderate", "high", "maximal"
    enforcement_mode: str                  # "guidance", "strict"

    reason: str                            # Why this level is recommended
    based_on_violations: int               # Violations that influenced decision
    based_on_patterns: list[str]           # Patterns that influenced decision

@dataclass
class CostMetrics:
    """Cost metrics for a session or operation."""

    total_tokens: int                      # Total tokens consumed
    orchestrator_tokens: int               # Tokens in orchestrator context
    subagent_tokens: int                   # Tokens in subagent contexts

    waste_tokens: int                      # Tokens wasted on direct execution
    optimal_tokens: int                    # What it would have cost with delegation

    efficiency_score: float                # 0-100 score
    waste_percentage: float                # waste / total * 100
```

### 3.2 Storage Schema (HtmlGraph Format)

**File: `.htmlgraph/cigs/violations.jsonl`**
```jsonl
{"id":"viol-001","session_id":"sess-abc","timestamp":"2026-01-04T10:15:00Z","tool":"Read","violation_type":"direct_exploration","actual_cost_tokens":5000,"optimal_cost_tokens":500,"waste_tokens":4500,"warning_level":1}
{"id":"viol-002","session_id":"sess-abc","timestamp":"2026-01-04T10:17:00Z","tool":"Grep","violation_type":"exploration_sequence","actual_cost_tokens":3000,"optimal_cost_tokens":500,"waste_tokens":2500,"warning_level":2}
```

**File: `.htmlgraph/cigs/patterns.json`**
```json
{
  "patterns": [
    {
      "id": "pattern-001",
      "pattern_type": "anti-pattern",
      "name": "Read-Grep-Read Sequence",
      "description": "Multiple exploration tools used in sequence instead of delegating to Explorer",
      "trigger_conditions": ["3+ exploration tools in last 5 calls"],
      "occurrence_count": 15,
      "sessions_affected": ["sess-abc", "sess-def"],
      "correct_approach": "Use spawn_gemini() for exploration",
      "delegation_suggestion": "spawn_gemini(prompt='Search and analyze codebase for...')"
    }
  ],
  "good_patterns": [
    {
      "id": "pattern-002",
      "pattern_type": "good-pattern",
      "name": "Immediate Delegation",
      "description": "Delegated exploration to Gemini without first trying direct Read",
      "occurrence_count": 42
    }
  ]
}
```

**File: `.htmlgraph/cigs/session-summaries/{session_id}.json`**
```json
{
  "session_id": "sess-abc",
  "start_time": "2026-01-04T09:00:00Z",
  "end_time": "2026-01-04T11:30:00Z",
  "metrics": {
    "total_tool_calls": 127,
    "delegations": 98,
    "direct_executions": 29,
    "violations": 7,
    "compliance_rate": 0.76,
    "total_tokens": 450000,
    "waste_tokens": 45000,
    "efficiency_score": 78
  },
  "patterns_detected": ["Read-Grep-Read Sequence", "Direct Git Commit"],
  "autonomy_level_used": "strict",
  "autonomy_level_recommended": "guided"
}
```

---

## Part 4: Imperative Messaging Framework

### 4.1 Message Escalation Levels

```python
# File: src/python/htmlgraph/cigs/messaging.py

class ImperativeMessageGenerator:
    """Generate imperative messages with escalation."""

    ESCALATION_LEVELS = {
        0: {
            "prefix": "💡 GUIDANCE",
            "tone": "informative",
            "includes_cost": False,
            "includes_suggestion": True,
            "requires_acknowledgment": False
        },
        1: {
            "prefix": "🔴 IMPERATIVE",
            "tone": "commanding",
            "includes_cost": True,
            "includes_suggestion": True,
            "requires_acknowledgment": False
        },
        2: {
            "prefix": "⚠️ FINAL WARNING",
            "tone": "urgent",
            "includes_cost": True,
            "includes_suggestion": True,
            "includes_consequences": True,
            "requires_acknowledgment": False
        },
        3: {
            "prefix": "🚨 CIRCUIT BREAKER",
            "tone": "blocking",
            "includes_cost": True,
            "includes_suggestion": True,
            "includes_consequences": True,
            "requires_acknowledgment": True
        }
    }

    def generate(self, tool: str, classification, violation_count: int, autonomy_level: str) -> str:
        """Generate imperative message based on context."""

        level = min(violation_count, 3)
        config = self.ESCALATION_LEVELS[level]

        message_parts = []

        # Prefix with escalation indicator
        message_parts.append(f"{config['prefix']}: {self._get_core_message(tool, classification)}")

        # Add WHY this is mandatory
        message_parts.append(f"\n\n**WHY:** {self._get_rationale(tool, classification)}")

        # Add cost impact if applicable
        if config.get("includes_cost"):
            message_parts.append(f"\n\n**COST IMPACT:** {self._get_cost_message(classification)}")

        # Add what to do instead
        if config.get("includes_suggestion"):
            message_parts.append(f"\n\n**INSTEAD:** {classification.suggested_delegation}")

        # Add consequences for level 2+
        if config.get("includes_consequences"):
            message_parts.append(f"\n\n**CONSEQUENCE:** {self._get_consequence_message(level)}")

        # Add acknowledgment requirement for level 3
        if config.get("requires_acknowledgment"):
            message_parts.append(
                "\n\n**REQUIRED:** Acknowledge this violation before proceeding:\n"
                "`uv run htmlgraph orchestrator acknowledge-violation`"
            )

        return "".join(message_parts)

    def _get_core_message(self, tool: str, classification) -> str:
        """Get core imperative message based on tool."""

        messages = {
            "Read": "YOU MUST delegate file reading to Explorer subagent",
            "Grep": "YOU MUST delegate code search to Explorer subagent",
            "Glob": "YOU MUST delegate file search to Explorer subagent",
            "Edit": "YOU MUST delegate code changes to Coder subagent",
            "Write": "YOU MUST delegate file writing to Coder subagent",
            "Bash": "YOU MUST delegate this command execution to appropriate subagent",
        }
        return messages.get(tool, f"YOU MUST delegate {tool} operations")

    def _get_rationale(self, tool: str, classification) -> str:
        """Explain WHY delegation is mandatory."""

        rationales = {
            "direct_exploration": (
                "Exploration operations have unpredictable scope. "
                "What looks like 'one Read' often becomes 3-5 reads. "
                "Each direct read pollutes your strategic context with tactical details."
            ),
            "direct_implementation": (
                "Implementation requires iteration (write → test → fix → test). "
                "Delegating keeps your context focused on architecture, "
                "while subagent handles the edit-test cycle."
            ),
            "exploration_sequence": (
                "You have already executed multiple exploration operations. "
                "This pattern indicates research work that should be delegated. "
                "Subagent can explore comprehensively and return a summary."
            ),
            "direct_git": (
                "Git operations cascade unpredictably (hooks, conflicts, push failures). "
                "Copilot specializes in git AND costs 60% less than Task()."
            )
        }
        return rationales.get(classification.category, "Delegation preserves your strategic context.")

    def _get_cost_message(self, classification) -> str:
        """Generate cost impact message."""

        return (
            f"Direct execution costs ~{classification.predicted_cost} tokens in your context. "
            f"Delegation would cost ~{classification.optimal_cost} tokens "
            f"({classification.waste_percentage}% savings)."
        )

    def _get_consequence_message(self, level: int) -> str:
        """Get consequence message for high escalation levels."""

        if level == 2:
            return "Next violation will trigger circuit breaker, requiring manual acknowledgment."
        elif level == 3:
            return "Circuit breaker is now active. All operations require explicit acknowledgment until reset."
        return ""
```

### 4.2 Positive Reinforcement Messages

```python
class PositiveReinforcementGenerator:
    """Generate positive feedback for correct delegation."""

    def generate(self, tool: str, cost_savings: int, compliance_rate: float) -> str:
        """Generate positive reinforcement message."""

        encouragements = [
            "Excellent delegation pattern!",
            "Perfect use of subagent!",
            "Context preserved effectively!",
            "Optimal delegation choice!",
        ]

        import random
        base = random.choice(encouragements)

        return f"""✅ {base}

**Impact:**
- Saved ~{cost_savings} tokens of context
- Subagent handled tactical details
- Your strategic view remains clean

**Session Stats:**
- Delegation compliance: {compliance_rate:.0%}
- Keep it up! Consistent delegation improves response quality.
"""
```

### 4.3 Message Templates by Scenario

| Scenario | Level | Template |
|----------|-------|----------|
| First exploration tool | 0 | "GUIDANCE: Consider delegating exploration to spawn_gemini() for comprehensive search." |
| Second exploration tool | 1 | "IMPERATIVE: YOU MUST delegate exploration. You've used 2+ exploration tools - this is research work. Use spawn_gemini()." |
| Third exploration tool | 2 | "FINAL WARNING: YOU MUST delegate NOW. Pattern detected: exploration sequence. Next violation triggers circuit breaker." |
| Circuit breaker | 3 | "CIRCUIT BREAKER: Delegation violations exceeded threshold. Acknowledge violation before proceeding." |
| Correct delegation | N/A | "Excellent! Saved ~4500 tokens. Compliance rate: 85%." |
| Edge case allowed | 0 | "Allowed: Single config file read (low complexity). Consider delegation for multi-file operations." |

---

## Part 5: Analytics Algorithms

### 5.1 Delegation Compliance Rate

```python
def calculate_compliance_rate(session_events: list[dict]) -> float:
    """
    Calculate delegation compliance rate for a session.

    Formula:
        compliance = delegated_operations / (delegated_operations + violations)

    Args:
        session_events: List of tool use events

    Returns:
        Compliance rate from 0.0 to 1.0
    """
    delegations = sum(1 for e in session_events if e["tool"] == "Task" or e["tool"].startswith("spawn_"))
    violations = sum(1 for e in session_events if e.get("was_violation", False))

    total = delegations + violations
    if total == 0:
        return 1.0  # No operations = 100% compliant

    return delegations / total
```

### 5.2 Cost Efficiency Score

```python
def calculate_efficiency_score(
    actual_cost: int,
    optimal_cost: int,
    violation_count: int
) -> float:
    """
    Calculate cost efficiency score (0-100).

    Formula:
        base_score = (optimal_cost / actual_cost) * 100
        penalty = violation_count * 5
        final_score = max(0, base_score - penalty)

    Args:
        actual_cost: Actual tokens consumed
        optimal_cost: Tokens with optimal delegation
        violation_count: Number of violations

    Returns:
        Efficiency score from 0 to 100
    """
    if actual_cost == 0:
        return 100.0

    base_score = (optimal_cost / actual_cost) * 100
    penalty = violation_count * 5  # 5 points per violation

    return max(0.0, min(100.0, base_score - penalty))
```

### 5.3 Pattern Detection Algorithm

```python
class PatternDetector:
    """Detect behavioral patterns from tool usage history."""

    # Known anti-patterns with detection rules
    ANTI_PATTERNS = {
        "exploration_sequence": {
            "description": "Multiple exploration tools in sequence",
            "detect": lambda history: sum(
                1 for h in history[-5:]
                if h["tool"] in ["Read", "Grep", "Glob"]
            ) >= 3,
            "remediation": "Use spawn_gemini() for comprehensive exploration"
        },
        "edit_without_test": {
            "description": "Edit operations without subsequent test delegation",
            "detect": lambda history: (
                any(h["tool"] == "Edit" for h in history[-3:]) and
                not any(h["tool"] == "Task" and "test" in h.get("prompt", "").lower() for h in history[-3:])
            ),
            "remediation": "Include testing in Task() prompt for code changes"
        },
        "direct_git_commit": {
            "description": "Git commit executed directly instead of via Copilot",
            "detect": lambda history: any(
                h["tool"] == "Bash" and "git commit" in h.get("command", "")
                for h in history[-3:]
            ),
            "remediation": "Use spawn_copilot() for git operations"
        },
        "repeated_read_same_file": {
            "description": "Same file read multiple times",
            "detect": lambda history: len(set(
                h.get("file_path") for h in history[-10:]
                if h["tool"] == "Read" and h.get("file_path")
            )) < len([h for h in history[-10:] if h["tool"] == "Read"]) * 0.7,
            "remediation": "Delegate to Explorer for comprehensive file analysis"
        }
    }

    def detect_patterns(self, history: list[dict]) -> list[PatternRecord]:
        """Detect patterns in tool usage history."""

        detected = []

        for name, pattern in self.ANTI_PATTERNS.items():
            if pattern["detect"](history):
                detected.append(PatternRecord(
                    id=f"pattern-{name}",
                    pattern_type="anti-pattern",
                    name=name,
                    description=pattern["description"],
                    correct_approach=pattern["remediation"]
                ))

        return detected
```

### 5.4 Autonomy Level Recommendation

```python
class AutonomyRecommender:
    """Recommend autonomy level based on history."""

    def recommend(
        self,
        violations: SessionViolationSummary,
        patterns: list[PatternRecord],
        compliance_history: list[float]  # Last 5 sessions
    ) -> AutonomyLevel:
        """
        Recommend autonomy level for next session.

        Decision Matrix:
        - Observer (minimal guidance): >90% compliance, no anti-patterns
        - Consultant (moderate): 70-90% compliance OR 1-2 anti-patterns
        - Collaborator (guided): 50-70% compliance OR 3+ anti-patterns
        - Operator (strict): <50% compliance OR circuit breaker triggered
        """

        avg_compliance = sum(compliance_history) / len(compliance_history) if compliance_history else 0.5
        anti_pattern_count = len([p for p in patterns if p.pattern_type == "anti-pattern"])

        if avg_compliance > 0.9 and anti_pattern_count == 0:
            return AutonomyLevel(
                level="observer",
                messaging_intensity="minimal",
                enforcement_mode="guidance",
                reason=f"Excellent compliance ({avg_compliance:.0%}), no anti-patterns"
            )
        elif avg_compliance > 0.7 or anti_pattern_count <= 2:
            return AutonomyLevel(
                level="consultant",
                messaging_intensity="moderate",
                enforcement_mode="guidance",
                reason=f"Good compliance ({avg_compliance:.0%}), {anti_pattern_count} anti-patterns"
            )
        elif avg_compliance > 0.5 or anti_pattern_count <= 4:
            return AutonomyLevel(
                level="collaborator",
                messaging_intensity="high",
                enforcement_mode="strict",
                reason=f"Moderate compliance ({avg_compliance:.0%}), needs improvement"
            )
        else:
            return AutonomyLevel(
                level="operator",
                messaging_intensity="maximal",
                enforcement_mode="strict",
                reason=f"Low compliance ({avg_compliance:.0%}), requires strict guidance"
            )
```

---

## Part 6: Implementation Plan

### Phase 1: Foundation (Week 1-2)

**Goal:** Basic tracking and soft guidance

**Deliverables:**
1. `ViolationTracker` class with JSONL storage
2. Enhanced `PreToolUse` hook with violation counting
3. Basic imperative messages (Level 0-1)
4. Session violation summary in `Stop` hook

**Files to Modify:**
- `src/python/htmlgraph/hooks/orchestrator.py` - Add violation tracking
- `src/python/htmlgraph/hooks/pretooluse.py` - Integrate CIGS
- `src/python/htmlgraph/hooks/posttooluse.py` - Add cost tracking
- New: `src/python/htmlgraph/cigs/tracker.py`
- New: `src/python/htmlgraph/cigs/models.py`

**Testing:**
- Unit tests for violation tracking
- Integration test for hook flow
- Manual testing with claude-code

### Phase 2: Imperative Messaging (Week 3-4)

**Goal:** Full escalation system with cost awareness

**Deliverables:**
1. `ImperativeMessageGenerator` with all escalation levels
2. `CostCalculator` for prediction and actual costs
3. Circuit breaker implementation with acknowledgment
4. Positive reinforcement for correct delegation

**Files to Modify:**
- New: `src/python/htmlgraph/cigs/messaging.py`
- New: `src/python/htmlgraph/cigs/cost.py`
- `src/python/htmlgraph/orchestrator_mode.py` - Circuit breaker enhancement
- `packages/claude-plugin/hooks/scripts/*.py` - Update all hooks

**Testing:**
- Test escalation progression
- Test cost calculations
- Test circuit breaker triggers

### Phase 3: Pattern Detection (Week 5-6)

**Goal:** Learn from violations and detect anti-patterns

**Deliverables:**
1. `PatternDetector` with initial anti-patterns
2. Pattern storage in HtmlGraph format
3. Session summary with pattern analysis
4. Pattern-based guidance customization

**Files to Modify:**
- New: `src/python/htmlgraph/cigs/patterns.py`
- `packages/claude-plugin/hooks/scripts/session-start.py` - Load patterns
- `packages/claude-plugin/hooks/scripts/stop.py` - Pattern summary

**Testing:**
- Test anti-pattern detection
- Test pattern persistence
- Test customized guidance

### Phase 4: Adaptive Autonomy (Week 7-8)

**Goal:** Self-adjusting system based on performance

**Deliverables:**
1. `AutonomyRecommender` with decision matrix
2. Cross-session compliance tracking
3. Autonomy level persistence and application
4. UserPromptSubmit pre-response guidance

**Files to Modify:**
- New: `src/python/htmlgraph/cigs/autonomy.py`
- `packages/claude-plugin/hooks/scripts/user-prompt-submit.py` - Pre-guidance
- `packages/claude-plugin/hooks/scripts/session-start.py` - Load autonomy

**Testing:**
- Test autonomy recommendations
- Test cross-session learning
- End-to-end system test

### Phase 5: Analytics Dashboard (Week 9-10)

**Goal:** Visibility into CIGS performance

**Deliverables:**
1. CIGS analytics CLI commands
2. Dashboard integration for CIGS metrics
3. Export functionality for analysis
4. Documentation and user guide

**Files to Modify:**
- `src/python/htmlgraph/cli.py` - Add CIGS commands
- `src/python/htmlgraph/dashboard.html` - CIGS tab
- New: `docs/CIGS_USER_GUIDE.md`

**Testing:**
- Test CLI commands
- Test dashboard rendering
- User acceptance testing

---

## Part 7: Success Metrics

### 7.1 Primary Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Delegation Compliance Rate | >80% | Delegations / (Delegations + Violations) |
| Cost Efficiency Score | >75/100 | (Optimal / Actual) * 100 - penalties |
| Circuit Breaker Frequency | <10% of sessions | Sessions with breaker / Total sessions |
| Positive Reinforcement Ratio | >3:1 | Positive messages / Imperative messages |

### 7.2 Secondary Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Anti-Pattern Reduction | -50% month-over-month | Anti-patterns detected / Session |
| Time to Correct Pattern | <5 sessions | Sessions until pattern eliminated |
| User Satisfaction | No complaints | User feedback on guidance intrusiveness |
| System Performance | <50ms added latency | Hook execution time |

### 7.3 Learning Effectiveness

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pattern Recognition Accuracy | >90% | True positives / (True + False positives) |
| Autonomy Level Appropriateness | >85% match | Recommended vs observed behavior |
| Cost Prediction Accuracy | +/- 20% | Predicted vs actual token costs |

---

## Appendix A: Research Foundation

### A.1 AI Behavioral Science (Key Finding)

> "AI agents are 6-16x more susceptible to nudges compared to humans (30-80% vs 5%)"

**Implication:** Imperative messaging can be highly effective without blocking. Strong framing and clear consequences change AI behavior more than mechanical restrictions.

### A.2 Constitutional AI Pattern

> "Constitutional rules provide self-critique layer"

**Implication:** Frame delegation rules as constitutional principles that Claude can reason about, not just mechanical blockers. Include WHY in every imperative.

### A.3 Multi-Agent Orchestration

> "Handoff pattern: 15x cost difference between patterns. Stateful patterns save 40-50%."

**Implication:** Cost messaging should be concrete and quantified. Show exact token savings to make delegation benefits tangible.

### A.4 Autonomy Levels

> "5 levels with context-aware autonomy certificates"

**Implication:** One-size-fits-all doesn't work. CIGS adapts guidance intensity based on demonstrated competence.

---

## Appendix B: Message Examples

### B.1 Level 0 (Guidance)
```
💡 GUIDANCE: Consider delegating exploration to spawn_gemini() for comprehensive search.

spawn_gemini() is FREE and can search your entire codebase at once.
Direct Read operations add ~5000 tokens to your context per file.
```

### B.2 Level 1 (Imperative)
```
🔴 IMPERATIVE: YOU MUST delegate file reading to Explorer subagent.

**WHY:** Exploration operations have unpredictable scope. What looks like 'one Read' often becomes 3-5 reads. Each direct read pollutes your strategic context with tactical details.

**COST IMPACT:** Direct execution costs ~5000 tokens in your context. Delegation would cost ~500 tokens (90% savings).

**INSTEAD:**
spawn_gemini(prompt="Search and analyze codebase for authentication patterns")
```

### B.3 Level 2 (Final Warning)
```
⚠️ FINAL WARNING: YOU MUST delegate NOW. Pattern detected: exploration sequence.

**WHY:** You have already executed 3 exploration operations. This is research work that should be delegated. Subagent can explore comprehensively and return a summary.

**COST IMPACT:** Session waste so far: 15,000 tokens. Optimal path: 2,000 tokens.

**INSTEAD:**
spawn_gemini(prompt="Comprehensive search for all authentication-related code")

**CONSEQUENCE:** Next violation will trigger circuit breaker, requiring manual acknowledgment.
```

### B.4 Level 3 (Circuit Breaker)
```
🚨 CIRCUIT BREAKER: Delegation violations exceeded threshold (3/3).

**WHY:** Repeated direct execution despite warnings indicates need for mandatory intervention.

**SESSION IMPACT:**
- Violations: 3
- Total waste: 25,000 tokens
- Efficiency score: 45/100

**REQUIRED:** Acknowledge this violation before proceeding:
`uv run htmlgraph orchestrator acknowledge-violation`

OR disable enforcement:
`uv run htmlgraph orchestrator set-level guidance`
```

### B.5 Positive Reinforcement
```
✅ Excellent delegation pattern!

**Impact:**
- Saved ~4,500 tokens of context
- Subagent handled tactical details
- Your strategic view remains clean

**Session Stats:**
- Delegation compliance: 87%
- Efficiency score: 82/100
- Keep it up! Consistent delegation improves response quality.
```

---

## Appendix C: Integration Points Summary

| Hook | Purpose | Key Actions |
|------|---------|-------------|
| SessionStart | Initialize | Load history, set autonomy level, inject context |
| UserPromptSubmit | Pre-response | Classify intent, inject delegation reminders |
| PreToolUse | Pre-execution | Classify tool, generate imperative, track violation |
| PostToolUse | Post-execution | Calculate cost, provide feedback, update model |
| Stop | Session end | Generate summary, persist patterns, recommend autonomy |

---

**Document Complete**

This design provides a comprehensive framework for implementing the Computational Imperative Guidance System in HtmlGraph. The system leverages all three integration points (system prompt, plugin hooks, Python package) to create a reinforcing loop that guides Claude toward delegation without mechanical blocking.
