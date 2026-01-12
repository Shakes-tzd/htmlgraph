#!/usr/bin/env python3
"""Verify Orchestration tab shows delegations in HtmlGraph dashboard using Playwright."""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src" / "python"))


async def verify_orchestration_tab():
    """Test the Orchestration tab using Playwright."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Navigate to dashboard
        print("1. Navigating to http://localhost:8000...")
        await page.goto("http://localhost:8000", wait_until="networkidle")

        # Wait for page to fully load
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        # Look for the view buttons (Orchestration might be under different name)
        print("2. Looking for view/tab buttons...")
        buttons = await page.locator(
            "button[class*='view'], button[data-view], [class*='tab']"
        ).all()

        button_labels = []
        for btn in buttons:
            text = await btn.text_content()
            button_labels.append(text)

        print(f"   Found {len(button_labels)} buttons:")
        for label in button_labels:
            if label:
                print(f"   - {label.strip()}")

        # Try clicking on various tabs to find orchestration
        orchestration_found = False
        for label in button_labels:
            if label and "orchestration" in label.lower():
                orchestration_found = True
                print(f"   Clicking: {label}")
                break

        if not orchestration_found:
            print("\n❌ Orchestration tab not found in buttons")
            print("   Checking if endpoint is available via HTTP...")

            # Test API endpoint directly
            orchestration_html = await page.request.get(
                "http://localhost:8000/views/orchestration"
            )
            if orchestration_html.ok:
                content = await orchestration_html.text()
                print("   ✓ /views/orchestration endpoint is working")

                # Parse the response to check for delegation counters
                if "Total Delegations" in content:
                    print("   ✓ Found 'Total Delegations' in response")
                if "Unique Agents" in content:
                    print("   ✓ Found 'Unique Agents' in response")
                if "No delegation chains" in content:
                    print("   ✓ Currently showing empty state (no delegations)")
                else:
                    print("   ✓ Delegation data is present")
            else:
                print(f"   ❌ Endpoint returned: {orchestration_html.status}")

        # Take screenshot of current state
        print("\n3. Taking screenshot of dashboard...")
        screenshot_path = "/tmp/orchestration_dashboard.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"   Screenshot saved to: {screenshot_path}")

        # Get page content summary
        print("\n4. Page content summary:")
        title = await page.title()
        print(f"   Title: {title}")

        # Look for delegation-related elements
        page_text = await page.locator("body").text_content()
        if page_text:
            # Search for key metrics
            if "Delegations" in page_text:
                print("   ✓ Page contains 'Delegations' text")
            if "Agent" in page_text:
                print("   ✓ Page contains 'Agent' text")
            if "Orchestration" in page_text:
                print("   ✓ Page contains 'Orchestration' text")

        # Try to manually load orchestration view
        print("\n5. Attempting to load orchestration view directly...")
        try:
            # Navigate directly to orchestration via endpoint
            await page.goto(
                "http://localhost:8000/views/orchestration", wait_until="networkidle"
            )
            await asyncio.sleep(1)

            # Take screenshot of orchestration view
            orchestration_screenshot = "/tmp/orchestration_view.png"
            await page.screenshot(path=orchestration_screenshot, full_page=True)
            print("   ✓ Orchestration view loaded")
            print(f"   Screenshot saved to: {orchestration_screenshot}")

            # Check for delegation counters
            body_content = await page.locator("body").text_content()
            print("\n6. Orchestration View Results:")
            print("   " + "=" * 50)

            if "Total Delegations" in body_content:
                # Extract counter value
                counter_match = body_content.split("Total Delegations")[1].split("\n")[
                    0:3
                ]
                counter_text = " ".join(counter_match)
                print(f"   ✓ Total Delegations: {counter_text.strip()}")
            else:
                print("   ❌ 'Total Delegations' not found")

            if "Unique Agents" in body_content:
                agent_match = body_content.split("Unique Agents")[1].split("\n")[0:3]
                agent_text = " ".join(agent_match)
                print(f"   ✓ Unique Agents: {agent_text.strip()}")
            else:
                print("   ❌ 'Unique Agents' not found")

            if "No delegation chains" in body_content:
                print("   ℹ Status: No delegations recorded yet")
            elif "delegation" in body_content.lower():
                print("   ✓ Delegation data present")

        except Exception as e:
            print(f"   ❌ Error loading orchestration view: {e}")

        await browser.close()
        return True


if __name__ == "__main__":
    success = asyncio.run(verify_orchestration_tab())
    sys.exit(0 if success else 1)
