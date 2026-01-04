#!/usr/bin/env python3
"""
CIGS Wave 1 Parallel Delegation Script

Launches 9 agents simultaneously to implement the foundation of the
Computational Imperative Guidance System (CIGS).

Wave 1 Groups:
- A1 (3 agents): ViolationTracker + Models + Basic messages
- B1 (2 agents): ImperativeMessageGenerator + CostCalculator
- C1 (2 agents): PatternDetector + Pattern storage
- D1 (1 agent): AutonomyRecommender
- E0 (1 agent): Documentation

Expected speedup: 9x faster than sequential execution
"""

import json
from datetime import datetime

from htmlgraph import SDK
from htmlgraph.orchestration import HeadlessSpawner

# Initialize
sdk = SDK(agent="orchestrator")
spawner = HeadlessSpawner()

print("=" * 80)
print("CIGS Wave 1: Parallel Delegation")
print("=" * 80)
print(f"\nStarting at: {datetime.now().isoformat()}")
print("\nLaunching 9 agents in parallel...\n")

# Track all agent results
wave1_results = {"start_time": datetime.now().isoformat(), "agents": []}

# ============================================================================
# GROUP A1: Foundation Components (3 agents)
# ============================================================================

print("Group A1: Foundation Components (3 agents)")
print("-" * 80)

# A1-1: ViolationTracker
print("  [A1-1] Launching ViolationTracker agent...")
a1_1_result = spawner.spawn_codex(
    prompt="""
Implement the ViolationTracker class for CIGS (Computational Imperative Guidance System).

**Location:** `src/python/htmlgraph/cigs/tracker.py`

**Requirements:**

1. **Class: ViolationTracker**
   - Tracks delegation violations in JSONL format
   - Stores in `.htmlgraph/cigs/violations.jsonl`
   - Thread-safe for concurrent access

2. **Methods to implement:**
   ```python
   def record_violation(
       self,
       tool: str,
       params: dict,
       classification: OperationClassification,
       predicted_waste: int
   ) -> str:
       # Record a violation, return violation ID

   def get_session_violations(self, session_id: Optional[str] = None) -> SessionViolationSummary:
       # Get violations for current or specific session

   def get_recent_violations(self, sessions: int = 5) -> list[ViolationRecord]:
       # Get violations from last N sessions

   def record_actual_cost(self, tool: str, cost: TokenCost) -> None:
       # Update violation with actual cost after execution

   def get_session_waste(self) -> int:
       # Get total wasted tokens for current session
   ```

3. **Storage format:**
   - JSONL (one violation per line)
   - Fields: id, session_id, timestamp, tool, violation_type, actual_cost_tokens, optimal_cost_tokens, waste_tokens, warning_level

4. **Integration:**
   - Use HtmlGraph's existing graph_dir for storage location
   - Create `.htmlgraph/cigs/` directory if needed
   - Import from `htmlgraph.cigs.models` for data types

**Design reference:** `.htmlgraph/spikes/computational-imperative-guidance-system-design.md` (Part 3)

**Deliverables:**
- Complete implementation in `src/python/htmlgraph/cigs/tracker.py`
- Unit tests in `tests/python/test_violation_tracker.py`
- Ensure thread-safety and error handling
""",
    model="gpt-4",
)
wave1_results["agents"].append(
    {
        "id": "A1-1",
        "name": "ViolationTracker",
        "status": "success" if a1_1_result.success else "failed",
        "error": a1_1_result.error,
    }
)

# A1-2: Data Models
print("  [A1-2] Launching Data Models agent...")
a1_2_result = spawner.spawn_codex(
    prompt="""
Create violation data models for CIGS (Computational Imperative Guidance System).

**Location:** `src/python/htmlgraph/cigs/models.py`

**Requirements:**

1. **Implement these dataclasses:**

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class ViolationType(Enum):
    DIRECT_EXPLORATION = "direct_exploration"
    DIRECT_IMPLEMENTATION = "direct_implementation"
    DIRECT_TESTING = "direct_testing"
    DIRECT_GIT = "direct_git"
    EXPLORATION_SEQUENCE = "exploration_sequence"
    IGNORED_WARNING = "ignored_warning"

@dataclass
class ViolationRecord:
    id: str
    session_id: str
    timestamp: datetime
    tool: str
    tool_params: dict
    violation_type: ViolationType
    context_before: Optional[str] = None
    should_have_delegated_to: str = ""
    actual_cost_tokens: int = 0
    optimal_cost_tokens: int = 0
    waste_tokens: int = 0
    warning_level: int = 1
    was_warned: bool = False
    warning_ignored: bool = False
    agent: str = "claude-code"
    feature_id: Optional[str] = None

@dataclass
class SessionViolationSummary:
    session_id: str
    total_violations: int
    violations_by_type: dict[ViolationType, int]
    total_waste_tokens: int
    circuit_breaker_triggered: bool
    compliance_rate: float
    violations: list[ViolationRecord] = field(default_factory=list)

    def summary(self) -> str:
        # Return human-readable summary

@dataclass
class TokenCost:
    total_tokens: int
    orchestrator_tokens: int
    subagent_tokens: int
    estimated_savings: int

@dataclass
class CostPrediction:
    should_delegate: bool
    optimal_cost: int
    waste_percentage: float

@dataclass
class OperationClassification:
    tool: str
    category: str
    should_delegate: bool
    reason: str
    is_exploration_sequence: bool
    suggested_delegation: str
    predicted_cost: int = 0
    optimal_cost: int = 0
    waste_percentage: float = 0.0
```

2. **Add helper methods:**
   - JSON serialization/deserialization
   - Validation methods
   - String representations

**Design reference:** `.htmlgraph/spikes/computational-imperative-guidance-system-design.md` (Part 3, Section 3.1)

**Deliverables:**
- Complete data models in `src/python/htmlgraph/cigs/models.py`
- Type hints and docstrings
- Validation logic
""",
    model="gpt-4",
)
wave1_results["agents"].append(
    {
        "id": "A1-2",
        "name": "Data Models",
        "status": "success" if a1_2_result.success else "failed",
        "error": a1_2_result.error,
    }
)

# A1-3: Basic Imperative Messages
print("  [A1-3] Launching Basic Messages agent...")
a1_3_result = spawner.spawn_codex(
    prompt="""
Implement basic imperative message templates (Level 0-1) for CIGS.

**Location:** `src/python/htmlgraph/cigs/messages_basic.py`

**Requirements:**

1. **Create message templates for:**
   - Level 0 (Guidance): Informative, suggestion-based
   - Level 1 (Imperative): Commanding tone with cost impact

2. **Message structure:**
```python
class BasicMessageGenerator:
    def generate_guidance(
        self,
        tool: str,
        operation_type: str
    ) -> str:
        # Level 0: Soft guidance
        # "💡 Consider delegating X to spawn_Y() for better efficiency"

    def generate_imperative(
        self,
        tool: str,
        operation_type: str,
        cost_waste: int
    ) -> str:
        # Level 1: Strong imperative
        # "🔴 YOU MUST delegate X. Cost waste: N tokens"
```

3. **Tool-specific templates:**
   - Read/Grep/Glob → spawn_gemini() (exploration)
   - Edit/Write → spawn_codex() (implementation)
   - Bash(git) → spawn_copilot() (git operations)

4. **Include in messages:**
   - WHY delegation is needed (rationale)
   - WHAT to do instead (exact command)
   - COST impact (token waste estimate)

**Design reference:** `.htmlgraph/spikes/computational-imperative-guidance-system-design.md` (Part 4, Appendix B.1-B.2)

**Deliverables:**
- Message generator class in `src/python/htmlgraph/cigs/messages_basic.py`
- Template examples for common tools
- Unit tests for message generation
""",
    model="gpt-4",
)
wave1_results["agents"].append(
    {
        "id": "A1-3",
        "name": "Basic Messages",
        "status": "success" if a1_3_result.success else "failed",
        "error": a1_3_result.error,
    }
)

# ============================================================================
# GROUP B1: Messaging Infrastructure (2 agents)
# ============================================================================

print("\nGroup B1: Messaging Infrastructure (2 agents)")
print("-" * 80)

# B1-1: ImperativeMessageGenerator
print("  [B1-1] Launching ImperativeMessageGenerator agent...")
b1_1_result = spawner.spawn_codex(
    prompt="""
Implement complete ImperativeMessageGenerator with all escalation levels for CIGS.

**Location:** `src/python/htmlgraph/cigs/messaging.py`

**Requirements:**

1. **Implement 4 escalation levels:**
   - Level 0: Guidance (informative)
   - Level 1: Imperative (commanding)
   - Level 2: Final Warning (urgent + consequences)
   - Level 3: Circuit Breaker (requires acknowledgment)

2. **Class structure:**
```python
class ImperativeMessageGenerator:
    ESCALATION_LEVELS = {
        0: {"prefix": "💡 GUIDANCE", "tone": "informative", ...},
        1: {"prefix": "🔴 IMPERATIVE", "tone": "commanding", ...},
        2: {"prefix": "⚠️ FINAL WARNING", "tone": "urgent", ...},
        3: {"prefix": "🚨 CIRCUIT BREAKER", "tone": "blocking", ...}
    }

    def generate(
        self,
        tool: str,
        classification: OperationClassification,
        violation_count: int,
        autonomy_level: str
    ) -> str:
        # Generate escalated message based on context
```

3. **Message components:**
   - Prefix with escalation indicator
   - Core imperative message
   - WHY rationale (why delegation is mandatory)
   - COST impact (token waste)
   - INSTEAD suggestion (exact delegation command)
   - CONSEQUENCE (for levels 2-3)
   - ACKNOWLEDGMENT requirement (level 3)

4. **Integration:**
   - Use OperationClassification from models.py
   - Tool-specific core messages
   - Cost-aware messaging

**Design reference:** `.htmlgraph/spikes/computational-imperative-guidance-system-design.md` (Part 4, Section 4.1)

**Deliverables:**
- Complete ImperativeMessageGenerator in `src/python/htmlgraph/cigs/messaging.py`
- All 4 escalation levels
- Unit tests with example outputs
""",
    model="gpt-4",
)
wave1_results["agents"].append(
    {
        "id": "B1-1",
        "name": "ImperativeMessageGenerator",
        "status": "success" if b1_1_result.success else "failed",
        "error": b1_1_result.error,
    }
)

# B1-2: CostCalculator
print("  [B1-2] Launching CostCalculator agent...")
b1_2_result = spawner.spawn_codex(
    prompt="""
Implement CostCalculator for token prediction and actual cost tracking in CIGS.

**Location:** `src/python/htmlgraph/cigs/cost.py`

**Requirements:**

1. **Class: CostCalculator**
```python
class CostCalculator:
    def predict_cost(
        self,
        tool: str,
        params: dict
    ) -> int:
        # Predict token cost for direct execution
        # Based on tool type and parameters

    def optimal_cost(
        self,
        classification: OperationClassification
    ) -> int:
        # Calculate optimal cost with delegation

    def calculate_actual_cost(
        self,
        tool: str,
        result: dict
    ) -> TokenCost:
        # Calculate actual cost after execution
        # Parse from result metadata
```

2. **Cost estimation rules:**
   - Read: ~5000 tokens per file (depends on file size)
   - Grep: ~3000 tokens for search results
   - Edit: ~4000 tokens per edit (depends on file size)
   - Bash: ~2000-10000 (depends on output)
   - Task: ~500 tokens (orchestrator context only)
   - spawn_*: ~500 tokens (orchestrator context only)

3. **Waste calculation:**
```python
def calculate_waste(
    self,
    actual_cost: int,
    optimal_cost: int
) -> dict:
    return {
        "waste_tokens": actual_cost - optimal_cost,
        "waste_percentage": ((actual_cost - optimal_cost) / actual_cost) * 100,
        "efficiency_score": (optimal_cost / actual_cost) * 100
    }
```

4. **Integration:**
   - Use TokenCost model from models.py
   - Account for context accumulation
   - Consider cascading costs (failures → retries)

**Design reference:** `.htmlgraph/spikes/computational-imperative-guidance-system-design.md` (Part 5, Analytics)

**Deliverables:**
- Complete CostCalculator in `src/python/htmlgraph/cigs/cost.py`
- Cost estimation heuristics
- Unit tests with example calculations
""",
    model="gpt-4",
)
wave1_results["agents"].append(
    {
        "id": "B1-2",
        "name": "CostCalculator",
        "status": "success" if b1_2_result.success else "failed",
        "error": b1_2_result.error,
    }
)

# ============================================================================
# GROUP C1: Pattern Detection (2 agents)
# ============================================================================

print("\nGroup C1: Pattern Detection (2 agents)")
print("-" * 80)

# C1-1: PatternDetector
print("  [C1-1] Launching PatternDetector agent...")
c1_1_result = spawner.spawn_codex(
    prompt="""
Implement PatternDetector for detecting delegation anti-patterns in CIGS.

**Location:** `src/python/htmlgraph/cigs/patterns.py`

**Requirements:**

1. **Class: PatternDetector**
```python
class PatternDetector:
    ANTI_PATTERNS = {
        "exploration_sequence": {
            "description": "Multiple exploration tools in sequence",
            "detect": lambda history: ...,
            "remediation": "Use spawn_gemini() for comprehensive exploration"
        },
        "edit_without_test": {...},
        "direct_git_commit": {...},
        "repeated_read_same_file": {...}
    }

    def detect_patterns(
        self,
        history: list[dict]
    ) -> list[PatternRecord]:
        # Detect anti-patterns from tool usage history
```

2. **Initial anti-patterns to implement:**
   - **exploration_sequence**: 3+ Read/Grep/Glob in sequence
   - **edit_without_test**: Edit without subsequent test delegation
   - **direct_git_commit**: git commit via Bash instead of Copilot
   - **repeated_read_same_file**: Same file read multiple times

3. **Detection logic:**
   - Analyze last N tool calls (sliding window)
   - Pattern matching on tool sequences
   - File path analysis for repeated reads
   - Command analysis for git operations

4. **Pattern metadata:**
   - Pattern ID, type (anti-pattern vs good-pattern)
   - Description and trigger conditions
   - Occurrence count and affected sessions
   - Remediation suggestion

**Design reference:** `.htmlgraph/spikes/computational-imperative-guidance-system-design.md` (Part 5, Section 5.3)

**Deliverables:**
- Complete PatternDetector in `src/python/htmlgraph/cigs/patterns.py`
- 4 initial anti-patterns implemented
- Unit tests with pattern detection examples
""",
    model="gpt-4",
)
wave1_results["agents"].append(
    {
        "id": "C1-1",
        "name": "PatternDetector",
        "status": "success" if c1_1_result.success else "failed",
        "error": c1_1_result.error,
    }
)

# C1-2: Pattern Storage
print("  [C1-2] Launching Pattern Storage agent...")
c1_2_result = spawner.spawn_codex(
    prompt="""
Implement pattern storage for persisting detected patterns in HtmlGraph format for CIGS.

**Location:** `src/python/htmlgraph/cigs/pattern_storage.py`

**Requirements:**

1. **Class: PatternStorage**
```python
class PatternStorage:
    def __init__(self, graph_dir: Path):
        self.patterns_file = graph_dir / "cigs" / "patterns.json"

    def save_pattern(
        self,
        pattern: PatternRecord
    ) -> None:
        # Save or update pattern

    def load_patterns(self) -> list[PatternRecord]:
        # Load all patterns

    def increment_occurrence(
        self,
        pattern_id: str,
        session_id: str
    ) -> None:
        # Increment pattern occurrence count

    def get_anti_patterns(self) -> list[PatternRecord]:
        # Get only anti-patterns

    def get_good_patterns(self) -> list[PatternRecord]:
        # Get only good patterns
```

2. **Storage format (JSON):**
```json
{
  "patterns": [
    {
      "id": "pattern-001",
      "pattern_type": "anti-pattern",
      "name": "exploration_sequence",
      "description": "...",
      "occurrence_count": 15,
      "sessions_affected": ["sess-abc", "sess-def"],
      "remediation": "Use spawn_gemini()"
    }
  ]
}
```

3. **Features:**
   - Thread-safe read/write
   - Atomic updates
   - Pattern deduplication
   - Session tracking

4. **Integration:**
   - Use PatternRecord from models.py
   - Store in `.htmlgraph/cigs/patterns.json`
   - Create directory if needed

**Design reference:** `.htmlgraph/spikes/computational-imperative-guidance-system-design.md` (Part 3, Section 3.2)

**Deliverables:**
- Complete PatternStorage in `src/python/htmlgraph/cigs/pattern_storage.py`
- JSON persistence with atomic writes
- Unit tests with pattern CRUD operations
""",
    model="gpt-4",
)
wave1_results["agents"].append(
    {
        "id": "C1-2",
        "name": "Pattern Storage",
        "status": "success" if c1_2_result.success else "failed",
        "error": c1_2_result.error,
    }
)

# ============================================================================
# GROUP D1: Autonomy Management (1 agent)
# ============================================================================

print("\nGroup D1: Autonomy Management (1 agent)")
print("-" * 80)

# D1-1: AutonomyRecommender
print("  [D1-1] Launching AutonomyRecommender agent...")
d1_1_result = spawner.spawn_codex(
    prompt="""
Implement AutonomyRecommender for adaptive autonomy level management in CIGS.

**Location:** `src/python/htmlgraph/cigs/autonomy.py`

**Requirements:**

1. **Class: AutonomyRecommender**
```python
class AutonomyRecommender:
    def recommend(
        self,
        violations: SessionViolationSummary,
        patterns: list[PatternRecord],
        compliance_history: list[float]
    ) -> AutonomyLevel:
        # Recommend autonomy level based on performance
```

2. **Decision matrix (5 levels):**
   - **Observer** (>90% compliance, 0 anti-patterns): Minimal guidance
   - **Consultant** (70-90% OR 1-2 anti-patterns): Moderate guidance
   - **Collaborator** (50-70% OR 3-4 anti-patterns): High guidance
   - **Operator** (<50% OR circuit breaker): Strict enforcement

3. **AutonomyLevel dataclass:**
```python
@dataclass
class AutonomyLevel:
    level: str  # "observer", "consultant", "collaborator", "operator"
    messaging_intensity: str  # "minimal", "moderate", "high", "maximal"
    enforcement_mode: str  # "guidance", "strict"
    reason: str  # Why this level
    based_on_violations: int
    based_on_patterns: list[str]
```

4. **Recommendation logic:**
   - Calculate average compliance from last 5 sessions
   - Count anti-patterns
   - Apply decision matrix
   - Generate reasoning explanation

**Design reference:** `.htmlgraph/spikes/computational-imperative-guidance-system-design.md` (Part 5, Section 5.4)

**Deliverables:**
- Complete AutonomyRecommender in `src/python/htmlgraph/cigs/autonomy.py`
- Decision matrix implementation
- Unit tests with various compliance scenarios
""",
    model="gpt-4",
)
wave1_results["agents"].append(
    {
        "id": "D1-1",
        "name": "AutonomyRecommender",
        "status": "success" if d1_1_result.success else "failed",
        "error": d1_1_result.error,
    }
)

# ============================================================================
# GROUP E0: Documentation (1 agent)
# ============================================================================

print("\nGroup E0: Documentation (1 agent)")
print("-" * 80)

# E0-1: Documentation
print("  [E0-1] Launching Documentation agent...")
e0_1_result = spawner.spawn_codex(
    prompt="""
Create CIGS user guide documentation.

**Location:** `docs/CIGS_USER_GUIDE.md`

**Requirements:**

1. **Documentation sections:**
   - What is CIGS?
   - How it works (3-layer architecture)
   - Imperative messaging system (4 levels)
   - Pattern detection and learning
   - Autonomy levels
   - How to use CIGS
   - Configuration options
   - Troubleshooting

2. **User-facing content:**
   - Clear explanations (non-technical)
   - Examples of imperative messages
   - How to interpret guidance
   - When to adjust autonomy levels
   - FAQ section

3. **Integration guide:**
   - How hooks work
   - What data is tracked
   - Privacy considerations
   - How to disable/configure

**Design reference:** `.htmlgraph/spikes/computational-imperative-guidance-system-design.md` (entire document)

**Deliverables:**
- Complete user guide in `docs/CIGS_USER_GUIDE.md`
- Examples and screenshots (text descriptions)
- FAQ and troubleshooting sections
""",
    model="gpt-4",
)
wave1_results["agents"].append(
    {
        "id": "E0-1",
        "name": "Documentation",
        "status": "success" if e0_1_result.success else "failed",
        "error": e0_1_result.error,
    }
)

# ============================================================================
# Results Summary
# ============================================================================

wave1_results["end_time"] = datetime.now().isoformat()
wave1_results["success_count"] = sum(
    1 for a in wave1_results["agents"] if a["status"] == "success"
)
wave1_results["failed_count"] = sum(
    1 for a in wave1_results["agents"] if a["status"] == "failed"
)

print("\n" + "=" * 80)
print("Wave 1 Delegation Complete")
print("=" * 80)
print(f"\nEnd time: {wave1_results['end_time']}")
print(f"Successful agents: {wave1_results['success_count']}/9")
print(f"Failed agents: {wave1_results['failed_count']}/9")

if wave1_results["failed_count"] > 0:
    print("\n⚠️  Failed agents:")
    for agent in wave1_results["agents"]:
        if agent["status"] == "failed":
            print(f"  - {agent['id']} ({agent['name']}): {agent['error']}")

print("\n📊 Results saved to: .htmlgraph/cigs/wave1-results.json")

# Save results
import os

os.makedirs(".htmlgraph/cigs", exist_ok=True)
with open(".htmlgraph/cigs/wave1-results.json", "w") as f:
    json.dump(wave1_results, f, indent=2, default=str)

print("\n✅ Wave 1 delegation complete!")
print("Next steps:")
print("  1. Review agent outputs in their respective files")
print("  2. Run tests: uv run pytest tests/python/test_cigs_*.py")
print("  3. When ready, launch Wave 2 delegation")
