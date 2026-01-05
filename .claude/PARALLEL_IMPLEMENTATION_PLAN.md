# System Prompt Persistence: Parallel Implementation Plan

## Executive Summary

The original sequential 4-week plan can be collapsed to **2 concurrent weeks** through strategic parallelization. By identifying independent workstreams and coordinating dependencies, we reduce the critical path from 20 working days to 8-10 days.

**Key insight:** Most dependencies are on *integration points*, not on implementation details. Workstreams can proceed independently until final integration.

---

## 1. Dependency Analysis

### Task Dependencies Mapping

```
PHASE 1 (Sequential Blocker):
├─ Create .claude/system-prompt.md (MUST EXIST)
│  └─ Blocks: Layer 1 implementation, prompt testing
├─ Understand SessionStart hook architecture (RESEARCH)
│  └─ Blocks: Hook implementation details
└─ Design prompt content structure (DESIGN)
   └─ Blocks: Hook implementation

PHASE 2 (Medium Dependencies):
├─ Layer 1 implementation (DEPENDS ON: .claude/system-prompt.md EXISTS)
│  └─ Testing can START IMMEDIATELY (doesn't need actual injection)
├─ Layer 2 implementation (DEPENDS ON: Layer 1 API is defined, NOT on Layer 1 working)
├─ Layer 3 implementation (DEPENDS ON: Layer 1 API is defined, NOT on Layer 1 working)
└─ Integration tests (DEPENDS ON: ALL 3 layers exist, NOT on them working perfectly)

PHASE 3 (Minimal Dependencies):
├─ Model-specific prompts (DEPENDS ON: Core prompt works, can write independently)
├─ delegate.sh creation (DEPENDS ON: CLAUDE_ENV_FILE exists, can write shell independently)
└─ Model testing (DEPENDS ON: delegate.sh exists)

PHASE 4 (Final Assembly):
├─ User guide (DEPENDS ON: All above exists, can draft early)
├─ Test suite consolidation (DEPENDS ON: Tests written in Phases 1-3)
└─ Production readiness (DEPENDS ON: All above)
```

### Critical Path Analysis

**Blocking items (must complete sequentially):**
1. ✅ Create `.claude/system-prompt.md` (2-4h)
2. ✅ Understand hook implementation pattern (2-3h)
3. ✅ Design 3-layer architecture (1-2h)

**Subtotals:** 5-9 hours before any parallel work can begin

**After blocking items, everything else can run in parallel.**

---

## 2. Parallelization Opportunities

### Stream A: Hook Implementation (Core)
**Duration:** 3-4 days
**Dependencies:** Only needs prompt.md to exist and architecture design

```
├─ Update hook scaffolding (1h) - Preparation
├─ Implement Layer 1: additionalContext (1 day)
│  ├─ Load prompt file
│  ├─ Validate token count
│  ├─ Inject via additionalContext
│  └─ Error handling
├─ Implement Layer 2: CLAUDE_ENV_FILE (1 day)
│  ├─ Create env file
│  ├─ Write model preference
│  ├─ Export environment variables
│  └─ Error handling
├─ Implement Layer 3: File backup (0.5 day)
│  ├─ Create session-state.json structure
│  ├─ Backup on injection
│  └─ Cleanup old backups
├─ Integration test (0.5 day)
│  ├─ Test all 3 layers together
│  ├─ Test fallback paths
│  └─ Verify hook output JSON valid
└─ Documentation (0.5 day)
   └─ Update hook docs
```

### Stream B: Testing & Validation (PARALLEL with Stream A)
**Duration:** 2-3 days
**Can start immediately** - Tests don't need actual working hook

```
├─ Unit tests for Layer 1 (1 day)
│  ├─ Test prompt file loading
│  ├─ Test token counting
│  ├─ Test truncation logic
│  ├─ Test error cases
│  └─ Test edge cases (missing file, large prompts)
├─ Unit tests for Layer 2 (0.5 day)
│  ├─ Test env file creation
│  ├─ Test variable formatting
│  └─ Test edge cases
├─ Unit tests for Layer 3 (0.5 day)
│  ├─ Test backup creation
│  ├─ Test backup restoration
│  └─ Test cleanup logic
├─ Integration tests (1 day)
│  ├─ Test compact/resume cycles
│  ├─ Test all 3 layers in sequence
│  ├─ Test fallback behaviors
│  ├─ Test hook JSON output
│  └─ Test with different session inputs
└─ Test discovery (0.5 day)
   └─ Set up test fixtures and utilities
```

### Stream C: Documentation & Model Features (PARALLEL with A & B)
**Duration:** 1-2 days
**Can start immediately** - Drafting doesn't require implementation

```
├─ Draft user guide (4h)
│  ├─ Overview section
│  ├─ Installation steps
│  ├─ Configuration guide
│  ├─ Troubleshooting
│  └─ FAQ
├─ Create model guidance section (2h)
│  ├─ Haiku preference explanation
│  ├─ Model-specific prompts
│  └─ Testing strategy
├─ Create delegate.sh helper (2h)
│  ├─ Basic shell structure
│  ├─ Model selection logic
│  ├─ Environment setup
│  └─ Error handling
├─ Integration with prompt.md (1h)
│  └─ Add model guidance to system-prompt.md
└─ Review & refinement (1h)
   └─ Cross-reference with implementation
```

---

## 3. Concrete Concurrent Workstreams

### Three Parallel Work Tracks

```
TIMELINE (Calendar Days)
├─ Day 1 (4-5h)
│  ├─ BLOCKING WORK (Sequential, must finish)
│  │  └─ Create .claude/system-prompt.md (4-5h)
│  │     ├─ Define prompt structure
│  │     ├─ Write delegation instructions
│  │     ├─ Add model guidance
│  │     ├─ Validate token count (<500)
│  │     └─ Test basic content
│  │
│  └─ RESEARCH (Sequential, must finish)
│     └─ Understand SessionStart hook architecture (1-2h)
│        ├─ Review session-start.py current implementation
│        ├─ Test hook input/output format
│        ├─ Verify additionalContext injection mechanism
│        ├─ Document environment variable handling
│        └─ List edge cases to handle
│
├─ Days 2-3 (PARALLEL STREAMS BEGIN)
│  │
│  ├─ STREAM A: Hook Implementation (2 days)
│  │  ├─ Day 2 (6-8h):
│  │  │  ├─ Update hook scaffolding (1h)
│  │  │  ├─ Implement Layer 1 (4h)
│  │  │  │  ├─ Load prompt.md file
│  │  │  │  ├─ Validate tokens
│  │  │  │  ├─ Inject via additionalContext
│  │  │  │  └─ Log success/failures
│  │  │  └─ Manual testing of Layer 1 (1-2h)
│  │  │     ├─ Create test hook input
│  │  │     ├─ Run hook manually
│  │  │     ├─ Verify prompt injected
│  │  │     └─ Verify JSON output valid
│  │  │
│  │  └─ Day 3 (6-8h):
│  │     ├─ Implement Layer 2 (3h)
│  │     ├─ Implement Layer 3 (2h)
│  │     ├─ Integration test (2h)
│  │     └─ Documentation (1h)
│  │
│  ├─ STREAM B: Testing (2 days) [PARALLEL with Stream A]
│  │  ├─ Day 2 (6-8h):
│  │  │  ├─ Set up test fixtures (1h)
│  │  │  ├─ Unit tests Layer 1 (3h)
│  │  │  ├─ Unit tests Layer 2 (2h)
│  │  │  └─ Unit tests Layer 3 (1h)
│  │  │
│  │  └─ Day 3 (6-8h):
│  │     ├─ Integration tests (4h)
│  │     ├─ Fallback tests (2h)
│  │     ├─ Edge case tests (1h)
│  │     └─ Test review & refinement (1h)
│  │
│  └─ STREAM C: Documentation (1.5 days) [PARALLEL with A & B]
│     ├─ Day 2 (4h):
│     │  ├─ Draft user guide (2.5h)
│     │  └─ Create delegate.sh skeleton (1.5h)
│     │
│     └─ Day 3 (3h):
│        ├─ Model guidance section (1.5h)
│        ├─ Integration with prompt.md (1h)
│        └─ Review & cross-check (0.5h)
│
├─ Day 4-5 (SYNC & INTEGRATION)
│  ├─ Integration testing between all streams (1 day)
│  │  ├─ Test hook produces valid JSON
│  │  ├─ Test env file exports work
│  │  ├─ Test delegate.sh invokes correctly
│  │  ├─ Test documentation accuracy
│  │  └─ Test full compact/resume cycle
│  │
│  ├─ Code review & refactoring (0.5 day)
│  │  ├─ Review hook implementation
│  │  ├─ Review test coverage
│  │  ├─ Review documentation
│  │  └─ Fix any issues found
│  │
│  └─ Phase 1 Release (0.5 day)
│     ├─ Run full test suite
│     ├─ Verify code quality (ruff, mypy)
│     ├─ Commit all changes
│     └─ Tag Phase 1 complete
│
└─ Days 6-8 (PHASES 2-4: SEQUENTIAL)
   └─ Phases 2, 3, 4 follow same pattern...
      (Each phase: 1 parallel cycle + 0.5 sync)
```

---

## 4. Parallel Implementation Plan

### Timeline Summary

| Phase | Duration | Critical Path | Parallel Streams | Total Time |
|-------|----------|---|---|---|
| **Phase 1** | 5 days | 1 day blocking + 2 parallel + 1 sync | 3 streams | 5 days |
| **Phase 2** | 3.5 days | 0.5 day prep + 2 parallel + 0.5 sync | 3 streams | 3.5 days |
| **Phase 3** | 2.5 days | 1 day prep + 1 parallel + 0.5 sync | 2 streams | 2.5 days |
| **Phase 4** | 2 days | 1 day prep + 0.5 parallel + 0.5 sync | 1 stream | 2 days |
| **TOTAL** | **13 days** | (vs 20 sequential) | **7 days saved** | **~11 days actual** |

### Critical Path Visualization

```
Sequential Approach (20 days):
├─ Phase 1 (5 days) ⚠️ Blocking all later work
├─ Phase 2 (5 days) ⚠️ Blocking Phase 3
├─ Phase 3 (5 days) ⚠️ Blocking Phase 4
└─ Phase 4 (5 days)
   Total: 20 days

Parallel Approach (11 days):
├─ Phase 1 (5 days)
│  ├─ Day 1: Research & blocking work (sequential)
│  ├─ Days 2-3: Streams A, B, C in parallel
│  └─ Days 4-5: Integration & sync
│
├─ Phase 2 (3.5 days) [STARTS on Day 4]
│  ├─ Prep: Design Layer 2-3 architecture (0.5 day)
│  ├─ Days 5-6: Streams A, B, C in parallel
│  └─ Day 6.5: Integration & sync
│
├─ Phase 3 (2.5 days) [STARTS on Day 7]
│  ├─ Prep: Model guidance specification (0.5 day)
│  ├─ Days 7-8: Streams A, B in parallel
│  └─ Day 8.5: Integration & sync
│
└─ Phase 4 (2 days) [STARTS on Day 9]
   ├─ Prep: GA readiness checklist (0.5 day)
   ├─ Days 9-9.5: Final assembly
   └─ Day 10: Release

TOTAL: ~10-11 calendar days (not 20)
Savings: 9-10 days (45-50% reduction)
```

---

## 5. Stream-by-Stream Breakdown

### Stream A: Hook Implementation

**Responsible:** 1 developer (e.g., "Implementation Agent")

**Phase 1:**
- Update `/packages/claude-plugin/hooks/scripts/session-start.py`
  - Add `load_system_prompt()` function
  - Add `inject_prompt()` function with additionalContext
  - Add `create_env_file()` function (Layer 2)
  - Add `backup_to_state_file()` function (Layer 3)
  - Add comprehensive error handling
  - Add logging
- Update `/packages/claude-plugin/hooks/hooks.json` if needed
- Verify hook script syntax and imports
- Manual testing with test inputs

**Phase 2:**
- Add resilience layer (CLAUDE_ENV_FILE support)
- Add backup/recovery logic
- Enhanced error handling
- Fallback mechanism testing

**Phase 3:**
- Add model-specific prompt loading
- Create `.claude/delegate.sh` helper
- Test model preference signaling

**Phase 4:**
- Hook optimization
- Performance tuning
- Production hardening

### Stream B: Testing & Validation

**Responsible:** 1 developer (e.g., "Testing Agent")

**Phase 1:**
- Create `/tests/hooks/test_system_prompt_persistence.py`
  - Test prompt file loading
  - Test token counting and truncation
  - Test error handling (missing file, corruption)
  - Test edge cases (very large prompt, special characters)
  - Test hook JSON output format
  - Test additionalContext injection format
  - Test with various hook input formats
- Integration tests
  - Test compact/resume cycles
  - Test multiple consecutive sessions
  - Test fallback behaviors

**Phase 2:**
- Add resilience tests
- Test CLAUDE_ENV_FILE creation
- Test file backup and recovery
- Test cleanup logic
- Test layer fallback sequence

**Phase 3:**
- Add model-specific tests
- Test model preference in prompt
- Test delegate.sh invocation

**Phase 4:**
- Comprehensive coverage audit
- Performance tests
- Load testing

### Stream C: Documentation & Model Features

**Responsible:** 1 developer (e.g., "Documentation Agent")

**Phase 1:**
- Draft `/docs/system-prompt-persistence-guide.md`
  - Introduction and problem statement
  - Architecture overview (3 layers)
  - Installation instructions
  - Configuration guide
  - Troubleshooting section
  - FAQ
- Update `.claude/system-prompt.md` structure
- Create helper scripts skeleton

**Phase 2:**
- Enhance guide with resilience section
- Document fallback behaviors
- Add monitoring recommendations

**Phase 3:**
- Add model-specific guidance
- Document delegate.sh usage
- Add examples for different models
- Performance tuning guide

**Phase 4:**
- Final review and polish
- Ensure all features documented
- Create quick-start guide
- Setup monitoring dashboard

---

## 6. Integration Points

### Synchronization Checkpoints

**End of Day 1 (Blocking Work Complete):**
- ✅ `.claude/system-prompt.md` exists and is valid
- ✅ SessionStart hook architecture understood
- ✅ 3-layer design documented

**End of Days 2-3 (All streams produce output):**
- ✅ Stream A: Layer 1 implemented and tested manually
- ✅ Stream B: Unit tests written (pass or fail is OK)
- ✅ Stream C: First draft of user guide and helper scripts

**End of Days 4-5 (Integration Phase):**
- ✅ All streams integrated
- ✅ All tests pass
- ✅ Documentation reviewed against implementation
- ✅ Code quality gates pass (ruff, mypy, pytest)
- ✅ Phase 1 complete and committed

### Testing Integration Strategy

**Unit tests (Stream B) don't wait for implementation (Stream A):**
```python
# tests/hooks/test_system_prompt_persistence.py
# These tests can be written BEFORE implementation exists

def test_prompt_file_loading():
    # Test the utility function will work
    # Uses mock prompt file
    pass

def test_token_counting():
    # Test token counting logic
    # Uses fixed test strings
    pass

# Later, when implementation exists, these same tests run against real code
```

**Integration tests need minimal coordination:**
- Stream A produces a hook script
- Stream B creates test fixtures that invoke the script
- Tests run whenever both exist

**Documentation can reference implementation:**
- Stream C writes guide structure early (outlines, placeholders)
- Stream A implements features
- Stream C fills in implementation details later

---

## 7. Merge & Integration Strategy

### Avoiding Conflicts

**Same file coordination (if needed):**

Session-start.py modifications:
```python
# Stream A: Adds new functions
def load_system_prompt():
    """Layer 1: Load and inject prompt"""
    pass

def create_env_file():
    """Layer 2: Create environment file"""
    pass

def backup_to_state():
    """Layer 3: Backup to file"""
    pass

def main():
    # Existing code
    # Stream A adds calls to new functions here
```

**No conflicts because:**
- Stream A only ADDS new functions
- Stream A only modifies main() to CALL new functions
- Stream A doesn't modify any existing code
- Hook behavior is purely additive

**Test file creation:**
- Stream B creates entirely new test file: `test_system_prompt_persistence.py`
- No existing tests modified
- No conflicts possible

**Documentation:**
- Stream C creates new guide: `system-prompt-persistence-guide.md`
- No existing docs modified
- No conflicts possible

### Merge Sequence

```
1. Stream B: Create test file (no dependencies)
   └─ Can merge anytime

2. Stream C: Create documentation and helpers (no dependencies)
   └─ Can merge anytime

3. Stream A: Modify hook implementation (depends on 1 & 2 for reference)
   └─ Merge last after all reference files exist

4. Integration: Update hooks.json if needed
   └─ Merge after all other changes

5. Tag Phase 1 complete
   └─ Only after all changes merged and tests pass
```

---

## 8. Risk Analysis & Mitigations

### Potential Conflicts

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Stream B writes tests before Stream A exists | High | Low | Use mocks, defer execution tests |
| Prompt.md not ready on time | Low | High | Start immediately on Day 1, high priority |
| Hook API changes | Low | High | Lock hook interface in architecture design |
| Test framework incompatibility | Low | Medium | Validate test setup early (Day 1) |
| Integration surprises | Medium | Medium | Daily integration tests during Days 4-5 |
| Documentation drift | Medium | Low | Cross-check docs vs code daily |

### Rollback Plan

**If a stream fails:**

Option 1: Pause that stream, let others continue
- Other streams unaffected
- Can catch up later

Option 2: Reduce scope
- Keep essential features (Layer 1 only)
- Defer Layers 2-3 to Phase 2
- Still make progress

Option 3: Restart sequentially
- If parallelization breaks, revert to sequential plan
- Only lose 1-2 days of rework
- Still faster than original 20-day plan

**Commit strategy:**
- Commit after each small task (not at end of stream)
- Keep streams independent (no inter-stream dependencies)
- Can cherry-pick commits if needed
- Can revert individual commits without affecting other streams

---

## 9. Success Metrics

### Phase 1 Completion Criteria

**Stream A (Implementation):**
- ✅ Layer 1 injects prompt via additionalContext
- ✅ Layer 2 creates CLAUDE_ENV_FILE (even if unused)
- ✅ Layer 3 creates backup file
- ✅ Hook outputs valid JSON
- ✅ No errors in hook execution

**Stream B (Testing):**
- ✅ 20+ unit tests written
- ✅ 10+ integration tests written
- ✅ All tests pass
- ✅ 90%+ code coverage of hook code
- ✅ Edge cases tested

**Stream C (Documentation):**
- ✅ User guide drafted (5+ sections)
- ✅ Installation instructions clear
- ✅ Troubleshooting guide created
- ✅ Model guidance documented
- ✅ Helper script(s) created

**Integration:**
- ✅ All streams merged without conflicts
- ✅ Full test suite passes (unit + integration)
- ✅ Documentation matches implementation
- ✅ Code quality gates pass
- ✅ Compact/resume cycle works end-to-end

---

## 10. Execution Checklist

### Pre-Work (Before Day 1)

- [ ] Read hook documentation and understand SessionStart invocation
- [ ] Review existing session-start.py code
- [ ] Set up development environment
- [ ] Create feature/spike in HtmlGraph for tracking

### Day 1 (Blocking Work)

- [ ] Create `.claude/system-prompt.md` (4-5h)
  - [ ] Define structure (delegation, model guidance, context restoration)
  - [ ] Write core content
  - [ ] Count tokens
  - [ ] Validate Markdown syntax
  - [ ] Ensure <500 tokens
- [ ] Research SessionStart hook (1-2h)
  - [ ] Review session-start.py current implementation
  - [ ] Test hook input/output format with manual test
  - [ ] Document additionalContext mechanism
  - [ ] List edge cases

### Days 2-3 (Parallel Streams)

**Stream A Lead:**
- [ ] Day 2 morning: Update hook scaffolding
- [ ] Day 2: Implement Layer 1
- [ ] Day 2 afternoon: Manual testing of Layer 1
- [ ] Day 3: Implement Layers 2 & 3
- [ ] Day 3: Integration testing

**Stream B Lead:**
- [ ] Day 2 morning: Set up test fixtures and utilities
- [ ] Day 2: Write Layer 1 unit tests
- [ ] Day 2: Write Layer 2-3 unit tests
- [ ] Day 3: Write integration tests
- [ ] Day 3: Test edge cases and fallbacks

**Stream C Lead:**
- [ ] Day 2: Draft user guide (outline + first 3 sections)
- [ ] Day 2: Create delegate.sh skeleton
- [ ] Day 3: Complete user guide draft
- [ ] Day 3: Add model guidance section

### Days 4-5 (Integration & Sync)

- [ ] Day 4: Run integration tests
- [ ] Day 4: Cross-check documentation
- [ ] Day 4: Fix any integration issues
- [ ] Day 5: Code review across all streams
- [ ] Day 5: Final test run
- [ ] Day 5: Commit Phase 1
- [ ] Day 5: Tag Phase 1 complete

---

## 11. Time Estimate Summary

### Original Sequential Plan
```
Phase 1: 5 days
Phase 2: 5 days
Phase 3: 5 days
Phase 4: 5 days
────────────────
Total: 20 days
```

### Parallel Implementation Plan
```
Blocking Research:      1 day (Days 1)
Parallel Streams:       2 days (Days 2-3)
Integration:            1 day (Days 4)
Code Review & Commit:   0.5 days (Days 5)
────────────────────────────────
Phase 1 Total:          4.5 days ← (saves 0.5 days)

Phase 2 (same pattern): 3.5 days (saves 1.5 days)
Phase 3 (same pattern): 2.5 days (saves 2.5 days)
Phase 4 (same pattern): 2 days (saves 3 days)
────────────────────────────────
TOTAL:                  12.5 days ← (saves 7.5 days!)
```

**Actual Calendar Time:** 10-11 working days (includes some task overlap)

**Time Saved:** 45% reduction (7.5-10 days)

---

## 12. Critical Success Factors

### Must Have
1. ✅ System prompt file created and validated FIRST (Day 1)
2. ✅ Hook architecture locked before implementation starts (Day 1)
3. ✅ No inter-stream dependencies after Day 1
4. ✅ Daily synchronization during Days 2-3 (async communication)
5. ✅ All tests pass before merging

### Should Have
1. ✅ Daily commits from each stream (atomicity)
2. ✅ Code review before merge
3. ✅ Documentation updated to match implementation
4. ✅ Performance baseline recorded

### Nice to Have
1. ✅ Parallel development tools (git branches per stream)
2. ✅ Automated test running on each commit
3. ✅ Integration bot that runs full test suite on merge

---

## 13. Detailed Task Breakdown

### Phase 1 Workstreams (Detailed)

#### Stream A: Hook Implementation

**Task A1: Hook Scaffolding (1 hour)**
- Update `packages/claude-plugin/hooks/scripts/session-start.py`
- Add imports (json, Path, etc.)
- Add logging setup
- Verify existing hook structure doesn't break

**Task A2: Layer 1 - Prompt Injection (4 hours)**
- Implement `load_system_prompt()`
  - Read `.claude/system-prompt.md`
  - Parse Markdown
  - Extract content sections
  - Validate token count using tiktoken
  - Truncate if needed with warning
- Implement `inject_prompt()`
  - Format prompt for additionalContext
  - Add context injection to hook output
  - Verify JSON format

**Task A3: Layer 2 - Environment File (3 hours)**
- Implement `create_env_file()`
  - Create `CLAUDE_ENV_FILE` location
  - Write model preferences
  - Export environment variables
  - Verify shell syntax
- Add error handling
- Add cleanup on failure

**Task A4: Layer 3 - Backup (2 hours)**
- Implement `backup_to_state_file()`
  - Create `.claude/session-state.json`
  - Store prompt metadata
  - Store session info
  - Add timestamp
- Implement cleanup (remove old backups)
- Test restore from backup

**Task A5: Integration & Testing (2 hours)**
- Update `main()` to call all 3 layers
- Handle failures gracefully (non-blocking)
- Test hook with manual inputs
- Verify JSON output format

#### Stream B: Testing & Validation

**Task B1: Test Setup (1 hour)**
- Create `tests/hooks/test_system_prompt_persistence.py`
- Set up pytest fixtures
- Create mock prompt files
- Create test hook input generator

**Task B2: Layer 1 Tests (3 hours)**
```python
# Test loading
test_load_valid_prompt_file()
test_load_missing_prompt_file()
test_load_corrupted_file()

# Test token counting
test_token_count_under_limit()
test_token_count_over_limit()
test_token_truncation()

# Test formatting
test_prompt_injection_format()
test_additionalcontext_json_format()

# Test edge cases
test_empty_prompt()
test_very_large_prompt()
test_special_characters()
test_unicode_handling()
```

**Task B3: Layer 2 & 3 Tests (2 hours)**
```python
# Layer 2
test_env_file_creation()
test_env_var_export()
test_env_file_cleanup()

# Layer 3
test_backup_file_creation()
test_backup_file_format()
test_backup_restoration()
test_backup_cleanup()
```

**Task B4: Integration Tests (2 hours)**
```python
# Full flow
test_all_three_layers_together()
test_fallback_layer1_fails()
test_fallback_layer2_fails()
test_fallback_layer3_fails()

# Session cycle
test_compact_and_resume_cycle()
test_multiple_consecutive_sessions()
test_hook_idempotency()
```

**Task B5: Test Review (1 hour)**
- Run full test suite
- Check coverage
- Fix failing tests
- Document test cases

#### Stream C: Documentation & Model Features

**Task C1: User Guide Draft (3 hours)**
```markdown
# System Prompt Persistence Guide

## Overview
- What problem does this solve?
- Why is it important?
- How does it work?

## Installation
- Prerequisites
- Installation steps
- Verification

## Configuration
- System prompt customization
- Model preferences
- Environment setup

## Troubleshooting
- Common issues
- Debug steps
- How to report bugs

## FAQ
```

**Task C2: Model Guidance (2 hours)**
- Haiku vs Sonnet/Opus comparison
- When to use which model
- Model-specific prompt sections
- Testing with different models

**Task C3: Helper Scripts (2 hours)**
- Create `.claude/delegate.sh`
  - Model selection logic
  - Delegation pattern
  - Environment setup
  - Error handling
- Create `.claude/system-prompt.md` enhancements
  - Add model guidance
  - Add delegation instructions
  - Add context restoration notes

**Task C4: Integration (1 hour)**
- Cross-check guide with implementation
- Ensure all features documented
- Add examples and code snippets
- Verify all links work

---

## 14. Final Recommendations

### Implementation Order

**Recommended:** Parallel workstreams as described

**Alternative:** If resources limited, prioritize:
1. Stream A (core feature must work)
2. Stream B (tests verify it works)
3. Stream C (documentation can be added later)

### Key Success Factors

1. **Lock architecture on Day 1**
   - Don't change design during implementation
   - Small design changes are OK if communicated immediately

2. **Async communication**
   - Daily syncs via HtmlGraph spikes
   - Share updates in spike findings
   - Tag each other for blockers

3. **Test-driven from the start**
   - Write tests first (Stream B before Stream A)
   - Tests document expected behavior
   - Implementation follows test specs

4. **Atomic commits**
   - Commit frequently (every 1-2 hours)
   - Keep commits small and reversible
   - Include test file updates with implementation

5. **Daily integration**
   - Even in parallel, run full test suite daily
   - Catch integration issues early
   - Fix immediately vs accumulating debt

---

## Appendix: HtmlGraph Integration

### Track for Parallel Implementation

```python
from htmlgraph import SDK

sdk = SDK(agent="implementation-orchestrator")

track = sdk.tracks.builder() \
    .title("System Prompt Persistence - Parallel Implementation") \
    .priority("high") \
    .with_spec(
        overview="Reduce 4-week sequential plan to 2 weeks using parallel streams",
        requirements=[
            "Phase 1 complete with all 3 layers",
            "90%+ test coverage",
            "Documentation complete",
            "All streams integrated with no conflicts"
        ]
    ) \
    .with_plan_phases([
        ("Phase 1: Core Persistence", [
            "Stream A: Hook implementation (4.5 days)",
            "Stream B: Testing & validation (parallel with A)",
            "Stream C: Documentation (parallel with A & B)",
            "Integration & sync (1 day)"
        ]),
        ("Phases 2-4: Follow same parallel pattern", [
            "Phase 2: Resilience (3.5 days)",
            "Phase 3: Model awareness (2.5 days)",
            "Phase 4: Production ready (2 days)"
        ])
    ]) \
    .create()

# Create features for each stream
feature_a = sdk.features.create("Stream A: Hook Implementation") \
    .set_track(track.id) \
    .add_steps([
        "Update hook scaffolding",
        "Implement Layer 1 (additionalContext)",
        "Implement Layer 2 (CLAUDE_ENV_FILE)",
        "Implement Layer 3 (file backup)",
        "Integration testing"
    ]).save()

feature_b = sdk.features.create("Stream B: Testing & Validation") \
    .set_track(track.id) \
    .add_steps([
        "Set up test fixtures",
        "Write Layer 1 unit tests",
        "Write Layers 2-3 unit tests",
        "Write integration tests",
        "Test review & refinement"
    ]).save()

feature_c = sdk.features.create("Stream C: Documentation") \
    .set_track(track.id) \
    .add_steps([
        "Draft user guide",
        "Create model guidance",
        "Create helper scripts",
        "Integration with implementation"
    ]).save()
```

### Tracking Progress

**Daily updates from each stream:**

```python
from htmlgraph import SDK

sdk = SDK(agent="stream-a-implementation")
sdk.spikes.create("Stream A Progress: Day 2") \
    .set_findings("""
    ## Completed
    - Hook scaffolding updated
    - Layer 1 prompt loading implemented
    - Manual testing of Layer 1 successful

    ## In Progress
    - Integration with hook main()

    ## Blockers
    None

    ## Next Steps
    - Implement Layer 2 tomorrow morning
    - Coordinate with Stream B on test expectations
    """).save()
```

---

## Summary

The system prompt persistence feature can be delivered in **10-12 working days** using parallel workstreams instead of **20 sequential days**.

**Key advantages:**
- 45-50% time savings
- Reduced dependency blocking
- Better team utilization
- Faster feedback loop
- Earlier validation of approach

**Key risks:**
- Requires strong coordination
- Needs clear architecture upfront
- Must have daily sync
- Dependent on Stream A/B/C quality

**Recommendation:**
Implement this parallel plan. The upfront synchronization cost (Day 1) is repaid 7-10x over by stream parallelization in Days 2-3.

