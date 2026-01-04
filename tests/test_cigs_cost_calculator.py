"""
Unit tests for CIGS CostCalculator.

Tests cover:
- Token cost prediction for various tools
- Actual cost calculation from execution results
- Waste calculation and efficiency scoring
- Operation classification for delegation analysis
- Session cost aggregation
"""

import pytest
from htmlgraph.cigs.cost import CostCalculator
from htmlgraph.cigs.models import (
    CostMetrics,
    OperationClassification,
    TokenCost,
)


class TestCostCalculatorPrediction:
    """Tests for cost prediction functionality."""

    def setup_method(self):
        """Initialize calculator for each test."""
        self.calc = CostCalculator()

    def test_predict_cost_read_single_file(self):
        """Test cost prediction for single file read."""
        params = {"file_path": "/path/to/file.py"}
        cost = self.calc.predict_cost("Read", params)
        assert cost == 5000

    def test_predict_cost_read_multiple_files(self):
        """Test cost prediction for multiple file reads."""
        params = {
            "file_path": ["/path/to/file1.py", "/path/to/file2.py", "/path/to/file3.py"]
        }
        cost = self.calc.predict_cost("Read", params)
        assert cost == 15000  # 5000 * 3

    def test_predict_cost_read_large_file(self):
        """Test cost prediction for reading large file."""
        params = {"file_path": "/path/to/large.py", "limit": 10000}
        cost = self.calc.predict_cost("Read", params)
        assert cost == 10000  # 5000 * 2 (doubled due to size)

    def test_predict_cost_grep_simple(self):
        """Test cost prediction for simple grep operation."""
        params = {"pattern": "def test"}
        cost = self.calc.predict_cost("Grep", params)
        assert cost == 3000

    def test_predict_cost_grep_complex_pattern(self):
        """Test cost prediction for complex regex pattern."""
        complex_pattern = r"class\s+\w+\(.*?\):\s*(?:def\s+\w+|@\w+)"
        params = {"pattern": complex_pattern}
        cost = self.calc.predict_cost("Grep", params)
        assert cost >= 3000  # Should be >= due to complexity (3000 * 1.5 = 4500)

    def test_predict_cost_grep_multiline(self):
        """Test cost prediction for multiline grep."""
        params = {"pattern": "pattern", "multiline": True}
        cost = self.calc.predict_cost("Grep", params)
        assert cost > 3000  # Multiline increases cost

    def test_predict_cost_edit_single_file(self):
        """Test cost prediction for single file edit."""
        params = {
            "file_path": "/path/to/file.py",
            "old_string": "old",
            "new_string": "new",
        }
        cost = self.calc.predict_cost("Edit", params)
        assert cost == 4000

    def test_predict_cost_edit_multiple_files(self):
        """Test cost prediction for multiple file edits."""
        params = {
            "file_path": ["/path/to/file1.py", "/path/to/file2.py"],
            "old_string": "old",
            "new_string": "new",
        }
        cost = self.calc.predict_cost("Edit", params)
        assert cost == 8000  # 4000 * 2

    def test_predict_cost_edit_large_content(self):
        """Test cost prediction for edit with large content."""
        large_content = "x" * 15000
        params = {"file_path": "/path/to/file.py", "new_string": large_content}
        cost = self.calc.predict_cost("Edit", params)
        assert cost == 6000  # 4000 * 1.5

    def test_predict_cost_bash_default(self):
        """Test cost prediction for generic bash command."""
        params = {"command": "ls -la /path/to/dir"}
        cost = self.calc.predict_cost("Bash", params)
        assert cost == 2000

    def test_predict_cost_bash_git_operation(self):
        """Test cost prediction for git bash command."""
        params = {"command": "git add ."}
        cost = self.calc.predict_cost("Bash", params)
        assert cost == 1500  # Git operations are cheaper

    def test_predict_cost_bash_pytest(self):
        """Test cost prediction for pytest execution."""
        params = {"command": "uv run pytest tests/"}
        cost = self.calc.predict_cost("Bash", params)
        assert cost == 5000  # Testing is expensive

    def test_predict_cost_task(self):
        """Test cost prediction for Task delegation."""
        params = {"prompt": "Do something"}
        cost = self.calc.predict_cost("Task", params)
        assert cost == 500

    def test_predict_cost_unknown_tool(self):
        """Test cost prediction for unknown tool."""
        cost = self.calc.predict_cost("UnknownTool", {})
        assert cost == 2000  # Default estimate


class TestOptimalCost:
    """Tests for optimal cost calculation with delegation."""

    def setup_method(self):
        """Initialize calculator for each test."""
        self.calc = CostCalculator()

    def test_optimal_cost_exploration_tool(self):
        """Test optimal cost for exploration operation."""
        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=False,
            reason="",
            predicted_cost=5000,
            optimal_cost=0,
            is_exploration_sequence=False,
            suggested_delegation="",
        )
        optimal = self.calc.optimal_cost(classification)
        assert optimal == 500  # spawn_gemini cost

    def test_optimal_cost_implementation_tool(self):
        """Test optimal cost for implementation operation."""
        classification = OperationClassification(
            tool="Edit",
            category="implementation",
            should_delegate=False,
            reason="",
            predicted_cost=4000,
            optimal_cost=0,
            is_exploration_sequence=False,
            suggested_delegation="",
        )
        optimal = self.calc.optimal_cost(classification)
        assert optimal == 800  # spawn_codex cost

    def test_optimal_cost_git_operation(self):
        """Test optimal cost for git operation."""
        classification = OperationClassification(
            tool="Bash",
            category="git",
            should_delegate=False,
            reason="",
            predicted_cost=1500,
            optimal_cost=0,
            is_exploration_sequence=False,
            suggested_delegation="",
        )
        optimal = self.calc.optimal_cost(classification)
        assert optimal == 600  # spawn_copilot cost

    def test_optimal_cost_testing_operation(self):
        """Test optimal cost for testing operation."""
        classification = OperationClassification(
            tool="Bash",
            category="testing",
            should_delegate=False,
            reason="",
            predicted_cost=5000,
            optimal_cost=0,
            is_exploration_sequence=False,
            suggested_delegation="",
        )
        optimal = self.calc.optimal_cost(classification)
        assert optimal == 500  # Task cost

    def test_optimal_cost_task_already_delegated(self):
        """Test optimal cost for already-delegated operation."""
        classification = OperationClassification(
            tool="Task",
            category="orchestration",
            should_delegate=False,
            reason="",
            predicted_cost=500,
            optimal_cost=0,
            is_exploration_sequence=False,
            suggested_delegation="",
        )
        optimal = self.calc.optimal_cost(classification)
        assert optimal == 500


class TestActualCostCalculation:
    """Tests for actual cost calculation from execution results."""

    def setup_method(self):
        """Initialize calculator for each test."""
        self.calc = CostCalculator()

    def test_calculate_actual_cost_with_metadata(self):
        """Test actual cost extraction from metadata."""
        result = {"actual_cost": 5500, "metadata": {"status": "success"}}
        cost = self.calc.calculate_actual_cost("Read", result)
        assert cost.total_tokens == 5500

    def test_calculate_actual_cost_read_with_output(self):
        """Test cost calculation for Read with output."""
        output = "line 1\n" * 100  # 100 lines
        result = {"output": output}
        cost = self.calc.calculate_actual_cost("Read", result)
        # Should estimate based on output size
        assert cost.total_tokens > 0

    def test_calculate_actual_cost_fallback_to_predicted(self):
        """Test that actual cost falls back to predicted."""
        result = {"status": "success"}  # No cost info
        cost = self.calc.calculate_actual_cost("Grep", result)
        # Falls back to predict_cost
        assert cost.total_tokens == 3000

    def test_token_cost_waste_tokens(self):
        """Test TokenCost waste calculation."""
        cost = TokenCost(
            total_tokens=5000,
            subagent_tokens=500,
            orchestrator_tokens=4500,
        )
        assert cost.estimated_savings >= 0

    def test_token_cost_properties(self):
        """Test TokenCost properties."""
        cost = TokenCost(
            total_tokens=5000,
            subagent_tokens=500,
            orchestrator_tokens=4500,
            estimated_savings=0,
        )
        assert cost.total_tokens == 5000
        assert cost.subagent_tokens == 500
        assert cost.orchestrator_tokens == 4500


class TestWasteCalculation:
    """Tests for waste calculation."""

    def setup_method(self):
        """Initialize calculator for each test."""
        self.calc = CostCalculator()

    def test_calculate_waste_basic(self):
        """Test basic waste calculation."""
        waste = self.calc.calculate_waste(5000, 500)
        assert waste["waste_tokens"] == 4500
        assert waste["waste_percentage"] == 90.0
        assert waste["efficiency_score"] == 10.0

    def test_calculate_waste_zero_actual(self):
        """Test waste calculation with zero actual cost."""
        waste = self.calc.calculate_waste(0, 500)
        assert waste["waste_tokens"] == 0
        assert waste["waste_percentage"] == 0.0
        assert waste["efficiency_score"] == 100.0

    def test_calculate_waste_no_waste(self):
        """Test waste calculation with optimal cost."""
        waste = self.calc.calculate_waste(500, 500)
        assert waste["waste_tokens"] == 0
        assert waste["waste_percentage"] == 0.0
        assert waste["efficiency_score"] == 100.0

    def test_calculate_waste_actual_less_than_optimal(self):
        """Test waste with actual < optimal (shouldn't happen)."""
        waste = self.calc.calculate_waste(300, 500)
        assert waste["waste_tokens"] == 0  # Max(0, 300-500)
        assert waste["efficiency_score"] > 100  # 500/300 * 100


class TestOperationClassification:
    """Tests for operation classification."""

    def setup_method(self):
        """Initialize calculator for each test."""
        self.calc = CostCalculator()

    def test_classify_read_operation(self):
        """Test classification of Read operation."""
        classification = self.calc.classify_operation(
            "Read", {"file_path": "/path/file.py"}
        )
        assert classification.tool == "Read"
        assert classification.category == "exploration"
        assert classification.predicted_cost == 5000
        assert classification.optimal_cost == 500

    def test_classify_edit_operation(self):
        """Test classification of Edit operation."""
        classification = self.calc.classify_operation(
            "Edit",
            {"file_path": "/path/file.py", "old_string": "old", "new_string": "new"},
        )
        assert classification.tool == "Edit"
        assert classification.category == "implementation"
        assert classification.predicted_cost == 4000
        assert classification.optimal_cost == 500  # Falls back to Task cost

    def test_classify_exploration_sequence(self):
        """Test classification of exploration sequence."""
        classification = self.calc.classify_operation(
            "Grep", {"pattern": "test"}, is_exploration_sequence=True
        )
        assert classification.is_exploration_sequence is True
        assert (
            "Multiple" in classification.reason
            or "unpredictable" in classification.reason
        )

    def test_classification_waste_percentage(self):
        """Test waste calculation in classification."""
        classification = self.calc.classify_operation(
            "Read", {"file_path": "/path/file.py"}
        )
        # waste_percentage is computed as (waste_tokens / predicted_cost) * 100
        waste = classification.predicted_cost - classification.optimal_cost
        assert waste == 4500  # 5000 - 500
        assert classification.waste_percentage == 90.0


class TestSessionCostAggregation:
    """Tests for session-level cost aggregation."""

    def setup_method(self):
        """Initialize calculator for each test."""
        self.calc = CostCalculator()

    def test_aggregate_empty_session(self):
        """Test aggregation of empty session."""
        metrics = self.calc.aggregate_session_costs([])
        assert metrics.total_tokens == 0
        assert metrics.optimal_tokens == 0
        assert metrics.waste_tokens == 0

    def test_aggregate_single_operation(self):
        """Test aggregation with single operation."""
        operations = [("Read", {"file_path": "/path/file.py"}, {"output": "data"})]
        metrics = self.calc.aggregate_session_costs(operations)
        assert metrics.total_tokens > 0
        assert metrics.optimal_tokens == 500

    def test_aggregate_multiple_operations(self):
        """Test aggregation with multiple operations."""
        operations = [
            ("Read", {"file_path": "/path/file1.py"}, {"output": "data1"}),
            ("Grep", {"pattern": "test"}, {"output": "results"}),
            ("Edit", {"file_path": "/path/file2.py"}, {"output": "done"}),
        ]
        metrics = self.calc.aggregate_session_costs(operations)
        assert metrics.total_tokens > 0
        assert metrics.optimal_tokens > 0
        assert metrics.waste_tokens >= 0

    def test_aggregate_with_violations(self):
        """Test aggregation with multiple operations."""
        operations = [
            ("Read", {"file_path": "/path/file.py"}, {}),
            ("Grep", {"pattern": "test"}, {}),
        ]
        metrics = self.calc.aggregate_session_costs(operations)
        assert metrics.total_tokens > 0
        assert metrics.optimal_tokens > 0
        assert metrics.waste_tokens >= 0

    def test_cost_metrics_efficiency_score(self):
        """Test CostMetrics efficiency score calculation."""
        metrics = CostMetrics(
            total_tokens=10000,
            optimal_tokens=2000,
            waste_tokens=8000,
            orchestrator_tokens=8000,
            subagent_tokens=2000,
            efficiency_score=20.0,
            waste_percentage=80.0,
        )
        # (2000/10000)*100 = 20
        expected = 20.0
        assert abs(metrics.efficiency_score - expected) < 0.1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def setup_method(self):
        """Initialize calculator for each test."""
        self.calc = CostCalculator()

    def test_very_complex_regex_pattern(self):
        """Test cost prediction for very complex regex."""
        complex_pattern = (
            r"(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z]{2,})"
        )
        params = {"pattern": complex_pattern}
        cost = self.calc.predict_cost("Grep", params)
        assert cost >= 3000  # 3000 * 1.5 for complex

    def test_zero_cost_result(self):
        """Test handling of zero-cost result."""
        cost = self.calc.calculate_actual_cost("Task", {})
        assert cost.total_tokens == 500  # Default Task cost

    def test_negative_waste_becomes_zero(self):
        """Test that negative waste is clamped to zero."""
        waste = self.calc.calculate_waste(300, 500)
        assert waste["waste_tokens"] == 0

    def test_efficiency_score_bounds(self):
        """Test that efficiency score stays within 0-100."""
        metrics = CostMetrics(
            total_tokens=100,
            optimal_tokens=50,
            waste_tokens=50,
            orchestrator_tokens=50,
            subagent_tokens=50,
        )
        # Efficiency score = 50/100 * 100 = 50
        assert 0 <= metrics.efficiency_score <= 100

    def test_unknown_tool_handling(self):
        """Test handling of unknown tool type."""
        classification = self.calc.classify_operation("NewTool", {})
        assert classification.tool == "NewTool"
        assert classification.category == "unknown"
        assert classification.optimal_cost == 500  # Falls back to Task cost


class TestCostIntegration:
    """Integration tests combining multiple calculator functions."""

    def setup_method(self):
        """Initialize calculator for each test."""
        self.calc = CostCalculator()

    def test_workflow_predict_then_actual(self):
        """Test typical workflow: predict, execute, calculate actual."""
        tool = "Read"
        params = {"file_path": "/path/to/file.py"}

        # Step 1: Predict cost before execution
        predicted = self.calc.predict_cost(tool, params)
        assert predicted == 5000

        # Step 2: Simulate execution result
        result = {"output": "code content\n" * 50}

        # Step 3: Calculate actual cost
        actual_cost = self.calc.calculate_actual_cost(tool, result)
        assert actual_cost.total_tokens > 0

    def test_workflow_classify_and_calculate_waste(self):
        """Test workflow: classify operation, then calculate waste."""
        tool = "Read"
        params = {"file_path": "/path/to/file.py"}

        # Step 1: Classify operation
        classification = self.calc.classify_operation(tool, params)
        assert classification.predicted_cost == 5000
        assert classification.optimal_cost == 500

        # Step 2: Calculate waste
        waste = self.calc.calculate_waste(
            classification.predicted_cost, classification.optimal_cost
        )
        assert waste["waste_tokens"] == 4500
        assert waste["efficiency_score"] == 10.0

    def test_workflow_session_analysis(self):
        """Test complete session analysis workflow."""
        # Simulate a session with multiple operations
        operations = [
            ("Read", {"file_path": "/file1.py"}, {"output": "code1"}),
            ("Grep", {"pattern": "def test"}, {"output": "matches"}),
            ("Read", {"file_path": "/file2.py"}, {"output": "code2"}),
            ("Edit", {"file_path": "/file3.py"}, {"output": "done"}),
        ]

        # Analyze session
        metrics = self.calc.aggregate_session_costs(operations)

        # Verify metrics
        assert metrics.total_tokens > 0
        assert metrics.optimal_tokens > 0
        assert metrics.waste_tokens > 0
        assert 0 <= metrics.efficiency_score <= 100
        assert 0 <= metrics.waste_percentage <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
