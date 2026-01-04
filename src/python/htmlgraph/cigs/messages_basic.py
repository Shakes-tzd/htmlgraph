"""
Basic Imperative Message Templates for CIGS (Level 0-1)

This module provides message generators for the Computational Imperative Guidance System.
It handles Level 0 (Guidance) and Level 1 (Imperative) messages with cost awareness.

Design Reference:
- CIGS Design Doc: .htmlgraph/spikes/computational-imperative-guidance-system-design.md
- Part 4: Appendix B.1-B.2 (Message Examples)
- Part 4.1: Message Escalation Levels

Architecture:
- BasicMessageGenerator: Level 0-1 templates with tool-specific messaging
- PositiveReinforcementGenerator: Positive feedback for correct delegation
- Tool-specific delegation suggestions (spawn_gemini, spawn_codex, spawn_copilot)
- Cost impact estimation and rationale generation
"""

from dataclasses import dataclass
from enum import Enum


class ToolCategory(Enum):
    """Classification of tools by operational type."""

    EXPLORATION = "exploration"  # Read, Grep, Glob
    IMPLEMENTATION = "implementation"  # Edit, Write, NotebookEdit
    GIT_OPERATIONS = "git_operations"  # git commands via Bash
    TESTING = "testing"  # pytest, npm test via Bash
    UNKNOWN = "unknown"


@dataclass
class OperationContext:
    """Context for an operation being classified."""

    tool: str
    operation_type: str  # e.g., "direct_read", "multiple_edits"
    category: ToolCategory
    predicted_cost: int = 5000  # Default estimated tokens
    optimal_cost: int = 500  # Default with delegation
    violation_count: int = 0  # Violations this session
    is_sequence: bool = False  # Part of a sequence


class BasicMessageGenerator:
    """Generate Level 0-1 imperative messages for CIGS."""

    # Tool-to-delegation mapping
    DELEGATION_SUGGESTIONS = {
        ToolCategory.EXPLORATION: {
            "subagent": "spawn_gemini()",
            "rationale": "Exploration operations have unpredictable scope. What looks like 'one Read' often becomes 3-5 reads. Each direct read pollutes your strategic context with tactical details.",
            "example": "spawn_gemini(prompt='Search and analyze codebase for...')",
        },
        ToolCategory.IMPLEMENTATION: {
            "subagent": "spawn_codex()",
            "rationale": "Implementation requires iteration (write → test → fix → test). Delegating keeps your context focused on architecture, while subagent handles the edit-test cycle.",
            "example": "spawn_codex(prompt='Implement feature X with full test coverage')",
        },
        ToolCategory.GIT_OPERATIONS: {
            "subagent": "spawn_copilot()",
            "rationale": "Git operations cascade unpredictably (hooks, conflicts, push failures). Copilot specializes in git AND costs 60% less than Task().",
            "example": "spawn_copilot(prompt='Commit these changes with appropriate message')",
        },
        ToolCategory.TESTING: {
            "subagent": "Task()",
            "rationale": "Testing requires careful iteration and interpretation of results. Task() delegation keeps your context clean while handling the full test cycle.",
            "example": "Task(prompt='Run all tests and fix failures')",
        },
    }

    # Tool classification
    TOOL_TO_CATEGORY = {
        "Read": ToolCategory.EXPLORATION,
        "Grep": ToolCategory.EXPLORATION,
        "Glob": ToolCategory.EXPLORATION,
        "Edit": ToolCategory.IMPLEMENTATION,
        "Write": ToolCategory.IMPLEMENTATION,
        "NotebookEdit": ToolCategory.IMPLEMENTATION,
        "Delete": ToolCategory.IMPLEMENTATION,
    }

    def __init__(self) -> None:
        """Initialize message generator."""
        pass

    def generate_guidance(
        self,
        tool: str,
        operation_type: str,
        cost_estimate: int = 5000,
        optimal_cost: int = 500,
    ) -> str:
        """
        Generate Level 0 (Guidance) message - soft suggestion.

        Args:
            tool: Tool being used (Read, Edit, Bash, etc.)
            operation_type: Type of operation (e.g., "direct_read", "exploration_sequence")
            cost_estimate: Estimated tokens for direct execution
            optimal_cost: Estimated tokens with delegation

        Returns:
            Formatted guidance message
        """
        category = self._get_category(tool)
        delegation = self.DELEGATION_SUGGESTIONS.get(category)

        if not delegation:
            return f"💡 GUIDANCE: Consider delegating {tool} operations for better efficiency."

        savings_percent = int(((cost_estimate - optimal_cost) / cost_estimate) * 100)

        return f"""💡 GUIDANCE: Consider delegating {tool} operations to {delegation["subagent"]}

{delegation["subagent"]} is designed for exploration work and can search your entire codebase efficiently.
Direct {tool} operations add ~{cost_estimate} tokens to your context per operation.

**Example:**
```python
{delegation["example"]}
```

**Benefit:** Estimated {savings_percent}% token savings + cleaner context"""

    def generate_imperative(
        self,
        tool: str,
        operation_type: str,
        cost_waste: int = 4500,
        violation_count: int = 1,
    ) -> str:
        """
        Generate Level 1 (Imperative) message - commanding with cost impact.

        Args:
            tool: Tool being used
            operation_type: Type of operation
            cost_waste: Estimated token waste from direct execution
            violation_count: Number of violations so far this session

        Returns:
            Formatted imperative message with cost and delegation guidance
        """
        category = self._get_category(tool)
        delegation = self.DELEGATION_SUGGESTIONS.get(category)

        if not delegation:
            return f"🔴 IMPERATIVE: YOU MUST delegate {tool} operations."

        rationale = self._get_rationale(operation_type, category)
        cost_message = self._get_cost_message(tool, cost_waste)
        warning_suffix = self._get_warning_suffix(violation_count)

        return f"""🔴 IMPERATIVE: YOU MUST delegate {tool} operations to {delegation["subagent"]}.

**WHY:** {rationale}

{cost_message}

**INSTEAD:**
```python
{delegation["example"]}
```

{warning_suffix}"""

    def generate_guidance_with_context(
        self,
        context: OperationContext,
    ) -> str:
        """
        Generate Level 0 message from structured context.

        Args:
            context: OperationContext with all relevant details

        Returns:
            Formatted guidance message
        """
        return self.generate_guidance(
            tool=context.tool,
            operation_type=context.operation_type,
            cost_estimate=context.predicted_cost,
            optimal_cost=context.optimal_cost,
        )

    def generate_imperative_with_context(
        self,
        context: OperationContext,
    ) -> str:
        """
        Generate Level 1 message from structured context.

        Args:
            context: OperationContext with all relevant details

        Returns:
            Formatted imperative message
        """
        cost_waste = context.predicted_cost - context.optimal_cost
        return self.generate_imperative(
            tool=context.tool,
            operation_type=context.operation_type,
            cost_waste=cost_waste,
            violation_count=context.violation_count,
        )

    def _get_category(self, tool: str) -> ToolCategory:
        """Get tool category."""
        return self.TOOL_TO_CATEGORY.get(tool, ToolCategory.UNKNOWN)

    def _get_rationale(self, operation_type: str, category: ToolCategory) -> str:
        """Get specific rationale for operation type."""
        rationales = {
            "direct_exploration": (
                "Exploration operations have unpredictable scope. "
                "What looks like 'one Read' often becomes 3-5 reads. "
                "Each direct read pollutes your strategic context with tactical details."
            ),
            "exploration_sequence": (
                "You have already executed multiple exploration operations. "
                "This pattern indicates research work that should be delegated. "
                "Subagent can explore comprehensively and return a summary."
            ),
            "direct_implementation": (
                "Implementation requires iteration (write → test → fix → test). "
                "Delegating keeps your context focused on architecture, "
                "while subagent handles the edit-test cycle."
            ),
            "direct_git": (
                "Git operations cascade unpredictably (hooks, conflicts, push failures). "
                "Copilot specializes in git AND costs 60% less than Task()."
            ),
            "direct_testing": (
                "Test execution requires careful interpretation of results. "
                "Task() delegation keeps your context clean while handling the full test cycle."
            ),
        }

        # Use provided rationale if available, otherwise use category default
        if operation_type in rationales:
            return rationales[operation_type]

        delegation = self.DELEGATION_SUGGESTIONS.get(category)
        return (
            delegation["rationale"]
            if delegation
            else "Delegation preserves your strategic context."
        )

    def _get_cost_message(self, tool: str, cost_waste: int) -> str:
        """Generate cost impact message."""
        optimal_estimate = max(500, cost_waste // 10)  # Rough estimate
        savings_pct = int((cost_waste / (cost_waste + optimal_estimate)) * 100)

        return f"""**COST IMPACT:**
- Direct execution: ~{cost_waste + optimal_estimate} tokens in your context
- Delegation: ~{optimal_estimate} tokens ({savings_pct}% savings)
- This session waste so far: {cost_waste} tokens"""

    def _get_warning_suffix(self, violation_count: int) -> str:
        """Get warning message based on violation count."""
        if violation_count == 0:
            return ""
        elif violation_count == 1:
            return "**NOTE:** This is your first violation this session. Next violation escalates to final warning."
        elif violation_count == 2:
            return "**WARNING:** This is your second violation this session. Next violation triggers circuit breaker."
        else:
            return "**CRITICAL:** Circuit breaker will trigger with next violation."


class PositiveReinforcementGenerator:
    """Generate positive feedback for correct delegation patterns."""

    ENCOURAGEMENTS = [
        "Excellent delegation pattern!",
        "Perfect use of subagent!",
        "Context preserved effectively!",
        "Optimal delegation choice!",
        "Great orchestration!",
        "Superb task decomposition!",
    ]

    def generate(
        self,
        tool: str,
        cost_savings: int,
        compliance_rate: float,
        delegation_type: str = "Task",
    ) -> str:
        """
        Generate positive reinforcement message.

        Args:
            tool: Tool that was delegated (spawn_gemini, Task, etc.)
            cost_savings: Estimated tokens saved
            compliance_rate: Delegation compliance rate (0.0-1.0)
            delegation_type: Type of delegation ("Task", "spawn_gemini", etc.)

        Returns:
            Positive reinforcement message
        """
        import random

        base = random.choice(self.ENCOURAGEMENTS)

        # Estimate context size saved
        context_impact = f"~{cost_savings} tokens"
        if cost_savings > 5000:
            context_impact = "large portion of your"

        return f"""✅ {base}

**Impact:**
- Saved {context_impact} of strategic context
- Subagent handled tactical details
- Your focus remained on orchestration

**Session Stats:**
- Delegation compliance: {compliance_rate:.0%}
- Keep maintaining this pattern! Consistent delegation improves response quality."""

    def generate_from_metrics(
        self,
        actual_cost: int,
        optimal_cost: int,
        compliance_rate: float,
    ) -> str:
        """
        Generate positive reinforcement from cost metrics.

        Args:
            actual_cost: Actual tokens used (with delegation)
            optimal_cost: Optimal tokens for the operation
            compliance_rate: Overall delegation compliance

        Returns:
            Positive reinforcement message
        """
        cost_savings = max(0, actual_cost - optimal_cost)
        return self.generate(
            tool="subagent",
            cost_savings=cost_savings,
            compliance_rate=compliance_rate,
        )


class MessageTemplateLibrary:
    """Pre-built message templates for common scenarios."""

    # Template scenarios
    TEMPLATES = {
        "first_read": {
            "level": 0,
            "message": "💡 GUIDANCE: Reading a single file is allowed. If you need to explore multiple files, consider delegating to spawn_gemini() for comprehensive search.",
        },
        "second_read": {
            "level": 1,
            "message": "🔴 IMPERATIVE: YOU MUST delegate file reading. You've used 2 exploration tools - this indicates research work. Use spawn_gemini() for comprehensive analysis.",
        },
        "third_exploration": {
            "level": 1,
            "message": "🔴 IMPERATIVE: YOU MUST delegate NOW. Pattern detected: exploration sequence. spawn_gemini() can handle all remaining searches at once.",
        },
        "direct_edit": {
            "level": 1,
            "message": "🔴 IMPERATIVE: YOU MUST delegate code changes to spawn_codex(). This ensures full test cycle and prevents context pollution.",
        },
        "git_commit": {
            "level": 1,
            "message": "🔴 IMPERATIVE: YOU MUST delegate git operations to spawn_copilot(). Saves 60% tokens and handles hooks/conflicts automatically.",
        },
        "correct_delegation": {
            "level": 0,
            "message": "✅ Excellent! Delegating keeps your strategic context clean and improves response quality.",
        },
    }

    @classmethod
    def get_template(cls, scenario: str) -> str | None:
        """
        Get a pre-built template for a scenario.

        Args:
            scenario: Template scenario key

        Returns:
            Message template or None if not found
        """
        if scenario not in cls.TEMPLATES:
            return None
        template = cls.TEMPLATES[scenario].get("message")
        return template if isinstance(template, str) else None

    @classmethod
    def list_scenarios(cls) -> list[str]:
        """List all available template scenarios."""
        return list(cls.TEMPLATES.keys())


# Utility functions for hook integration


def classify_operation(
    tool: str, history_count: int = 0, is_git: bool = False
) -> tuple[str, str]:
    """
    Classify an operation for guidance generation.

    Args:
        tool: Tool name
        history_count: Number of recent similar operations
        is_git: Whether this is a git operation

    Returns:
        (operation_type, category_name) tuple
    """
    if is_git:
        return ("direct_git", "git_operations")

    if tool in ["Read", "Grep", "Glob"]:
        if history_count >= 2:
            return ("exploration_sequence", "exploration")
        return ("direct_exploration", "exploration")

    if tool in ["Edit", "Write", "NotebookEdit", "Delete"]:
        return ("direct_implementation", "implementation")

    return ("unknown", "unknown")


def estimate_costs(
    operation_type: str,
    tool: str,
) -> tuple[int, int]:
    """
    Estimate costs for an operation.

    Args:
        operation_type: Type of operation
        tool: Tool being used

    Returns:
        (predicted_cost, optimal_cost) tuple in tokens
    """
    # Base costs by tool
    base_costs = {
        "Read": 5000,
        "Grep": 3000,
        "Glob": 2000,
        "Edit": 8000,
        "Write": 6000,
    }

    predicted = base_costs.get(tool, 5000)

    # Optimal costs with delegation
    if tool in ["Read", "Grep", "Glob"]:
        optimal = 500  # spawn_gemini very efficient
    elif tool in ["Edit", "Write"]:
        optimal = 2000  # spawn_codex handles iteration
    else:
        optimal = 1000

    # Increase predicted cost for sequences
    if "sequence" in operation_type:
        predicted = int(predicted * 1.5)

    return (predicted, optimal)
