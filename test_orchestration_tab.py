#!/usr/bin/env python3
"""Verify Orchestration tab shows delegations in HtmlGraph dashboard."""

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

        # Wait for page to load
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        # Click Orchestration tab
        print("2. Clicking Orchestration tab...")
        orchestration_tab = page.locator('a:has-text("Orchestration")')

        # Check if tab exists
        tab_count = await orchestration_tab.count()
        if tab_count == 0:
            print("❌ ERROR: Orchestration tab not found on page")
            print("Available tabs:")
            tabs = page.locator("[role='tab'], .nav-link, a[class*='tab']")
            for i in range(await tabs.count()):
                text = await tabs.nth(i).text_content()
                print(f"  - {text}")
            await browser.close()
            return False

        await orchestration_tab.click()
        await asyncio.sleep(2)

        # Take screenshot
        print("3. Taking screenshot...")
        screenshot_path = "/tmp/orchestration_tab.png"
        await page.screenshot(path=screenshot_path)
        print(f"   Screenshot saved to: {screenshot_path}")

        # Check for delegation counters
        print("\n4. Checking for delegation metrics...")

        # Extract text content
        body_text = await page.locator("body").text_content()

        # Report findings
        findings = {
            "total_delegations": None,
            "unique_agents": None,
            "delegation_chains": False,
            "agent_arrows": False,
            "delegation_details": None,
        }

        # Search for delegation counters
        if "Delegations" in body_text:
            print("✓ Found 'Delegations' text on page")
            findings["delegation_chains"] = True

        if "Agent" in body_text:
            print("✓ Found 'Agent' text on page")

        # Look for numbers that might be counters
        delegation_card = page.locator('[class*="delegation"], [class*="Delegation"]')
        if await delegation_card.count() > 0:
            print(
                f"✓ Found {await delegation_card.count()} delegation-related elements"
            )
            findings["delegation_details"] = await delegation_card.nth(0).text_content()

        # Check for SVG/arrows
        arrows = page.locator("svg, [class*='arrow'], [class*='->']")
        if await arrows.count() > 0:
            print(f"✓ Found {await arrows.count()} potential arrow/diagram elements")
            findings["agent_arrows"] = True

        # Try to find specific counters by looking for numbers
        h1_elements = page.locator("h1, h2, h3, .stat-badge, [class*='counter']")
        print(f"\n5. Found {await h1_elements.count()} heading/stat elements:")
        for i in range(min(10, await h1_elements.count())):
            text = await h1_elements.nth(i).text_content()
            print(f"   - {text}")
            if text and any(char.isdigit() for char in text):
                findings["total_delegations"] = text

        # Get complete page content for analysis
        print("\n6. Orchestration Tab Content Summary:")
        orchestration_section = page.locator('main, [role="main"], .tab-content')
        if await orchestration_section.count() > 0:
            section_text = await orchestration_section.nth(0).text_content()
            print(section_text[:500] if section_text else "No content found")

        print("\n" + "=" * 60)
        print("VERIFICATION RESULTS")
        print("=" * 60)
        print(f"Screenshot: {screenshot_path}")
        print(f"Delegations Visible: {findings['delegation_chains']}")
        print(f"Agent Arrows: {findings['agent_arrows']}")
        print(f"Delegation Details: {findings['delegation_details'] is not None}")

        await browser.close()
        return True


if __name__ == "__main__":
    success = asyncio.run(verify_orchestration_tab())
    sys.exit(0 if success else 1)
