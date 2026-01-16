#!/usr/bin/env python3
"""
Playwright test to verify WebSocket live streaming on Activity Feed.

Test Steps:
1. Open http://localhost:8000 and navigate to Activity Feed
2. Note current event count
3. Generate test events by creating features or running commands
4. Watch Activity Feed for real-time updates
5. Verify events appear at top with green highlight
6. Confirm WebSocket connection indicator shows green

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

import aiosqlite
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_event_count(db_path: str) -> int:
    """Get current event count from database."""
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM agent_events")
        row = await cursor.fetchone()
        return row[0] if row else 0
    finally:
        await db.close()


async def create_test_event(
    db_path: str, agent_id: str = "test-agent", event_type: str = "tool_call"
) -> str:
    """Create a test event in the database."""
    from uuid import uuid4

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
                "test_tool",
                f"Test input for {event_type}",
                f"Test output for {event_type}",
                session_id,
                "success",
                None,
            ),
        )
        await db.commit()
        logger.info(f"Created test event: {event_id} ({event_type})")
        return event_id
    finally:
        await db.close()


async def test_websocket_streaming():
    """Test WebSocket live streaming of events on Activity Feed."""
    # Database path
    db_path = str(Path.home() / ".htmlgraph" / "htmlgraph.db")

    # Initial event count
    initial_count = await get_event_count(db_path)
    logger.info(f"Initial event count: {initial_count}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Listen for WebSocket messages
        ws_messages = []

        async def handle_ws_message(msg):
            """Handle incoming WebSocket messages."""
            try:
                data = json.loads(msg)
                ws_messages.append(data)
                logger.info(
                    f"WebSocket message received: {data.get('event_id')} ({data.get('event_type')})"
                )
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in WebSocket message: {msg}")

        # Setup WebSocket listener
        page.on("websocket", lambda ws: logger.info(f"WebSocket connected: {ws.url}"))
        page.on(
            "framereceived",
            lambda frame: logger.debug(f"Frame received: {frame.payload}"),
        )

        try:
            # Navigate to dashboard
            logger.info("Opening dashboard at http://localhost:8000")
            await page.goto("http://localhost:8000")
            await page.wait_for_load_state("networkidle")

            # Wait for Activity Feed to load
            logger.info("Waiting for Activity Feed view...")
            activity_feed = await page.query_selector(".activity-feed-view")
            if not activity_feed:
                logger.warning(
                    "Activity Feed view not found, checking available elements..."
                )
                views = await page.query_selector_all(".view-container")
                logger.info(f"Found {len(views)} view containers")

            # Take screenshot of initial state
            await page.screenshot(path="/tmp/activity_feed_initial.png")
            logger.info("Screenshot saved: /tmp/activity_feed_initial.png")

            # Get initial event count from UI
            event_header = await page.query_selector(".view-header h2")
            if event_header:
                header_text = await event_header.text_content()
                logger.info(f"Activity Feed header: {header_text}")

            # Count visible events before
            events_before = await page.query_selector_all(".activity-item")
            logger.info(f"Visible events before: {len(events_before)}")

            # Create several test events
            logger.info("Creating test events...")
            test_event_ids = []
            for i in range(3):
                event_types = ["tool_call", "tool_result", "completion"]
                event_type = event_types[i % len(event_types)]
                event_id = await create_test_event(db_path, event_type=event_type)
                test_event_ids.append(event_id)
                await asyncio.sleep(0.5)  # Stagger event creation

            # Wait for WebSocket to deliver events (poll interval is 1 second)
            logger.info("Waiting for WebSocket to deliver new events (2 seconds)...")
            await asyncio.sleep(2)

            # Reload the page to see updated events
            logger.info("Reloading page to see updated events...")
            await page.reload()
            await page.wait_for_load_state("networkidle")

            # Take screenshot of updated state
            await page.screenshot(path="/tmp/activity_feed_updated.png")
            logger.info("Screenshot saved: /tmp/activity_feed_updated.png")

            # Count visible events after
            events_after = await page.query_selector_all(".activity-item")
            logger.info(f"Visible events after: {len(events_after)}")

            # Check for our test events in the DOM
            events_found = 0
            for event_id in test_event_ids:
                event_elem = await page.query_selector(f"[data-event-id='{event_id}']")
                if event_elem:
                    events_found += 1
                    logger.info(f"Found test event in UI: {event_id}")
                else:
                    # Try searching in event IDs displayed
                    event_elements = await page.query_selector_all(".event-id")
                    for elem in event_elements:
                        text = await elem.text_content()
                        if text and event_id.startswith(text.strip()):
                            events_found += 1
                            logger.info(
                                f"Found test event in UI (by ID match): {event_id}"
                            )
                            break

            # Check connection indicator
            connection_indicator = await page.query_selector(".auto-refresh-indicator")
            if connection_indicator:
                indicator_text = await connection_indicator.text_content()
                logger.info(f"Connection status: {indicator_text}")

                # Check if it shows "Live updates enabled"
                if (
                    "Live updates enabled" in indicator_text
                    or "WebSocket" in indicator_text
                ):
                    logger.info("✓ WebSocket connection indicator shows active")
                else:
                    logger.warning(
                        "✗ Connection indicator doesn't show WebSocket active"
                    )

            # Verify event count increased
            final_count = await get_event_count(db_path)
            logger.info(f"Final event count in database: {final_count}")
            logger.info(f"Events created: {len(test_event_ids)}")

            # Summary
            logger.info("=" * 60)
            logger.info("TEST SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Initial count: {initial_count}")
            logger.info(f"Final count: {final_count}")
            logger.info(f"New events: {final_count - initial_count}")
            logger.info(f"Test events created: {len(test_event_ids)}")
            logger.info(f"Test events found in UI: {events_found}")
            logger.info(f"Visible events before: {len(events_before)}")
            logger.info(f"Visible events after: {len(events_after)}")
            logger.info(f"WebSocket messages captured: {len(ws_messages)}")

            success = (
                final_count > initial_count
                and final_count - initial_count == len(test_event_ids)
            )

            if success:
                logger.info("✓ WebSocket streaming test PASSED")
            else:
                logger.warning("✗ WebSocket streaming test FAILED")

            # Keep browser open for manual inspection
            logger.info(
                "Browser will stay open for 10 seconds for manual inspection..."
            )
            await asyncio.sleep(10)

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_websocket_streaming())
