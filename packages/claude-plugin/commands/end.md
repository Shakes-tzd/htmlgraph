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

This command uses the SDK's `None()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Run these commands to capture session info:**
   ```bash
   htmlgraph session list --limit 1
   htmlgraph session end
   ```

2. **Parse the output** to extract:
   - Session ID
   - Session duration
   - Event count
   - Features worked on
   - Activity summary

3. **Present the session summary** using the output template above

4. **Include the summary of accomplishments:**
   - List features worked on during this session
   - Show any steps marked as complete
   - Acknowledge progress made

5. **Provide next-session guidance:**
   - Mention how to view dashboard: `htmlgraph serve`
   - Suggest next steps for the next session
   - Link to session record in `.htmlgraph/sessions/`

6. **CRITICAL CONSTRAINT:**
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
