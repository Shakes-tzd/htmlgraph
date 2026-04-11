"""
Jinja2 template filters for HtmlGraph dashboard.

These filters format data for display in the dashboard templates.
"""

from typing import Any


def format_number(value: int | None) -> str:
    """Format integer with thousands separator."""
    if value is None:
        return "0"
    return f"{value:,}"


def format_duration(seconds: float | int | None) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds is None:
        return "0.00s"
    return f"{float(seconds):.2f}s"


def format_bytes(bytes_size: int | float | None) -> str:
    """Format bytes to MB with 2 decimal places."""
    if bytes_size is None:
        return "0.00MB"
    return f"{int(bytes_size) / (1024 * 1024):.2f}MB"


def truncate_text(text: str | None, length: int = 50) -> str:
    """Truncate text to specified length with ellipsis."""
    if text is None:
        return ""
    return text[:length] + "..." if len(text) > length else text


def format_timestamp(ts: Any) -> str:
    """Format timestamp to readable string."""
    if ts is None:
        return ""
    if hasattr(ts, "strftime"):
        return str(ts.strftime("%Y-%m-%d %H:%M:%S"))
    return str(ts)


def register_filters(templates: Any) -> None:
    """
    Register all custom filters with Jinja2 templates.

    Args:
        templates: Jinja2Templates instance
    """
    templates.env.filters["format_number"] = format_number
    templates.env.filters["format_duration"] = format_duration
    templates.env.filters["format_bytes"] = format_bytes
    templates.env.filters["truncate"] = truncate_text
    templates.env.filters["format_timestamp"] = format_timestamp
