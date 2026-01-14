from __future__ import annotations

"""HtmlGraph CLI - Browse command for opening dashboard in browser."""


import argparse
import webbrowser
from typing import TYPE_CHECKING

from htmlgraph.cli.base import BaseCommand, CommandResult

if TYPE_CHECKING:
    pass


class BrowseCommand(BaseCommand):
    """Open the HtmlGraph dashboard in your default browser.

    Usage:
        htmlgraph browse                      # Open dashboard
        htmlgraph browse --port 8080          # Custom port
        htmlgraph browse --query-type feature # Show only features
        htmlgraph browse --query-status todo  # Show only todo items
    """

    def __init__(
        self,
        *,
        port: int = 8080,
        query_type: str | None = None,
        query_status: str | None = None,
    ) -> None:
        """Initialize BrowseCommand.

        Args:
            port: Server port (default: 8080)
            query_type: Filter by type (feature, track, bug, spike, chore, epic)
            query_status: Filter by status (todo, in_progress, blocked, done)
        """
        super().__init__()
        self.port = port
        self.query_type = query_type
        self.query_status = query_status

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> BrowseCommand:
        """Create BrowseCommand from argparse arguments.

        Args:
            args: Argparse namespace with command arguments

        Returns:
            BrowseCommand instance
        """
        return cls(
            port=args.port,
            query_type=args.query_type,
            query_status=args.query_status,
        )

    def execute(self) -> CommandResult:
        """Execute the browse command.

        Opens the dashboard in the default browser with optional query parameters.

        Returns:
            CommandResult with success status and URL
        """
        # Build URL with query params
        url = f"http://localhost:{self.port}"

        params = []
        if self.query_type:
            params.append(f"type={self.query_type}")
        if self.query_status:
            params.append(f"status={self.query_status}")

        if params:
            url += "?" + "&".join(params)

        # Check if server is running
        try:
            import requests  # type: ignore[import-untyped]

            response = requests.head(f"http://localhost:{self.port}", timeout=1)
            response.raise_for_status()
        except ImportError:
            # requests module not available - try to open anyway with a warning
            webbrowser.open(url)
            return CommandResult(
                data={"url": url},
                text=f"Opening dashboard at {url}\n(Note: Could not verify server is running - install 'requests' for server checks)",
                exit_code=0,
            )
        except Exception:
            # Server not running or not responding
            return CommandResult(
                text=f"Dashboard server not running on port {self.port}.\nStart with: htmlgraph serve --port {self.port}",
                exit_code=1,
            )

        # Open browser
        try:
            webbrowser.open(url)
        except Exception as e:
            return CommandResult(
                text=f"Failed to open browser: {e}\nYou can manually visit: {url}",
                exit_code=1,
            )

        return CommandResult(
            data={"url": url},
            text=f"Opening dashboard at {url}",
            exit_code=0,
        )
