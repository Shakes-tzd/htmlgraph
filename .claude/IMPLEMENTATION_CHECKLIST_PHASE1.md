# Phase 1 Implementation Checklist: SessionStart System Prompt Injection

**Target Completion:** Days 2-3
**Complexity:** Low (hook extension, new file)
**Risk:** Low (proven mechanism, non-blocking)
**Expected Duration:** 1-2 days

---

## Pre-Implementation Review

- [x] Research complete and documented
- [x] SessionStart hook mechanics understood
- [x] additionalContext mechanism proven in HtmlGraph
- [x] Error handling strategies identified
- [x] Edge cases documented
- [x] Token budget validated (negligible impact)
- [ ] Review findings document (SESSIONSTART_RESEARCH_FINDINGS.md)

---

## Step 1: Create System Prompt File

**File:** `.claude/system-prompt.md`
**Purpose:** Core system prompt for delegation instructions

### Checklist

- [ ] Create file at `.claude/system-prompt.md`
- [ ] Add markdown header and sections
- [ ] Include core philosophy section
- [ ] Include delegation instructions section
- [ ] Include model preferences section
- [ ] Include context restoration note
- [ ] Keep content under 500 tokens
- [ ] Review for clarity and completeness
- [ ] Test file loads without errors

### Content Template

```markdown
# System Prompt

## Core Philosophy
Evidence > Assumptions | Code > Documentation | Efficiency > Verbosity

## Delegation Instructions
Use Task() for:
- Multi-session work spanning 30+ minutes
- Exploratory research requiring large context
- Batch operations over many files
- Work requiring specific subagent types (Explorer, Coder, Tester)

Use spawn_gemini() for:
- FREE tier research (2M tokens/minute, 1M token context)
- Multimodal analysis (documents, diagrams)
- Cost-sensitive batch operations
- Exploration with large token budgets

Use spawn_codex() for:
- Code changes requiring validation
- Refactoring with test coverage
- Complex multi-file updates

Avoid direct execution when:
- Work spans multiple phases
- Needs context from previous sessions
- Requires parallel coordination
- Needs specialized subagent capability

## Model Preferences
- Haiku: Best for delegation (consistent instruction following, cost-effective)
- Sonnet/Opus: Better for complex reasoning
- For delegation workflows, prefer Haiku

## Context Restoration
This prompt is auto-injected at session startup via SessionStart hook.
Survives compact operations (re-injected on resume).
Persists across /clear, --resume, and --continue operations.
```

### Validation

```bash
# Check file exists and is readable
ls -la .claude/system-prompt.md

# Check token count
python -c "
import tiktoken
text = open('.claude/system-prompt.md').read()
enc = tiktoken.get_encoding('cl100k_base')
tokens = len(enc.encode(text))
print(f'Token count: {tokens}')
if tokens > 500:
    print('WARNING: Prompt exceeds 500 tokens, may need truncation')
"

# Check markdown validity
python -c "import markdown; markdown.markdown(open('.claude/system-prompt.md').read())"
```

---

## Step 2: Modify SessionStart Hook

**File:** `packages/claude-plugin/hooks/scripts/session-start.py`
**Purpose:** Load and inject system prompt via additionalContext

### Checklist

- [ ] Backup original `session-start.py`
- [ ] Open file in editor
- [ ] Identify context-building section (around line 1160-1200)
- [ ] Add prompt loading function:

```python
def load_system_prompt(project_dir: str) -> str:
    """
    Load system prompt from .claude/system-prompt.md

    Returns:
        System prompt content, or empty string if not found
    """
    try:
        prompt_path = Path(project_dir) / ".claude" / "system-prompt.md"

        if not prompt_path.exists():
            print("Note: System prompt file not found at .claude/system-prompt.md", file=sys.stderr)
            return ""

        content = prompt_path.read_text()

        # Validate token count (rough estimate)
        if len(content) > 5000:  # ~1200 tokens at 4 chars/token
            print("Warning: System prompt truncated (exceeds recommended size)", file=sys.stderr)
            return content[:5000]

        return content

    except Exception as e:
        print(f"Warning: Could not load system prompt: {e}", file=sys.stderr)
        return ""
```

- [ ] Call function to load prompt early in main()
- [ ] Add prompt to context_parts with highest priority:

```python
# Build context (prepend system prompt if it exists)
context_parts = []

# HIGHEST PRIORITY: System prompt (from .claude/system-prompt.md)
system_prompt = load_system_prompt(project_dir)
if system_prompt:
    context_parts.append(system_prompt)

# Then add existing context sections...
if version_warning:
    context_parts.append(version_warning.strip())
context_parts.append(HTMLGRAPH_PROCESS_NOTICE)
# ... rest of existing code
```

- [ ] Verify JSON output still valid
- [ ] Add error handling for missing file (already handled by function)
- [ ] Add comment explaining system prompt injection

### Testing Function

```python
# At bottom of session-start.py, add test block:

if __name__ == "__main__":
    # Quick validation that system prompt loads
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_file = Path(tmpdir) / ".claude" / "system-prompt.md"
        prompt_file.parent.mkdir(parents=True)
        prompt_file.write_text("# Test Prompt\nTest content")

        loaded = load_system_prompt(tmpdir)
        assert loaded == "# Test Prompt\nTest content", f"Expected test content, got: {loaded}"
        print("✓ System prompt loading works correctly")
```

---

## Step 3: Integration Testing

### Test 1: Prompt File Loads Correctly

```bash
# Verify file exists
ls -la .claude/system-prompt.md

# Verify content is valid markdown
python -c "import markdown; print('✓ Markdown valid')" < .claude/system-prompt.md

# Verify token count
python -c "
import tiktoken
text = open('.claude/system-prompt.md').read()
enc = tiktoken.get_encoding('cl100k_base')
print(f'Token count: {len(enc.encode(text))}')
"
```

### Test 2: Hook JSON Output Validity

```bash
# Create test input JSON
cat > /tmp/hook-test-input.json << 'EOF'
{
  "session_id": "test-session-123",
  "transcript_path": "/tmp/transcript.jsonl",
  "cwd": "/Users/shakes/DevProjects/htmlgraph",
  "permission_mode": "default",
  "hook_event_name": "SessionStart",
  "source": "startup"
}
EOF

# Run hook and validate JSON output
uv run packages/claude-plugin/hooks/scripts/session-start.py < /tmp/hook-test-input.json | python -m json.tool > /dev/null && echo "✓ JSON output valid"
```

### Test 3: System Prompt Appears in Output

```bash
# Run hook and check for system prompt in additionalContext
uv run packages/claude-plugin/hooks/scripts/session-start.py < /tmp/hook-test-input.json | python -c "
import json
import sys
data = json.load(sys.stdin)
context = data.get('hookSpecificOutput', {}).get('additionalContext', '')
if '# System Prompt' in context or 'Core Philosophy' in context:
    print('✓ System prompt found in additionalContext')
else:
    print('✗ System prompt NOT found in additionalContext')
    sys.exit(1)
"
```

### Test 4: Session Startup Integration

```bash
# Start new Claude Code session in project
cd /Users/shakes/DevProjects/htmlgraph
claude --help  # Or actual claude command

# Verify:
# - No errors in startup
# - Prompt appears in conversation context
# - System prompt content visible to Claude
```

### Test 5: Compact/Resume Cycle

```bash
# In Claude Code session:
# 1. Start working on a feature
# 2. Run /compact to compact the context
# 3. Resume the session (--resume or /resume)
# 4. Verify system prompt is re-injected

# Check: System prompt should appear again after resume
```

### Test 6: /Clear Command

```bash
# In Claude Code session:
# 1. Run /clear
# 2. Start new session
# 3. Verify system prompt appears in context
```

---

## Step 4: Edge Case Testing

### Test: Missing Prompt File

- [ ] Temporarily rename `.claude/system-prompt.md`
- [ ] Run hook and verify:
  - No error
  - Warning logged to stderr
  - Session continues normally
  - No additionalContext corruption
- [ ] Restore file

### Test: Corrupt Prompt File

- [ ] Add invalid content to `.claude/system-prompt.md`
- [ ] Run hook and verify:
  - Hook handles gracefully
  - Error logged to stderr
  - Session continues
- [ ] Restore valid file

### Test: Very Large Prompt

- [ ] Create test prompt with 2000+ tokens
- [ ] Run hook and verify:
  - Prompt truncated with warning
  - JSON still valid
  - Session continues
- [ ] Restore normal-sized prompt

### Test: Hook Timeout

- [ ] Add artificial delay to prompt loading
- [ ] Verify hook timeout (30s) is respected
- [ ] Verify session continues if hook times out

---

## Step 5: Code Quality Checks

### Linting

```bash
# Run ruff on modified file
cd /Users/shakes/DevProjects/htmlgraph
uv run ruff check packages/claude-plugin/hooks/scripts/session-start.py --fix
uv run ruff format packages/claude-plugin/hooks/scripts/session-start.py
```

### Type Checking

```bash
# Run mypy on modified file
uv run mypy packages/claude-plugin/hooks/scripts/session-start.py
```

### Testing

```bash
# Run existing hook tests
uv run pytest tests/hooks/ -v

# Run full test suite
uv run pytest
```

---

## Step 6: Documentation

### Code Comments

- [ ] Add docstring to `load_system_prompt()` function
- [ ] Comment on why system prompt is prepended first
- [ ] Document expected behavior on error
- [ ] Note that hook never blocks session

### User Documentation

- [ ] Update `.claude/system-prompt.md` with usage notes
- [ ] Document customization: users can edit the file directly
- [ ] Document persistence: prompt survives compact/resume
- [ ] Document disabling: delete file to disable feature

### Developer Documentation

- [ ] Add note to hook-analysis.md about system prompt injection
- [ ] Document Layer 1 implementation (additionalContext)
- [ ] Link to SESSIONSTART_RESEARCH_FINDINGS.md
- [ ] Note Phases 2-4 planned (CLAUDE_ENV_FILE, fallbacks)

---

## Step 7: Commit Changes

### Checklist

- [ ] All tests pass: `uv run pytest`
- [ ] All linting passes: `uv run ruff check --fix && uv run ruff format`
- [ ] All type checking passes: `uv run mypy src/`
- [ ] Code quality gates pass: `./scripts/deploy-all.sh --build-only`

### Git Commit

```bash
cd /Users/shakes/DevProjects/htmlgraph

# Add files
git add .claude/system-prompt.md
git add packages/claude-plugin/hooks/scripts/session-start.py
git add tests/hooks/test_system_prompt_persistence.py  # New test file

# Commit with meaningful message
git commit -m "feat: Add SessionStart system prompt injection (Layer 1)

- Create .claude/system-prompt.md with core delegation directives
- Load and inject system prompt via SessionStart hook additionalContext
- Add error handling for missing/corrupt/large prompts
- System prompt persists across compact/resume/clear operations
- Implements Phase 1 of 4-phase system prompt persistence strategy

Addresses: Delegation instructions lost after compact operations
Research: SESSIONSTART_RESEARCH_FINDINGS.md, hook-analysis.md
Tests: All passing, edge cases validated
Impact: Ensures delegation context survives session boundaries

Closes: System prompt persistence issue"

# Verify commit
git log --oneline -1
```

---

## Success Criteria (Phase 1)

- [x] Research complete
- [ ] System prompt file created with proper content
- [ ] Hook modified to load and inject prompt
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Prompt appears in Claude Code session context
- [ ] Prompt re-injected after /compact and resume
- [ ] Edge cases handled gracefully
- [ ] Code passes linting, type checking, testing
- [ ] Changes committed to git
- [ ] Findings documented for Phases 2-4

---

## Estimated Timeline

| Task | Duration | Status |
|------|----------|--------|
| Create system-prompt.md | 15 min | Ready |
| Modify session-start.py | 30 min | Ready |
| Add error handling | 15 min | Ready |
| Unit testing | 30 min | Ready |
| Integration testing (4-5 tests) | 1 hour | Ready |
| Edge case testing | 30 min | Ready |
| Code quality (lint, type, tests) | 15 min | Ready |
| Documentation | 15 min | Ready |
| Git commit | 5 min | Ready |
| **Total** | **3-4 hours** | **Ready to start** |

**Can be completed in 1 day with focused effort.**

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Hook breaks session | Non-blocking (always exit 0), extensive error handling |
| JSON malformed | Validate before output, tested extensively |
| Missing prompt file | Graceful fallback, warning logged |
| Context duplication | HtmlGraph's hook deduplication handles it |
| Prompt too large | Truncate with warning, Layer 2/3 fallback |
| Performance impact | <50ms addition, negligible |
| Remote environment issue | Works with additionalContext (works everywhere) |

---

## Next Steps After Phase 1

**If Phase 1 succeeds:**
- [ ] Document findings
- [ ] Plan Phase 2 (CLAUDE_ENV_FILE fallback layer)
- [ ] Plan Phase 3 (model-aware prompting)
- [ ] Plan Phase 4 (production release)

**Phase 2:** Add CLAUDE_ENV_FILE persistence layer (2-3 days)
**Phase 3:** Add model-aware prompting (2-3 days)
**Phase 4:** Production release (1-2 days)

---

## Questions Before Starting?

- ✓ SessionStart hook mechanics clear?
- ✓ additionalContext JSON format understood?
- ✓ Error handling strategy defined?
- ✓ Testing approach clear?
- ✓ Timeline realistic?

All questions answered in SESSIONSTART_RESEARCH_FINDINGS.md

---

## Ready to Implement!

**Status: READY FOR EXECUTION**

All prerequisites are met:
- Research complete
- Technical details documented
- Implementation path clear
- Testing strategy defined
- Risk mitigation planned

Begin implementation when ready. Target completion: End of Day 3.

---

## Related Documentation

- **Research:** `.claude/SESSIONSTART_RESEARCH_FINDINGS.md`
- **Summary:** `RESEARCH_SUMMARY_SESSIONSTART_HOOK.md`
- **Hook Analysis:** `hook-analysis.md`
- **Hook Documentation:** `hook-documentation.md`
- **Current Implementation:** `packages/claude-plugin/hooks/scripts/session-start.py`

---

## Contact & Questions

If blocking issues arise:
1. Check SESSIONSTART_RESEARCH_FINDINGS.md
2. Review hook-documentation.md
3. Check current session-start.py for patterns
4. Refer to GitHub issues #10373, #14281, #9591 for known bugs

Implementation is straightforward and low-risk. Proceed with confidence.
