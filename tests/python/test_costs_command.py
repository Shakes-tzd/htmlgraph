"""Tests for the costs command (Phase 1 Feature 3).

Verifies cost dashboard CLI functionality including:
- Cost querying by session, feature, tool, and agent
- Different time periods (today, day, week, month, all)
- Multiple output formats (terminal, csv)
- Model pricing (opus, sonnet, haiku, auto)
- Cost insights and recommendations
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from htmlgraph.cli.analytics import CostsCommand
from htmlgraph.cli.base import CommandResult


@pytest.fixture
def mock_graph_dir(tmp_path):
    """Create a temporary graph directory with test database."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir()
    db_path = graph_dir / "htmlgraph.db"

    # Create test database with cost data
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create agent_events table
    cursor.execute(
        """
        CREATE TABLE agent_events (
            event_id TEXT PRIMARY KEY,
            session_id TEXT,
            feature_id TEXT,
            timestamp TEXT,
            event_type TEXT,
            tool_name TEXT,
            agent TEXT,
            cost_tokens INTEGER DEFAULT 0
        )
    """
    )

    # Insert test data with various costs
    now = datetime.now(timezone.utc)

    test_events = [
        # Session 1: High cost session
        {
            "event_id": "evt-001",
            "session_id": "sess-001",
            "feature_id": "feat-001",
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "event_type": "tool_call",
            "tool_name": "Read",
            "agent": "claude",
            "cost_tokens": 50000,
        },
        {
            "event_id": "evt-002",
            "session_id": "sess-001",
            "feature_id": "feat-001",
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "event_type": "tool_call",
            "tool_name": "Bash",
            "agent": "claude",
            "cost_tokens": 30000,
        },
        # Session 2: Medium cost session
        {
            "event_id": "evt-003",
            "session_id": "sess-002",
            "feature_id": "feat-002",
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "event_type": "tool_call",
            "tool_name": "Grep",
            "agent": "claude",
            "cost_tokens": 25000,
        },
        # Session 3: Low cost session
        {
            "event_id": "evt-004",
            "session_id": "sess-003",
            "feature_id": "feat-001",
            "timestamp": now.isoformat(),
            "event_type": "tool_call",
            "tool_name": "Edit",
            "agent": "claude",
            "cost_tokens": 10000,
        },
        # Unlinked feature event
        {
            "event_id": "evt-005",
            "session_id": "sess-003",
            "feature_id": None,
            "timestamp": now.isoformat(),
            "event_type": "tool_call",
            "tool_name": "Write",
            "agent": "codex",
            "cost_tokens": 15000,
        },
    ]

    for event in test_events:
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, session_id, feature_id, timestamp, event_type, tool_name, agent, cost_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event["event_id"],
                event["session_id"],
                event["feature_id"],
                event["timestamp"],
                event["event_type"],
                event["tool_name"],
                event["agent"],
                event["cost_tokens"],
            ),
        )

    conn.commit()
    conn.close()

    return graph_dir


class TestCostsCommandInitialization:
    """Test CostsCommand instantiation and argument parsing."""

    def test_command_initialization(self):
        """Test creating a CostsCommand instance."""
        cmd = CostsCommand(
            period="week", by="session", format="terminal", model="opus", limit=10
        )
        assert cmd.period == "week"
        assert cmd.by == "session"
        assert cmd.format == "terminal"
        assert cmd.model == "opus"
        assert cmd.limit == 10

    def test_command_from_args(self):
        """Test creating CostsCommand from argparse Namespace."""
        args = MagicMock()
        args.period = "month"
        args.by = "tool"
        args.format = "csv"
        args.model = "sonnet"
        args.limit = 5

        cmd = CostsCommand.from_args(args)

        assert cmd.period == "month"
        assert cmd.by == "tool"
        assert cmd.format == "csv"
        assert cmd.model == "sonnet"
        assert cmd.limit == 5

    def test_command_from_args_defaults(self):
        """Test from_args with default values."""
        args = MagicMock()
        args.period = "week"
        args.by = "session"
        args.format = "terminal"
        args.model = "auto"
        args.limit = 10

        cmd = CostsCommand.from_args(args)

        assert cmd.period == "week"
        assert cmd.by == "session"
        assert cmd.format == "terminal"


class TestCostsCommandQueries:
    """Test cost database queries."""

    def test_query_by_session(self, mock_graph_dir):
        """Test querying costs grouped by session."""
        cmd = CostsCommand(
            period="all", by="session", format="terminal", model="auto", limit=10
        )
        cmd.graph_dir = str(mock_graph_dir)

        db_path = mock_graph_dir / "htmlgraph.db"
        results = cmd._query_costs(db_path)

        assert len(results) > 0
        assert all("session_id" in r or "name" in r for r in results)
        # First result should be sess-001 with highest cost
        assert results[0]["total_tokens"] == 80000

    def test_query_by_feature(self, mock_graph_dir):
        """Test querying costs grouped by feature."""
        cmd = CostsCommand(
            period="all", by="feature", format="terminal", model="auto", limit=10
        )
        cmd.graph_dir = str(mock_graph_dir)

        db_path = mock_graph_dir / "htmlgraph.db"
        results = cmd._query_costs(db_path)

        assert len(results) > 0
        # Should have feat-001, feat-002, and unlinked
        feature_names = [r["name"] for r in results]
        assert "feat-001" in feature_names or "feat-002" in feature_names

    def test_query_by_tool(self, mock_graph_dir):
        """Test querying costs grouped by tool."""
        cmd = CostsCommand(
            period="all", by="tool", format="terminal", model="auto", limit=10
        )
        cmd.graph_dir = str(mock_graph_dir)

        db_path = mock_graph_dir / "htmlgraph.db"
        results = cmd._query_costs(db_path)

        assert len(results) > 0
        tool_names = [r["name"] for r in results]
        # Should include Read, Bash, Grep, Edit, Write
        assert any(t in tool_names for t in ["Read", "Bash", "Grep", "Edit", "Write"])

    def test_query_by_agent(self, mock_graph_dir):
        """Test querying costs grouped by agent."""
        cmd = CostsCommand(
            period="all", by="agent", format="terminal", model="auto", limit=10
        )
        cmd.graph_dir = str(mock_graph_dir)

        db_path = mock_graph_dir / "htmlgraph.db"
        results = cmd._query_costs(db_path)

        assert len(results) > 0
        agent_names = [r["name"] for r in results]
        assert "claude" in agent_names
        assert "codex" in agent_names

    def test_query_respects_limit(self, mock_graph_dir):
        """Test that query respects the limit parameter."""
        cmd = CostsCommand(
            period="all", by="session", format="terminal", model="auto", limit=2
        )
        cmd.graph_dir = str(mock_graph_dir)

        db_path = mock_graph_dir / "htmlgraph.db"
        results = cmd._query_costs(db_path)

        assert len(results) <= 2


class TestCostsCommandTimeFiltering:
    """Test time period filtering."""

    def test_time_filter_today(self):
        """Test time filter for today."""
        cmd = CostsCommand(
            period="today", by="session", format="terminal", model="auto", limit=10
        )

        now = datetime.now(timezone.utc)
        time_filter = cmd._get_time_filter(now)

        # Should be approximately 24 hours ago
        cutoff = datetime.fromisoformat(time_filter)
        delta = now - cutoff
        assert 23.5 < delta.total_seconds() / 3600 < 24.5

    def test_time_filter_week(self):
        """Test time filter for week."""
        cmd = CostsCommand(
            period="week", by="session", format="terminal", model="auto", limit=10
        )

        now = datetime.now(timezone.utc)
        time_filter = cmd._get_time_filter(now)

        cutoff = datetime.fromisoformat(time_filter)
        delta = now - cutoff
        assert 6.5 < delta.total_seconds() / (24 * 3600) < 7.5

    def test_time_filter_month(self):
        """Test time filter for month."""
        cmd = CostsCommand(
            period="month", by="session", format="terminal", model="auto", limit=10
        )

        now = datetime.now(timezone.utc)
        time_filter = cmd._get_time_filter(now)

        cutoff = datetime.fromisoformat(time_filter)
        delta = now - cutoff
        assert 29 < delta.total_seconds() / (24 * 3600) < 31


class TestCostsCommandPricing:
    """Test cost calculation and pricing models."""

    def test_calculate_usd_opus(self):
        """Test USD calculation for Opus model."""
        cmd = CostsCommand(
            period="week", by="session", format="terminal", model="opus", limit=10
        )

        # 1M tokens at Opus pricing
        # 90% input: 900k * $15/1M = $13.50
        # 10% output: 100k * $45/1M = $4.50
        # Total: $18.00
        cost = cmd._calculate_usd(1_000_000)
        assert 17.5 < cost < 18.5

    def test_calculate_usd_sonnet(self):
        """Test USD calculation for Sonnet model."""
        cmd = CostsCommand(
            period="week", by="session", format="terminal", model="sonnet", limit=10
        )

        # 1M tokens at Sonnet pricing
        # 90% input: 900k * $3/1M = $2.70
        # 10% output: 100k * $15/1M = $1.50
        # Total: $4.20
        cost = cmd._calculate_usd(1_000_000)
        assert 4.1 < cost < 4.3

    def test_calculate_usd_haiku(self):
        """Test USD calculation for Haiku model."""
        cmd = CostsCommand(
            period="week", by="session", format="terminal", model="haiku", limit=10
        )

        # 1M tokens at Haiku pricing
        # 90% input: 900k * $0.80/1M = $0.72
        # 10% output: 100k * $4/1M = $0.40
        # Total: $1.12
        cost = cmd._calculate_usd(1_000_000)
        assert 1.1 < cost < 1.2

    def test_add_usd_costs(self):
        """Test adding USD cost estimates to data."""
        cmd = CostsCommand(
            period="week", by="session", format="terminal", model="opus", limit=10
        )

        test_data = [
            {
                "name": "session-1",
                "event_count": 5,
                "total_tokens": 100_000,
            },
            {
                "name": "session-2",
                "event_count": 3,
                "total_tokens": 50_000,
            },
        ]

        result = cmd._add_usd_costs(test_data)

        assert len(result) == 2
        assert "cost_usd" in result[0]
        assert "cost_usd" in result[1]
        assert result[0]["cost_usd"] > 0
        assert result[1]["cost_usd"] > 0


class TestCostsCommandExecution:
    """Test command execution."""

    def test_execute_no_database(self, tmp_path):
        """Test execute when database doesn't exist."""
        cmd = CostsCommand(
            period="week", by="session", format="terminal", model="auto", limit=10
        )
        cmd.graph_dir = str(tmp_path / ".htmlgraph")

        result = cmd.execute()

        assert result.exit_code == 1
        assert "No database" in result.text or result.text != ""

    def test_execute_with_valid_database(self, mock_graph_dir):
        """Test execute with valid database."""
        cmd = CostsCommand(
            period="week", by="session", format="terminal", model="opus", limit=10
        )
        cmd.graph_dir = str(mock_graph_dir)

        with patch("htmlgraph.cli.analytics.console") as mock_console:
            result = cmd.execute()

        assert isinstance(result, CommandResult)
        # Should call console.print for output
        assert mock_console.print.called or mock_console.status.called


class TestCostsCommandFormatting:
    """Test output formatting."""

    def test_format_duration_with_hours(self):
        """Test duration formatting with hours."""
        cmd = CostsCommand(
            period="week", by="session", format="terminal", model="auto", limit=10
        )

        now = datetime.now(timezone.utc)
        test_data = [
            {
                "name": "session-1",
                "start_time": (now - timedelta(hours=5)).isoformat(),
                "end_time": now.isoformat(),
            }
        ]

        duration = cmd._format_duration(test_data)

        assert "h" in duration or "m" in duration
        assert duration != "unknown"

    def test_format_duration_with_minutes(self):
        """Test duration formatting with minutes."""
        cmd = CostsCommand(
            period="week", by="session", format="terminal", model="auto", limit=10
        )

        now = datetime.now(timezone.utc)
        test_data = [
            {
                "name": "session-1",
                "start_time": (now - timedelta(minutes=30)).isoformat(),
                "end_time": now.isoformat(),
            }
        ]

        duration = cmd._format_duration(test_data)

        assert "m" in duration
        assert duration != "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
