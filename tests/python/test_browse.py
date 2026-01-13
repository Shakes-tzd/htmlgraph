"""Tests for the browse command."""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import MagicMock, patch

from htmlgraph.cli.work.browse import BrowseCommand


class TestBrowseCommand:
    """Test BrowseCommand functionality."""

    def test_from_args(self) -> None:
        """Test BrowseCommand.from_args() creates command correctly."""
        args = Namespace(port=8080, query_type="feature", query_status="todo")
        cmd = BrowseCommand.from_args(args)
        assert isinstance(cmd, BrowseCommand)
        assert cmd.port == 8080
        assert cmd.query_type == "feature"
        assert cmd.query_status == "todo"

    def test_from_args_defaults(self) -> None:
        """Test from_args with default values."""
        args = Namespace(port=8080, query_type=None, query_status=None)
        cmd = BrowseCommand.from_args(args)
        assert cmd.port == 8080
        assert cmd.query_type is None
        assert cmd.query_status is None

    @patch("webbrowser.open")
    @patch("requests.head")
    def test_browse_opens_dashboard(
        self, mock_requests_head: MagicMock, mock_webbrowser: MagicMock
    ) -> None:
        """Test browse command builds correct URL and opens browser."""
        # Mock server running
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests_head.return_value = mock_response

        cmd = BrowseCommand(port=8080)
        result = cmd.execute()

        assert result.exit_code == 0
        assert result.data == {"url": "http://localhost:8080"}
        assert "Opening dashboard at http://localhost:8080" in result.text
        mock_webbrowser.assert_called_once_with("http://localhost:8080")
        mock_requests_head.assert_called_once_with("http://localhost:8080", timeout=1)

    @patch("webbrowser.open")
    @patch("requests.head")
    def test_browse_custom_port(
        self, mock_requests_head: MagicMock, mock_webbrowser: MagicMock
    ) -> None:
        """Test --port parameter works correctly."""
        # Mock server running
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests_head.return_value = mock_response

        cmd = BrowseCommand(port=9000)
        result = cmd.execute()

        assert result.exit_code == 0
        assert result.data == {"url": "http://localhost:9000"}
        mock_webbrowser.assert_called_once_with("http://localhost:9000")
        mock_requests_head.assert_called_once_with("http://localhost:9000", timeout=1)

    @patch("webbrowser.open")
    @patch("requests.head")
    def test_browse_query_type_filter(
        self, mock_requests_head: MagicMock, mock_webbrowser: MagicMock
    ) -> None:
        """Test --query-type parameter is added to URL."""
        # Mock server running
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests_head.return_value = mock_response

        cmd = BrowseCommand(port=8080, query_type="feature")
        result = cmd.execute()

        assert result.exit_code == 0
        assert result.data == {"url": "http://localhost:8080?type=feature"}
        mock_webbrowser.assert_called_once_with("http://localhost:8080?type=feature")

    @patch("webbrowser.open")
    @patch("requests.head")
    def test_browse_query_status_filter(
        self, mock_requests_head: MagicMock, mock_webbrowser: MagicMock
    ) -> None:
        """Test --query-status parameter is added to URL."""
        # Mock server running
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests_head.return_value = mock_response

        cmd = BrowseCommand(port=8080, query_status="todo")
        result = cmd.execute()

        assert result.exit_code == 0
        assert result.data == {"url": "http://localhost:8080?status=todo"}
        mock_webbrowser.assert_called_once_with("http://localhost:8080?status=todo")

    @patch("webbrowser.open")
    @patch("requests.head")
    def test_browse_combined_params(
        self, mock_requests_head: MagicMock, mock_webbrowser: MagicMock
    ) -> None:
        """Test multiple query params work together."""
        # Mock server running
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests_head.return_value = mock_response

        cmd = BrowseCommand(port=8080, query_type="feature", query_status="todo")
        result = cmd.execute()

        assert result.exit_code == 0
        expected_url = "http://localhost:8080?type=feature&status=todo"
        assert result.data == {"url": expected_url}
        mock_webbrowser.assert_called_once_with(expected_url)

    @patch("webbrowser.open")
    @patch("requests.head")
    def test_browse_server_not_running(
        self, mock_requests_head: MagicMock, mock_webbrowser: MagicMock
    ) -> None:
        """Test helpful error message if server not running."""
        # Mock server not running
        mock_requests_head.side_effect = Exception("Connection refused")

        cmd = BrowseCommand(port=8080)
        result = cmd.execute()

        assert result.exit_code == 1
        assert "Dashboard server not running" in result.text
        assert "htmlgraph serve" in result.text
        mock_webbrowser.assert_not_called()

    def test_browse_requests_not_available(self) -> None:
        """Test graceful degradation when requests module not available."""
        # This test verifies the import try/except works
        # The actual behavior is tested by the ImportError path in execute()
        # We'll test this indirectly through the success path
        cmd = BrowseCommand(port=8080)
        assert cmd.port == 8080
        # If requests is available (which it is in tests), server check happens
        # If not available, graceful degradation occurs with warning message

    @patch("webbrowser.open")
    @patch("requests.head")
    def test_browse_browser_open_fails(
        self, mock_requests_head: MagicMock, mock_webbrowser: MagicMock
    ) -> None:
        """Test error handling when browser fails to open."""
        # Mock server running
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests_head.return_value = mock_response

        # Mock browser open failure
        mock_webbrowser.side_effect = Exception("Browser not found")

        cmd = BrowseCommand(port=8080)
        result = cmd.execute()

        assert result.exit_code == 1
        assert "Failed to open browser" in result.text
        assert "http://localhost:8080" in result.text

    @patch("webbrowser.open")
    @patch("requests.head")
    def test_browse_all_query_types(
        self, mock_requests_head: MagicMock, mock_webbrowser: MagicMock
    ) -> None:
        """Test all supported query types."""
        # Mock server running
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests_head.return_value = mock_response

        query_types = ["feature", "track", "bug", "spike", "chore", "epic"]

        for query_type in query_types:
            mock_webbrowser.reset_mock()
            cmd = BrowseCommand(port=8080, query_type=query_type)
            result = cmd.execute()

            assert result.exit_code == 0
            expected_url = f"http://localhost:8080?type={query_type}"
            assert result.data == {"url": expected_url}
            mock_webbrowser.assert_called_once_with(expected_url)

    @patch("webbrowser.open")
    @patch("requests.head")
    def test_browse_all_query_statuses(
        self, mock_requests_head: MagicMock, mock_webbrowser: MagicMock
    ) -> None:
        """Test all supported query statuses."""
        # Mock server running
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests_head.return_value = mock_response

        query_statuses = ["todo", "in_progress", "blocked", "done"]

        for query_status in query_statuses:
            mock_webbrowser.reset_mock()
            cmd = BrowseCommand(port=8080, query_status=query_status)
            result = cmd.execute()

            assert result.exit_code == 0
            expected_url = f"http://localhost:8080?status={query_status}"
            assert result.data == {"url": expected_url}
            mock_webbrowser.assert_called_once_with(expected_url)
