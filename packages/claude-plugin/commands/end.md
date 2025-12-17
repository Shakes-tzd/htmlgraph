# /htmlgraph:end

End the current session gracefully.

## Usage

```
/htmlgraph:end
```

## Instructions for Claude

### End the session:
```bash
# Get session summary before ending
htmlgraph session list --limit 1

# End the session
htmlgraph session end
```

### Present summary:
```markdown
## Session Ended

**Session ID:** {session_id}
**Duration:** {duration}
**Events:** {event_count}

### Work Summary
{List features worked on with activity counts}

### Progress Made
- {Summary of what was accomplished}

---

Session recorded in `.htmlgraph/sessions/`
View dashboard: `htmlgraph serve`
```

### Important
Do NOT automatically end sessions - only run this when the user explicitly requests it with `/htmlgraph:end`.
