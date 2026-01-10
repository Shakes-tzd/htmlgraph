# System Prompt Persistence Guide

## Overview

The system prompt persistence feature ensures your Claude Code system prompt survives across session boundaries—compacts, resumes, and context clears. This guide covers installation, configuration, troubleshooting, and best practices.

### What It Does

- **Auto-injects system prompt** at session start via SessionStart hook
- **Survives compacts and resumes** — prompt re-appears after context clears
- **Customizable** — edit `.claude/system-prompt.md` for your needs
- **Model-aware** — includes guidance for delegating to different models
- **Zero-latency** — minimal impact on session startup time

### Why It Matters

System prompts guide Claude's reasoning and behavior throughout a session. Without persistence, your guidance vanishes when context compacts. This feature keeps it available automatically.

### How It Works

Three-layer architecture (phase rollout):

- **Layer 1 (Current)**: `additionalContext` injection via SessionStart hook
- **Layer 2 (Coming)**: `CLAUDE_ENV_FILE` environment variable support
- **Layer 3 (Coming)**: File backup and recovery system

---

## Installation

### Prerequisites

- HtmlGraph plugin installed in Claude Code
- `.claude/` directory in your project
- System prompt file created (auto-generated on first session start)

### Setup Steps

**Step 1: Verify plugin installation**

```bash
claude plugin list | grep htmlgraph
```

Expected output: `htmlgraph` listed with version number

**Step 2: System prompt auto-creation**

When you start a Claude Code session in your HtmlGraph project:
1. SessionStart hook runs automatically
2. `.claude/system-prompt.md` is created if missing
3. Prompt is injected as additional context
4. Available throughout your session

**Step 3: Verify injection**

After starting a new session:
1. You should see system prompt content in your context
2. Check hook execution: `claude --debug` for verbose output
3. Confirm prompt persists after using `/compact` command

### File Location

```
your-project/
├── .claude/
│   ├── system-prompt.md          ← Your custom prompt (EDIT THIS)
│   ├── hooks/
│   │   └── scripts/
│   │       └── session-start.py  ← Injection logic (read-only)
│   └── settings.json             ← Plugin config
└── .htmlgraph/
    └── sessions/                 ← Session tracking
```

---

## Configuration

### Customizing Your System Prompt

Edit `.claude/system-prompt.md` to customize Claude's behavior in your project.

**Structure:**

```markdown
# Your System Prompt Title

## Section 1: Primary Directive
Your core principle here...

## Section 2: Workflow Pattern
How work should be organized...

## Section 3: Model Guidance
Which models for which tasks...

## Section 4: Key Rules
Non-negotiable constraints...
```

**Best Practices:**

1. **Keep it under 500 tokens** — Too long and injection delays startup
2. **Use clear section headings** — Makes scanning easy
3. **Include model guidance** — Helps with delegation decisions
4. **Be specific to your project** — Generic prompts are less useful
5. **Update regularly** — Refine as you learn what works

**Example: HtmlGraph Development Prompt**

```markdown
# System Prompt - HtmlGraph Development

## Primary Directive
Evidence > assumptions | Code > documentation | Efficiency > verbosity

## Orchestration Pattern
- Use Task() for multi-session work, deep research, or complex reasoning
- Execute directly only for straightforward file operations or quick implementations
- Haiku: Default orchestrator—excellent at following delegation instructions
- Sonnet/Opus: For deep reasoning, but tends to over-execute; use Task() when uncertain

## Model Guidance
- Haiku (Recommended): Orchestration, delegation, quick tasks
- Sonnet: Complex reasoning, architecture decisions
- Opus: Novel problems, research-heavy investigations

## Context Persistence
This prompt auto-injects at session start via SessionStart hook. It survives
compact/resume cycles and remains available as reference throughout your session.

## Key Rules
1. Always Read before Write/Edit/Update
2. Use absolute paths only
3. Use `uv run` for all Python execution
4. Batch tool calls when independent
5. Fix all errors before committing
```

### Example: General Development Prompt

```markdown
# System Prompt - General Development

## Primary Directive
Writing reliable, maintainable code with comprehensive testing.

## Workflow
1. Read existing code before making changes
2. Plan changes before implementation
3. Write tests before code
4. Run tests before committing

## Model Selection
- Use Haiku for quick fixes, refactoring, simple features
- Use Sonnet for architecture, complex logic, research
- Use Opus only for novel problems or major decisions

## Delegation
Delegate when:
- Task takes >30 minutes
- Requires file exploration (many files)
- Needs extensive testing
- Affects multiple components

Execute directly when:
- Single file change
- Takes <10 minutes
- Simple, safe change
- Easy to verify
```

### Testing Your Configuration

After editing `.claude/system-prompt.md`:

1. **Restart your session** — Hook runs at session start
2. **Use `/compact`** — Clears context, then re-injects prompt
3. **Verify** — Check that your custom content appears in context
4. **Debug** — If prompt doesn't appear: `claude --debug` for verbose output

---

## How It Works (3-Layer Architecture)

### Layer 1: Session Hook Injection (Current)

**Mechanism**: SessionStart hook runs when Claude Code starts.

**Flow**:
```
Session Start
    ↓
SessionStart hook executes (session-start.py)
    ↓
Reads .claude/system-prompt.md
    ↓
Injects as additionalContext
    ↓
Prompt available throughout session
```

**Token Impact**: <50ms execution, <2% context overhead

**Reliability**: High — uses built-in hook mechanism

### Layer 2: Environment Variable Support (Phase 2)

Future enhancement using `CLAUDE_ENV_FILE`:

```bash
export CLAUDE_ENV_FILE=~/.claude/system-prompt.md
```

Advantages:
- Works across all Claude Code sessions
- Survives environment changes
- Doesn't consume context tokens

### Layer 3: File Backup System (Phase 3)

Automatic backup and recovery:
- Detects lost prompts
- Restores from backup
- Validates injection success

---

## Model-Specific Guidance

### When to Use Which Model

**Haiku (Recommended for most work)**

Best for:
- Orchestration and delegation
- Following complex instructions
- Quick implementations and fixes
- Refactoring and cleanup
- Running tests and quality gates
- File operations and searches

Why it excels:
- Highly responsive to detailed instructions
- Excellent at following patterns
- Fast execution (40-80ms typical)
- Lower cost
- Ideal for delegation workflows

Example delegation:
```python
Task(
    prompt="""
    Fix the bug in src/auth/jwt.py where tokens expire immediately.
    The issue is in the validate_token() function.
    Run tests after fixing to verify the fix works.
    """,
    subagent_type="general-purpose"  # Uses Haiku by default
)
```

**Sonnet (Complex reasoning)**

Best for:
- Architecture and design decisions
- Complex algorithms and logic
- Performance optimization
- Security analysis
- Code review and quality assessment
- When initial attempt fails

Why it excels:
- Strong reasoning about trade-offs
- Better understanding of complex contexts
- Good balance of speed and power
- Good for cross-domain problems

Example use:
```python
Task(
    prompt="""
    Design a caching strategy for our API.
    Consider: hit rate, memory limits, invalidation complexity.
    Compare Redis vs. in-memory approaches.
    """,
    subagent_type="sonnet"  # Request Sonnet explicitly
)
```

**Opus (Novel problems, research)**

Best for:
- Entirely new feature design
- Research-heavy tasks
- Multi-step reasoning with many unknowns
- When Sonnet's attempt was insufficient
- Novel problem domains

Why it excels:
- Strongest reasoning capabilities
- Handles ambiguity well
- Good for exploration and discovery
- Best for completely novel problems

Example use:
```python
Task(
    prompt="""
    We're building a real-time collaboration system.
    Research: What are the key technical challenges?
    Design: How would you approach it from first principles?
    """,
    subagent_type="opus"  # Request Opus for novel design
)
```

### Signaling Model Preference

In your system prompt, indicate preferred models:

```markdown
## Model Guidance

**Haiku (Default for delegation)**
- Use for: Quick fixes, orchestration, following patterns
- When to use: Most everyday tasks, especially delegated work

**Sonnet (Complex reasoning)**
- Use for: Architecture, algorithm design, optimization
- When to use: Task requires multi-step reasoning or design decisions

**Opus (Novel problems)**
- Use for: Entirely new features, research, complex discovery
- When to use: Previous attempts with other models insufficient
```

### Cost Optimization

**Rule: Match model size to task complexity**

```
Simple task + Haiku = Fast + Cheap ✅
Simple task + Sonnet = Slow + Expensive ❌
Complex task + Haiku = Fast but limited ⚠️
Complex task + Sonnet = Balanced ✅
Complex task + Opus = Best but expensive ✅
```

---

## Troubleshooting

### Prompt Not Appearing After Session Start

**Symptom**: You don't see custom prompt content in initial context.

**Diagnosis Steps**:

1. Check file exists:
   ```bash
   ls -la .claude/system-prompt.md
   ```
   Expected: File should exist, size >100 bytes

2. Check file is readable:
   ```bash
   head -5 .claude/system-prompt.md
   ```
   Expected: Your prompt content appears

3. Check hook is registered:
   ```bash
   claude /hooks
   ```
   Expected: `SessionStart` hook listed

4. Run with debug output:
   ```bash
   claude --debug
   # Look for "SessionStart hook" or "additionalContext" in output
   ```

**Solutions**:

- **File missing**: System will recreate at next session start
- **File unreadable**: Check permissions: `chmod 644 .claude/system-prompt.md`
- **Hook not registered**: Verify plugin installed: `claude plugin list`
- **Still broken**: See "Debug Mode" section below

### Prompt Not Persisting After Compact

**Symptom**: Prompt disappears after using `/compact` command.

**Expected behavior**: Prompt re-appears automatically when context resumes.

**If not re-appearing**:

1. Verify hook is still active:
   ```bash
   claude /hooks
   ```

2. Check recent session logs:
   ```bash
   ls -lt .htmlgraph/sessions/ | head -1
   ```

3. Run `/compact` again with debug:
   ```bash
   claude --debug
   # Use /compact command
   # Check for hook execution in output
   ```

**Note**: First `/compact` might not trigger injection if hook timing is off. Second compact should work.

### Prompt Has Wrong Content

**Symptom**: Your custom prompt isn't appearing, or old content still shows.

**Solution**:

1. Edit `.claude/system-prompt.md` with new content
2. Restart your session (or use `/clear` then `/compact`)
3. Verify new content appears
4. If old content still shows: Clear browser cache if using dashboard

### Hook Timeout or Failure

**Symptom**: Hook takes too long or exits with error.

**Cause**: Prompt file too large or malformed.

**Solution**:

1. Check file size:
   ```bash
   wc -w .claude/system-prompt.md
   # Should be <500 words
   ```

2. If >500 words: Remove least important sections

3. Validate markdown syntax:
   ```bash
   # No unclosed markdown syntax (## without closing)
   # No invalid YAML if using frontmatter
   ```

4. Simplify content and retry

### Plugin Not Installed

**Symptom**: `claude plugin list` doesn't show htmlgraph.

**Solution**:

```bash
# Install the plugin
claude plugin install htmlgraph

# Verify installation
claude plugin list | grep htmlgraph
```

### Debug Mode

For detailed troubleshooting output:

```bash
# Run Claude with verbose logging
claude --debug

# Look for these log lines:
# "SessionStart hook executing"
# "Reading system-prompt.md"
# "Injecting additionalContext"
# "Hook completed successfully"
```

If you see errors:
- `FileNotFoundError`: Prompt file missing (will recreate)
- `PermissionError`: File not readable (check permissions)
- `TimeoutError`: Prompt too large (reduce size)
- `JSONDecodeError`: Hook output malformed (restart plugin)

---

## FAQ

### Q: How often is the prompt injected?

**A**: At session start, after context resume, and after `/clear` command. Typically once per session (unless you compact).

### Q: Does this add latency to session startup?

**A**: Minimal impact:
- Hook execution: <50ms typically
- Context overhead: <2% (100-200 tokens)
- Notice: Only on first session start in a new project

### Q: Can I customize the prompt per project?

**A**: Yes, completely. Edit `.claude/system-prompt.md` for your project.

Examples:
- **HtmlGraph projects**: Include orchestration patterns
- **General projects**: Include your coding standards
- **Research projects**: Include methodology and focus areas

### Q: What if the file is missing?

**A**: Feature degrades gracefully:
- Hook logs warning to stderr
- Session continues normally
- File auto-creates with default content on next session start
- No impact to functionality

### Q: Can I disable this feature?

**A**: Not recommended, but if needed:

```bash
# Disable session tracking (stops all hooks)
export HTMLGRAPH_DISABLE_TRACKING=1

# To re-enable
unset HTMLGRAPH_DISABLE_TRACKING
```

### Q: Does prompt injection work after `/clear`?

**A**: Yes. `/clear` is treated like a compact, triggering hook re-execution.

### Q: How do I know it's working?

**A**:
1. After session start, your prompt content appears in context
2. After `/compact`, prompt re-appears when context resumes
3. Check hook execution: `claude /hooks` shows SessionStart registered
4. Debug output shows injection: `claude --debug`

### Q: What if I have multiple projects?

**A**: Each project gets its own `.claude/system-prompt.md`. Edit per-project prompts independently.

### Q: Can I use environment variables in my prompt?

**A**: Not yet (Phase 2 feature). Currently, prompt is static markdown.

Workaround: Create separate prompts for different scenarios and commit to version control.

### Q: What's the token cost?

**A**: Approximately 100-300 tokens depending on prompt size:
- HtmlGraph example prompt: ~200 tokens
- General project prompt: ~150-250 tokens
- Minimal prompt: ~100 tokens

Choose length based on your needs.

### Q: Does this work with other Claude Code features?

**A**: Yes, fully compatible with:
- `/compact` and context resume
- `/clear` command
- Orchestrator mode
- All hooks and plugins
- Session tracking

### Q: What if I want to update my prompt?

**A**: Simple:
1. Edit `.claude/system-prompt.md`
2. Changes take effect at next session start
3. Or use `/compact` to trigger re-injection immediately

### Q: Is this synced across my machines?

**A**: Only if you commit `.claude/system-prompt.md` to git:

```bash
# Include in version control
git add .claude/system-prompt.md
git commit -m "chore: add system prompt"
git push

# On another machine, pull and start working
git pull
# New session automatically picks up your prompt
```

### Q: Can I test my prompt without starting a new session?

**A**: Yes:
1. Edit `.claude/system-prompt.md`
2. Use `/compact` command (triggers hook re-execution)
3. Verify new content appears
4. Or start a new session to test completely fresh

---

## Integration with HtmlGraph

System prompt persistence integrates with HtmlGraph's orchestration system:

### Orchestrator Mode Guidance

Your system prompt can include orchestrator directives:

```markdown
## Orchestration Pattern

- Use Task() for multi-session work, deep research, or complex reasoning
- Execute directly only for straightforward file operations
- Haiku: Default orchestrator—excellent at following delegation instructions
- Sonnet/Opus: For deep reasoning, but tends to over-execute
```

When orchestrator mode is active (default), Claude Code enforces these patterns.

### Session Tracking

All sessions are automatically tracked in `.htmlgraph/sessions/`:

```bash
# View session history
uv run htmlgraph session list

# Check current session details
uv run htmlgraph session show <session-id>
```

### Feature Attribution

Work is automatically attributed to in-progress features. Your system prompt can guide feature creation:

```markdown
## Feature Creation Decision Framework

Create a FEATURE if ANY apply:
- >30 minutes work
- 3+ files
- New tests needed
- Multi-component impact

Implement DIRECTLY if ALL apply:
- Single file
- <30 minutes
- Trivial change
- Easy to revert
```

---

## Best Practices

### 1. Keep It Fresh

Update your system prompt as you learn:

```markdown
# WRONG: Old, outdated guidance
## Review once a month

# RIGHT: Current, tested patterns
## Review when process changes
```

### 2. Be Specific

```markdown
# WRONG: "Use best practices"

# RIGHT: "Use uv run for Python execution, never raw python or pip"
```

### 3. Include Model Guidance

Help Claude choose the right tool:

```markdown
# WRONG: No model preferences

# RIGHT:
## Model Selection
- Haiku: Delegation, orchestration (default)
- Sonnet: Complex reasoning, architecture
- Opus: Novel problems, research
```

### 4. Document Your Workflow

Make your process explicit:

```markdown
## Workflow Steps
1. Read existing code
2. Plan changes
3. Write tests
4. Implement
5. Run tests
6. Commit
```

### 5. Keep It Concise

Longer isn't better:

```
Good: 100-300 tokens (specific, actionable)
Better: 200-300 tokens (comprehensive but focused)
Too long: >500 tokens (dilutes impact)
```

### 6. Use Section Headings

Makes scanning fast:

```markdown
## Primary Directive       ← Clear section
Evidence > assumptions     ← Specific guidance

## Workflow Pattern        ← Next section
1. Read before write       ← Action items
2. Test before commit
```

### 7. Test Regularly

After editing:
1. Use `/compact` to trigger re-injection
2. Verify content appears correct
3. Check hook execution: `claude --debug`

### 8. Commit to Version Control

Share with your team:

```bash
git add .claude/system-prompt.md
git commit -m "chore: update system prompt with new delegation patterns"
git push
```

---

## Advanced: Custom Hook Behavior

The SessionStart hook is read-only for end users, but you can see the logic:

**File**: `.claude/hooks/scripts/session-start.py`

The hook:
1. Loads your `.claude/system-prompt.md`
2. Validates it's not too large (<500 tokens)
3. Injects as `additionalContext` via SessionStart response
4. Logs injection details for debugging

To customize hook behavior beyond prompt content, see `.claude/hooks/README.md`.

---

## Next Steps

1. **Verify installation**: Check that prompt appears in your next session
2. **Customize your prompt**: Edit `.claude/system-prompt.md` for your project
3. **Test persistence**: Use `/compact` to verify prompt survives context reset
4. **Commit to git**: Share your prompt with team members
5. **Monitor effectiveness**: Adjust prompt based on how well it guides your work

---

## Related Documentation

- **AGENTS.md**: SDK reference and workflow patterns
- **CLAUDE.md**: Project-specific configuration and quick commands
- **ORCHESTRATOR_MODE_GUIDE.md**: Complete orchestration patterns
- **SESSION_START_INTEGRATION.md**: Technical hook documentation

---

## Support

For issues:

1. Check **Troubleshooting** section above
2. Verify `.claude/system-prompt.md` file exists and is readable
3. Run with debug: `claude --debug`
4. Check plugin: `claude plugin list | grep htmlgraph`
5. Review hook logs: `.htmlgraph/sessions/` and recent session file

For detailed implementation: See `.claude/hooks/scripts/session-start.py`
