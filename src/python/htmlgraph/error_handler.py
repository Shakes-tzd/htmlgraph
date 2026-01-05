"""
Hybrid Error Handling System - Core error handler module.

Provides structured exception capture, formatting, and storage with three-tier
display levels (minimal, verbose, debug) for token-efficient error reporting.

Features:
- ErrorRecord: Structured exception representation
- LocalsSanitizer: Safely extract locals (exclude secrets)
- MinimalFormatter: 163 tokens - error type + message only
- VerboseFormatter: 300 tokens - stack trace without locals
- DebugFormatter: 794 tokens - full Rich traceback with sanitized locals
- ErrorHandler: Main class for capturing and formatting exceptions
"""

import json
import re
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class ErrorRecord:
    """
    Structured representation of an exception with full context.

    Attributes:
        exception: The exception object
        exception_type: Class name of the exception
        message: Exception message
        traceback_str: Full traceback as string
        locals_dict: Local variables at point of exception
        stack_frames: List of stack frame information
        captured_at: Timestamp when error was captured
    """

    exception: BaseException
    exception_type: str
    message: str
    traceback_str: str
    locals_dict: dict[str, Any] = field(default_factory=dict)
    stack_frames: list[dict[str, Any]] = field(default_factory=list)
    captured_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict (excluding exception object)."""
        return {
            "exception_type": self.exception_type,
            "message": self.message,
            "traceback_str": self.traceback_str,
            "locals_dict": self.locals_dict,
            "stack_frames": self.stack_frames,
            "captured_at": self.captured_at.isoformat(),
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        try:
            return json.dumps(self.to_dict())
        except (TypeError, ValueError):
            # Fallback if serialization fails
            return json.dumps(
                {
                    "exception_type": self.exception_type,
                    "message": self.message,
                    "traceback_str": self.traceback_str,
                    "captured_at": self.captured_at.isoformat(),
                }
            )


class LocalsSanitizer:
    """
    Safely sanitize local variables for error logging.

    Excludes sensitive variables (passwords, tokens, secrets, api_keys),
    truncates large values, and limits container sizes to prevent
    exposing secrets or consuming excessive storage.
    """

    # Patterns for sensitive variable names
    SECRET_PATTERNS = {
        r".*password.*",
        r".*token.*",
        r".*secret.*",
        r".*api_key.*",
        r".*api.*",
        r".*credential.*",
        r".*auth.*",
        r".*oauth.*",
        r".*bearer.*",
        r".*key.*",
    }

    # Max sizes for truncation
    MAX_STRING_LENGTH = 500
    MAX_DICT_ITEMS = 10
    MAX_LIST_ITEMS = 10
    MAX_TOTAL_LOCALS = 5000

    def __init__(self) -> None:
        """Initialize sanitizer with compiled regex patterns."""
        self.secret_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.SECRET_PATTERNS
        ]

    def is_secret_pattern(self, key: str) -> bool:
        """
        Check if variable name matches sensitive patterns.

        Args:
            key: Variable name to check

        Returns:
            True if matches secret pattern, False otherwise
        """
        return any(pattern.match(key) for pattern in self.secret_patterns)

    def truncate_if_needed(self, value: Any, depth: int = 0) -> Any:
        """
        Recursively truncate large values.

        Args:
            value: Value to potentially truncate
            depth: Current recursion depth (prevents infinite recursion)

        Returns:
            Truncated value or original if within limits
        """
        # Prevent deep recursion
        if depth > 5:
            return "[truncated: max depth exceeded]"

        if isinstance(value, str):
            if len(value) > self.MAX_STRING_LENGTH:
                return value[: self.MAX_STRING_LENGTH] + "..."
            return value

        if isinstance(value, dict):
            if len(value) > self.MAX_DICT_ITEMS:
                return {
                    k: self.truncate_if_needed(v, depth + 1)
                    for k, v in list(value.items())[: self.MAX_DICT_ITEMS]
                } | {
                    "[...]": f"(truncated: {len(value) - self.MAX_DICT_ITEMS} more items)"
                }
            return {k: self.truncate_if_needed(v, depth + 1) for k, v in value.items()}

        if isinstance(value, (list, tuple)):
            if len(value) > self.MAX_LIST_ITEMS:
                truncated = [
                    self.truncate_if_needed(v, depth + 1)
                    for v in list(value)[: self.MAX_LIST_ITEMS]
                ]
                truncated.append(
                    f"[...truncated: {len(value) - self.MAX_LIST_ITEMS} more items]"
                )
                return truncated if isinstance(value, list) else tuple(truncated)
            return [self.truncate_if_needed(v, depth + 1) for v in value]

        return value

    def sanitize(self, locals_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize local variables, removing secrets and limiting sizes.

        Args:
            locals_dict: Dictionary of local variables

        Returns:
            Sanitized dictionary safe for logging
        """
        sanitized: dict[str, Any] = {}
        total_size = 0

        for key, value in locals_dict.items():
            # Skip secret patterns
            if self.is_secret_pattern(key):
                sanitized[key] = "[REDACTED]"
                continue

            # Skip common Python internals
            if key.startswith("__") or key in ("self", "cls"):
                continue

            try:
                # Truncate large values
                truncated = self.truncate_if_needed(value)

                # Convert to JSON-serializable form and measure size
                try:
                    json_str = json.dumps(truncated, default=str)
                    size = len(json_str)
                except (TypeError, ValueError):
                    # If not JSON-serializable, convert to string
                    json_str = json.dumps(str(truncated))
                    size = len(json_str)

                # Stop adding if we exceed max total size
                if total_size + size > self.MAX_TOTAL_LOCALS:
                    sanitized["[truncated]"] = (
                        f"(locals exceeded {self.MAX_TOTAL_LOCALS} chars)"
                    )
                    break

                sanitized[key] = truncated
                total_size += size

            except Exception:
                # If sanitization fails, skip this variable
                continue

        return sanitized


class MinimalFormatter:
    """
    Minimal error format (163 tokens).

    Displays only error type, message, and hint to use --debug flag.
    Used for normal operation to minimize token usage.
    """

    @staticmethod
    def format(record: ErrorRecord) -> str:
        """
        Format error in minimal style.

        Args:
            record: ErrorRecord to format

        Returns:
            Formatted error string
        """
        lines = [
            f"ERROR {record.exception_type}: {record.message}",
            "",
            "Run with --debug for full traceback and context",
        ]
        return "\n".join(lines)


class VerboseFormatter:
    """
    Verbose error format (300 tokens).

    Displays error type, message, and stack trace without local variables.
    Used with --verbose flag for intermediate detail level.
    """

    @staticmethod
    def format(record: ErrorRecord) -> str:
        """
        Format error in verbose style.

        Args:
            record: ErrorRecord to format

        Returns:
            Formatted error string
        """
        lines = [
            f"ERROR {record.exception_type}: {record.message}",
            "",
            "Stack trace:",
        ]

        # Add stack frames
        for frame in record.stack_frames:
            filename = frame.get("filename", "unknown")
            lineno = frame.get("lineno", "?")
            function = frame.get("function", "?")
            code_line = frame.get("code_line", "")

            lines.append(f'  File "{filename}", line {lineno}, in {function}')
            if code_line:
                lines.append(f"    {code_line.strip()}")

        lines.append("")
        lines.append("Run with --debug for full local variable context")

        return "\n".join(lines)


class DebugFormatter:
    """
    Debug error format (794 tokens).

    Displays full Rich-formatted traceback with sanitized local variables.
    Used with --debug flag for complete debugging information.
    """

    @staticmethod
    def format(record: ErrorRecord) -> str:
        """
        Format error in debug style.

        Args:
            record: ErrorRecord to format

        Returns:
            Formatted error string with full context
        """
        # Try to use Rich for fancy formatting
        try:
            # Rich is available but we format manually
            # Convert traceback string to Traceback object
            tb_str = record.traceback_str

            # Format as code block with traceback
            lines = [
                "═" * 60,
                "FULL TRACEBACK (--debug mode)",
                "═" * 60,
                "",
                tb_str,
                "",
            ]

            # Add locals if available
            if record.locals_dict:
                lines.append("─" * 60)
                lines.append("LOCAL VARIABLES")
                lines.append("─" * 60)
                for key, value in record.locals_dict.items():
                    try:
                        val_str = json.dumps(value, default=str, indent=2)
                        if len(val_str) > 100:
                            val_str = val_str[:100] + "..."
                    except (TypeError, ValueError):
                        val_str = str(value)

                    lines.append(f"{key} = {val_str}")

                lines.append("")

            return "\n".join(lines)

        except ImportError:
            # Fallback if Rich not available
            lines = [
                "FULL TRACEBACK",
                "═" * 60,
                record.traceback_str,
                "",
            ]

            if record.locals_dict:
                lines.append("LOCAL VARIABLES")
                lines.append("─" * 60)
                for key, value in record.locals_dict.items():
                    try:
                        val_str = json.dumps(value, default=str)
                    except (TypeError, ValueError):
                        val_str = str(value)
                    lines.append(f"{key} = {val_str}")

            return "\n".join(lines)


class ErrorHandler:
    """
    Main error handler for capturing and formatting exceptions.

    Provides methods to:
    - Capture exceptions with full context
    - Extract stack frames and locals
    - Format errors at different verbosity levels
    - Serialize for storage
    """

    def __init__(self, debug: bool = False, verbose: bool = False) -> None:
        """
        Initialize ErrorHandler.

        Args:
            debug: Whether to show debug output
            verbose: Whether to show verbose output
        """
        self.debug = debug
        self.verbose = verbose
        self.sanitizer = LocalsSanitizer()

    def capture_exception(self, exception: BaseException | None = None) -> ErrorRecord:
        """
        Capture exception with full context including stack frames and locals.

        Args:
            exception: Exception to capture (uses sys.exc_info() if None)

        Returns:
            ErrorRecord with captured exception details
        """
        exc_traceback = None
        if exception is None:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if exc_value is None:
                # No active exception
                raise RuntimeError("No active exception to capture")
            exception = exc_value

        # Get exception info
        exception_type = exception.__class__.__name__
        message = str(exception)

        # Capture traceback
        traceback_str = "".join(
            traceback.format_exception(type(exception), exception, exc_traceback)
        )

        # Extract stack frames
        stack_frames = self._extract_stack_frames(exc_traceback)

        # Extract locals from each frame
        locals_dict = self._extract_locals(exc_traceback)

        return ErrorRecord(
            exception=exception,
            exception_type=exception_type,
            message=message,
            traceback_str=traceback_str,
            locals_dict=locals_dict,
            stack_frames=stack_frames,
        )

    def _extract_stack_frames(self, tb: Any) -> list[dict[str, Any]]:
        """
        Extract stack frame information from traceback.

        Args:
            tb: Traceback object

        Returns:
            List of frame dictionaries
        """
        frames: list[dict[str, Any]] = []

        while tb is not None:
            frame = tb.tb_frame
            frames.append(
                {
                    "filename": frame.f_code.co_filename,
                    "lineno": tb.tb_lineno,
                    "function": frame.f_code.co_name,
                    "code_line": self._get_code_line(
                        frame.f_code.co_filename, tb.tb_lineno
                    ),
                }
            )
            tb = tb.tb_next

        return frames

    def _get_code_line(self, filename: str, lineno: int) -> str:
        """
        Get source code line at specified location.

        Args:
            filename: Source file path
            lineno: Line number

        Returns:
            Source code line or empty string if not found
        """
        try:
            with open(filename, encoding="utf-8") as f:
                lines = f.readlines()
                if 0 < lineno <= len(lines):
                    return lines[lineno - 1].rstrip()
        except OSError:
            pass
        return ""

    def _extract_locals(self, tb: Any) -> dict[str, Any]:
        """
        Extract local variables from traceback frames.

        Args:
            tb: Traceback object

        Returns:
            Sanitized locals dictionary from innermost frame
        """
        locals_dict: dict[str, Any] = {}

        # Get locals from innermost frame (where exception occurred)
        while tb is not None:
            locals_dict = tb.tb_frame.f_locals.copy()
            tb = tb.tb_next

        # Sanitize before returning
        return self.sanitizer.sanitize(locals_dict)

    def format_error(
        self,
        record: ErrorRecord,
        level: Literal["minimal", "verbose", "debug"] | None = None,
    ) -> str:
        """
        Format error record at specified verbosity level.

        Args:
            record: ErrorRecord to format
            level: Display level (minimal/verbose/debug). If None, infers from flags.

        Returns:
            Formatted error string
        """
        if level is None:
            if self.debug:
                level = "debug"
            elif self.verbose:
                level = "verbose"
            else:
                level = "minimal"

        if level == "debug":
            return DebugFormatter.format(record)
        elif level == "verbose":
            return VerboseFormatter.format(record)
        else:  # minimal
            return MinimalFormatter.format(record)

    def serialize_for_storage(self, record: ErrorRecord) -> dict[str, Any]:
        """
        Serialize ErrorRecord for storage in ErrorEntry.

        Args:
            record: ErrorRecord to serialize

        Returns:
            Dictionary suitable for JSON storage
        """
        return {
            "exception_type": record.exception_type,
            "message": record.message,
            "traceback": record.traceback_str,
            "locals_dump": json.dumps(record.locals_dict, default=str),
            "stack_frames": record.stack_frames,
            "captured_at": record.captured_at.isoformat(),
        }
