"""
CIGSPostToolAnalyzer for PostToolUse Hook Integration

Provides cost accounting and reinforcement messages for PostToolUse hook.
Integrates with ViolationTracker and CostCalculator to analyze actual costs
and generate appropriate feedback (positive reinforcement or cost accounting).

Design Reference:
- CIGS Design Doc: .htmlgraph/spikes/computational-imperative-guidance-system-design.md
- Part 2.4: PostToolUse Hook Enhancement
"""

from pathlib import Path
from typing import Any

from htmlgraph.cigs.cost import CostCalculator
from htmlgraph.cigs.messaging import PositiveReinforcementGenerator
from htmlgraph.cigs.models import TokenCost
from htmlgraph.cigs.tracker import ViolationTracker


class CIGSPostToolAnalyzer:
    """
    Analyze tool execution results and provide cost-aware feedback.

    Integrates with PostToolUse hook to:
    1. Calculate actual cost using CostCalculator
    2. Load prediction from ViolationTracker (if violation was recorded)
    3. Determine if operation was delegation (Task, spawn_*)
    4. Generate positive reinforcement for delegations
    5. Generate cost accounting for direct executions
    6. Update violation tracker with actual costs
    """

    def __init__(self, graph_dir: Path | None = None):
        """
        Initialize CIGSPostToolAnalyzer.

        Args:
            graph_dir: Root directory for HtmlGraph (defaults to .htmlgraph)
        """
        if graph_dir is None:
            graph_dir = Path.cwd() / ".htmlgraph"

        self.graph_dir = Path(graph_dir)
        self.cost_calculator = CostCalculator()
        self.tracker = ViolationTracker(self.graph_dir)
        self.positive_gen = PositiveReinforcementGenerator()

    def analyze(self, tool: str, params: dict, result: dict) -> dict[str, Any]:
        """
        Analyze tool execution and provide feedback.

        Args:
            tool: Tool that was executed (Read, Task, Edit, etc.)
            params: Tool parameters
            result: Tool execution result

        Returns:
            Hook response dict with feedback:
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "Feedback message"
                }
            }
        """
        # Calculate actual cost
        actual_cost = self.cost_calculator.calculate_actual_cost(tool, result)

        # Determine if this was a delegation or direct execution
        was_delegation = self._is_delegation(tool)

        if was_delegation:
            return self._positive_reinforcement(tool, actual_cost)
        else:
            return self._cost_accounting(tool, actual_cost)

    def _is_delegation(self, tool: str) -> bool:
        """
        Check if tool represents delegation.

        Args:
            tool: Tool name

        Returns:
            True if tool is a delegation operation
        """
        return tool == "Task" or tool.startswith("spawn_")

    def _positive_reinforcement(self, tool: str, cost: TokenCost) -> dict[str, Any]:
        """
        Provide positive reinforcement for correct delegation.

        Args:
            tool: Delegation tool used (Task, spawn_gemini, etc.)
            cost: Actual token cost breakdown

        Returns:
            Hook response with positive reinforcement message
        """
        # Get current session stats
        violations = self.tracker.get_session_violations()
        compliance_rate = self._calculate_compliance_rate(violations.total_violations)
        session_waste = violations.total_waste_tokens

        # Generate positive message
        message = self.positive_gen.generate(
            tool=tool,
            cost_savings=cost.estimated_savings,
            compliance_rate=compliance_rate,
            session_waste=session_waste,
        )

        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": message,
            }
        }

    def _cost_accounting(self, tool: str, cost: TokenCost) -> dict[str, Any]:
        """
        Account for cost of direct execution.

        Args:
            tool: Tool that was executed directly
            cost: Actual token cost breakdown

        Returns:
            Hook response with cost accounting message
        """
        # Update violation tracker with actual cost
        self.tracker.record_actual_cost(tool, cost)

        # Get session violations for context
        violations = self.tracker.get_session_violations()

        # Check if this was a warned violation (look for recent violation with this tool)
        has_violation = any(
            v.tool == tool for v in violations.violations[-3:] if violations.violations
        )

        if has_violation or violations.total_violations > 0:
            # This was likely a warned violation - provide cost impact
            message = self._generate_violation_cost_message(
                tool, cost, violations.total_violations, violations.total_waste_tokens
            )
        else:
            # Allowed operation - just informational
            message = f"Operation completed. Cost: {cost.total_tokens} tokens."

        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": message,
            }
        }

    def _generate_violation_cost_message(
        self, tool: str, cost: TokenCost, violation_count: int, total_waste: int
    ) -> str:
        """
        Generate cost impact message for violation.

        Args:
            tool: Tool that was executed
            cost: Actual token cost
            violation_count: Total violations in session
            total_waste: Total wasted tokens in session

        Returns:
            Formatted cost impact message
        """
        # Calculate optimal cost for this tool
        optimal_cost = cost.subagent_tokens + cost.orchestrator_tokens
        waste = cost.total_tokens - optimal_cost

        # Calculate compliance rate
        compliance_rate = self._calculate_compliance_rate(violation_count)

        message_parts = [
            "📊 Direct execution completed.",
            "",
            "**Cost Impact (Violation):**",
            f"- Actual cost: {cost.total_tokens:,} tokens",
            f"- If delegated: ~{optimal_cost:,} tokens",
            f"- Waste: {waste:,} tokens ({(waste / cost.total_tokens * 100):.0f}% overhead)",
            "",
            "**Session Statistics:**",
            f"- Violations: {violation_count}",
            f"- Total waste: {total_waste:,} tokens",
            f"- Delegation compliance: {compliance_rate:.0%}",
            "",
            "REFLECTION: Was this delegation worth the context cost?",
            f"The same operation via Task() would have cost ~{optimal_cost:,} tokens",
            "with full isolation of tactical details.",
        ]

        return "\n".join(message_parts)

    def _calculate_compliance_rate(self, violation_count: int) -> float:
        """
        Calculate delegation compliance rate.

        Args:
            violation_count: Number of violations

        Returns:
            Compliance rate from 0.0 to 1.0
        """
        # For simplicity: (max_violations - actual) / max_violations
        # where max_violations = 5 (violation rate saturates)
        max_violations = 5
        return max(0.0, 1.0 - (violation_count / max_violations))

    def get_session_summary(self) -> dict[str, Any]:
        """
        Get session summary for Stop hook.

        Returns:
            Summary dict with metrics
        """
        violations = self.tracker.get_session_violations()

        return {
            "total_violations": violations.total_violations,
            "violations_by_type": {
                str(k): v for k, v in violations.violations_by_type.items()
            },
            "total_waste_tokens": violations.total_waste_tokens,
            "circuit_breaker_triggered": violations.circuit_breaker_triggered,
            "compliance_rate": violations.compliance_rate,
        }
