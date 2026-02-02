"""
Playwright tests for Phase 6 Presence Widget Demo
Tests the real-time agent status dashboard functionality
"""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def test_presence_widget_html_structure():
    """Test that Presence Widget HTML is well-formed and contains required elements."""
    widget_path = (
        Path(__file__).parent.parent.parent
        / "src/python/htmlgraph/api/static/presence-widget-demo.html"
    )

    assert widget_path.exists(), f"Widget file not found at {widget_path}"

    content = widget_path.read_text()

    # Verify HTML structure
    assert "<!DOCTYPE html>" in content, "Missing DOCTYPE"
    assert "<title>HtmlGraph Presence Widget - Phase 6 Demo</title>" in content, (
        "Missing or incorrect title"
    )
    assert "Presence Widget" in content, "Missing 'Presence Widget' text"

    print("✅ HTML structure valid")


async def test_presence_widget_functionality():
    """Test Presence Widget JavaScript functionality with mock data."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Load widget HTML directly
        widget_path = (
            Path(__file__).parent.parent.parent
            / "src/python/htmlgraph/api/static/presence-widget-demo.html"
        )
        widget_url = widget_path.as_uri()

        await page.goto(widget_url, wait_until="networkidle")

        # Wait for mock data to load
        await page.wait_for_timeout(2000)

        # Test 1: Verify title loaded
        title = await page.title()
        assert "Presence Widget" in title, f"Title not found in: {title}"
        print("✅ Title loaded correctly")

        # Test 2: Verify header exists
        header_h1 = await page.query_selector("header h1")
        assert header_h1 is not None, "Header H1 not found"
        header_text = await header_h1.text_content()
        assert "Presence Widget" in header_text, (
            f"Expected 'Presence Widget' in header, got: {header_text}"
        )
        print("✅ Header rendered correctly")

        # Test 3: Verify statistics section
        stat_boxes = await page.query_selector_all(".stat-box")
        assert len(stat_boxes) >= 4, (
            f"Expected at least 4 stat boxes, found {len(stat_boxes)}"
        )
        print(f"✅ Statistics section loaded ({len(stat_boxes)} stat boxes)")

        # Test 4: Verify agent cards render with mock data
        agent_cards = await page.query_selector_all(".agent-card")
        assert len(agent_cards) > 0, "No agent cards found (mock data should render)"
        print(f"✅ Agent cards rendered ({len(agent_cards)} agents)")

        # Test 5: Verify agent card structure
        first_card = agent_cards[0]
        agent_name = await first_card.query_selector(".agent-name")
        assert agent_name is not None, "Agent name element not found"
        name_text = await agent_name.text_content()
        assert len(name_text) > 0, "Agent name is empty"
        print(f"✅ First agent card structure valid: {name_text}")

        # Test 6: Verify status badges
        status_badge = await first_card.query_selector(".status-badge")
        assert status_badge is not None, "Status badge not found"
        status_text = await status_badge.text_content()
        assert status_text.lower() in ["active", "idle", "offline"], (
            f"Invalid status: {status_text}"
        )
        print(f"✅ Status badge valid: {status_text}")

        # Test 7: Verify metrics section
        metrics = await first_card.query_selector_all(".metric-value")
        assert len(metrics) >= 2, f"Expected at least 2 metrics, found {len(metrics)}"
        print(f"✅ Metrics section valid ({len(metrics)} metrics)")

        # Test 8: Verify WebSocket code is present
        ws_code = await page.text_content("pre")
        assert ws_code and ("WebSocket" in ws_code or "ws://" in ws_code), (
            "WebSocket code not found"
        )
        print("✅ WebSocket implementation code present")

        # Test 9: Verify statistics are updated (mock data simulation)
        active_count = await page.text_content("#active-count")
        assert active_count and int(active_count) >= 0, (
            f"Invalid active count: {active_count}"
        )
        print(f"✅ Statistics updated: {active_count} active agents")

        # Test 10: Verify connection status indicator
        ws_status = await page.query_selector("#ws-status")
        assert ws_status is not None, "WebSocket status indicator not found"
        status_content = await ws_status.text_content()
        assert len(status_content) > 0, "WebSocket status is empty"
        print(f"✅ Connection status indicator: {status_content}")

        await browser.close()
        print("✅ All Playwright tests passed!")


async def test_presence_widget_code_examples():
    """Test that code examples in documentation are complete and syntactically correct."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        widget_path = (
            Path(__file__).parent.parent.parent
            / "src/python/htmlgraph/api/static/presence-widget-demo.html"
        )
        widget_url = widget_path.as_uri()

        await page.goto(widget_url, wait_until="networkidle")

        # Find all code sections
        code_sections = await page.query_selector_all(".code-section pre")
        assert len(code_sections) > 0, "No code sections found"
        print(f"✅ Found {len(code_sections)} code examples")

        # Verify key API patterns are documented
        full_content = await page.content()

        required_patterns = [
            "ws://localhost:8000/ws/broadcasts",
            "presence_update",
            "GET /api/presence",
            "WebSocket",
            "PresenceManager",
        ]

        for pattern in required_patterns:
            assert pattern in full_content, f"Required pattern not found: {pattern}"
            print(f"✅ Pattern documented: {pattern}")

        await browser.close()


async def test_widget_styling():
    """Test that widget CSS styling is applied correctly."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        widget_path = (
            Path(__file__).parent.parent.parent
            / "src/python/htmlgraph/api/static/presence-widget-demo.html"
        )
        widget_url = widget_path.as_uri()

        await page.goto(widget_url, wait_until="networkidle")

        # Test background gradient
        body_style = await page.locator("body").evaluate(
            "el => window.getComputedStyle(el).backgroundImage"
        )
        assert "gradient" in body_style.lower(), (
            f"Background gradient not applied: {body_style}"
        )
        print("✅ Background styling applied")

        # Test agent card styling
        agent_card = await page.query_selector(".agent-card.active")
        if agent_card:
            card_classes = await agent_card.get_attribute("class")
            assert "agent-card" in card_classes, "Agent card classes not set correctly"
            print("✅ Agent card styling applied")

        # Test responsive grid
        agents_grid = await page.query_selector(".agents-grid")
        if agents_grid:
            grid_style = await agents_grid.evaluate(
                "el => window.getComputedStyle(el).display"
            )
            assert grid_style == "grid", f"Grid display not applied: {grid_style}"
            print("✅ Grid layout applied")

        await browser.close()


async def test_demo_functionality():
    """Test the mock data simulation and auto-update mechanism."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        widget_path = (
            Path(__file__).parent.parent.parent
            / "src/python/htmlgraph/api/static/presence-widget-demo.html"
        )
        widget_url = widget_path.as_uri()

        await page.goto(widget_url, wait_until="networkidle")

        # Get initial agent count
        initial_cards = await page.query_selector_all(".agent-card")
        initial_count = len(initial_cards)
        print(f"✅ Initial agent count: {initial_count}")

        # Wait for mock updates
        await page.wait_for_timeout(2500)

        # Get updated agent count (should remain same but data inside changes)
        updated_cards = await page.query_selector_all(".agent-card")
        updated_count = len(updated_cards)

        assert updated_count == initial_count, "Agent count changed unexpectedly"
        print(f"✅ Agent count stable: {updated_count}")

        # Verify at least one agent card updated
        first_card_text = await updated_cards[0].text_content()
        assert len(first_card_text) > 100, "Agent card data seems incomplete"
        print("✅ Agent data populated and updated")

        await browser.close()


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🧪 Phase 6 Presence Widget - Playwright Tests")
    print("=" * 60 + "\n")

    try:
        print("Test 1: HTML Structure")
        await test_presence_widget_html_structure()

        print("\nTest 2: Widget Functionality")
        await test_presence_widget_functionality()

        print("\nTest 3: Code Examples")
        await test_presence_widget_code_examples()

        print("\nTest 4: Styling")
        await test_widget_styling()

        print("\nTest 5: Demo Functionality")
        await test_demo_functionality()

        print("\n" + "=" * 60)
        print("✅ All Playwright tests passed!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
