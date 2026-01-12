"""Base spawner class with common functionality for all AI spawners."""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.orchestration.live_events import LiveEventPublisher
    from htmlgraph.sdk import SDK


@dataclass
class AIResult:
    """Result from AI CLI execution."""

    success: bool
    response: str
    tokens_used: int | None
    error: str | None
    raw_output: dict | list | str | None
    tracked_events: list[dict] | None = None  # Events tracked in HtmlGraph


class BaseSpawner:
    """
    Base class for AI spawners with common functionality.

    Provides:
    - Live event publishing for WebSocket streaming
    - SDK initialization with parent session support
    - Common error handling patterns
    """

    def __init__(self) -> None:
        """Initialize spawner."""
        self._live_publisher: LiveEventPublisher | None = None

    def _get_live_publisher(self) -> "LiveEventPublisher | None":
        """
        Get LiveEventPublisher instance for real-time WebSocket streaming.

        Returns None if publisher unavailable (optional dependency).
        """
        if self._live_publisher is None:
            try:
                from htmlgraph.orchestration.live_events import LiveEventPublisher

                self._live_publisher = LiveEventPublisher()
            except Exception:
                # Live events are optional
                pass
        return self._live_publisher

    def _publish_live_event(
        self,
        event_type: str,
        spawner_type: str,
        **kwargs: str | int | float | bool | None,
    ) -> None:
        """
        Publish a live event for WebSocket streaming.

        Silently fails if publisher unavailable (optional feature).
        """
        publisher = self._get_live_publisher()
        if publisher is None:
            return

        parent_event_id = os.getenv("HTMLGRAPH_PARENT_EVENT")

        try:
            if event_type == "spawner_start":
                publisher.spawner_start(
                    spawner_type=spawner_type,
                    prompt=str(kwargs.get("prompt", "")),
                    parent_event_id=parent_event_id,
                    model=str(kwargs.get("model", "")) if kwargs.get("model") else None,
                )
            elif event_type == "spawner_phase":
                progress_val = kwargs.get("progress")
                publisher.spawner_phase(
                    spawner_type=spawner_type,
                    phase=str(kwargs.get("phase", "executing")),
                    progress=int(progress_val) if progress_val is not None else None,
                    details=str(kwargs.get("details", ""))
                    if kwargs.get("details")
                    else None,
                    parent_event_id=parent_event_id,
                )
            elif event_type == "spawner_complete":
                duration_val = kwargs.get("duration")
                tokens_val = kwargs.get("tokens")
                publisher.spawner_complete(
                    spawner_type=spawner_type,
                    success=bool(kwargs.get("success", False)),
                    duration_seconds=float(duration_val)
                    if duration_val is not None
                    else None,
                    response_preview=str(kwargs.get("response", ""))[:200]
                    if kwargs.get("response")
                    else None,
                    tokens_used=int(tokens_val) if tokens_val is not None else None,
                    error=str(kwargs.get("error", "")) if kwargs.get("error") else None,
                    parent_event_id=parent_event_id,
                )
            elif event_type == "spawner_tool_use":
                publisher.spawner_tool_use(
                    spawner_type=spawner_type,
                    tool_name=str(kwargs.get("tool_name", "unknown")),
                    parent_event_id=parent_event_id,
                )
            elif event_type == "spawner_message":
                publisher.spawner_message(
                    spawner_type=spawner_type,
                    message=str(kwargs.get("message", "")),
                    role=str(kwargs.get("role", "assistant")),
                    parent_event_id=parent_event_id,
                )
        except Exception:
            # Live events should never break spawner execution
            pass

    def _get_sdk(self) -> "SDK | None":
        """
        Get SDK instance for HtmlGraph tracking with parent session support.

        Returns None if SDK unavailable.
        """
        try:
            from htmlgraph.sdk import SDK

            # Read parent session context from environment
            parent_session = os.getenv("HTMLGRAPH_PARENT_SESSION")
            parent_agent = os.getenv("HTMLGRAPH_PARENT_AGENT")

            # Create SDK with parent session context
            sdk = SDK(
                agent=f"spawner-{parent_agent}" if parent_agent else "spawner",
                parent_session=parent_session,  # Pass parent session
            )

            return sdk

        except Exception:
            # SDK unavailable or not properly initialized (optional dependency)
            # This happens in test contexts without active sessions
            # Don't log error to avoid noise in tests
            return None

    def _get_parent_context(self) -> tuple[str | None, int]:
        """
        Get parent activity context for event tracking.

        Returns:
            Tuple of (parent_activity_id, nesting_depth)
        """
        parent_activity = os.getenv("HTMLGRAPH_PARENT_ACTIVITY")
        nesting_depth_str = os.getenv("HTMLGRAPH_NESTING_DEPTH", "0")
        nesting_depth = int(nesting_depth_str) if nesting_depth_str.isdigit() else 0
        return parent_activity, nesting_depth

    def _track_activity(
        self,
        sdk: "SDK",
        tool: str,
        summary: str,
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Track activity in HtmlGraph with parent context.

        Args:
            sdk: SDK instance
            tool: Tool name
            summary: Activity summary
            payload: Activity payload (will be enriched with parent context)
            **kwargs: Additional arguments for track_activity
        """
        if payload is None:
            payload = {}

        # Enrich with parent context
        parent_activity, nesting_depth = self._get_parent_context()
        if parent_activity:
            payload["parent_activity"] = parent_activity
        if nesting_depth > 0:
            payload["nesting_depth"] = nesting_depth

        try:
            sdk.track_activity(tool=tool, summary=summary, payload=payload, **kwargs)
        except Exception:
            # Tracking failure should not break execution
            pass
