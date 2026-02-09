"""
Jinja2 template initialization and custom filters for HtmlGraph API.

Provides template environment setup and server-side rendering filters.
"""

from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates


def create_jinja_environment(template_dir: str | Path | None = None) -> Jinja2Templates:
    """Create and configure Jinja2 template environment with custom filters.

    Args:
        template_dir: Directory containing templates. Defaults to api/templates.

    Returns:
        Configured Jinja2Templates instance.
    """
    if template_dir is None:
        template_dir = Path(__file__).parent / "templates"
    else:
        template_dir = Path(template_dir)

    template_dir.mkdir(parents=True, exist_ok=True)
    templates = Jinja2Templates(directory=str(template_dir))

    # Register custom filters
    templates.env.filters["format_number"] = format_number
    templates.env.filters["format_duration"] = format_duration
    templates.env.filters["format_bytes"] = format_bytes
    templates.env.filters["truncate_text"] = truncate_text
    templates.env.filters["format_timestamp"] = format_timestamp
    templates.env.filters["format_datetime"] = format_datetime
    templates.env.filters["format_event_status"] = format_event_status
    templates.env.filters["to_json"] = to_json
    templates.env.filters["group_by_agent"] = group_by_agent

    return templates


def format_number(value: int | None) -> str:
    """Format number with thousands separator.

    Args:
        value: Number to format.

    Returns:
        Formatted number string.
    """
    if value is None:
        return "0"
    return f"{value:,}"


def format_duration(seconds: float | int | None) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted duration string (e.g., "1.23s").
    """
    if seconds is None:
        return "0.00s"
    return f"{float(seconds):.2f}s"


def format_bytes(bytes_size: int | float | None) -> str:
    """Format bytes to MB with 2 decimal places.

    Args:
        bytes_size: Size in bytes.

    Returns:
        Formatted size string (e.g., "1.23MB").
    """
    if bytes_size is None:
        return "0.00MB"
    return f"{int(bytes_size) / (1024 * 1024):.2f}MB"


def truncate_text(text: str | None, length: int = 50) -> str:
    """Truncate text to specified length with ellipsis.

    Args:
        text: Text to truncate.
        length: Maximum length.

    Returns:
        Truncated text with "..." if longer than length.
    """
    if text is None:
        return ""
    return text[:length] + "..." if len(text) > length else text


def format_timestamp(ts: Any) -> str:
    """Format timestamp to readable string.

    Args:
        ts: Timestamp (various formats supported).

    Returns:
        Formatted timestamp string.
    """
    if ts is None:
        return ""
    if isinstance(ts, str):
        # Already formatted
        if "T" in ts and len(ts) > 19:
            # ISO format - extract HH:MM:SS
            return ts.split("T")[1].split(".")[0]
        return ts
    return str(ts)


def format_datetime(dt: Any) -> str:
    """Format datetime to readable string.

    Args:
        dt: Datetime (various formats supported).

    Returns:
        Formatted datetime string.
    """
    if dt is None:
        return ""
    if isinstance(dt, str):
        # Try to parse ISO format
        if "T" in dt:
            return dt.split("T")[0] + " " + dt.split("T")[1].split(".")[0]
        return dt
    return str(dt)


def format_event_status(status: str | None) -> str:
    """Format event status to CSS-friendly class.

    Args:
        status: Event status string.

    Returns:
        CSS-friendly status class.
    """
    if status is None:
        return "unknown"
    return status.lower().replace(" ", "-")


def to_json(value: Any) -> str:
    """Convert value to JSON string for HTML attribute.

    Args:
        value: Value to serialize.

    Returns:
        JSON string.
    """
    import json

    return json.dumps(value)


def group_by_agent(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group events by agent_id.

    Args:
        events: List of event dictionaries.

    Returns:
        Dictionary with agent_id keys and event lists as values.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        agent_id = event.get("agent_id", "unknown")
        if agent_id not in grouped:
            grouped[agent_id] = []
        grouped[agent_id].append(event)
    return grouped
