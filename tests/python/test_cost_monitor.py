"""
Unit tests for CostMonitor real-time cost tracking and alerts.

Tests cover:
- Cost calculation accuracy (5% target)
- Token tracking per session
- Alert generation (80% budget, breach, trajectory)
- Cost breakdown by dimension (model, tool, agent)
- Database integration
- Edge cases and error handling
"""

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from htmlgraph.analytics.cost_monitor import (
    CostBreakdown,
    CostMonitor,
    TokenCost,
)
from htmlgraph.db.schema import HtmlGraphDB


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Create temporary database for testing."""
    db_path = str(tmp_path / "test_htmlgraph.db")
    # Initialize schema
    db = HtmlGraphDB(db_path)
    db.disconnect()
    return db_path


@pytest.fixture
def cost_monitor(temp_db_path: str) -> CostMonitor:
    """Create CostMonitor instance with test database."""
    return CostMonitor(db_path=temp_db_path)


@pytest.fixture
def sample_session_id() -> str:
    """Sample session ID for testing."""
    return "test-session-001"


@pytest.fixture
def setup_test_session(cost_monitor: CostMonitor, sample_session_id: str) -> None:
    """Set up test session in database."""
    conn = cost_monitor.connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO sessions (session_id, agent_assigned, status)
        VALUES (?, ?, ?)
        """,
        (sample_session_id, "test-agent", "active"),
    )
    conn.commit()


class TestCostCalculation:
    """Test cost calculation accuracy."""

    def test_calculate_cost_haiku_model(self, cost_monitor: CostMonitor) -> None:
        """Test cost calculation for Claude Haiku."""
        # Haiku: $0.80/1M input, $4.00/1M output
        cost = cost_monitor.calculate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        # Expected: 0.80 + 4.00 = 4.80
        assert abs(cost - 4.80) < 0.01

    def test_calculate_cost_sonnet_model(self, cost_monitor: CostMonitor) -> None:
        """Test cost calculation for Claude Sonnet."""
        # Sonnet: $3.00/1M input, $15.00/1M output
        cost = cost_monitor.calculate_cost_usd(
            model="claude-sonnet-4-20250514",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        # Expected: 3.00 + 15.00 = 18.00
        assert abs(cost - 18.00) < 0.01

    def test_calculate_cost_opus_model(self, cost_monitor: CostMonitor) -> None:
        """Test cost calculation for Claude Opus."""
        # Opus: $15.00/1M input, $75.00/1M output
        cost = cost_monitor.calculate_cost_usd(
            model="claude-opus-4-1-20250805",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        # Expected: 15.00 + 75.00 = 90.00
        assert abs(cost - 90.00) < 0.01

    def test_calculate_cost_partial_tokens(self, cost_monitor: CostMonitor) -> None:
        """Test cost calculation with partial token counts."""
        cost = cost_monitor.calculate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=500_000,
            output_tokens=250_000,
        )
        # Expected: (0.80 * 0.5) + (4.00 * 0.25) = 0.40 + 1.00 = 1.40
        assert abs(cost - 1.40) < 0.01

    def test_calculate_cost_unknown_model_uses_defaults(
        self, cost_monitor: CostMonitor
    ) -> None:
        """Test unknown model uses default rates."""
        cost = cost_monitor.calculate_cost_usd(
            model="unknown-model-123",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        # Defaults: $2.00/1M input, $10.00/1M output
        # Expected: 2.00 + 10.00 = 12.00
        assert abs(cost - 12.00) < 0.01

    def test_calculate_cost_zero_tokens(self, cost_monitor: CostMonitor) -> None:
        """Test cost calculation with zero tokens."""
        cost = cost_monitor.calculate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=0,
            output_tokens=0,
        )
        assert cost == 0.0


class TestTokenTracking:
    """Test token usage tracking."""

    def test_track_token_usage_creates_record(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test tracking token usage creates database record."""
        token_cost = cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-001",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=1000,
            output_tokens=500,
        )

        assert token_cost.tool_name == "Read"
        assert token_cost.model == "claude-haiku-4-5-20251001"
        assert token_cost.input_tokens == 1000
        assert token_cost.output_tokens == 500
        assert token_cost.total_tokens == 1500

    def test_track_token_usage_calculates_cost(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test token tracking calculates cost correctly."""
        token_cost = cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-002",
            tool_name="Grep",
            model="claude-sonnet-4-20250514",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )

        # Sonnet: (3.00 * 1.0) + (15.00 * 0.5) = 3.00 + 7.50 = 10.50
        assert abs(token_cost.cost_usd - 10.50) < 0.01

    def test_track_multiple_token_usages(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test tracking multiple token usages."""
        cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-003",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=1000,
            output_tokens=500,
        )

        cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-004",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=2000,
            output_tokens=1000,
        )

        session_cost = cost_monitor.get_session_cost(sample_session_id)
        assert session_cost["total_tokens"] == 4500

    def test_track_token_usage_with_agent_info(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test token tracking with agent information."""
        token_cost = cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-005",
            tool_name="Task",
            model="claude-haiku-4-5-20251001",
            input_tokens=500,
            output_tokens=200,
            agent_id="agent-001",
            subagent_type="orchestrator",
        )

        assert token_cost.agent_id == "agent-001"
        assert token_cost.subagent_type == "orchestrator"


class TestCostBreakdown:
    """Test cost breakdown by dimensions."""

    def test_get_cost_breakdown_by_model(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test cost breakdown by model."""
        cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-006",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=1_000_000,
            output_tokens=0,
        )

        cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-007",
            tool_name="Grep",
            model="claude-sonnet-4-20250514",
            input_tokens=1_000_000,
            output_tokens=0,
        )

        breakdown = cost_monitor.get_cost_breakdown(sample_session_id)

        assert "claude-haiku-4-5-20251001" in breakdown.by_model
        assert "claude-sonnet-4-20250514" in breakdown.by_model
        assert abs(breakdown.by_model["claude-haiku-4-5-20251001"] - 0.80) < 0.01
        assert abs(breakdown.by_model["claude-sonnet-4-20250514"] - 3.00) < 0.01

    def test_get_cost_breakdown_by_tool(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test cost breakdown by tool."""
        cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-008",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=1_000_000,
            output_tokens=0,
        )

        cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-009",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=1_000_000,
            output_tokens=0,
        )

        breakdown = cost_monitor.get_cost_breakdown(sample_session_id)

        assert "Read" in breakdown.by_tool
        assert abs(breakdown.by_tool["Read"] - 1.60) < 0.01

    def test_get_cost_breakdown_total_cost(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test total cost in breakdown."""
        cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-010",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )

        breakdown = cost_monitor.get_cost_breakdown(sample_session_id)

        # Haiku: 0.80 + 4.00 = 4.80
        assert abs(breakdown.total_cost_usd - 4.80) < 0.01
        assert breakdown.total_tokens == 2_000_000


class TestAlertGeneration:
    """Test alert generation."""

    def test_alert_creation(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test creating an alert."""
        alert = cost_monitor._create_alert(
            session_id=sample_session_id,
            alert_type="budget_warning",
            message="Cost at 80% of budget",
            current_cost_usd=8.0,
            budget_usd=10.0,
            severity="warning",
        )

        assert alert.alert_type == "budget_warning"
        assert alert.message == "Cost at 80% of budget"
        assert alert.current_cost_usd == 8.0
        assert alert.budget_usd == 10.0

    def test_alert_to_dict(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test alert serialization to dict."""
        alert = cost_monitor._create_alert(
            session_id=sample_session_id,
            alert_type="budget_warning",
            message="Warning message",
            current_cost_usd=5.0,
            budget_usd=10.0,
        )

        alert_dict = alert.to_dict()
        assert alert_dict["alert_type"] == "budget_warning"
        assert alert_dict["current_cost_usd"] == 5.0
        assert "timestamp" in alert_dict


class TestCostTrajectoryPrediction:
    """Test cost trajectory prediction."""

    def test_predict_cost_trajectory_insufficient_data(
        self, cost_monitor: CostMonitor, sample_session_id: str
    ) -> None:
        """Test prediction with insufficient data."""
        prediction = cost_monitor.predict_cost_trajectory(sample_session_id)
        assert not prediction["prediction_available"]
        assert prediction["reason"] == "insufficient_data"

    def test_predict_cost_trajectory_with_data(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test cost trajectory prediction with valid data."""
        # Add multiple cost events over time
        for i in range(5):
            cost_monitor.track_token_usage(
                session_id=sample_session_id,
                event_id=f"evt-{i:03d}",
                tool_name="Read",
                model="claude-haiku-4-5-20251001",
                input_tokens=100_000,
                output_tokens=0,
            )
            time.sleep(0.1)  # Small delay between events

        prediction = cost_monitor.predict_cost_trajectory(
            sample_session_id, lookback_minutes=5
        )

        assert prediction["prediction_available"]
        assert prediction["cost_per_minute"] > 0
        assert prediction["projected_hourly_cost"] > 0


class TestSessionCostTracking:
    """Test session-level cost tracking."""

    def test_get_session_cost_empty_session(
        self, cost_monitor: CostMonitor, sample_session_id: str
    ) -> None:
        """Test getting cost for empty session."""
        session_cost = cost_monitor.get_session_cost(sample_session_id)
        assert session_cost["total_cost_usd"] == 0.0
        assert session_cost["total_tokens"] == 0

    def test_get_session_cost_with_events(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test getting cost for session with events."""
        cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-011",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )

        session_cost = cost_monitor.get_session_cost(sample_session_id)

        assert session_cost["total_tokens"] == 2_000_000
        assert abs(session_cost["total_cost_usd"] - 4.80) < 0.01


class TestCostAccuracy:
    """Test cost tracking accuracy (5% target)."""

    def test_cost_accuracy_haiku(self, cost_monitor: CostMonitor) -> None:
        """Test cost accuracy within 5% for Haiku."""
        cost = cost_monitor.calculate_cost_usd(
            model="claude-haiku-4-5-20251001",
            input_tokens=12_345,
            output_tokens=6_789,
        )

        # Manual calculation
        expected = (12_345 / 1_000_000 * 0.80) + (6_789 / 1_000_000 * 4.00)
        error_percent = abs(cost - expected) / expected * 100

        assert error_percent < 5.0

    def test_cost_accuracy_sonnet(self, cost_monitor: CostMonitor) -> None:
        """Test cost accuracy within 5% for Sonnet."""
        cost = cost_monitor.calculate_cost_usd(
            model="claude-sonnet-4-20250514",
            input_tokens=54_321,
            output_tokens=12_345,
        )

        expected = (54_321 / 1_000_000 * 3.00) + (12_345 / 1_000_000 * 15.00)
        error_percent = abs(cost - expected) / expected * 100

        assert error_percent < 5.0


class TestTokenCostDataModel:
    """Test TokenCost data model."""

    def test_token_cost_to_dict(self) -> None:
        """Test TokenCost serialization."""
        now = datetime.now(timezone.utc)
        token_cost = TokenCost(
            timestamp=now,
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            cost_usd=5.0,
            session_id="test-session",
            event_id="evt-001",
        )

        cost_dict = token_cost.to_dict()

        assert cost_dict["tool_name"] == "Read"
        assert cost_dict["model"] == "claude-haiku-4-5-20251001"
        assert cost_dict["total_tokens"] == 1500
        assert cost_dict["cost_usd"] == 5.0


class TestCostBreakdownDataModel:
    """Test CostBreakdown data model."""

    def test_cost_breakdown_to_dict(self) -> None:
        """Test CostBreakdown serialization."""
        breakdown = CostBreakdown(
            by_model={"claude-haiku": 10.0, "claude-sonnet": 20.0},
            by_tool={"Read": 15.0, "Grep": 15.0},
            total_cost_usd=30.0,
            total_tokens=5_000_000,
        )

        breakdown_dict = breakdown.to_dict()

        assert breakdown_dict["total_cost_usd"] == 30.0
        assert breakdown_dict["total_tokens"] == 5_000_000
        assert len(breakdown_dict["by_model"]) == 2


class TestDatabaseIntegration:
    """Test database integration."""

    def test_cost_events_table_created(self, temp_db_path: str) -> None:
        """Test that cost_events table is created."""
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cost_events'"
        )
        result = cursor.fetchone()

        assert result is not None
        conn.close()

    def test_sessions_table_has_cost_columns(self, temp_db_path: str) -> None:
        """Test that sessions table has cost columns."""
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(sessions)")
        columns = {row[1] for row in cursor.fetchall()}

        assert "cost_budget" in columns
        assert "cost_threshold_breached" in columns
        assert "predicted_cost" in columns

        conn.close()


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_track_usage_with_session_created(
        self, cost_monitor: CostMonitor, setup_test_session, sample_session_id: str
    ) -> None:
        """Test tracking usage with valid session."""
        token_cost = cost_monitor.track_token_usage(
            session_id=sample_session_id,
            event_id="evt-012",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=1000,
            output_tokens=500,
        )

        assert token_cost.total_tokens == 1500

    def test_cost_monitor_initialization_with_default_config(
        self, temp_db_path: str
    ) -> None:
        """Test CostMonitor initialization with default config."""
        monitor = CostMonitor(db_path=temp_db_path)
        assert monitor.config is not None
        assert "models" in monitor.config
        assert "claude-haiku-4-5-20251001" in monitor.config["models"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
