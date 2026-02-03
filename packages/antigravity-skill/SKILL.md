---
name: antigravity-skill
description: HtmlGraph session tracking and work continuity for Antigravity (Gemini Advanced). Ensures proper activity attribution, feature awareness, and continuous work tracking.
metadata:
  short-description: HtmlGraph session tracking for Antigravity
---

# HtmlGraph Session Tracking for Antigravity

**Description**: This skill enables Antigravity to track its own work sessions, features, and activities within the HtmlGraph system.

**MANDATORY Workflow**:
1.  **Start Session**: Always start by checking or initializing a session.
2.  **Pick Feature**: Identify or create the feature you are working on.
3.  **Track Work**: Mark steps as complete as you go.
4.  **End Session**: Explicitly end the session when your task is complete.

**Commands**:
-   `uv run htmlgraph session start --agent antigravity`
-   `uv run htmlgraph feature start <feature_id>`
-   `uv run htmlgraph step complete <step_id>`
-   `uv run htmlgraph session list`

**Workflows**:
-   `start_session.md`: Initialize your session foundation.
-   `feature_work.md`: The recommended loop for implementing features.

**Best Practices**:
-   **Always** identify yourself as `agent="antigravity"` if using the SDK directly.
-   **Never** edit HTML files in `.htmlgraph` directly. Use the CLI or SDK.
-   **Verify** your presence on the dashboard `http://localhost:8085` periodically.
