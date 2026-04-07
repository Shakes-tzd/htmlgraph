# Orchestrator Routing Decision Flow - Visual Guide

---

## QUICK DECISION FLOW (< 5 seconds)

```
                          START: New Task
                               |
                               v
                    Is this STRATEGIC?
                  (planning/design/decisions)
                          /      \
                       YES        NO
                       /            \
                    EXECUTE       Can ONE tool call?
                   DIRECTLY       (read/check/status)
                                   /       \
                                YES        NO
                                /           \
                          EXECUTE      Needs ERROR
                          DIRECTLY      HANDLING?
                                        /        \
                                      YES        NO
                                      /           \
                                   DELEGATE    Can CASCADE
                                   (Task)      to 3+ calls?
                                              (git/build/analysis)
                                               /         \
                                             YES         NO
                                             /            \
                                        DELEGATE      Is INDEPENDENT
                                        (Task)        PARALLEL WORK?
                                                      /          \
                                                    YES           NO
                                                    /              \
                                              SPAWN            USE TASK()
                                            (spawn_*)     (shared context)
```

**Decision Time:** ~5 seconds
**Coverage:** 90% of real-world orchestration scenarios
**Fallback:** When uncertain → DELEGATE (cheaper than failed direct execution)

---

## SPAWNER SELECTION TREE (Specific)

```
                    START: Which Spawner?
                           |
                           v
                  Code generation/debug/refactor?
                  (fixing bugs, writing features)
                    /                        \
                  YES                         NO
                  /                            \
          spawn_codex              Image/screenshot/visual?
          sandbox=               (UI analysis, diagrams)
          workspace-write       /                      \
                              YES                      NO
                              /                         \
                       spawn_gemini            GitHub/git work?
                     include_directories=    (PR review, branches)
                       ["docs/"]           /                   \
                                         YES                   NO
                                         /                      \
                                spawn_copilot        Quick validation/fact-check?
                                allow_tools=         (syntax, is JSON valid?)
                                ["shell(git)"]      /                        \
                                                  YES                        NO
                                                  /                           \
                                         spawn_gemini        Complex reasoning/
                                        (default, cheap)    architecture/strategy?
                                                             /               \
                                                           YES              NO
                                                           /                 \
                                                 spawn_claude        ↑ BACKTRACK
                                              permission_mode=    (Unclear?
                                                 "plan"           Try again or
                                                                  delegate)
```

---

## SPAWNER DECISION TABLE (At-a-Glance)

```
┌─────────────────────────────────────────────────────────────────┐
│                 SPAWNER SELECTION QUICK REFERENCE                │
├────────────────────┬─────────────────────┬──────────────────────┤
│ USE CASE           │ SELECT SPAWNER      │ KEY SETTING          │
├────────────────────┬─────────────────────┬──────────────────────┤
│ Fix bug            │ spawn_codex         │ sandbox="workspace-  │
│ Code generation    │                     │ write"               │
│ Code refactoring   │                     │                      │
├────────────────────┼─────────────────────┼──────────────────────┤
│ Screenshot analysis│ spawn_gemini        │ include_directories= │
│ UI feedback        │                     │ ["docs/"]            │
│ Visual diagram     │                     │                      │
├────────────────────┼─────────────────────┼──────────────────────┤
│ PR review          │ spawn_copilot       │ allow_tools=         │
│ Git branch work    │                     │ ["shell(git)"]       │
│ GitHub workflows   │                     │                      │
├────────────────────┼─────────────────────┼──────────────────────┤
│ Validation check   │ spawn_gemini        │ (default)            │
│ Syntax checking    │                     │ No extra settings    │
│ Fact-check         │                     │                      │
├────────────────────┼─────────────────────┼──────────────────────┤
│ Architecture       │ spawn_claude        │ permission_mode=     │
│ Strategic planning │                     │ "plan"               │
│ Complex reasoning  │                     │                      │
└────────────────────┴─────────────────────┴──────────────────────┘
```

---

## TASK() vs SPAWN_* DECISION

```
                Is work DEPENDENT
            (each step builds on prior)?
                    /          \
                  YES           NO
                  /              \
            Use Task()      Is work PARALLEL
          (shared context)   independent?
            + caching           /        \
            5x cheaper        YES        NO
                              /           \
                         Spawn_*      Back to
                       (parallel)     decision
                                      tree
```

**Rule:**
- Feature impl (auth → test → docs) = DEPENDENT → Task()
- Analyze 20 files = PARALLEL → spawn_gemini (concurrent)
- "What's next?" = STRATEGIC → Execute directly

---

## PERMISSION MODES (spawn_claude only)

```
                  Need Permission Control?
                       /          \
                      NO          YES
                      /            \
                  Use            Which level?
                default           /    |    \
                mode         Safe Auto Strategy
                             /    |          \
                        plan  delegate  bypassPermissions

        plan: Generate idea without execution
     delegate: Auto-approve delegated work
bypassPermissions: Auto-approve everything
```

**Recommendation:** Start with `plan` for strategy. Use `delegate` for known patterns.

---

## COST OPTIMIZATION LADDER

```
CHEAPEST (10% baseline)
         ↓
    spawn_gemini
    ├─ Quick analysis
    ├─ Parallel work
    └─ Fact-checking
         ↓
    Task() (20% baseline)
    ├─ Sequential steps
    ├─ Uses caching
    └─ 5x cheaper than spawn isolation
         ↓
    spawn_codex (50% baseline)
    ├─ Code generation
    ├─ Specialized tooling
    └─ Worth premium for coding work
         ↓
    spawn_copilot (60% baseline)
    ├─ GitHub integration
    ├─ Fine-grained permissions
    └─ Premium for GitHub workflows
         ↓
MOST EXPENSIVE (100% baseline)
    spawn_claude
    ├─ Highest reasoning
    ├─ Complex analysis
    └─ Best for strategic decisions

OPTIMIZATION RULES:
    Large parallel (10+) → Always spawn_gemini
    Sequential related  → Always Task()
    Code work          → spawn_codex (worth it)
    Complex strategy   → spawn_claude (best capability)
```

---

## ROUTING EXAMPLES WITH PATHS

### Example 1: Bug Fix
```
User: "Fix the null pointer in auth.py"
        |
        v
Is strategic? NO
        |
        v
One tool call? NO (likely needs testing, retries)
        |
        v
Needs error handling? YES
        |
        v
Can cascade? YES (compile → test → fix → compile)
        |
        v
DECISION: Delegate
        |
        v
ROUTING: spawn_codex (code generation + testing)
        |
        v
SETTINGS: sandbox="workspace-write"
        |
        v
COMMAND: spawner.spawn_codex("Fix null pointer...", sandbox="workspace-write")
```

### Example 2: Multi-File Analysis
```
User: "Check 20 config files for security issues"
        |
        v
Is strategic? NO
        |
        v
One tool call? NO (20 independent files)
        |
        v
Needs error handling? Partially (per-file)
        |
        v
Can cascade? NO (each file independent)
        |
        v
Independent parallel work? YES
        |
        v
DECISION: Spawn (not Task)
        |
        v
ROUTING: spawn_gemini (quick analysis, cheap)
        |
        v
PATTERN: Concurrent execution
        |
        v
CODE: with ThreadPoolExecutor() as ex:
        results = [ex.submit(spawner.spawn_gemini, f"Check {f}") for f in files]
```

### Example 3: Feature Implementation
```
User: "Implement OAuth, write tests, update docs"
        |
        v
Is strategic? NO (tactical implementation)
        |
        v
One tool call? NO (3 dependent steps)
        |
        v
Needs error handling? YES
        |
        v
Can cascade? YES (but dependent chain, not failure cascade)
        |
        v
Independent parallel? NO (each step builds on prior)
        |
        v
DECISION: Use Task() (not spawn)
        |
        v
REASONING: Steps are dependent. Shared context helps. Cache hits save 5x.
        |
        v
COMMAND: Task("Implement OAuth flow, write tests, update docs")
```

### Example 4: Architecture Design
```
User: "Design the microservices architecture"
        |
        v
Is strategic? YES
        |
        v
Execute directly? WAIT
        |
        v
Actually: Is this USER asking for design (strategic)?
        → YES, but involves reasoning I should do
        → NO, user is asking me to compute it
        |
        v
User asking for COMPUTATION (analysis/design/reasoning)?
        |
        v
DECISION: Delegate to spawn_claude (strategic capability)
        |
        v
REASONING: Complex reasoning beyond simple planning
        |
        v
SETTINGS: permission_mode="plan" (generate plan, no execution)
        |
        v
COMMAND: spawner.spawn_claude("Design microservices arch...",
                              permission_mode="plan")
```

---

## COMMON MISTAKES & FIXES

```
❌ MISTAKE: Cascading direct git calls
    git add file
    git commit (fails - hook runs tests - tests fail)
    Fix code
    git commit (succeeds)
    git push (fails - conflict)
    Pull/merge
    git push (succeeds)
    Total: 7+ tool calls, lots of context consumed

✓ FIX: Delegate
    Task("Commit and push changes with error handling")
    Total: 1 tool call + result, built-in retries

─────────────────────────────────────────────────

❌ MISTAKE: Choosing wrong spawner
    "Fix bug" → spawn_claude (strategic, wrong)
    Should: spawn_codex (code, correct)

✓ FIX: Use decision tree
    Code generation? YES → spawn_codex

─────────────────────────────────────────────────

❌ MISTAKE: Using Task() for independent parallel work
    Task("Analyze file 1")
    Task("Analyze file 2")  ← Sequential! (wasteful)
    Task("Analyze file 3")

✓ FIX: Use spawn with parallel execution
    with ThreadPoolExecutor() as ex:
        [ex.submit(spawn_gemini, f"Analyze {f}") for f in files]
    ← Parallel! (faster + cheaper)

─────────────────────────────────────────────────

❌ MISTAKE: Executing directly when should delegate
    git add .
    git commit (hook fails, context consumed)

✓ FIX: Delegate git operations
    Task("Commit changes with proper error handling")
```

---

## DECISION VALIDATION CHECKLIST

Before executing your decision:

```
☐ Did I ask all 5 questions in sequence?
☐ Is my decision on the decision tree above?
☐ Can I justify my spawner choice from the table?
☐ Have I included cost/speed/capability considerations?
☐ Does my example match a real scenario?
☐ Have I identified error cases and retries?
☐ If delegating: Is error handling included?
☐ If spawning: Is parallelization possible?
☐ Can I explain this decision to someone else?
```

If you answer NO to any: RECONSIDER your decision.

---

## METRICS AFTER IMPLEMENTATION

Track these to validate the routing system:

```
Routing Accuracy: (Successful delegations / Total delegations)
    Target: ≥95%
    Measure: Delegations completed vs re-routed

Decision Speed: Time to make routing decision
    Baseline: ~30 seconds (old system)
    Target: ~5 seconds (new system)
    Measure: Self-reported in sessions

Spawner Accuracy: (First-choice success / Total spawns)
    Target: ≥90%
    Measure by spawner: spawn_codex, spawn_gemini, spawn_copilot, spawn_claude

Task Completion: (First-attempt success / Total tasks)
    Target: ≥85%
    Measure: Tasks completed without retry

Cost Savings: Token usage reduction
    Target: 20-30% reduction vs full prompt
    Measure: Average tokens per session (monthly)
```

---

**Use this as a printed reference while learning the system. After 10-20 decisions, routing should become automatic.**
