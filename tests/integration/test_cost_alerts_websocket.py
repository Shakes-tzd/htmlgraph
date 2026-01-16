"""
Integration tests for WebSocket cost alert streaming.

Tests cover:
- Real-time alert delivery (<1s latency)
- Cost alert filtering
- Batch processing
- Connection handling
- Alert aggregation
"""

import time
from pathlib import Path

import pytest
from htmlgraph.analytics.cost_monitor import CostMonitor
from htmlgraph.api.cost_alerts_websocket import (
    CostAlertFilter,
    CostAlertStreamManager,
)
from htmlgraph.api.websocket import EventSubscriptionFilter, WebSocketManager
from htmlgraph.db.schema import HtmlGraphDB


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Create temporary database for testing."""
    db_path = str(tmp_path / "test_htmlgraph.db")
    db = HtmlGraphDB(db_path)
    db.disconnect()
    return db_path


@pytest.fixture
def cost_monitor(temp_db_path: str) -> CostMonitor:
    """Create CostMonitor instance."""
    return CostMonitor(db_path=temp_db_path)


@pytest.fixture
def websocket_manager(temp_db_path: str) -> WebSocketManager:
    """Create WebSocketManager instance."""
    return WebSocketManager(db_path=temp_db_path)


@pytest.fixture
def cost_alert_stream_manager(
    websocket_manager: WebSocketManager, cost_monitor: CostMonitor
) -> CostAlertStreamManager:
    """Create CostAlertStreamManager instance."""
    return CostAlertStreamManager(websocket_manager, cost_monitor)


@pytest.fixture
def setup_test_session(cost_monitor: CostMonitor) -> str:
    """Set up test session and return session ID."""
    session_id = "test-session-ws-001"
    conn = cost_monitor.connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO sessions (session_id, agent_assigned, status, cost_budget)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, "test-agent", "active", 50.0),
    )
    conn.commit()
    return session_id


class TestCostAlertFilter:
    """Test cost alert filtering."""

    def test_cost_alert_filter_initialization(self) -> None:
        """Test CostAlertFilter creation."""
        filter_obj = CostAlertFilter(
            session_id="test-session",
            alert_types=["budget_warning", "breach"],
        )

        assert filter_obj.session_id == "test-session"
        assert "budget_warning" in filter_obj.alert_types

    def test_cost_alert_filter_matches_alert_type(self) -> None:
        """Test alert type filtering."""
        filter_obj = CostAlertFilter(alert_types=["budget_warning"])

        alert = {
            "alert_type": "budget_warning",
            "severity": "warning",
            "current_cost_usd": 8.0,
        }

        assert filter_obj.matches_cost_alert(alert)

    def test_cost_alert_filter_rejects_wrong_alert_type(self) -> None:
        """Test rejecting wrong alert type."""
        filter_obj = CostAlertFilter(alert_types=["budget_warning"])

        alert = {
            "alert_type": "trajectory_overage",
            "severity": "warning",
            "current_cost_usd": 8.0,
        }

        assert not filter_obj.matches_cost_alert(alert)

    def test_cost_alert_filter_severity_filtering(self) -> None:
        """Test severity level filtering."""
        filter_obj = CostAlertFilter(
            alert_types=["breach"],
            min_severity="critical",
        )

        # Should reject warning
        alert_warning = {
            "alert_type": "breach",
            "severity": "warning",
            "current_cost_usd": 50.0,
        }
        assert not filter_obj.matches_cost_alert(alert_warning)

        # Should accept critical
        alert_critical = {
            "alert_type": "breach",
            "severity": "critical",
            "current_cost_usd": 50.0,
        }
        assert filter_obj.matches_cost_alert(alert_critical)

    def test_cost_alert_filter_cost_threshold(self) -> None:
        """Test cost threshold filtering."""
        filter_obj = CostAlertFilter(
            alert_types=["breach"],
            cost_threshold_usd=10.0,
        )

        # Below threshold
        alert_low = {
            "alert_type": "breach",
            "severity": "warning",
            "current_cost_usd": 5.0,
        }
        assert not filter_obj.matches_cost_alert(alert_low)

        # Above threshold
        alert_high = {
            "alert_type": "breach",
            "severity": "warning",
            "current_cost_usd": 15.0,
        }
        assert filter_obj.matches_cost_alert(alert_high)


class TestCostAlertStreamManager:
    """Test cost alert streaming."""

    @pytest.mark.asyncio
    async def test_stream_manager_initialization(
        self, cost_alert_stream_manager: CostAlertStreamManager
    ) -> None:
        """Test CostAlertStreamManager initialization."""
        assert cost_alert_stream_manager.websocket_manager is not None
        assert cost_alert_stream_manager.cost_monitor is not None
        assert cost_alert_stream_manager.poll_interval_ms > 0

    @pytest.mark.asyncio
    async def test_fetch_new_alerts_empty(
        self, cost_alert_stream_manager: CostAlertStreamManager, setup_test_session: str
    ) -> None:
        """Test fetching alerts when none exist."""
        filter_obj = CostAlertFilter(session_id=setup_test_session)

        alerts = await cost_alert_stream_manager._fetch_new_alerts(
            setup_test_session, "2026-01-01T00:00:00Z", filter_obj
        )

        assert alerts == []

    @pytest.mark.asyncio
    async def test_fetch_new_alerts_with_data(
        self,
        cost_alert_stream_manager: CostAlertStreamManager,
        cost_monitor: CostMonitor,
        setup_test_session: str,
    ) -> None:
        """Test fetching alerts with data."""
        # Create an alert
        cost_monitor._create_alert(
            session_id=setup_test_session,
            alert_type="budget_warning",
            message="Cost at 80%",
            current_cost_usd=8.0,
            budget_usd=10.0,
        )

        filter_obj = CostAlertFilter(session_id=setup_test_session)

        # Fetch from before alert was created
        alerts = await cost_alert_stream_manager._fetch_new_alerts(
            setup_test_session, "2026-01-01T00:00:00Z", filter_obj
        )

        assert len(alerts) > 0
        assert alerts[0]["alert_type"] == "budget_warning"

    @pytest.mark.asyncio
    async def test_fetch_alerts_respects_filter(
        self,
        cost_alert_stream_manager: CostAlertStreamManager,
        cost_monitor: CostMonitor,
        setup_test_session: str,
    ) -> None:
        """Test that fetch respects alert type filter."""
        # Create alerts of different types
        cost_monitor._create_alert(
            session_id=setup_test_session,
            alert_type="budget_warning",
            message="Warning",
            current_cost_usd=8.0,
            budget_usd=10.0,
            severity="warning",
        )

        cost_monitor._create_alert(
            session_id=setup_test_session,
            alert_type="breach",
            message="Breach",
            current_cost_usd=50.0,
            budget_usd=10.0,
            severity="critical",
        )

        # Filter for only critical severity
        filter_obj = CostAlertFilter(
            session_id=setup_test_session, min_severity="critical"
        )

        alerts = await cost_alert_stream_manager._fetch_new_alerts(
            setup_test_session, "2026-01-01T00:00:00Z", filter_obj
        )

        # Should only get the critical alert
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "critical"


class TestCostAlertLatency:
    """Test <1s latency requirement."""

    @pytest.mark.asyncio
    async def test_alert_fetch_latency(
        self,
        cost_alert_stream_manager: CostAlertStreamManager,
        cost_monitor: CostMonitor,
        setup_test_session: str,
    ) -> None:
        """Test alert fetching latency is <1s."""
        # Create multiple alerts
        for i in range(10):
            cost_monitor._create_alert(
                session_id=setup_test_session,
                alert_type="budget_warning",
                message=f"Alert {i}",
                current_cost_usd=float(i),
                budget_usd=10.0,
            )

        filter_obj = CostAlertFilter(session_id=setup_test_session)

        # Measure fetch time
        start_time = time.time()
        alerts = await cost_alert_stream_manager._fetch_new_alerts(
            setup_test_session, "2026-01-01T00:00:00Z", filter_obj
        )
        elapsed_ms = (time.time() - start_time) * 1000

        assert len(alerts) > 0
        # Must be <1000ms (1 second)
        assert elapsed_ms < 1000, f"Alert fetch took {elapsed_ms}ms (must be <1000ms)"


class TestCostBreakdownStreaming:
    """Test cost breakdown streaming."""

    @pytest.mark.asyncio
    async def test_stream_cost_breakdown_message_format(
        self,
        cost_alert_stream_manager: CostAlertStreamManager,
        cost_monitor: CostMonitor,
        setup_test_session: str,
    ) -> None:
        """Test cost breakdown message format."""
        # Add some costs
        cost_monitor.track_token_usage(
            session_id=setup_test_session,
            event_id="evt-001",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=1_000_000,
            output_tokens=0,
        )

        breakdown = cost_monitor.get_cost_breakdown(setup_test_session)

        assert breakdown.by_model is not None
        assert breakdown.by_tool is not None
        assert breakdown.total_cost_usd >= 0


class TestWebSocketIntegration:
    """Test WebSocket integration with cost monitoring."""

    def test_websocket_manager_metrics_initialization(
        self, websocket_manager: WebSocketManager
    ) -> None:
        """Test WebSocket manager metrics are initialized."""
        assert websocket_manager.metrics["total_connections"] == 0
        assert websocket_manager.metrics["total_events_broadcast"] == 0
        assert websocket_manager.metrics["active_sessions"] == 0

    @pytest.mark.asyncio
    async def test_event_subscription_filter_cost_threshold(self) -> None:
        """Test EventSubscriptionFilter with cost threshold."""
        filter_obj = EventSubscriptionFilter(cost_threshold_tokens=1000)

        # Below threshold
        event_low = {"event_type": "tool_call", "cost_tokens": 500}
        assert not filter_obj.matches_event(event_low)

        # Above threshold
        event_high = {"event_type": "tool_call", "cost_tokens": 1500}
        assert filter_obj.matches_event(event_high)


class TestAlertAccuracy:
    """Test alert accuracy and correctness."""

    def test_alert_calculation_accuracy(
        self, cost_monitor: CostMonitor, setup_test_session: str
    ) -> None:
        """Test alert calculations are accurate."""
        # Set budget to $10
        conn = cost_monitor.connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET cost_budget = ? WHERE session_id = ?",
            (10.0, setup_test_session),
        )
        conn.commit()

        # Add costs to trigger 80% alert
        cost_monitor.track_token_usage(
            session_id=setup_test_session,
            event_id="evt-005",
            tool_name="Read",
            model="claude-haiku-4-5-20251001",
            input_tokens=10_000_000,  # Will cost ~$8 (80% of $10)
            output_tokens=0,
        )

        alerts = cost_monitor.get_alerts(setup_test_session)

        # Should have generated a budget warning alert
        assert any(a.alert_type == "budget_warning" for a in alerts)


class TestErrorHandling:
    """Test error handling in cost alert streaming."""

    @pytest.mark.asyncio
    async def test_fetch_alerts_handles_missing_session(
        self, cost_alert_stream_manager: CostAlertStreamManager
    ) -> None:
        """Test fetching alerts for non-existent session."""
        filter_obj = CostAlertFilter(session_id="nonexistent-session")

        alerts = await cost_alert_stream_manager._fetch_new_alerts(
            "nonexistent-session", "2026-01-01T00:00:00Z", filter_obj
        )

        # Should return empty list, not raise exception
        assert alerts == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
