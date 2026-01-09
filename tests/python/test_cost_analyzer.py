"""
Unit tests for CostAnalyzer.

Tests cover:
- Cost calculation accuracy
- Cost grouping by subagent_type
- Aggregation functions
- Edge cases (missing data, unknown models)
"""

import json

from htmlgraph.cost_analysis import CostAnalyzer


class TestCostAnalyzerInitialization:
    """Test CostAnalyzer initialization."""

    def test_init_default_directory(self, tmp_path):
        """Test initialization with default directory."""
        analyzer = CostAnalyzer()
        assert analyzer.htmlgraph_dir.name == ".htmlgraph"

    def test_init_custom_directory(self, tmp_path):
        """Test initialization with custom directory."""
        custom_dir = tmp_path / "custom_htmlgraph"
        custom_dir.mkdir()
        analyzer = CostAnalyzer(custom_dir)
        assert analyzer.htmlgraph_dir == custom_dir

    def test_result_initialized_empty(self):
        """Test that result is initialized empty."""
        analyzer = CostAnalyzer()
        assert analyzer.result.total_events == 0
        assert analyzer.result.total_cost == 0.0


class TestTokenCostCalculation:
    """Test token cost calculations."""

    def setup_method(self):
        """Set up analyzer for each test."""
        self.analyzer = CostAnalyzer()

    def test_calculate_cost_with_explicit_tokens(self):
        """Test cost calculation with explicit token counts."""
        event = {
            "event_id": "evt-test-001",
            "tool": "Task",
            "timestamp": "2026-01-08T00:00:00",
            "input_tokens": 1000,
            "output_tokens": 500,
            "model": "claude-3.5-sonnet",
        }

        breakdown = self.analyzer._calculate_event_cost(event)
        assert breakdown is not None
        assert breakdown.input_tokens == 1000
        assert breakdown.output_tokens == 500

        # Verify pricing: 1000 * 3/1M + 500 * 15/1M
        expected_cost = (1000 * 3 + 500 * 15) / 1_000_000
        assert abs(breakdown.total_cost - expected_cost) < 0.0001

    def test_calculate_cost_different_models(self):
        """Test cost calculation for different Claude models."""
        models_and_expected = [
            ("claude-3.5-sonnet", (1000 * 3 + 500 * 15) / 1_000_000),
            ("claude-3-opus", (1000 * 15 + 500 * 75) / 1_000_000),
            ("claude-3-haiku", (1000 * 0.25 + 500 * 1.25) / 1_000_000),
        ]

        for model, expected_cost in models_and_expected:
            event = {
                "event_id": f"evt-{model}",
                "tool": "Read",
                "timestamp": "2026-01-08T00:00:00",
                "input_tokens": 1000,
                "output_tokens": 500,
                "model": model,
            }

            breakdown = self.analyzer._calculate_event_cost(event)
            assert breakdown is not None
            assert abs(breakdown.total_cost - expected_cost) < 0.0001
            assert breakdown.model == model

    def test_calculate_cost_unknown_model_defaults_to_sonnet(self):
        """Test that unknown models default to claude-3.5-sonnet."""
        event = {
            "event_id": "evt-unknown-model",
            "tool": "Read",
            "timestamp": "2026-01-08T00:00:00",
            "input_tokens": 1000,
            "output_tokens": 500,
            "model": "unknown-model-xyz",
        }

        breakdown = self.analyzer._calculate_event_cost(event)
        assert breakdown is not None
        assert breakdown.model == "claude-3.5-sonnet"

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        event = {
            "event_id": "evt-zero",
            "tool": "TodoWrite",
            "timestamp": "2026-01-08T00:00:00",
            "input_tokens": 0,
            "output_tokens": 0,
        }

        breakdown = self.analyzer._calculate_event_cost(event)
        assert breakdown is not None
        assert breakdown.total_cost == 0.0

    def test_extract_tokens_from_event_field(self):
        """Test extracting tokens from event field."""
        event = {
            "input_tokens": 1000,
            "output_tokens": 500,
        }

        input_tokens = self.analyzer._extract_tokens(event, "input")
        output_tokens = self.analyzer._extract_tokens(event, "output")

        assert input_tokens == 1000
        assert output_tokens == 500

    def test_extract_tokens_from_metadata(self):
        """Test extracting tokens from metadata."""
        event = {
            "metadata": {
                "input_tokens": 2000,
                "output_tokens": 1000,
            }
        }

        input_tokens = self.analyzer._extract_tokens(event, "input")
        output_tokens = self.analyzer._extract_tokens(event, "output")

        assert input_tokens == 2000
        assert output_tokens == 1000

    def test_extract_tokens_from_payload(self):
        """Test extracting tokens from payload."""
        event = {
            "payload": {
                "input_tokens": 3000,
                "output_tokens": 1500,
            }
        }

        input_tokens = self.analyzer._extract_tokens(event, "input")
        output_tokens = self.analyzer._extract_tokens(event, "output")

        assert input_tokens == 3000
        assert output_tokens == 1500

    def test_extract_tokens_missing_returns_zero(self):
        """Test that missing tokens return 0."""
        event = {"tool": "Read", "timestamp": "2026-01-08T00:00:00"}

        input_tokens = self.analyzer._extract_tokens(event, "input")
        output_tokens = self.analyzer._extract_tokens(event, "output")

        assert input_tokens == 0
        assert output_tokens == 0


class TestTokenEstimation:
    """Test token estimation from text content."""

    def setup_method(self):
        """Set up analyzer for each test."""
        self.analyzer = CostAnalyzer()

    def test_estimate_tokens_from_summary(self):
        """Test token estimation from summary field."""
        event = {
            "summary": "x" * 400,  # 400 chars = ~100 tokens
        }

        input_est, output_est = self.analyzer._estimate_tokens_from_event(event)
        assert input_est == 100  # 400 / 4

    def test_estimate_tokens_from_findings(self):
        """Test token estimation from findings field."""
        event = {
            "findings": "x" * 400,  # 400 chars = ~100 tokens
        }

        input_est, output_est = self.analyzer._estimate_tokens_from_event(event)
        assert output_est == 100

    def test_estimate_tokens_from_payload_dict(self):
        """Test token estimation from payload dict."""
        event = {
            "payload": {
                "data": "x" * 400,
            }
        }

        input_est, output_est = self.analyzer._estimate_tokens_from_event(event)
        # Should estimate output from payload json size
        assert output_est > 0

    def test_estimate_tokens_empty_event(self):
        """Test token estimation with empty event."""
        event = {}

        input_est, output_est = self.analyzer._estimate_tokens_from_event(event)
        assert input_est == 0
        assert output_est == 0


class TestCostAggregation:
    """Test cost aggregation by different dimensions."""

    def setup_method(self):
        """Set up analyzer for each test."""
        self.analyzer = CostAnalyzer()

    def create_test_breakdown(
        self,
        event_id: str,
        tool: str = "Read",
        subagent_type: str = None,
        input_tokens: int = 1000,
        output_tokens: int = 500,
    ):
        """Create a test TokenCostBreakdown."""
        event = {
            "event_id": event_id,
            "tool": tool,
            "timestamp": "2026-01-08T00:00:00",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "subagent_type": subagent_type,
        }
        return self.analyzer._calculate_event_cost(event)

    def test_aggregate_by_subagent(self):
        """Test cost aggregation by subagent type."""
        breakdowns = [
            self.create_test_breakdown("evt-001", subagent_type="spawn_gemini"),
            self.create_test_breakdown("evt-002", subagent_type="spawn_gemini"),
            self.create_test_breakdown("evt-003", subagent_type="spawn_codex"),
        ]

        self.analyzer._aggregate_costs(breakdowns)

        assert "spawn_gemini" in self.analyzer.result.cost_by_subagent
        assert "spawn_codex" in self.analyzer.result.cost_by_subagent

        # Two events for Gemini should have 2x cost of one event for Codex
        gemini_cost = self.analyzer.result.cost_by_subagent["spawn_gemini"]
        codex_cost = self.analyzer.result.cost_by_subagent["spawn_codex"]

        assert abs(gemini_cost - 2 * codex_cost) < 0.0001

    def test_aggregate_by_tool(self):
        """Test cost aggregation by tool name."""
        breakdowns = [
            self.create_test_breakdown("evt-001", tool="Read"),
            self.create_test_breakdown("evt-002", tool="Read"),
            self.create_test_breakdown("evt-003", tool="Write"),
        ]

        self.analyzer._aggregate_costs(breakdowns)

        assert "Read" in self.analyzer.result.cost_by_tool
        assert "Write" in self.analyzer.result.cost_by_tool

    def test_aggregate_by_event_type(self):
        """Test cost aggregation by event type."""
        breakdowns = [
            self.create_test_breakdown("evt-001", tool="Task"),
            self.create_test_breakdown("evt-002", tool="Task"),
            self.create_test_breakdown("evt-003", tool="Bash"),
        ]

        self.analyzer._aggregate_costs(breakdowns)

        assert "Task" in self.analyzer.result.cost_by_event_type
        assert "Bash" in self.analyzer.result.cost_by_event_type

    def test_aggregate_total_tokens(self):
        """Test aggregation of total tokens."""
        breakdowns = [
            self.create_test_breakdown("evt-001", input_tokens=1000, output_tokens=500),
            self.create_test_breakdown(
                "evt-002", input_tokens=2000, output_tokens=1000
            ),
        ]

        self.analyzer._aggregate_costs(breakdowns)

        assert self.analyzer.result.total_input_tokens == 3000
        assert self.analyzer.result.total_output_tokens == 1500

    def test_aggregate_total_cost(self):
        """Test aggregation of total cost."""
        breakdowns = [
            self.create_test_breakdown("evt-001", input_tokens=1000, output_tokens=500),
            self.create_test_breakdown("evt-002", input_tokens=1000, output_tokens=500),
        ]

        self.analyzer._aggregate_costs(breakdowns)

        # Each should cost (1000*3 + 500*15) / 1M = 0.0000105
        expected_total = 2 * (1000 * 3 + 500 * 15) / 1_000_000
        assert abs(self.analyzer.result.total_cost - expected_total) < 0.00001


class TestCostBySubagent:
    """Test get_cost_by_subagent method."""

    def test_cost_by_subagent_empty(self):
        """Test get_cost_by_subagent with no events."""
        analyzer = CostAnalyzer()
        analyzer.result = analyzer.result  # Ensure initialized
        costs = analyzer.get_cost_by_subagent()
        assert costs == {}

    def test_cost_by_subagent_multiple(self, tmp_path):
        """Test get_cost_by_subagent with multiple events."""
        # Create events directory
        events_dir = tmp_path / ".htmlgraph" / "events"
        events_dir.mkdir(parents=True)

        # Create test events
        events = [
            {
                "event_id": "evt-001",
                "tool": "Read",
                "timestamp": "2026-01-08T00:00:00",
                "input_tokens": 1000,
                "output_tokens": 500,
                "subagent_type": "spawn_gemini",
            },
            {
                "event_id": "evt-002",
                "tool": "Read",
                "timestamp": "2026-01-08T00:01:00",
                "input_tokens": 1000,
                "output_tokens": 500,
                "subagent_type": "spawn_gemini",
            },
            {
                "event_id": "evt-003",
                "tool": "Write",
                "timestamp": "2026-01-08T00:02:00",
                "input_tokens": 1000,
                "output_tokens": 500,
                "subagent_type": "spawn_codex",
            },
        ]

        # Write events file
        events_file = events_dir / "test.jsonl"
        with open(events_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        # Analyze
        analyzer = CostAnalyzer(tmp_path / ".htmlgraph")
        analyzer.analyze_events()

        # Check costs
        costs = analyzer.get_cost_by_subagent()
        assert "spawn_gemini" in costs
        assert "spawn_codex" in costs
        assert costs["spawn_gemini"] > costs["spawn_codex"]


class TestCostByTool:
    """Test get_cost_by_tool method."""

    def test_cost_by_tool_empty(self):
        """Test get_cost_by_tool with no events."""
        analyzer = CostAnalyzer()
        analyzer.result = analyzer.result
        costs = analyzer.get_cost_by_tool()
        assert costs == {}

    def test_cost_by_tool_multiple(self, tmp_path):
        """Test get_cost_by_tool with multiple events."""
        # Create events directory
        events_dir = tmp_path / ".htmlgraph" / "events"
        events_dir.mkdir(parents=True)

        # Create test events
        events = [
            {
                "event_id": "evt-001",
                "tool": "Read",
                "timestamp": "2026-01-08T00:00:00",
                "input_tokens": 2000,
                "output_tokens": 1000,
            },
            {
                "event_id": "evt-002",
                "tool": "Write",
                "timestamp": "2026-01-08T00:01:00",
                "input_tokens": 1000,
                "output_tokens": 500,
            },
        ]

        # Write events file
        events_file = events_dir / "test.jsonl"
        with open(events_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        # Analyze
        analyzer = CostAnalyzer(tmp_path / ".htmlgraph")
        analyzer.analyze_events()

        # Check costs
        costs = analyzer.get_cost_by_tool()
        assert "Read" in costs
        assert "Write" in costs
        assert costs["Read"] > costs["Write"]  # Read has more tokens


class TestDelegationCosts:
    """Test get_delegation_costs method."""

    def test_delegation_costs_empty(self):
        """Test get_delegation_costs with no delegations."""
        analyzer = CostAnalyzer()
        analyzer.result = analyzer.result
        costs = analyzer.get_delegation_costs()
        assert costs == []

    def test_delegation_costs_calculation(self, tmp_path):
        """Test delegation cost calculation."""
        # Create events directory
        events_dir = tmp_path / ".htmlgraph" / "events"
        events_dir.mkdir(parents=True)

        # Create test events
        events = [
            {
                "event_id": "evt-001",
                "tool": "Task",
                "timestamp": "2026-01-08T00:00:00",
                "input_tokens": 1000,
                "output_tokens": 500,
                "subagent_type": "spawn_gemini",
            },
            {
                "event_id": "evt-002",
                "tool": "Task",
                "timestamp": "2026-01-08T00:01:00",
                "input_tokens": 1000,
                "output_tokens": 500,
                "subagent_type": "spawn_gemini",
            },
        ]

        # Write events file
        events_file = events_dir / "test.jsonl"
        with open(events_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        # Analyze
        analyzer = CostAnalyzer(tmp_path / ".htmlgraph")
        analyzer.analyze_events()

        # Check delegation costs
        costs = analyzer.get_delegation_costs()
        assert len(costs) > 0
        assert costs[0]["count"] == 2  # Two events for spawn_gemini
        assert costs[0]["average_cost"] < costs[0]["total_cost"]


class TestDirectExecutionCost:
    """Test estimate_direct_execution_cost method."""

    def test_estimate_direct_execution(self):
        """Test direct execution cost estimation."""
        analyzer = CostAnalyzer()
        delegation_cost = 0.01
        estimated = analyzer.estimate_direct_execution_cost(delegation_cost)
        assert estimated == 0.015  # 50% more


class TestCostSummary:
    """Test get_cost_summary method."""

    def test_cost_summary_structure(self, tmp_path):
        """Test that cost summary has all required fields."""
        # Create events directory
        events_dir = tmp_path / ".htmlgraph" / "events"
        events_dir.mkdir(parents=True)

        # Create test event
        event = {
            "event_id": "evt-001",
            "tool": "Read",
            "timestamp": "2026-01-08T00:00:00",
            "input_tokens": 1000,
            "output_tokens": 500,
            "subagent_type": "spawn_gemini",
        }

        # Write events file
        events_file = events_dir / "test.jsonl"
        with open(events_file, "w") as f:
            f.write(json.dumps(event) + "\n")

        # Analyze
        analyzer = CostAnalyzer(tmp_path / ".htmlgraph")
        analyzer.analyze_events()

        # Check summary
        summary = analyzer.get_cost_summary()
        assert "total_events" in summary
        assert "total_input_tokens" in summary
        assert "total_output_tokens" in summary
        assert "total_cost" in summary
        assert "direct_execution_cost_estimate" in summary
        assert "estimated_savings" in summary
        assert "cost_by_model" in summary
        assert "cost_by_subagent" in summary
        assert "cost_by_tool" in summary
        assert "cost_by_event_type" in summary
        assert "delegation_costs" in summary


class TestEventLoading:
    """Test event loading from .htmlgraph directory."""

    def test_load_events_empty_directory(self, tmp_path):
        """Test loading events from empty directory."""
        events_dir = tmp_path / ".htmlgraph" / "events"
        events_dir.mkdir(parents=True)

        analyzer = CostAnalyzer(tmp_path / ".htmlgraph")
        analyzer._load_events()

        assert len(analyzer.events) == 0

    def test_load_events_single_file(self, tmp_path):
        """Test loading events from single JSONL file."""
        events_dir = tmp_path / ".htmlgraph" / "events"
        events_dir.mkdir(parents=True)

        events = [
            {"event_id": "evt-001", "tool": "Read"},
            {"event_id": "evt-002", "tool": "Write"},
        ]

        events_file = events_dir / "test.jsonl"
        with open(events_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        analyzer = CostAnalyzer(tmp_path / ".htmlgraph")
        analyzer._load_events()

        assert len(analyzer.events) == 2
        assert analyzer.events[0]["event_id"] == "evt-001"
        assert analyzer.events[1]["event_id"] == "evt-002"

    def test_load_events_multiple_files(self, tmp_path):
        """Test loading events from multiple JSONL files."""
        events_dir = tmp_path / ".htmlgraph" / "events"
        events_dir.mkdir(parents=True)

        # Create first file
        file1 = events_dir / "events1.jsonl"
        with open(file1, "w") as f:
            f.write(json.dumps({"event_id": "evt-001", "tool": "Read"}) + "\n")
            f.write(json.dumps({"event_id": "evt-002", "tool": "Write"}) + "\n")

        # Create second file
        file2 = events_dir / "events2.jsonl"
        with open(file2, "w") as f:
            f.write(json.dumps({"event_id": "evt-003", "tool": "Task"}) + "\n")

        analyzer = CostAnalyzer(tmp_path / ".htmlgraph")
        analyzer._load_events()

        assert len(analyzer.events) == 3

    def test_load_events_invalid_json(self, tmp_path):
        """Test loading events with invalid JSON lines."""
        events_dir = tmp_path / ".htmlgraph" / "events"
        events_dir.mkdir(parents=True)

        events_file = events_dir / "test.jsonl"
        with open(events_file, "w") as f:
            f.write(json.dumps({"event_id": "evt-001"}) + "\n")
            f.write("invalid json line\n")
            f.write(json.dumps({"event_id": "evt-002"}) + "\n")

        analyzer = CostAnalyzer(tmp_path / ".htmlgraph")
        analyzer._load_events()

        # Should load 2 valid events and skip invalid one
        assert len(analyzer.events) == 2


class TestAnalyzeEvents:
    """Test full analyze_events workflow."""

    def test_analyze_events_complete_flow(self, tmp_path):
        """Test complete event analysis flow."""
        events_dir = tmp_path / ".htmlgraph" / "events"
        events_dir.mkdir(parents=True)

        # Create test events with various characteristics
        events = [
            {
                "event_id": "evt-001",
                "tool": "Read",
                "timestamp": "2026-01-08T00:00:00",
                "input_tokens": 2000,
                "output_tokens": 1000,
                "model": "claude-3.5-sonnet",
                "subagent_type": "spawn_gemini",
                "success": True,
            },
            {
                "event_id": "evt-002",
                "tool": "Write",
                "timestamp": "2026-01-08T00:01:00",
                "input_tokens": 1500,
                "output_tokens": 750,
                "model": "claude-3.5-sonnet",
                "subagent_type": "spawn_codex",
                "success": True,
            },
            {
                "event_id": "evt-003",
                "tool": "Task",
                "timestamp": "2026-01-08T00:02:00",
                "input_tokens": 1000,
                "output_tokens": 500,
                "model": "claude-3-haiku",
                "success": True,
            },
        ]

        # Write events
        events_file = events_dir / "test.jsonl"
        with open(events_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        # Analyze
        analyzer = CostAnalyzer(tmp_path / ".htmlgraph")
        result = analyzer.analyze_events()

        # Verify results
        assert result.total_events == 3
        assert result.total_input_tokens == 4500  # 2000 + 1500 + 1000
        assert result.total_output_tokens == 2250  # 1000 + 750 + 500
        assert result.total_cost > 0
        assert len(result.cost_by_model) > 0
        assert len(result.cost_by_subagent) > 0
        assert len(result.cost_by_tool) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_event_fields(self):
        """Test handling of events with missing fields."""
        analyzer = CostAnalyzer()
        event = {
            # Minimal event, missing most fields
            "event_id": "evt-minimal",
        }

        breakdown = analyzer._calculate_event_cost(event)
        assert breakdown is not None
        assert breakdown.event_id == "evt-minimal"
        assert breakdown.total_cost == 0.0

    def test_invalid_token_values(self):
        """Test handling of invalid token values."""
        analyzer = CostAnalyzer()
        event = {
            "event_id": "evt-invalid",
            "input_tokens": "not a number",
            "output_tokens": None,
        }

        breakdown = analyzer._calculate_event_cost(event)
        assert breakdown is not None
        # Should gracefully handle invalid values

    def test_very_large_token_counts(self):
        """Test handling of very large token counts."""
        analyzer = CostAnalyzer()
        event = {
            "event_id": "evt-large",
            "input_tokens": 10_000_000,
            "output_tokens": 5_000_000,
            "model": "claude-3.5-sonnet",
        }

        breakdown = analyzer._calculate_event_cost(event)
        assert breakdown is not None
        assert breakdown.total_cost > 0

    def test_negative_tokens(self):
        """Test handling of negative token counts."""
        analyzer = CostAnalyzer()
        event = {
            "event_id": "evt-negative",
            "input_tokens": -1000,
            "output_tokens": 500,
        }

        breakdown = analyzer._calculate_event_cost(event)
        assert breakdown is not None
        # Should handle gracefully, even if results are unusual


class TestExportToJson:
    """Test JSON export functionality."""

    def test_export_to_json(self, tmp_path):
        """Test exporting cost analysis to JSON."""
        # Create events
        events_dir = tmp_path / ".htmlgraph" / "events"
        events_dir.mkdir(parents=True)

        event = {
            "event_id": "evt-001",
            "tool": "Read",
            "timestamp": "2026-01-08T00:00:00",
            "input_tokens": 1000,
            "output_tokens": 500,
        }

        events_file = events_dir / "test.jsonl"
        with open(events_file, "w") as f:
            f.write(json.dumps(event) + "\n")

        # Analyze
        analyzer = CostAnalyzer(tmp_path / ".htmlgraph")
        analyzer.analyze_events()

        # Export
        output_file = tmp_path / "cost_analysis.json"
        analyzer.export_to_json(output_file)

        # Verify
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert "total_events" in data
        assert "total_cost" in data
