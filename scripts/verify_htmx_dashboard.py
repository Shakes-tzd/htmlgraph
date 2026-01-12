from htmlgraph.orchestration.headless_spawner import HeadlessSpawner


def verify_htmx_dashboard():
    spawner = HeadlessSpawner()

    print("Spawning Claude to verify HTMX Dashboard UI on port 8000...")

    prompt = """
    Please verify the HtmlGraph Dashboard UI at http://localhost:8000.

    1. Navigate to http://localhost:8000
    2. Check if the page is the new HTMX/FastAPI dashboard.
       - Look for HTMX attributes in the source (e.g., hx-get, hx-target, hx-swap).
       - Look for sections like "Unified Activity Feed" or hierarchical trace view.
    3. Verify that the "Agents" tab works correctly.
       - Click on "Agents" tab.
       - Take a screenshot of the Agents view.
    4. Report findings:
       - Is it the new dashboard?
       - Does the Agents tab work?
       - Does it show hierarchical events?
    """

    # Pass --dangerously-skip-permissions to ensure non-interactive mode
    # Pass --plugin-dir packages/claude-plugin to load the HtmlGraph plugin with Chrome DevTools MCP
    result = spawner.spawn_claude(
        prompt,
        permission_mode="bypassPermissions",
        timeout=300,
        extra_args=[
            "--dangerously-skip-permissions",
            "--plugin-dir",
            "packages/claude-plugin",
        ],
    )

    if result.success:
        print("\n✅ HTMX Dashboard Verification Completed")
        print("Response from Claude:")
        print("--------------------------------------------------")
        print(result.response)
        print("--------------------------------------------------")
    else:
        print("\n❌ HTMX Dashboard Verification Failed")
        print(f"Error: {result.error}")
        if result.raw_output:
            # Print last 1000 chars of raw output to debug
            output_str = str(result.raw_output)
            print(f"Raw Output (tail): {output_str[-1000:]}")


if __name__ == "__main__":
    verify_htmx_dashboard()
