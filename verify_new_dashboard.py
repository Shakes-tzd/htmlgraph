from htmlgraph.orchestration.headless_spawner import HeadlessSpawner


def verify_new_dashboard():
    spawner = HeadlessSpawner()

    print("Spawning Claude to verify NEW HTMX Dashboard UI...")

    prompt = """
    Please verify the HtmlGraph Dashboard UI at http://localhost:8080.

    1. Navigate to http://localhost:8080
    2. Check if the page is the new HTMX/FastAPI dashboard.
       - Look for HTMX attributes in the source (e.g., hx-get, hx-target).
       - Look for the "Unified Activity Feed" or hierarchical trace view.
    3. Verify that the "Agents" tab works correctly this time.
       - Click on "Agents" tab.
       - Verify no JavaScript errors (the previous error was TypeError: Cannot read properties of null).
    4. Take a screenshot of the main view.
    5. Report findings:
       - Is it the new dashboard?
       - Does the Agents tab work?
    """

    # We use permission_mode="bypassPermissions" to allow tool use without prompting
    result = spawner.spawn_claude(
        prompt, permission_mode="bypassPermissions", timeout=300
    )

    if result.success:
        print("\n✅ Verification Task Completed")
        print("Response from Claude:")
        print("--------------------------------------------------")
        print(result.response)
        print("--------------------------------------------------")
    else:
        print("\n❌ Verification Task Failed")
        print(f"Error: {result.error}")
        if result.raw_output:
            print(f"Raw Output: {result.raw_output}")


if __name__ == "__main__":
    verify_new_dashboard()
