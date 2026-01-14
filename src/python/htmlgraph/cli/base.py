from __future__ import annotations

"""Base classes and utilities for CLI commands.

Provides:
- BaseCommand: Abstract base class for all commands
- CommandResult: Structured command output
- CommandError: User-facing errors
- Formatters: JSON and text output formatting
- TableBuilder: Utility for creating Rich tables with consistent styling
- TextOutputBuilder: Utility for building formatted text output consistently
- save_traceback: Save full tracebacks to log files instead of console
"""


import argparse
import json
import sys
import traceback
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol

from rich import box
from rich.console import Console
from rich.table import Table
from typing_extensions import Self

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

_console = Console()


class CommandError(Exception):
    """User-facing CLI error with an exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


# ============================================================================
# Traceback Logger - Save error tracebacks to log files
# ============================================================================


def save_traceback(error: Exception, context: dict[str, Any] | None = None) -> Path:
    """Save full traceback to log file instead of printing to console.

    Args:
        error: The exception that was raised
        context: Optional context dict with command, args, cwd, etc.

    Returns:
        Path to the saved log file

    Example:
        try:
            # Some operation
            pass
        except Exception as e:
            log_file = save_traceback(e, context={"command": "serve", "cwd": os.getcwd()})
            console.print(f"[red]Error:[/red] {e}")
            console.print(f"[dim]Full traceback saved to:[/dim] {log_file}")
    """
    # Create logs directory
    log_dir = Path(".htmlgraph/logs/errors")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_dir / f"error-{timestamp}.log"

    # Write traceback with context
    with open(log_file, "w") as f:
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        if context:
            f.write(f"Context: {context}\n")
        f.write("\n--- Traceback ---\n")
        traceback.print_exc(file=f)

    return log_file


# ============================================================================
# TableBuilder - Consistent table styling across CLI
# ============================================================================


class TableBuilder:
    """Builder for creating Rich tables with consistent styling.

    Provides factory methods for common table patterns and column types.
    Eliminates duplicated table creation code across CLI modules.

    Example:
        # List table with standard styling
        builder = TableBuilder.create_list_table("Features")
        builder.add_id_column()
        builder.add_text_column("Title", max_width=40)
        builder.add_status_column()
        builder.add_timestamp_column("Updated")

        # Add rows
        for feature in features:
            builder.add_row(feature.id, feature.title, feature.status, feature.updated)

        # Access the table
        console.print(builder.table)
    """

    def __init__(
        self,
        *,
        title: str | None = None,
        show_header: bool = True,
        header_style: str = "bold magenta",
        box_style: box.Box = box.ROUNDED,
    ) -> None:
        """Initialize TableBuilder with styling options.

        Args:
            title: Table title
            show_header: Show header row
            header_style: Style for header text
            box_style: Box drawing style from rich.box
        """
        self.table = Table(
            title=title,
            show_header=show_header,
            header_style=header_style,
            box=box_style,
        )

    @classmethod
    def create_list_table(cls, title: str | None = None) -> TableBuilder:
        """Create a standard list table with rounded box."""
        return cls(title=title, show_header=True, header_style="bold magenta")

    @classmethod
    def create_status_table(cls, title: str | None = None) -> TableBuilder:
        """Create a key-value status table without header."""
        return cls(title=title, show_header=False, box_style=box.SIMPLE)

    @classmethod
    def create_compact_table(cls) -> TableBuilder:
        """Create a compact table with no header or box."""
        return cls(title=None, show_header=False, box_style=box.SIMPLE)

    def add_id_column(
        self,
        name: str = "ID",
        *,
        style: str = "cyan",
        no_wrap: bool = False,
        max_width: int | None = None,
    ) -> TableBuilder:
        """Add an ID column with cyan styling.

        Args:
            name: Column header name
            style: Text style
            no_wrap: Prevent text wrapping
            max_width: Maximum column width in characters
        """
        self.table.add_column(name, style=style, no_wrap=no_wrap, max_width=max_width)
        return self

    def add_text_column(
        self,
        name: str,
        *,
        style: str = "yellow",
        max_width: int | None = None,
        no_wrap: bool = False,
    ) -> TableBuilder:
        """Add a text column with yellow styling.

        Args:
            name: Column header name
            style: Text style
            max_width: Maximum column width in characters
            no_wrap: Prevent text wrapping
        """
        self.table.add_column(name, style=style, max_width=max_width, no_wrap=no_wrap)
        return self

    def add_status_column(
        self,
        name: str = "Status",
        *,
        style: str = "green",
        width: int | None = None,
    ) -> TableBuilder:
        """Add a status column with green styling.

        Args:
            name: Column header name
            style: Text style
            width: Fixed column width in characters
        """
        self.table.add_column(name, style=style, width=width)
        return self

    def add_priority_column(
        self,
        name: str = "Priority",
        *,
        style: str = "blue",
        width: int | None = None,
    ) -> TableBuilder:
        """Add a priority column with blue styling.

        Args:
            name: Column header name
            style: Text style
            width: Fixed column width in characters
        """
        self.table.add_column(name, style=style, width=width)
        return self

    def add_timestamp_column(
        self,
        name: str,
        *,
        style: str = "white",
        width: int | None = None,
    ) -> TableBuilder:
        """Add a timestamp column with white styling.

        Args:
            name: Column header name
            style: Text style
            width: Fixed column width in characters
        """
        self.table.add_column(name, style=style, width=width)
        return self

    def add_numeric_column(
        self,
        name: str,
        *,
        style: str = "yellow",
        justify: Literal["left", "center", "right"] = "right",
        width: int | None = None,
    ) -> TableBuilder:
        """Add a numeric column with right justification.

        Args:
            name: Column header name
            style: Text style
            justify: Text alignment
            width: Fixed column width in characters
        """
        self.table.add_column(name, style=style, justify=justify, width=width)
        return self

    def add_column(
        self,
        name: str,
        *,
        style: str | None = None,
        justify: Literal["left", "center", "right"] = "left",
        width: int | None = None,
        max_width: int | None = None,
        no_wrap: bool = False,
    ) -> TableBuilder:
        """Add a custom column with full control over styling.

        Args:
            name: Column header name
            style: Text style (e.g., "cyan", "bold red")
            justify: Text alignment
            width: Fixed column width in characters
            max_width: Maximum column width in characters
            no_wrap: Prevent text wrapping
        """
        self.table.add_column(
            name,
            style=style,
            justify=justify,
            width=width,
            max_width=max_width,
            no_wrap=no_wrap,
        )
        return self

    def add_row(self, *values: str) -> TableBuilder:
        """Add a data row to the table.

        Args:
            *values: Cell values (converted to strings)
        """
        self.table.add_row(*values)
        return self

    def add_separator(self, style: str = "dim") -> TableBuilder:
        """Add a separator row.

        Args:
            style: Style for separator row
        """
        # Add empty row with style
        num_columns = len(self.table.columns)
        self.table.add_row(*[""] * num_columns, style=style)
        return self


# ============================================================================
# TextOutputBuilder - Consistent text output formatting across CLI
# ============================================================================


class TextOutputBuilder:
    """Builder for creating formatted text output consistently.

    Provides fluent API methods for building structured text output with
    Rich console styling. Eliminates duplicated text output building code
    across CLI modules.

    Example:
        output = TextOutputBuilder()
        output.add_success(f"Session started: {session.id}")
        output.add_field("Agent", session.agent)
        output.add_field("Started", session.started_at.isoformat())
        return CommandResult(text=output.build())
    """

    def __init__(self) -> None:
        """Initialize TextOutputBuilder with empty lines list."""
        self._lines: list[str] = []

    def add_success(self, message: str) -> Self:
        """Add success message with green styling.

        Args:
            message: Success message text

        Returns:
            Self for method chaining
        """
        from htmlgraph.cli.constants import get_style

        self._lines.append(f"{get_style('success')}{message}")
        return self

    def add_error(self, message: str) -> Self:
        """Add error message with red styling.

        Args:
            message: Error message text

        Returns:
            Self for method chaining
        """
        from htmlgraph.cli.constants import get_style

        self._lines.append(f"{get_style('error')}{message}")
        return self

    def add_warning(self, message: str) -> Self:
        """Add warning message with yellow styling.

        Args:
            message: Warning message text

        Returns:
            Self for method chaining
        """
        from htmlgraph.cli.constants import get_style

        self._lines.append(f"{get_style('warning')}{message}")
        return self

    def add_info(self, message: str) -> Self:
        """Add info message with cyan styling.

        Args:
            message: Info message text

        Returns:
            Self for method chaining
        """
        from htmlgraph.cli.constants import get_style

        self._lines.append(f"{get_style('info')}{message}")
        return self

    def add_dim(self, message: str) -> Self:
        """Add dimmed message with dim styling.

        Args:
            message: Dimmed message text

        Returns:
            Self for method chaining
        """
        from htmlgraph.cli.constants import get_style

        self._lines.append(f"{get_style('dim')}{message}")
        return self

    def add_field(self, label: str, value: str | int | float | None) -> Self:
        """Add indented field in 'Label: value' format.

        Args:
            label: Field label
            value: Field value (converted to string)

        Returns:
            Self for method chaining
        """
        value_str = str(value) if value is not None else ""
        self._lines.append(f"  {label}: {value_str}")
        return self

    def add_line(self, text: str) -> Self:
        """Add plain text line without styling.

        Args:
            text: Plain text to add

        Returns:
            Self for method chaining
        """
        self._lines.append(text)
        return self

    def add_blank(self) -> Self:
        """Add blank line.

        Returns:
            Self for method chaining
        """
        self._lines.append("")
        return self

    def build(self) -> str:
        """Build final text output by joining all lines.

        Returns:
            Joined string with newline separators
        """
        return "\n".join(self._lines)


@dataclass
class CommandResult:
    """Structured command result for flexible output formatting."""

    data: Any = None
    text: str | Iterable[str] | None = None
    json_data: Any | None = None
    exit_code: int = 0  # Exit code for the command (0 = success)


class Formatter(Protocol):
    """Protocol for output formatters."""

    def output(self, result: CommandResult) -> None: ...


def _serialize_json(value: Any) -> Any:
    """Recursively serialize value to JSON-compatible types.

    Sanitizes strings to remove control characters (newlines, tabs) that
    would break JSON validity when using json.dumps().
    """
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        # Sanitize string: replace control characters with spaces
        # This prevents newlines/tabs in JSON string values from breaking JSON validity
        sanitized = value.replace("\n", " ").replace("\r", " ").replace("\t", " ")
        # Collapse multiple spaces to single space
        sanitized = " ".join(sanitized.split())
        return sanitized
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        return _serialize_json(value.model_dump())
    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        return _serialize_json(value.to_dict())
    if isinstance(value, dict):
        return {key: _serialize_json(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_json(item) for item in value]
    return value


class JsonFormatter:
    """Format command output as JSON."""

    def output(self, result: CommandResult) -> None:
        payload = result.json_data if result.json_data is not None else result.data
        # Use sys.stdout.write instead of _console.print to avoid Rich's line-wrapping
        # which inserts literal newlines into JSON string values, breaking JSON validity
        sys.stdout.write(json.dumps(_serialize_json(payload), indent=2) + "\n")


class TextFormatter:
    """Format command output as plain text."""

    def output(self, result: CommandResult) -> None:
        # If data is provided and it's a Rich renderable, print it directly
        if result.data is not None:
            from rich.table import Table

            # Check if data is a Rich renderable (Table, Panel, etc.)
            if isinstance(result.data, (Table,)) or hasattr(result.data, "__rich__"):
                _console.print(result.data)
                return

        # Fall back to text output
        if result.text is None:
            if result.data is not None:
                _console.print(result.data)
            return
        if isinstance(result.text, str):
            # Use sys.stdout.write() for ANSI-formatted text to preserve colors when piped
            # This bypasses Rich's reprocessing and ensures ANSI codes are preserved
            sys.stdout.write(result.text)
            if not result.text.endswith("\n"):
                sys.stdout.write("\n")
            return
        # For text as list/iterable, write directly to preserve ANSI codes
        sys.stdout.write("\n".join(str(line) for line in result.text) + "\n")


def get_formatter(format_name: str) -> Formatter:
    """Get formatter by name (json, text, plain, refs)."""
    if format_name == "json":
        return JsonFormatter()
    if format_name in ("text", "plain", "refs", ""):
        return TextFormatter()
    raise CommandError(f"Unknown output format '{format_name}'")


class BaseCommand(ABC):
    """Abstract base class for all CLI commands.

    Provides:
    - SDK initialization and caching
    - Structured error handling
    - Validation lifecycle hook
    - Output formatting

    Subclasses must implement:
    - from_args(): Create command instance from argparse.Namespace
    - execute(): Execute command logic and return CommandResult
    """

    def __init__(self) -> None:
        self.graph_dir: str | None = None
        self.agent: str | None = None
        self._sdk: SDK | None = None
        self.override_output_format: str | None = (
            None  # Allow commands to override formatter
        )

    @classmethod
    @abstractmethod
    def from_args(cls, args: argparse.Namespace) -> BaseCommand:
        """Create command instance from argparse arguments.

        This separates argument parsing from command execution,
        making commands easier to test.
        """
        raise NotImplementedError

    def validate(self) -> None:
        """Validate command parameters before execution.

        Raise CommandError if validation fails.
        Default implementation does nothing.
        """
        return None

    @abstractmethod
    def execute(self) -> CommandResult:
        """Execute the command and return structured result.

        Raise CommandError for user-facing errors.
        """
        raise NotImplementedError

    def get_sdk(self) -> SDK:
        """Get or create SDK instance.

        Caches SDK to avoid repeated initialization.
        """
        if self.graph_dir is None:
            raise CommandError("Missing graph directory for command execution.")
        if self._sdk is None:
            from htmlgraph.sdk import SDK

            self._sdk = SDK(directory=self.graph_dir, agent=self.agent)
        return self._sdk

    def require_node(self, node: Any, entity_type: str, entity_id: str) -> None:
        """Validate that a node exists, raising CommandError if None.

        Args:
            node: The node object to validate
            entity_type: Type of entity (feature, session, track, etc.)
            entity_id: ID of the entity for error message

        Raises:
            CommandError: If node is None

        Usage:
            node = collection.get(feature_id)
            self.require_node(node, "feature", feature_id)
        """
        if node is None:
            from htmlgraph.cli.constants import get_error_message

            error_key = f"{entity_type}_not_found"
            id_key = f"{entity_type}_id"
            raise CommandError(get_error_message(error_key, **{id_key: entity_id}))

    def require_value(self, value: Any, message: str) -> None:
        """Generic validation helper that raises CommandError if value is falsy.

        Args:
            value: The value to validate
            message: Error message to raise if validation fails

        Raises:
            CommandError: If value is falsy (None, False, empty string, etc.)

        Usage:
            self.require_value(self.title, "Title is required")
            self.require_value(len(items) > 0, "At least one item required")
        """
        if not value:
            raise CommandError(message)

    def require_collection(self, collection: Any, collection_name: str) -> None:
        """Validate that a collection exists on SDK, raising CommandError if None.

        Args:
            collection: The collection object to validate
            collection_name: Name of the collection for error message

        Raises:
            CommandError: If collection is None/falsy

        Usage:
            collection = getattr(sdk, self.collection, None)
            self.require_collection(collection, self.collection)
        """
        if not collection:
            raise CommandError(f"Collection '{collection_name}' not found in SDK")

    def run(self, *, graph_dir: str, agent: str | None, output_format: str) -> None:
        """Run command with context.

        Args:
            graph_dir: Path to .htmlgraph directory
            agent: Agent name (optional)
            output_format: Output format (json, text, plain)
        """
        self.graph_dir = graph_dir
        self.agent = agent
        try:
            self.validate()
            result = self.execute()
            # Allow commands to override output format
            # (e.g., snapshot command's --output-format flag overrides global --format)
            actual_format = self.override_output_format or output_format
            formatter = get_formatter(actual_format)
            formatter.output(result)
        except CommandError as exc:
            error_console = Console(file=sys.stderr)
            error_console.print(f"[red]Error: {exc}[/red]")
            sys.exit(exc.exit_code)
        except ValueError as exc:
            error_console = Console(file=sys.stderr)
            error_console.print(f"[red]Error: {exc}[/red]")
            sys.exit(1)
