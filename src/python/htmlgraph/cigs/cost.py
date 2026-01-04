"""
CostCalculator for CIGS (Computational Imperative Guidance System).

Provides token cost prediction and actual cost tracking for tool operations.
Implements cost estimation heuristics based on tool type and operation complexity.

Design Reference:
- CIGS Design Doc: .htmlgraph/spikes/computational-imperative-guidance-system-design.md
- Part 5.2: Cost Efficiency Score
- Part 5.3: Cost estimation rules
"""

from .models import (
    CostMetrics,
    OperationClassification,
    TokenCost,
)


class CostCalculator:
    """Calculate token costs for tool operations and delegations."""

    # Cost estimation heuristics (tokens per operation)
    # Based on typical token consumption patterns
    COST_ESTIMATES = {
        "Read": 5000,  # Per file read
        "Grep": 3000,  # Per search result batch
        "Glob": 2000,  # Per glob pattern
        "Edit": 4000,  # Per edit operation
        "Write": 4000,  # Per write operation
        "NotebookEdit": 4500,  # Notebook cells are complex
        "Delete": 2000,  # File deletion
        "Bash": {  # Variable based on command type
            "default": 2000,
            "git": 1500,
            "pytest": 5000,
            "npm": 5000,
        },
        "Task": 500,  # Orchestrator Task call (minimal context)
        "AskUserQuestion": 1000,  # User interaction
        "TodoWrite": 500,  # Tracking operations
    }

    # Subagent delegation costs (optimal path)
    SUBAGENT_COSTS = {
        "spawn_gemini": 500,  # Explorer subagent cost
        "spawn_codex": 800,  # Coder subagent cost
        "spawn_copilot": 600,  # Git subagent cost
        "Task": 500,  # Orchestrator Task
    }

    def __init__(self) -> None:
        """Initialize CostCalculator."""
        self.tool_history: list[str] = []  # Track recent tool usage for patterns

    def predict_cost(self, tool: str, params: dict) -> int:
        """
        Predict token cost for direct tool execution.

        Args:
            tool: Tool name (Read, Grep, Bash, etc.)
            params: Tool parameters

        Returns:
            Estimated token cost
        """
        if tool not in self.COST_ESTIMATES:
            return 2000  # Default estimate for unknown tools

        estimate = self.COST_ESTIMATES[tool]

        # Handle variable estimates
        if isinstance(estimate, dict):
            return self._estimate_variable_cost(tool, params, estimate)

        # Apply modifiers based on operation complexity
        assert isinstance(estimate, int)
        return self._apply_complexity_modifiers(tool, params, estimate)

    def _estimate_variable_cost(
        self, tool: str, params: dict, estimates: dict[str, int]
    ) -> int:
        """Estimate cost for tools with variable pricing."""
        if tool == "Bash":
            command = params.get("command", "")

            # Git operations
            if any(cmd in command for cmd in ["git add", "git commit", "git push"]):
                return int(estimates.get("git", estimates.get("default", 2000)))

            # Test operations
            if any(cmd in command for cmd in ["pytest", "uv run pytest"]):
                return int(estimates.get("pytest", estimates.get("default", 5000)))

            if "npm test" in command or "yarn test" in command:
                return int(estimates.get("npm", estimates.get("default", 5000)))

            # Default bash
            return int(estimates.get("default", 2000))

        return int(estimates.get("default", 2000))

    def _apply_complexity_modifiers(
        self, tool: str, params: dict, base_cost: int | dict[str, int]
    ) -> int:
        """Apply complexity modifiers to base cost estimate."""
        # Handle dict base_cost (shouldn't happen but for safety)
        if isinstance(base_cost, dict):
            base_cost = base_cost.get("default", 2000)

        modified_cost: float = float(base_cost)

        if tool == "Read":
            # Multiple files increase cost
            if isinstance(params.get("file_path"), list):
                modified_cost = base_cost * len(params["file_path"])
            # Large offset/limits indicate large reads
            elif params.get("limit", 2000) > 5000:
                modified_cost = base_cost * 2

        elif tool == "Grep":
            # Complex regex patterns increase cost
            pattern = params.get("pattern", "")
            if len(pattern) > 100:  # Complex pattern
                modified_cost = base_cost * 1.5
            # Multiline matching is more expensive
            if params.get("multiline", False):
                modified_cost = base_cost * 1.3

        elif tool in ["Edit", "Write"]:
            # Multiple edits or large content
            if isinstance(params.get("file_path"), list):
                modified_cost = base_cost * len(params["file_path"])
            # Large content increases cost
            content = params.get("content", params.get("new_string", ""))
            if len(content) > 10000:
                modified_cost = base_cost * 1.5

        return int(modified_cost)

    def optimal_cost(self, classification: OperationClassification) -> int:
        """
        Calculate optimal cost with proper delegation.

        Args:
            classification: OperationClassification with tool and category info

        Returns:
            Estimated token cost with optimal delegation strategy
        """
        tool = classification.tool

        # Orchestrator tools already optimal
        if tool in ["Task", "AskUserQuestion", "TodoWrite"]:
            estimate = self.COST_ESTIMATES.get(tool, 500)
            return int(estimate) if isinstance(estimate, int) else 500

        # Map to subagent based on category
        if classification.category == "exploration":
            return int(self.SUBAGENT_COSTS["spawn_gemini"])
        elif classification.category == "implementation":
            return int(self.SUBAGENT_COSTS["spawn_codex"])
        elif classification.category == "git":
            return int(self.SUBAGENT_COSTS["spawn_copilot"])
        elif classification.category == "testing":
            return int(self.SUBAGENT_COSTS["Task"])

        # Default to Task for unknown categories
        return int(self.SUBAGENT_COSTS["Task"])

    def calculate_actual_cost(self, tool: str, result: dict) -> TokenCost:
        """
        Calculate actual cost after tool execution.

        Args:
            tool: Tool that was executed
            result: Result dictionary from tool execution

        Returns:
            TokenCost with actual metrics
        """
        # Get predicted cost for this tool
        predicted_tokens = self._extract_predicted_cost(tool, result)

        # Extract actual cost if available in result
        actual_tokens = self._extract_actual_cost(tool, result)

        # If no actual cost in result, use predicted
        if actual_tokens is None:
            actual_tokens = predicted_tokens

        # Determine subagent cost based on tool type
        subagent_tokens = self._get_subagent_cost(tool)

        # Calculate orchestrator overhead
        orchestrator_tokens = self._estimate_orchestrator_overhead(tool, result)

        # Calculate savings
        estimated_savings = max(
            0, actual_tokens - subagent_tokens - orchestrator_tokens
        )

        return TokenCost(
            total_tokens=actual_tokens,
            orchestrator_tokens=orchestrator_tokens,
            subagent_tokens=subagent_tokens,
            estimated_savings=estimated_savings,
        )

    def _extract_predicted_cost(self, tool: str, result: dict) -> int:
        """Extract or estimate predicted cost from result."""
        # Check if result contains cost metadata
        if "predicted_cost" in result:
            return int(result["predicted_cost"])

        if "metadata" in result and "predicted_cost" in result["metadata"]:
            return int(result["metadata"]["predicted_cost"])

        # Fall back to default estimate
        estimate = self.COST_ESTIMATES.get(tool, 2000)
        return int(estimate) if isinstance(estimate, int) else 2000

    def _extract_actual_cost(self, tool: str, result: dict) -> int | None:
        """Extract actual cost from execution result if available."""
        # Check standard cost fields
        if "actual_cost" in result:
            return int(result["actual_cost"])

        if "cost" in result:
            return int(result["cost"])

        if "metadata" in result and "cost" in result["metadata"]:
            return int(result["metadata"]["cost"])

        if "tokens" in result:
            return int(result["tokens"])

        # Try to estimate from output size for Read operations
        if tool == "Read" and "output" in result:
            output = result["output"]
            if isinstance(output, str):
                # Rough estimate: ~4 tokens per line
                lines = len(output.split("\n"))
                return int(lines * 4)

        return None

    def _get_subagent_cost(self, tool: str) -> int:
        """Get cost if this operation were delegated to subagent."""
        if tool in ["Task", "AskUserQuestion", "TodoWrite"]:
            return 0  # Already delegated

        if tool in ["Read", "Grep", "Glob"]:
            return self.SUBAGENT_COSTS["spawn_gemini"]

        if tool in ["Edit", "Write", "NotebookEdit", "Delete"]:
            return self.SUBAGENT_COSTS["spawn_codex"]

        if tool == "Bash":
            # Might be git or test - estimate higher
            return self.SUBAGENT_COSTS["spawn_copilot"]  # or Task

        # Default
        return self.SUBAGENT_COSTS["Task"]

    def _estimate_orchestrator_overhead(self, tool: str, result: dict) -> int:
        """Estimate orchestrator context overhead."""
        # Orchestrator overhead is minimal for delegated operations
        if tool in ["Task", "AskUserQuestion"]:
            return 200  # Small overhead for delegation call

        # Direct execution contributes full cost to orchestrator context
        if tool == "Read":
            # Context cost is proportional to file size
            if "output" in result:
                output = result["output"]
                if isinstance(output, str):
                    # ~4 tokens per line
                    return int(len(output.split("\n")) * 4)
            return 5000

        # Other tools
        return 1000  # Placeholder for other tools

    def calculate_waste(self, actual_cost: int, optimal_cost: int) -> dict:
        """
        Calculate waste metrics comparing actual vs optimal cost.

        Args:
            actual_cost: Actual tokens consumed
            optimal_cost: Tokens with optimal delegation

        Returns:
            Dictionary with waste metrics
        """
        waste_tokens = max(0, actual_cost - optimal_cost)

        if actual_cost == 0:
            waste_percentage = 0.0
            efficiency_score = 100.0
        else:
            waste_percentage = (waste_tokens / actual_cost) * 100
            efficiency_score = (optimal_cost / actual_cost) * 100

        return {
            "waste_tokens": waste_tokens,
            "waste_percentage": waste_percentage,
            "efficiency_score": efficiency_score,
        }

    def aggregate_session_costs(
        self,
        operations: list[tuple[str, dict, dict]],
        violations_count: int = 0,
    ) -> CostMetrics:
        """
        Aggregate cost metrics for a session.

        Args:
            operations: List of (tool, params, result) tuples
            violations_count: Number of violations in session

        Returns:
            CostMetrics with aggregated session costs
        """
        total_tokens = 0
        optimal_tokens = 0
        orchestrator_tokens = 0
        subagent_tokens = 0

        for tool, params, result in operations:
            # Predict cost
            predicted = self.predict_cost(tool, params)
            total_tokens += predicted

            # Calculate actual if available
            cost_record = self.calculate_actual_cost(tool, result)
            total_tokens = max(total_tokens, cost_record.total_tokens)

            # Accumulate subagent costs
            subagent_tokens += cost_record.subagent_tokens
            orchestrator_tokens += cost_record.orchestrator_tokens

            # Accumulate optimal costs
            # For delegated operations, optimal = subagent cost
            # For direct operations that should be delegated, optimal = subagent cost
            if tool in ["Task", "AskUserQuestion"]:
                estimate = self.COST_ESTIMATES.get(tool, 500)
                optimal_tokens += int(estimate) if isinstance(estimate, int) else 500
            else:
                optimal_tokens += self._get_subagent_cost(tool)

        waste_tokens = max(0, total_tokens - optimal_tokens)

        metrics = CostMetrics(
            total_tokens=total_tokens,
            optimal_tokens=optimal_tokens,
            orchestrator_tokens=orchestrator_tokens,
            subagent_tokens=subagent_tokens,
            waste_tokens=waste_tokens,
        )

        return metrics

    def classify_operation(
        self,
        tool: str,
        params: dict,
        is_exploration_sequence: bool = False,
        tool_history: list[str] | None = None,
    ) -> OperationClassification:
        """
        Classify a tool operation for cost and delegation analysis.

        Args:
            tool: Tool name
            params: Tool parameters
            is_exploration_sequence: Whether this is part of exploration sequence
            tool_history: Recent tool usage history

        Returns:
            OperationClassification with cost and delegation info
        """
        # Categorize tool
        category = self._categorize_tool(tool)

        # Determine if delegation is recommended
        should_delegate = self._should_delegate(tool, is_exploration_sequence)

        # Get delegation suggestion
        suggestion = self._get_delegation_suggestion(tool, category)

        # Predict costs
        predicted_cost = self.predict_cost(tool, params)

        # Calculate optimal cost for this category
        dummy_classification = OperationClassification(
            tool=tool,
            category="",  # Will be set below
            should_delegate=should_delegate,
            reason="",
            predicted_cost=predicted_cost,
            optimal_cost=0,
            is_exploration_sequence=is_exploration_sequence,
            suggested_delegation=suggestion,
        )

        optimal_cost = self.optimal_cost(dummy_classification)

        # Calculate waste percentage
        waste_tokens = max(0, predicted_cost - optimal_cost)
        waste_pct = (waste_tokens / predicted_cost * 100) if predicted_cost > 0 else 0.0

        return OperationClassification(
            tool=tool,
            category=category,
            should_delegate=should_delegate,
            reason=self._get_delegation_reason(tool, category, is_exploration_sequence),
            predicted_cost=predicted_cost,
            optimal_cost=optimal_cost,
            is_exploration_sequence=is_exploration_sequence,
            suggested_delegation=suggestion,
            waste_percentage=waste_pct,
        )

    def _categorize_tool(self, tool: str) -> str:
        """Categorize tool into operational type."""
        if tool in ["Read", "Grep", "Glob"]:
            return "exploration"
        elif tool in ["Edit", "Write", "NotebookEdit", "Delete"]:
            return "implementation"
        elif tool in ["Task", "AskUserQuestion", "TodoWrite"]:
            return "orchestration"
        elif tool == "Bash":
            return "execution"
        else:
            return "unknown"

    def _should_delegate(self, tool: str, is_sequence: bool) -> bool:
        """Determine if operation should be delegated."""
        # Orchestrator tools are already delegated
        if tool in ["Task", "AskUserQuestion", "TodoWrite"]:
            return False

        # Exploration sequences should be delegated
        if is_sequence and tool in ["Read", "Grep", "Glob"]:
            return True

        # Single direct operations are allowed but not recommended
        # CIGS messaging will recommend delegation
        return False

    def _get_delegation_suggestion(self, tool: str, category: str) -> str:
        """Get suggested delegation for this tool."""
        suggestions = {
            "exploration": "spawn_gemini(prompt='Search and analyze codebase')",
            "implementation": "spawn_codex(prompt='Implement with full testing')",
            "execution": "Task(prompt='Execute and report results')",
            "testing": "Task(prompt='Run tests and report')",
        }
        return suggestions.get(category, "Task(prompt='Delegate this operation')")

    def _get_delegation_reason(
        self, tool: str, category: str, is_sequence: bool
    ) -> str:
        """Get reason for delegation recommendation."""
        if is_sequence:
            return f"Multiple {category} operations detected (research work should be delegated)"

        reasons = {
            "exploration": "Exploration operations have unpredictable scope",
            "implementation": "Implementation requires iteration and testing",
            "execution": "Consider delegating execution for better isolation",
        }
        return reasons.get(category, "Delegation preserves your strategic context")
