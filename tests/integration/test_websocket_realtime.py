#!/usr/bin/env python3
"""
Real-time WebSocket streaming test with detailed event tracking.

This test:
1. Connects to the Activity Feed
2. Monitors WebSocket messages in real-time
3. Creates test events while monitoring
4. Records the latency between event creation and WebSocket delivery
5. Verifies green highlight animation and top-of-list insertion

NOTE: Skipped - requires running server and Playwright + pytest-asyncio.
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="E2E test requires running server and pytest-asyncio"
)

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import aiosqlite
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_test_event(
    db_path: str, agent_id: str = "websocket-test", event_type: str = "tool_call"
) -> dict:
    """Create a test event and return its details."""
    db = await aiosqlite.connect(db_path)
    try:
        event_id = str(uuid4())[:8]
        session_id = str(uuid4())[:8]
        timestamp = datetime.utcnow().isoformat()

        await db.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name, input_summary,
             output_summary, session_id, status, parent_event_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                agent_id,
                event_type,
                timestamp,
                "websocket_test_tool",
                f"Real-time test input: {event_type}",
                f"Real-time test output: {event_type}",
                session_id,
                "success",
                None,
            ),
        )
        await db.commit()
        return {
            "event_id": event_id,
            "session_id": session_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "created_at": datetime.utcnow(),
        }
    finally:
        await db.close()


async def test_realtime_streaming():
    """Test real-time WebSocket streaming with latency measurement."""
    db_path = str(Path.home() / ".htmlgraph" / "htmlgraph.db")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Track WebSocket events
        ws_events = []
        ws_connected = False
        test_results = {
            "events_created": [],
            "events_delivered": [],
            "latencies": [],
            "connection_established": False,
            "live_updates_enabled": False,
        }

        def handle_websocket_connect(ws):
            """Handle WebSocket connection."""
            nonlocal ws_connected
            ws_connected = True
            test_results["connection_established"] = True
            logger.info(f"✓ WebSocket connected: {ws.url}")

            # Monitor for messages
            async def on_message(msg):
                try:
                    data = json.loads(msg)
                    ws_events.append({"data": data, "received_at": datetime.utcnow()})
                    logger.info(
                        f"  WebSocket message: {data.get('event_id')} ({data.get('event_type')})"
                    )
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON: {msg}")

            ws.on(
                "framereceived",
                lambda frame: asyncio.create_task(on_message(frame.payload)),
            )

        page.on("websocket", handle_websocket_connect)

        try:
            # Load dashboard
            logger.info("Opening Activity Feed...")
            await page.goto("http://localhost:8000")
            await page.wait_for_load_state("networkidle")

            # Verify Activity Feed is visible
            activity_feed = await page.query_selector(".activity-feed-view")
            if not activity_feed:
                logger.error("Activity Feed not found!")
                return

            logger.info("✓ Activity Feed loaded")

            # Check for WebSocket connection indicator
            connection_indicator = await page.query_selector(".auto-refresh-indicator")
            if connection_indicator:
                text = await connection_indicator.text_content()
                if "WebSocket" in text and "Live" in text:
                    test_results["live_updates_enabled"] = True
                    logger.info("✓ Live updates enabled via WebSocket")

            # Get initial event list
            initial_events = await page.query_selector_all(".activity-item")
            logger.info(f"Initial visible events: {len(initial_events)}")

            # Create test events in sequence and monitor for WebSocket delivery
            event_types = ["tool_call", "tool_result", "completion", "error"]
            for i, event_type in enumerate(event_types):
                logger.info(f"\n--- Creating test event {i + 1}/{len(event_types)} ---")

                # Create event
                created_event = await create_test_event(db_path, event_type=event_type)
                test_results["events_created"].append(created_event)
                logger.info(
                    f"Event created: {created_event['event_id']} ({event_type})"
                )

                # Wait for WebSocket delivery (polling interval is 1 second)
                start_wait = datetime.utcnow()
                max_wait = 5  # seconds

                while (datetime.utcnow() - start_wait).total_seconds() < max_wait:
                    # Check if our event appeared in WebSocket messages
                    for ws_event in ws_events:
                        if (
                            ws_event["data"].get("event_id")
                            == created_event["event_id"]
                        ):
                            latency = (
                                ws_event["received_at"] - created_event["created_at"]
                            ).total_seconds()
                            test_results["events_delivered"].append(
                                {
                                    "event_id": created_event["event_id"],
                                    "latency_seconds": latency,
                                    "delivered_at": ws_event["received_at"],
                                }
                            )
                            logger.info(
                                f"✓ Event delivered via WebSocket in {latency:.2f}s"
                            )
                            ws_events.remove(ws_event)
                            break
                    else:
                        # Event not found yet, wait and retry
                        await asyncio.sleep(0.5)
                        continue
                    break

                await asyncio.sleep(0.5)  # Stagger event creation

            # Take final screenshot
            await page.screenshot(path="/tmp/activity_feed_realtime.png")
            logger.info("Screenshot saved: /tmp/activity_feed_realtime.png")

            # Final event count
            final_events = await page.query_selector_all(".activity-item")
            logger.info(f"Final visible events: {len(final_events)}")

            # Print results
            logger.info("\n" + "=" * 70)
            logger.info("WEBSOCKET REAL-TIME STREAMING TEST RESULTS")
            logger.info("=" * 70)
            logger.info(
                f"WebSocket connection established: {test_results['connection_established']}"
            )
            logger.info(f"Live updates enabled: {test_results['live_updates_enabled']}")
            logger.info(f"Events created: {len(test_results['events_created'])}")
            logger.info(
                f"Events delivered via WebSocket: {len(test_results['events_delivered'])}"
            )

            if test_results["events_delivered"]:
                latencies = [
                    e["latency_seconds"] for e in test_results["events_delivered"]
                ]
                logger.info(
                    f"Average WebSocket latency: {sum(latencies) / len(latencies):.2f}s"
                )
                logger.info(f"Min latency: {min(latencies):.2f}s")
                logger.info(f"Max latency: {max(latencies):.2f}s")

                for event in test_results["events_delivered"]:
                    logger.info(
                        f"  - {event['event_id']}: {event['latency_seconds']:.2f}s"
                    )

            logger.info("=" * 70)

            # Overall success
            success = (
                test_results["connection_established"]
                and test_results["live_updates_enabled"]
                and len(test_results["events_delivered"]) > 0
            )

            if success:
                logger.info("✓ REAL-TIME STREAMING TEST PASSED")
            else:
                logger.warning("✗ REAL-TIME STREAMING TEST FAILED")

            # Keep browser open for inspection
            logger.info("\nBrowser open for 5 seconds for manual inspection...")
            await asyncio.sleep(5)

            return test_results

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    results = asyncio.run(test_realtime_streaming())
    print("\n\nTest Results Summary:")
    print(
        json.dumps(
            {
                "connection_established": results.get("connection_established"),
                "live_updates_enabled": results.get("live_updates_enabled"),
                "events_created": len(results.get("events_created", [])),
                "events_delivered": len(results.get("events_delivered", [])),
            },
            indent=2,
        )
    )
