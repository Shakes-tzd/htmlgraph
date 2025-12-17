# /htmlgraph:start

Session start command - provides context continuity and asks what to work on.

## What This Command Does

Run this at the start of every session to:
1. See project status and WIP
2. View current feature(s) and progress
3. See step progress (if any)
4. Get asked what you'd like to work on next

## Usage

```
/htmlgraph:start
```

## Instructions for Claude

When the user runs `/htmlgraph:start`, follow the **HtmlGraph Development Process**.

---

### FIRST ACTION: Check Status

**BEFORE doing anything else:**

```bash
# Get status
htmlgraph status

# List features
htmlgraph feature list

# List recent sessions
htmlgraph session list

# Get recent commits
git log --oneline -5
```

---

### Present Status Update

Format your response as follows:

```markdown
## Session Status

**Project:** {project_name}
**Progress:** {completed}/{total} features ({percentage}%)
**Active Features (WIP):** {count of in_progress features}

---

### Previous Session
{Summarize what was done, or "First session"}

---

### Current Feature(s)
**Working On:** {feature description(s)}
**Status:** in_progress

#### Step Progress
- [x] Completed step
- [ ] Pending step

---

### Recent Commits
{List last 3-5 commits}

---

### What's Next
After completing current feature(s):
1. {next feature}
2. {next feature}

---

## What would you like to work on?

Options:
1. Continue with current feature
2. Start a different feature (`htmlgraph feature start <id>`)
3. Create new work item
4. Something else
```

### Wait for User Direction

After presenting the status, wait for the user to indicate what they want to do.

---

## Key Reminders

1. **Parallel development OK** - Up to 3 features can be in progress (WIP limit)
2. **Finish over start** - Complete existing work before starting new
3. **All activity tracked** - Hooks attribute work to features automatically
4. **View in browser** - Run `htmlgraph serve` and open http://localhost:8080
