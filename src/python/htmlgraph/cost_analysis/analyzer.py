"""
CostAnalyzer for HtmlGraph - Token cost tracking from HtmlGraph events.

Reads HtmlGraph events from .htmlgraph/ directories and calculates costs
based on token usage and standard Claude pricing models.

Design:
- Reads spike HTML files and session event files
- Extracts token usage from event metadata
- Calculates costs per event using standard Claude pricing
- Groups costs by: subagent_type, tool_name, event_type
- Calculates aggregates: total cost, cost per delegation, cost per spike
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Standard Claude pricing (tokens per 1M tokens)
CLAUDE_PRICING: dict[str, dict[str, float]] = {
    "claude-3.5-sonnet": {"input": 3.0, "output": 15.0},  # $3/$15 per 1M
    "claude-3-opus": {"input": 15.0, "output": 75.0},  # $15/$75 per 1M
    "claude-3-haiku": {"input": 0.25, "output": 1.25},  # $0.25/$1.25 per 1M
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},  # $3/$15 per 1M (alias)
}

# Default model if not specified
DEFAULT_MODEL = "claude-3.5-sonnet"


@dataclass
class TokenCostBreakdown:
    """Token cost breakdown for an event."""

    event_id: str
    event_type: str
    timestamp: str
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    model: str = DEFAULT_MODEL
    subagent_type: str | None = None
    tool_name: str | None = None
    success: bool = True
    notes: str = ""


@dataclass
class CostAnalyzerResult:
    """Result from cost analysis."""

    total_events: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    cost_by_model: dict[str, float] = field(default_factory=dict)
    cost_by_subagent: dict[str, float] = field(default_factory=dict)
    cost_by_tool: dict[str, float] = field(default_factory=dict)
    cost_by_event_type: dict[str, float] = field(default_factory=dict)
    event_breakdowns: list[TokenCostBreakdown] = field(default_factory=list)
    direct_execution_cost: float = 0.0
    estimated_savings: float = 0.0


class CostAnalyzer:
    """Analyze token costs from HtmlGraph events."""

    def __init__(self, htmlgraph_dir: Path | None = None) -> None:
        """
        Initialize CostAnalyzer.

        Args:
            htmlgraph_dir: Path to .htmlgraph directory. Defaults to ./.htmlgraph
        """
        if htmlgraph_dir is None:
            htmlgraph_dir = Path.cwd() / ".htmlgraph"
        self.htmlgraph_dir = Path(htmlgraph_dir)
        self.events: list[dict[str, Any]] = []
        self.spike_data: dict[str, dict[str, Any]] = {}
        self.result = CostAnalyzerResult()

    def analyze_events(self) -> CostAnalyzerResult:
        """
        Analyze events and return cost breakdown.

        Returns:
            CostAnalyzerResult with complete cost analysis
        """
        self.result = CostAnalyzerResult()

        # Load all events
        self._load_events()

        if not self.events:
            logger.warning("No events found in .htmlgraph directory")
            return self.result

        # Process each event
        cost_breakdowns: list[TokenCostBreakdown] = []

        for event in self.events:
            breakdown = self._calculate_event_cost(event)
            if breakdown:
                cost_breakdowns.append(breakdown)

        # Update result with event data
        self.result.event_breakdowns = cost_breakdowns
        self.result.total_events = len(cost_breakdowns)

        # Aggregate costs
        self._aggregate_costs(cost_breakdowns)

        # Calculate savings
        self.result.estimated_savings = max(
            0, self.result.direct_execution_cost - self.result.total_cost
        )

        return self.result

    def _load_events(self) -> None:
        """Load all events from .htmlgraph/events and .htmlgraph/spikes directories."""
        self.events = []

        # Load from events directory (JSONL files)
        events_dir = self.htmlgraph_dir / "events"
        if events_dir.exists():
            for jsonl_file in events_dir.glob("*.jsonl"):
                try:
                    with open(jsonl_file) as f:
                        for line in f:
                            if line.strip():
                                try:
                                    event = json.loads(line)
                                    self.events.append(event)
                                except json.JSONDecodeError as e:
                                    logger.warning(
                                        f"Failed to parse JSON line in {jsonl_file}: {e}"
                                    )
                except OSError as e:
                    logger.warning(f"Failed to read {jsonl_file}: {e}")

        logger.info(f"Loaded {len(self.events)} events from .htmlgraph/events")

    def _calculate_event_cost(self, event: dict[str, Any]) -> TokenCostBreakdown | None:
        """
        Calculate cost for a single event.

        Args:
            event: Event dictionary

        Returns:
            TokenCostBreakdown or None if no token info
        """
        event_id = event.get("event_id", "unknown")
        event_type = event.get("tool", "unknown")
        timestamp = event.get("timestamp", "")
        success = event.get("success", True)

        # Extract token counts from various possible locations
        input_tokens = self._extract_tokens(event, "input")
        output_tokens = self._extract_tokens(event, "output")

        # If no explicit token counts, estimate from text length
        if input_tokens == 0 and output_tokens == 0:
            input_tokens, output_tokens = self._estimate_tokens_from_event(event)

        # Determine model
        model = event.get("model", DEFAULT_MODEL)
        if not self._is_valid_model(model):
            model = DEFAULT_MODEL

        # Get subagent type if available
        subagent_type = event.get("subagent_type")

        # Get tool name
        tool_name = event.get("tool")

        # Calculate cost
        pricing = CLAUDE_PRICING.get(model) or CLAUDE_PRICING[DEFAULT_MODEL]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        breakdown = TokenCostBreakdown(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            model=model,
            subagent_type=subagent_type,
            tool_name=tool_name,
            success=success,
        )

        return breakdown

    def _extract_tokens(self, event: dict[str, Any], token_type: str) -> int:
        """
        Extract token counts from event.

        Args:
            event: Event dictionary
            token_type: "input" or "output"

        Returns:
            Token count or 0 if not found
        """
        # Check direct fields
        if f"{token_type}_tokens" in event:
            try:
                return int(event[f"{token_type}_tokens"])
            except (ValueError, TypeError):
                pass

        # Check metadata
        if "metadata" in event:
            meta = event["metadata"]
            if isinstance(meta, dict):
                if f"{token_type}_tokens" in meta:
                    try:
                        return int(meta[f"{token_type}_tokens"])
                    except (ValueError, TypeError):
                        pass

        # Check payload
        if "payload" in event:
            payload = event["payload"]
            if isinstance(payload, dict):
                if f"{token_type}_tokens" in payload:
                    try:
                        return int(payload[f"{token_type}_tokens"])
                    except (ValueError, TypeError):
                        pass

        return 0

    def _estimate_tokens_from_event(self, event: dict[str, Any]) -> tuple[int, int]:
        """
        Estimate tokens from event text content.

        Rough estimate: ~4 characters = 1 token (conservative)

        Args:
            event: Event dictionary

        Returns:
            Tuple of (input_tokens, output_tokens) estimates
        """
        input_estimate = 0
        output_estimate = 0

        # Estimate from summary
        summary = event.get("summary", "")
        if summary:
            input_estimate += len(summary) // 4

        # Estimate from findings or results
        for field_name in ["findings", "result", "output", "response", "payload"]:
            if field_name in event:
                content = event[field_name]
                if isinstance(content, str):
                    output_estimate += len(content) // 4
                elif isinstance(content, dict):
                    # Rough estimate for dict size
                    output_estimate += len(json.dumps(content)) // 4

        return input_estimate, output_estimate

    def _is_valid_model(self, model: str) -> bool:
        """Check if model is in pricing table."""
        return model in CLAUDE_PRICING

    def _aggregate_costs(self, breakdowns: list[TokenCostBreakdown]) -> None:
        """Aggregate costs by various dimensions."""
        cost_by_model: dict[str, float] = defaultdict(float)
        cost_by_subagent: dict[str, float] = defaultdict(float)
        cost_by_tool: dict[str, float] = defaultdict(float)
        cost_by_event_type: dict[str, float] = defaultdict(float)

        total_input = 0
        total_output = 0
        total_cost = 0.0

        for breakdown in breakdowns:
            # Aggregate by model
            cost_by_model[breakdown.model] += breakdown.total_cost

            # Aggregate by subagent
            if breakdown.subagent_type:
                cost_by_subagent[breakdown.subagent_type] += breakdown.total_cost

            # Aggregate by tool
            if breakdown.tool_name:
                cost_by_tool[breakdown.tool_name] += breakdown.total_cost

            # Aggregate by event type
            cost_by_event_type[breakdown.event_type] += breakdown.total_cost

            # Totals
            total_input += breakdown.input_tokens
            total_output += breakdown.output_tokens
            total_cost += breakdown.total_cost

        self.result.cost_by_model = dict(cost_by_model)
        self.result.cost_by_subagent = dict(cost_by_subagent)
        self.result.cost_by_tool = dict(cost_by_tool)
        self.result.cost_by_event_type = dict(cost_by_event_type)
        self.result.total_input_tokens = total_input
        self.result.total_output_tokens = total_output
        self.result.total_cost = total_cost

        # Estimate direct execution cost (assume 50% more without delegation)
        self.result.direct_execution_cost = total_cost * 1.5

    def get_cost_by_subagent(self) -> dict[str, float]:
        """
        Get total cost grouped by subagent type.

        Returns:
            Dictionary mapping subagent_type to total cost
        """
        return self.result.cost_by_subagent

    def get_cost_by_tool(self) -> dict[str, float]:
        """
        Get total cost grouped by tool name.

        Returns:
            Dictionary mapping tool_name to total cost
        """
        return self.result.cost_by_tool

    def get_delegation_costs(self) -> list[dict[str, Any]]:
        """
        Get cost breakdown per delegation.

        Returns:
            List of dicts with delegation costs
        """
        delegations: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
            }
        )

        for breakdown in self.result.event_breakdowns:
            if breakdown.subagent_type:
                key = breakdown.subagent_type
                delegations[key]["count"] += 1
                delegations[key]["total_cost"] += breakdown.total_cost
                delegations[key]["input_tokens"] += breakdown.input_tokens
                delegations[key]["output_tokens"] += breakdown.output_tokens

        # Convert to list and calculate averages
        result = []
        for subagent_type, data in delegations.items():
            result.append(
                {
                    "subagent_type": subagent_type,
                    "count": data["count"],
                    "total_cost": round(data["total_cost"], 4),
                    "average_cost": round(data["total_cost"] / data["count"], 4),
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                }
            )

        return sorted(result, key=lambda x: x["total_cost"], reverse=True)

    def estimate_direct_execution_cost(self, delegation_cost: float) -> float:
        """
        Estimate what cost would be without delegation optimization.

        Args:
            delegation_cost: Cost with delegations

        Returns:
            Estimated cost with direct execution (roughly 50% more)
        """
        return delegation_cost * 1.5

    def get_cost_summary(self) -> dict[str, Any]:
        """
        Get a summary of all costs.

        Returns:
            Dictionary with cost summary
        """
        return {
            "total_events": self.result.total_events,
            "total_input_tokens": self.result.total_input_tokens,
            "total_output_tokens": self.result.total_output_tokens,
            "total_cost": round(self.result.total_cost, 4),
            "direct_execution_cost_estimate": round(
                self.result.direct_execution_cost, 4
            ),
            "estimated_savings": round(self.result.estimated_savings, 4),
            "cost_by_model": {
                k: round(v, 4) for k, v in self.result.cost_by_model.items()
            },
            "cost_by_subagent": {
                k: round(v, 4) for k, v in self.result.cost_by_subagent.items()
            },
            "cost_by_tool": {
                k: round(v, 4) for k, v in self.result.cost_by_tool.items()
            },
            "cost_by_event_type": {
                k: round(v, 4) for k, v in self.result.cost_by_event_type.items()
            },
            "delegation_costs": self.get_delegation_costs(),
        }

    def export_to_json(self, output_path: Path) -> None:
        """
        Export cost analysis to JSON file.

        Args:
            output_path: Path to write JSON file
        """
        summary = self.get_cost_summary()
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Exported cost analysis to {output_path}")
