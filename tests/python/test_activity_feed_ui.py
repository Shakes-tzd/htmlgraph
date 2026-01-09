"""
Playwright UI tests for Activity Feed real-time WebSocket streaming.

Tests verify:
- Dashboard loads without errors
- Activity Feed container renders
- Page is responsive
- No 404 errors on load
- Performance meets baseline
"""

import socket
import subprocess
import time

import pytest
from playwright.async_api import async_playwright, expect


def wait_for_server(
    host: str = "localhost", port: int = 8080, timeout: int = 30
) -> bool:
    """Wait for server to be ready by attempting connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


class TestActivityFeedDashboard:
    """Test Activity Feed dashboard UI rendering."""

    @pytest.mark.asyncio
    async def test_activity_feed_loads_and_renders(self):
        """Test Activity Feed dashboard loads and renders properly."""
        # Start server
        server = subprocess.Popen(
            ["uv", "run", "htmlgraph", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait for server to be ready
        if not wait_for_server(timeout=30):
            server.kill()
            pytest.skip("Server failed to start")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                try:
                    # Navigate to dashboard
                    await page.goto("http://localhost:8080", timeout=10000)

                    # Wait for Activity Feed heading to appear (use specific heading selector)
                    await expect(
                        page.locator("h2:has-text('Agent Activity Feed')")
                    ).to_be_visible(timeout=5000)

                    # Verify page loaded
                    title = await page.title()
                    assert title is not None and len(title) > 0

                finally:
                    await browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

    @pytest.mark.asyncio
    async def test_activity_feed_no_console_errors(self):
        """Test Activity Feed loads without critical console errors."""
        server = subprocess.Popen(
            ["uv", "run", "htmlgraph", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not wait_for_server(timeout=30):
            server.kill()
            pytest.skip("Server failed to start")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                console_messages = []

                def on_console(msg):
                    console_messages.append(f"[{msg.type}] {msg.text}")

                page.on("console", on_console)

                try:
                    await page.goto("http://localhost:8080", timeout=10000)

                    # Wait for Activity Feed heading
                    await expect(
                        page.locator("h2:has-text('Agent Activity Feed')")
                    ).to_be_visible(timeout=5000)

                    # Wait for any JS errors
                    await page.wait_for_timeout(1000)

                    # Check for critical WebSocket errors
                    critical_errors = [
                        m
                        for m in console_messages
                        if "error" in m.lower() and "websocket" in m.lower()
                    ]
                    assert len(critical_errors) == 0, (
                        f"Critical errors found: {critical_errors}"
                    )

                finally:
                    await browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

    @pytest.mark.asyncio
    async def test_activity_feed_no_404_errors(self):
        """Test dashboard loads without 404 errors."""
        server = subprocess.Popen(
            ["uv", "run", "htmlgraph", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not wait_for_server(timeout=30):
            server.kill()
            pytest.skip("Server failed to start")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                request_errors = []

                def on_response(response):
                    if response.status >= 400:
                        request_errors.append(
                            f"{response.url}: {response.status} {response.status_text}"
                        )

                page.on("response", on_response)

                try:
                    await page.goto("http://localhost:8080", timeout=10000)

                    # Wait for page to fully load
                    await page.wait_for_load_state("networkidle", timeout=10000)

                    # Should not have 404 errors
                    not_found_errors = [e for e in request_errors if "404" in e]
                    assert len(not_found_errors) == 0, f"404 errors: {not_found_errors}"

                finally:
                    await browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

    @pytest.mark.asyncio
    async def test_activity_feed_responsive_layout(self):
        """Test Activity Feed is responsive to viewport changes."""
        server = subprocess.Popen(
            ["uv", "run", "htmlgraph", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not wait_for_server(timeout=30):
            server.kill()
            pytest.skip("Server failed to start")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                try:
                    await page.goto("http://localhost:8080", timeout=10000)

                    # Wait for Activity Feed heading
                    await expect(
                        page.locator("h2:has-text('Agent Activity Feed')")
                    ).to_be_visible(timeout=5000)

                    # Test viewport resizing
                    viewports = [
                        {"width": 800, "height": 600},
                        {"width": 1200, "height": 800},
                        {"width": 1920, "height": 1080},
                    ]

                    for viewport in viewports:
                        await page.set_viewport_size(viewport)
                        await expect(
                            page.locator("h2:has-text('Agent Activity Feed')")
                        ).to_be_visible(timeout=5000)

                finally:
                    await browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

    @pytest.mark.asyncio
    async def test_activity_feed_page_load_time(self):
        """Test dashboard loads in acceptable time."""
        server = subprocess.Popen(
            ["uv", "run", "htmlgraph", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not wait_for_server(timeout=30):
            server.kill()
            pytest.skip("Server failed to start")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                try:
                    # Measure load time
                    start_time = time.time()
                    await page.goto("http://localhost:8080", timeout=10000)
                    load_time = time.time() - start_time

                    # Should load in less than 5 seconds
                    assert load_time < 5.0, f"Page load took {load_time}s"

                    # Activity Feed heading should be visible
                    await expect(
                        page.locator("h2:has-text('Agent Activity Feed')")
                    ).to_be_visible(timeout=5000)

                finally:
                    await browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

    @pytest.mark.asyncio
    async def test_activity_feed_body_element_visible(self):
        """Test page body element renders and is visible."""
        server = subprocess.Popen(
            ["uv", "run", "htmlgraph", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not wait_for_server(timeout=30):
            server.kill()
            pytest.skip("Server failed to start")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                try:
                    await page.goto("http://localhost:8080", timeout=10000)

                    # Check body is visible
                    body = page.locator("body")
                    await expect(body).to_be_visible(timeout=5000)

                    # Check bounding box
                    box = await body.bounding_box()
                    assert box is not None
                    assert box["height"] > 0

                finally:
                    await browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

    @pytest.mark.asyncio
    async def test_activity_feed_does_not_reload_on_wait(self):
        """Test page remains stable and doesn't reload during interaction."""
        server = subprocess.Popen(
            ["uv", "run", "htmlgraph", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not wait_for_server(timeout=30):
            server.kill()
            pytest.skip("Server failed to start")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                try:
                    await page.goto("http://localhost:8080", timeout=10000)

                    # Wait for Activity Feed heading
                    await expect(
                        page.locator("h2:has-text('Agent Activity Feed')")
                    ).to_be_visible(timeout=5000)

                    # Get initial URL
                    initial_url = page.url

                    # Wait
                    await page.wait_for_timeout(2000)

                    # URL should not have changed
                    assert page.url == initial_url

                finally:
                    await browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
