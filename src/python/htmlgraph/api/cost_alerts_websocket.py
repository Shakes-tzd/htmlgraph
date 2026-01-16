"""
WebSocket Integration for Real-Time Cost Alerts - Phase 3.1

Streams cost monitoring alerts to clients with:
- <1s latency (critical requirement)
- Real-time budget warnings
- Cost trajectory predictions
- Per-model and per-tool cost breakdowns

Integrates with:
- WebSocketManager for connection handling
- CostMonitor for alert generation
- EventSubscriptionFilter for cost-specific filtering
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from htmlgraph.analytics.cost_monitor import CostMonitor
from htmlgraph.api.websocket import EventSubscriptionFilter, WebSocketManager

logger = logging.getLogger(__name__)


class CostAlertFilter(EventSubscriptionFilter):
    """Extended filter for cost alert subscriptions."""

    def __init__(
        self,
        session_id: str | None = None,
        alert_types: list[str] | None = None,
        min_severity: str = "info",
        cost_threshold_usd: float | None = None,
    ):
        """
        Initialize cost alert filter.

        Args:
            session_id: Filter by session
            alert_types: Filter by alert types (e.g., ["budget_warning", "breach"])
            min_severity: Minimum severity level ("info", "warning", "critical")
            cost_threshold_usd: Alert on costs >= threshold
        """
        # Initialize parent with cost-specific event types
        super().__init__(
            event_types=["cost_alert"],
            session_id=session_id,
            statuses=["alert"],
        )
        self.alert_types = alert_types or [
            "budget_warning",
            "trajectory_overage",
            "model_overage",
            "breach",
        ]
        self.min_severity = min_severity
        self.cost_threshold_usd = cost_threshold_usd

    def matches_cost_alert(self, alert: dict[str, Any]) -> bool:
        """Check if alert matches all cost-specific filters."""
        # Alert type filter
        if alert.get("alert_type") not in self.alert_types:
            return False

        # Severity filter (info < warning < critical)
        severity_levels = {"info": 0, "warning": 1, "critical": 2}
        alert_severity = severity_levels.get(alert.get("severity", "info"), 0)
        min_level = severity_levels.get(self.min_severity, 0)
        if alert_severity < min_level:
            return False

        # Cost threshold filter
        if self.cost_threshold_usd:
            if alert.get("current_cost_usd", 0) < self.cost_threshold_usd:
                return False

        return True


class CostAlertStreamManager:
    """
    Manages real-time cost alert streaming via WebSocket.

    Features:
    - <1s latency for alert delivery
    - Per-client cost alert filtering
    - Alert aggregation and deduplication
    - Trajectory prediction streaming
    - Cost breakdown updates
    """

    def __init__(
        self,
        websocket_manager: WebSocketManager,
        cost_monitor: CostMonitor,
        poll_interval_ms: float = 100.0,
        alert_batch_size: int = 10,
    ):
        """
        Initialize cost alert stream manager.

        Args:
            websocket_manager: WebSocketManager for connection handling
            cost_monitor: CostMonitor for cost data
            poll_interval_ms: How often to check for new alerts
            alert_batch_size: Max alerts per batch
        """
        self.websocket_manager = websocket_manager
        self.cost_monitor = cost_monitor
        self.poll_interval_ms = poll_interval_ms / 1000.0  # Convert to seconds
        self.alert_batch_size = alert_batch_size

        # Track last seen alert timestamp per session
        self.last_alert_timestamp: dict[str, str] = {}

    async def stream_cost_alerts(
        self, session_id: str, client_id: str, cost_alert_filter: CostAlertFilter
    ) -> None:
        """
        Stream cost alerts to a connected client.

        Maintains <1s latency by:
        - Quick database queries (indexed on timestamp)
        - Efficient batching
        - Minimal processing per alert

        Args:
            session_id: Session ID
            client_id: Client ID
            cost_alert_filter: Subscription filter for alerts
        """
        if (
            session_id not in self.websocket_manager.connections
            or client_id not in self.websocket_manager.connections[session_id]
        ):
            logger.warning(f"Client not found: {session_id}/{client_id}")
            return

        client = self.websocket_manager.connections[session_id][client_id]
        last_alert_time = self.last_alert_timestamp.get(
            session_id, "1970-01-01T00:00:00Z"
        )
        consecutive_empty_polls = 0
        max_empty_polls = 20

        try:
            while True:
                try:
                    # Fetch new alerts since last poll (rapid query)
                    alerts = await self._fetch_new_alerts(
                        session_id, last_alert_time, cost_alert_filter
                    )

                    if alerts:
                        consecutive_empty_polls = 0
                        last_alert_time = alerts[-1]["timestamp"]
                        self.last_alert_timestamp[session_id] = last_alert_time

                        # Batch alerts for sending
                        for i in range(0, len(alerts), self.alert_batch_size):
                            batch = alerts[i : i + self.alert_batch_size]

                            message = {
                                "type": "cost_alerts",
                                "session_id": session_id,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "alerts": batch,
                                "count": len(batch),
                            }

                            # Send with timestamp for latency tracking
                            message["sent_at"] = datetime.now(timezone.utc).isoformat()

                            try:
                                await client.websocket.send_json(message)
                                client.events_sent += 1
                                client.bytes_sent += len(json.dumps(message))
                                self.websocket_manager.metrics[
                                    "total_events_broadcast"
                                ] += 1
                                self.websocket_manager.metrics["total_bytes_sent"] += (
                                    len(json.dumps(message))
                                )
                            except Exception as e:
                                logger.error(f"Failed to send alert: {e}")
                                return
                    else:
                        consecutive_empty_polls += 1

                    # Adaptive polling: increase interval if no alerts
                    if consecutive_empty_polls > max_empty_polls:
                        poll_interval = min(self.poll_interval_ms * 2, 1.0)
                    else:
                        poll_interval = self.poll_interval_ms

                    await asyncio.sleep(poll_interval)

                except Exception as e:
                    logger.error(f"Error in cost alert streaming: {e}")
                    await asyncio.sleep(self.poll_interval_ms)

        except asyncio.CancelledError:
            logger.info(f"Cost alert stream cancelled for {session_id}/{client_id}")
        except Exception as e:
            logger.error(f"Unexpected error in cost alert stream: {e}")

    async def _fetch_new_alerts(
        self,
        session_id: str,
        since_timestamp: str,
        cost_alert_filter: CostAlertFilter,
    ) -> list[dict[str, Any]]:
        """
        Fetch new cost alerts for a session.

        Optimized for <1s latency with indexed queries.

        Args:
            session_id: Session ID
            since_timestamp: Only fetch alerts after this timestamp
            cost_alert_filter: Filter for alert types

        Returns:
            List of alert dictionaries
        """
        conn = self.cost_monitor.connect()
        cursor = conn.cursor()

        try:
            # Query with composite index on (session_id, timestamp DESC)
            cursor.execute(
                """
                SELECT event_id, session_id, alert_type, message,
                       current_cost_usd, budget_usd, severity, timestamp
                FROM cost_events
                WHERE session_id = ? AND alert_type IS NOT NULL
                  AND timestamp > ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (session_id, since_timestamp, self.alert_batch_size * 2),
            )

            alerts = []
            for row in cursor.fetchall():
                alert_dict = {
                    "alert_id": row["event_id"],
                    "alert_type": row["alert_type"],
                    "session_id": row["session_id"],
                    "message": row["message"],
                    "current_cost_usd": row["current_cost_usd"],
                    "budget_usd": row["budget_usd"],
                    "severity": row["severity"],
                    "timestamp": row["timestamp"],
                }

                # Apply custom cost alert filters
                if cost_alert_filter.matches_cost_alert(alert_dict):
                    alerts.append(alert_dict)

            return alerts

        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []

    async def stream_cost_breakdown(
        self, session_id: str, client_id: str, update_interval_seconds: float = 5.0
    ) -> None:
        """
        Stream cost breakdown updates to a client.

        Sends periodic updates of cost by model, tool, and agent.

        Args:
            session_id: Session ID
            client_id: Client ID
            update_interval_seconds: How often to send updates
        """
        if (
            session_id not in self.websocket_manager.connections
            or client_id not in self.websocket_manager.connections[session_id]
        ):
            return

        client = self.websocket_manager.connections[session_id][client_id]

        try:
            while True:
                try:
                    # Get current cost breakdown
                    breakdown = self.cost_monitor.get_cost_breakdown(session_id)

                    message = {
                        "type": "cost_breakdown",
                        "session_id": session_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "by_model": breakdown.by_model,
                        "by_tool": breakdown.by_tool,
                        "by_agent": breakdown.by_agent,
                        "by_subagent_type": breakdown.by_subagent_type,
                        "total_cost_usd": breakdown.total_cost_usd,
                        "total_tokens": breakdown.total_tokens,
                    }

                    await client.websocket.send_json(message)
                    client.events_sent += 1
                    self.websocket_manager.metrics["total_events_broadcast"] += 1

                except Exception as e:
                    logger.error(f"Error sending cost breakdown: {e}")
                    return

                await asyncio.sleep(update_interval_seconds)

        except asyncio.CancelledError:
            logger.info(f"Cost breakdown stream cancelled for {session_id}/{client_id}")

    async def stream_cost_trajectory(
        self,
        session_id: str,
        client_id: str,
        update_interval_seconds: float = 10.0,
        lookback_minutes: int = 5,
    ) -> None:
        """
        Stream cost trajectory predictions to a client.

        Periodically recalculates cost trajectory and sends predictions.

        Args:
            session_id: Session ID
            client_id: Client ID
            update_interval_seconds: How often to update predictions
            lookback_minutes: How far back to analyze
        """
        if (
            session_id not in self.websocket_manager.connections
            or client_id not in self.websocket_manager.connections[session_id]
        ):
            return

        client = self.websocket_manager.connections[session_id][client_id]

        try:
            while True:
                try:
                    # Get trajectory prediction
                    prediction = self.cost_monitor.predict_cost_trajectory(
                        session_id, lookback_minutes=lookback_minutes
                    )

                    message = {
                        "type": "cost_trajectory",
                        "session_id": session_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "prediction": prediction,
                    }

                    if prediction.get("prediction_available"):
                        await client.websocket.send_json(message)
                        client.events_sent += 1
                        self.websocket_manager.metrics["total_events_broadcast"] += 1

                except Exception as e:
                    logger.error(f"Error sending cost trajectory: {e}")
                    return

                await asyncio.sleep(update_interval_seconds)

        except asyncio.CancelledError:
            logger.info(
                f"Cost trajectory stream cancelled for {session_id}/{client_id}"
            )


async def create_cost_alert_subscription(
    session_id: str,
    client_id: str,
    websocket_manager: WebSocketManager,
    cost_monitor: CostMonitor,
    alert_types: list[str] | None = None,
    min_severity: str = "warning",
) -> CostAlertStreamManager:
    """
    Create a cost alert subscription for a WebSocket client.

    Factory function to set up cost alert streaming.

    Args:
        session_id: Session ID
        client_id: Client ID
        websocket_manager: WebSocketManager instance
        cost_monitor: CostMonitor instance
        alert_types: Which alert types to subscribe to
        min_severity: Minimum alert severity

    Returns:
        CostAlertStreamManager instance
    """
    manager = CostAlertStreamManager(websocket_manager, cost_monitor)
    filter_obj = CostAlertFilter(
        session_id=session_id,
        alert_types=alert_types,
        min_severity=min_severity,
    )

    # Start streaming tasks
    asyncio.create_task(manager.stream_cost_alerts(session_id, client_id, filter_obj))
    asyncio.create_task(manager.stream_cost_breakdown(session_id, client_id))
    asyncio.create_task(manager.stream_cost_trajectory(session_id, client_id))

    return manager
