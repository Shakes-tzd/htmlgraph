"""
CIGS Data Models - Violation tracking and cost analysis.

Provides comprehensive data structures for tracking delegation violations,
pattern detection, autonomy management, and cost accounting in the
Computational Imperative Guidance System.

Classes:
- ViolationType: Enum of violation categories
- ViolationRecord: Single violation with context and cost impact
- SessionViolationSummary: Aggregated session metrics
- PatternRecord: Detected behavioral patterns
- AutonomyLevel: Agent autonomy recommendations
- CostMetrics: Token cost analysis per session
- TokenCost: Per-operation token costs
- CostPrediction: Cost projection for operations
- OperationClassification: Tool operation classification

Design Reference:
    Part 3, Section 3.1 of computational-imperative-guidance-system-design.md
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum


class ViolationType(Enum):
    """Types of delegation violations.

    Categories:
    - DIRECT_EXPLORATION: Read/Grep/Glob when should delegate to spawn_gemini()
    - DIRECT_IMPLEMENTATION: Edit/Write when should delegate to spawn_codex()
    - DIRECT_TESTING: pytest/npm test directly instead of via Task()
    - DIRECT_GIT: git commands directly instead of via spawn_copilot()
    - EXPLORATION_SEQUENCE: 3+ exploration tools in sequence (indicates research work)
    - IGNORED_WARNING: Proceeded after imperative warning from PreToolUse hook
    """

    DIRECT_EXPLORATION = "direct_exploration"
    DIRECT_IMPLEMENTATION = "direct_implementation"
    DIRECT_TESTING = "direct_testing"
    DIRECT_GIT = "direct_git"
    EXPLORATION_SEQUENCE = "exploration_sequence"
    IGNORED_WARNING = "ignored_warning"

    def __str__(self) -> str:
        """Return human-readable violation type name."""
        names = {
            ViolationType.DIRECT_EXPLORATION: "Direct Exploration",
            ViolationType.DIRECT_IMPLEMENTATION: "Direct Implementation",
            ViolationType.DIRECT_TESTING: "Direct Testing",
            ViolationType.DIRECT_GIT: "Direct Git",
            ViolationType.EXPLORATION_SEQUENCE: "Exploration Sequence",
            ViolationType.IGNORED_WARNING: "Ignored Warning",
        }
        return names.get(self, self.value)


@dataclass
class ViolationRecord:
    """Record of a single delegation violation.

    Tracks a violation event including the tool used, context, cost impact,
    and escalation level. Used for session analytics and pattern detection.

    Attributes:
        id: Unique violation ID (e.g., "viol-001")
        session_id: Session where violation occurred
        timestamp: When violation was recorded
        tool: Tool name that was used directly (Read, Grep, Edit, etc.)
        tool_params: Parameters passed to tool for context
        violation_type: Category of violation (DIRECT_EXPLORATION, etc.)
        context_before: Description of what Claude was trying to accomplish
        should_have_delegated_to: Recommended delegation target (spawn_gemini, Task, etc.)
        actual_cost_tokens: Tokens consumed by direct execution
        optimal_cost_tokens: Tokens if delegated properly
        waste_tokens: Difference (actual - optimal)
        warning_level: Escalation level (1=first, 2=second, 3=circuit_breaker)
        was_warned: Whether PreToolUse hook warned before execution
        warning_ignored: Whether Claude proceeded despite warning
        agent: Agent that caused violation (default: "claude-code")
        feature_id: Feature ID if violation occurred during feature work
    """

    id: str
    session_id: str
    timestamp: datetime
    tool: str
    tool_params: dict
    violation_type: ViolationType

    context_before: str | None = None
    should_have_delegated_to: str = ""
    actual_cost_tokens: int = 0
    optimal_cost_tokens: int = 0
    waste_tokens: int = 0

    warning_level: int = 1
    was_warned: bool = False
    warning_ignored: bool = False

    agent: str = "claude-code"
    feature_id: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary, handling enum and datetime serialization."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "tool": self.tool,
            "tool_params": self.tool_params,
            "violation_type": self.violation_type.value,
            "context_before": self.context_before,
            "should_have_delegated_to": self.should_have_delegated_to,
            "actual_cost_tokens": self.actual_cost_tokens,
            "optimal_cost_tokens": self.optimal_cost_tokens,
            "waste_tokens": self.waste_tokens,
            "warning_level": self.warning_level,
            "was_warned": self.was_warned,
            "warning_ignored": self.warning_ignored,
            "agent": self.agent,
            "feature_id": self.feature_id,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "ViolationRecord":
        """Create from dictionary, handling enum and datetime deserialization."""
        data = data.copy()
        data["timestamp"] = (
            datetime.fromisoformat(data["timestamp"])
            if isinstance(data["timestamp"], str)
            else data["timestamp"]
        )
        data["violation_type"] = ViolationType(data["violation_type"])
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "ViolationRecord":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"Violation({self.id}): {self.tool} for {self.violation_type}\n"
            f"  Context: {self.context_before}\n"
            f"  Waste: {self.waste_tokens} tokens (actual: {self.actual_cost_tokens}, "
            f"optimal: {self.optimal_cost_tokens})\n"
            f"  Warning level: {self.warning_level}, Warned: {self.was_warned}"
        )

    def validate(self) -> tuple[bool, str]:
        """Validate violation record integrity.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.id:
            return False, "id cannot be empty"
        if not self.session_id:
            return False, "session_id cannot be empty"
        if not self.tool:
            return False, "tool cannot be empty"
        if self.actual_cost_tokens < 0:
            return False, "actual_cost_tokens cannot be negative"
        if self.optimal_cost_tokens < 0:
            return False, "optimal_cost_tokens cannot be negative"
        if self.waste_tokens != (self.actual_cost_tokens - self.optimal_cost_tokens):
            return False, "waste_tokens must equal actual_cost - optimal_cost"
        if not (1 <= self.warning_level <= 3):
            return False, "warning_level must be 1, 2, or 3"
        if self.was_warned and self.warning_ignored:
            if self.warning_level < 2:
                return False, "warning_ignored requires warning_level >= 2"
        return True, ""


@dataclass
class SessionViolationSummary:
    """Summary of violations for a single session.

    Aggregates all violations that occurred during a session with metrics
    for compliance rate, cost efficiency, and pattern analysis.

    Attributes:
        session_id: Session identifier
        total_violations: Total violation count for session
        violations_by_type: Count per violation type
        total_waste_tokens: Sum of waste_tokens across all violations
        circuit_breaker_triggered: Whether circuit breaker activated (>= 3 violations)
        compliance_rate: Delegation compliance as float 0.0-1.0
        violations: List of individual violation records
    """

    session_id: str
    total_violations: int
    violations_by_type: dict[ViolationType, int]
    total_waste_tokens: int
    circuit_breaker_triggered: bool
    compliance_rate: float
    violations: list[ViolationRecord] = field(default_factory=list)

    def summary(self) -> str:
        """Return human-readable summary text.

        Returns:
            Formatted summary with key metrics
        """
        breaker_status = "YES 🚨" if self.circuit_breaker_triggered else "No"

        violations_detail = ""
        for vtype, count in self.violations_by_type.items():
            violations_detail += f"  • {vtype}: {count}\n"

        return (
            f"Session {self.session_id}\n"
            f"─────────────────────────────────────\n"
            f"Total Violations: {self.total_violations}\n"
            f"\nViolation Breakdown:\n{violations_detail}"
            f"Total Waste: {self.total_waste_tokens} tokens\n"
            f"Compliance Rate: {self.compliance_rate:.1%}\n"
            f"Circuit Breaker: {breaker_status}"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "total_violations": self.total_violations,
            "violations_by_type": {
                k.value: v for k, v in self.violations_by_type.items()
            },
            "total_waste_tokens": self.total_waste_tokens,
            "circuit_breaker_triggered": self.circuit_breaker_triggered,
            "compliance_rate": self.compliance_rate,
            "violations": [v.to_dict() for v in self.violations],
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "SessionViolationSummary":
        """Create from dictionary."""
        data = data.copy()
        data["violations_by_type"] = {
            ViolationType(k): v for k, v in data.get("violations_by_type", {}).items()
        }
        data["violations"] = [
            ViolationRecord.from_dict(v) for v in data.get("violations", [])
        ]
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "SessionViolationSummary":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __str__(self) -> str:
        """Return summary representation."""
        return (
            f"SessionViolationSummary({self.session_id}): "
            f"{self.total_violations} violations, "
            f"{self.compliance_rate:.0%} compliant, "
            f"waste: {self.total_waste_tokens} tokens"
        )

    def validate(self) -> tuple[bool, str]:
        """Validate summary integrity.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.session_id:
            return False, "session_id cannot be empty"
        if self.total_violations < 0:
            return False, "total_violations cannot be negative"
        if not (0.0 <= self.compliance_rate <= 1.0):
            return False, "compliance_rate must be between 0.0 and 1.0"
        if self.total_waste_tokens < 0:
            return False, "total_waste_tokens cannot be negative"
        if self.circuit_breaker_triggered and self.total_violations < 3:
            return False, "circuit_breaker_triggered requires >= 3 violations"

        # Validate count sum matches total
        count_sum = sum(self.violations_by_type.values())
        if count_sum != self.total_violations:
            return (
                False,
                f"violations_by_type sum ({count_sum}) != total_violations "
                f"({self.total_violations})",
            )

        return True, ""

    @property
    def count(self) -> int:
        """Total violation count."""
        return self.total_violations


@dataclass
class TokenCost:
    """Token cost breakdown for an operation or session.

    Provides granular token accounting for cost analysis and efficiency
    calculation.

    Attributes:
        total_tokens: Total tokens consumed
        orchestrator_tokens: Tokens in orchestrator/main agent context
        subagent_tokens: Tokens consumed by delegated subagents
        estimated_savings: Estimated tokens saved via delegation
    """

    total_tokens: int
    orchestrator_tokens: int
    subagent_tokens: int
    estimated_savings: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "TokenCost":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "TokenCost":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"TokenCost: {self.total_tokens} total\n"
            f"  Orchestrator: {self.orchestrator_tokens}\n"
            f"  Subagents: {self.subagent_tokens}\n"
            f"  Estimated savings: {self.estimated_savings}"
        )

    def validate(self) -> tuple[bool, str]:
        """Validate token cost integrity.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.total_tokens < 0:
            return False, "total_tokens cannot be negative"
        if self.orchestrator_tokens < 0:
            return False, "orchestrator_tokens cannot be negative"
        if self.subagent_tokens < 0:
            return False, "subagent_tokens cannot be negative"
        if self.estimated_savings < 0:
            return False, "estimated_savings cannot be negative"
        if (self.orchestrator_tokens + self.subagent_tokens) > self.total_tokens:
            return (
                False,
                "orchestrator_tokens + subagent_tokens cannot exceed total_tokens",
            )
        return True, ""


@dataclass
class CostPrediction:
    """Prediction of cost impact for an operation.

    Used by PreToolUse hook to estimate token cost of direct execution vs
    optimal delegation approach.

    Attributes:
        should_delegate: Whether operation should be delegated
        optimal_cost: Predicted cost if delegated
        waste_percentage: Estimated waste as percentage
    """

    should_delegate: bool
    optimal_cost: int
    waste_percentage: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "CostPrediction":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "CostPrediction":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"CostPrediction: Should delegate: {self.should_delegate}\n"
            f"  Optimal cost: {self.optimal_cost} tokens\n"
            f"  Waste if direct: {self.waste_percentage:.1f}%"
        )

    def validate(self) -> tuple[bool, str]:
        """Validate cost prediction integrity.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.optimal_cost < 0:
            return False, "optimal_cost cannot be negative"
        if not (0.0 <= self.waste_percentage <= 100.0):
            return False, "waste_percentage must be between 0 and 100"
        return True, ""


@dataclass
class OperationClassification:
    """Classification of a tool operation for delegation decisions.

    Used by PreToolUse hook to classify operations and determine if delegation
    is required. Combines tool category with pattern analysis.

    Attributes:
        tool: Tool name (Read, Edit, Bash, etc.)
        category: Operation category (exploration, implementation, etc.)
        should_delegate: Whether operation requires delegation
        reason: Explanation for classification
        is_exploration_sequence: Whether this is part of multi-operation sequence
        suggested_delegation: Recommended delegation target
        predicted_cost: Predicted tokens for direct execution
        optimal_cost: Tokens if delegated
        waste_percentage: Waste as percentage
    """

    tool: str
    category: str
    should_delegate: bool
    reason: str
    is_exploration_sequence: bool
    suggested_delegation: str

    predicted_cost: int = 0
    optimal_cost: int = 0
    waste_percentage: float = 0.0

    VALID_CATEGORIES = {
        "exploration",
        "implementation",
        "testing",
        "git",
        "allowed",
        "edge_case",
    }

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "OperationClassification":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "OperationClassification":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"OperationClassification: {self.tool} ({self.category})\n"
            f"  Should delegate: {self.should_delegate}\n"
            f"  Reason: {self.reason}\n"
            f"  Suggested: {self.suggested_delegation}\n"
            f"  Cost: {self.predicted_cost} → {self.optimal_cost} "
            f"({self.waste_percentage:.1f}% waste)"
        )

    def validate(self) -> tuple[bool, str]:
        """Validate operation classification integrity.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.tool:
            return False, "tool cannot be empty"
        if self.category not in self.VALID_CATEGORIES:
            return False, f"category must be one of {self.VALID_CATEGORIES}"
        if not self.reason:
            return False, "reason cannot be empty"
        if not self.suggested_delegation:
            return False, "suggested_delegation cannot be empty"
        if self.predicted_cost < 0:
            return False, "predicted_cost cannot be negative"
        if self.optimal_cost < 0:
            return False, "optimal_cost cannot be negative"
        if not (0.0 <= self.waste_percentage <= 100.0):
            return False, "waste_percentage must be between 0 and 100"
        return True, ""


@dataclass
class PatternRecord:
    """Record of a detected behavioral pattern.

    Tracks identified patterns (both good patterns and anti-patterns) for
    learning and customizing guidance messages.

    Attributes:
        id: Unique pattern ID
        pattern_type: "anti-pattern" or "good-pattern"
        name: Human-readable pattern name
        description: What the pattern represents
        trigger_conditions: List of conditions that activate this pattern
        example_sequence: Example tool sequence that triggers pattern
        occurrence_count: How many times detected
        sessions_affected: Sessions where pattern was detected
        correct_approach: Recommended fix (for anti-patterns)
        delegation_suggestion: What to delegate to instead
    """

    id: str
    pattern_type: str
    name: str
    description: str
    trigger_conditions: list[str]
    example_sequence: list[str]

    occurrence_count: int = 0
    sessions_affected: list[str] = field(default_factory=list)

    correct_approach: str | None = None
    delegation_suggestion: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "PatternRecord":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "PatternRecord":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"PatternRecord({self.id}): {self.name} ({self.pattern_type})\n"
            f"  Description: {self.description}\n"
            f"  Occurrences: {self.occurrence_count} in {len(self.sessions_affected)} "
            f"sessions"
        )

    def validate(self) -> tuple[bool, str]:
        """Validate pattern record integrity.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.id:
            return False, "id cannot be empty"
        if self.pattern_type not in ("anti-pattern", "good-pattern"):
            return False, "pattern_type must be 'anti-pattern' or 'good-pattern'"
        if not self.name:
            return False, "name cannot be empty"
        if not self.description:
            return False, "description cannot be empty"
        if not self.trigger_conditions:
            return False, "trigger_conditions cannot be empty"
        if not self.example_sequence:
            return False, "example_sequence cannot be empty"
        if self.occurrence_count < 0:
            return False, "occurrence_count cannot be negative"
        if self.pattern_type == "anti-pattern" and not self.correct_approach:
            return False, "anti-patterns must have correct_approach"
        return True, ""


@dataclass
class AutonomyLevel:
    """Recommendation for agent autonomy level.

    Suggests appropriate autonomy settings based on demonstrated behavior and
    violation history. Adapts guidance intensity to agent competence.

    Levels:
    - "observer": Minimal guidance, only watch
    - "consultant": Moderate guidance, suggest alternatives
    - "collaborator": Strong guidance, detailed explanations
    - "operator": Maximal guidance, mandatory acknowledgments

    Attributes:
        level: One of "observer", "consultant", "collaborator", "operator"
        messaging_intensity: "minimal", "moderate", "high", or "maximal"
        enforcement_mode: "guidance" (no blocking) or "strict" (with acknowledgment)
        reason: Explanation of why this level is recommended
        based_on_violations: Count of violations influencing recommendation
        based_on_patterns: List of patterns influencing recommendation
    """

    level: str
    messaging_intensity: str
    enforcement_mode: str

    reason: str
    based_on_violations: int = 0
    based_on_patterns: list[str] = field(default_factory=list)

    VALID_LEVELS = {"observer", "consultant", "collaborator", "operator"}
    VALID_INTENSITIES = {"minimal", "moderate", "high", "maximal"}
    VALID_MODES = {"guidance", "strict"}

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "AutonomyLevel":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "AutonomyLevel":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"AutonomyLevel: {self.level}\n"
            f"  Messaging: {self.messaging_intensity}\n"
            f"  Enforcement: {self.enforcement_mode}\n"
            f"  Reason: {self.reason}"
        )

    def validate(self) -> tuple[bool, str]:
        """Validate autonomy level configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.level not in self.VALID_LEVELS:
            return False, f"level must be one of {self.VALID_LEVELS}"
        if self.messaging_intensity not in self.VALID_INTENSITIES:
            return False, (
                f"messaging_intensity must be one of {self.VALID_INTENSITIES}"
            )
        if self.enforcement_mode not in self.VALID_MODES:
            return False, f"enforcement_mode must be one of {self.VALID_MODES}"
        if not self.reason:
            return False, "reason cannot be empty"
        if self.based_on_violations < 0:
            return False, "based_on_violations cannot be negative"
        return True, ""


@dataclass
class CostMetrics:
    """Comprehensive cost metrics for a session or operation.

    Aggregates token costs with efficiency scoring and waste analysis.

    Attributes:
        total_tokens: Total tokens consumed
        orchestrator_tokens: Tokens in main orchestrator context
        subagent_tokens: Tokens in delegated subagent contexts
        waste_tokens: Tokens wasted on suboptimal decisions
        optimal_tokens: What it would have cost with optimal delegation
        efficiency_score: 0-100 efficiency rating
        waste_percentage: Waste as percentage of total
    """

    total_tokens: int
    orchestrator_tokens: int
    subagent_tokens: int

    waste_tokens: int
    optimal_tokens: int

    efficiency_score: float = 0.0
    waste_percentage: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "CostMetrics":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "CostMetrics":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"CostMetrics: {self.total_tokens} tokens\n"
            f"  Orchestrator: {self.orchestrator_tokens}\n"
            f"  Subagents: {self.subagent_tokens}\n"
            f"  Waste: {self.waste_tokens} tokens ({self.waste_percentage:.1f}%)\n"
            f"  Efficiency: {self.efficiency_score}/100"
        )

    def validate(self) -> tuple[bool, str]:
        """Validate cost metrics integrity.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.total_tokens < 0:
            return False, "total_tokens cannot be negative"
        if self.orchestrator_tokens < 0:
            return False, "orchestrator_tokens cannot be negative"
        if self.subagent_tokens < 0:
            return False, "subagent_tokens cannot be negative"
        if self.waste_tokens < 0:
            return False, "waste_tokens cannot be negative"
        if self.optimal_tokens < 0:
            return False, "optimal_tokens cannot be negative"
        if not (0.0 <= self.efficiency_score <= 100.0):
            return False, "efficiency_score must be between 0 and 100"
        if not (0.0 <= self.waste_percentage <= 100.0):
            return False, "waste_percentage must be between 0 and 100"
        if (self.orchestrator_tokens + self.subagent_tokens) > self.total_tokens:
            return (
                False,
                "orchestrator + subagent tokens cannot exceed total",
            )
        return True, ""
