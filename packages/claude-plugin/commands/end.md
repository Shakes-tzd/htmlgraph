<!-- Efficiency: SDK calls: 2-3, Bash calls: 0, Context: ~5% -->

# /htmlgraph:end

End the current session and record work summary

## Usage

```
/htmlgraph:end
```

## Parameters



## Examples

```bash
/htmlgraph:end
```
Gracefully end the current session and show work summary



## Instructions for Claude

This command uses the SDK's `end_session()` method.

### Implementation:

```python
import os
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Get current session ID:**
   ```python
   # First try environment variable (Claude Code provides this)
   session_id = os.getenv("CLAUDE_SESSION_ID")

   # Fallback to SDK query if not available
   if not session_id:
       active_sessions = sdk.sessions.where(status="active")
       if not active_sessions:
           print("Error: No active session to end")
           return
       session_id = active_sessions[0].id
   ```

2. **Get current work item for handoff:**
   ```python
   active_work = sdk.get_active_work_item()
   handoff_notes = None

   if active_work:
       # Prepare handoff notes with current work context
       handoff_notes = f"Working on: {active_work.get('title', 'Unknown')}"
       if active_work.get('description'):
           handoff_notes += f"\n\nContext: {active_work['description']}"
   ```

3. **End the session using SDK:**
   ```python
   session = sdk.end_session(
       session_id=session_id,
       handoff_notes=handoff_notes
   )
   ```

4. **Extract session details:**
   - Session ID: `session.id`
   - Duration: Calculate from `session.created_at` to now
   - Event count: Query from database or session metadata
   - Features worked on: Get from session activities

5. **Present the session summary** using the output template below

6. **Include the summary of accomplishments:**
   - List features worked on during this session
   - Show any steps marked as complete
   - Acknowledge progress made

7. **Provide next-session guidance:**
   - Mention how to view dashboard: `htmlgraph serve`
   - Suggest next steps for the next session
   - Link to session record in `.htmlgraph/sessions/`
   - Show handoff notes if any

8. **CRITICAL CONSTRAINT:**
   - ONLY run `/htmlgraph:end` when the user explicitly requests it
   - Do NOT automatically end sessions
   - Wait for explicit user command
```

### Output Format:

## Session Ended

**Session ID:** {session_id}
**Duration:** {duration}
**Events:** {event_count}

### Work Summary
{features_worked_on_with_counts}

### Progress Made
- {accomplishment_summary}

---

Session recorded in `.htmlgraph/sessions/`
View dashboard: `htmlgraph serve`
