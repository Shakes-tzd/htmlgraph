---
name: htmlgraph:plan-review
description: Multi-AI plan review — dispatches gemini-operator (design critic) and codex-operator (feasibility checker) in parallel to critique a CRISPI plan before human finalization. Use when a plan has been generated and needs AI review before execution.
user_invocable: true
---

# HtmlGraph Plan Review

Use this skill after generating a plan (`/htmlgraph:plan`) and before executing it (`/htmlgraph:execute`). Dispatches two AI reviewers in parallel to enrich the plan with structured critique, then opens it for human finalization.

**Trigger keywords:** review plan, critique plan, AI review plan, plan review, check plan, validate plan before execution, review before building

---

## What This Skill Does

1. Dispatches **gemini-operator** (design critic) and **codex-operator** (feasibility checker) in parallel
2. Each reviewer reads the plan HTML + referenced source files
3. Each injects findings directly into the plan via CLI commands (`plan set-section`, `plan add-question`, `plan set-slice`)
4. Opens the enriched plan for human review
5. Waits for human finalization before handing off to `/htmlgraph:execute`

The human sees AI-generated critique alongside the original plan sections and makes the final call.

---

## Step 0: Identify the Plan

```bash
htmlgraph plan list
```

The user will specify a plan ID, or you can identify it from context (most recently generated plan).

Verify the plan exists and is in `draft` status:

```bash
htmlgraph plan read-feedback <plan-id>
```

If status is already `finalized`, skip review — the plan was already approved.

---

## Step 1: Dispatch Reviewers (Parallel)

Spawn both reviewers in a **single message** so they run concurrently:

```
Agent(
    description="Design critique: <plan-id>",
    subagent_type="htmlgraph:gemini-operator",
    prompt="[gemini design critic prompt — see below]"
)

Agent(
    description="Feasibility check: <plan-id>",
    subagent_type="htmlgraph:codex-operator",
    prompt="[codex feasibility checker prompt — see below]"
)
```

---

## Gemini Prompt: Design Critic

The gemini-operator has large context (2M tokens) and is free. Use it for broad codebase analysis.

```
## Task: Design Review of CRISPI Plan
**Plan:** .htmlgraph/plans/{plan-id}.html

## Step 1: Read the Plan
Read the plan HTML file. Extract:
- The title and description
- Each vertical slice (Section C): name, files, test strategy, dependencies
- The open questions (Section A)
- The structure outline (Section B)

## Step 2: Read Referenced Source Files
For each file mentioned in the slices, read the current source code.
If a file doesn't exist yet, note that it's a new file.

## Step 3: Evaluate Design
For each slice, assess:
1. **Scope**: Is the slice properly scoped? Too big? Too small? Does it mix concerns?
2. **Files**: Are the right files listed? Are any files missing that would need changes?
3. **Dependencies**: Are inter-slice dependencies correct? Are any missing?
4. **Test Strategy**: Is the test strategy specific and actionable, or just placeholder text?
5. **Risks**: What could go wrong? Are there edge cases the plan doesn't address?

## Step 4: Write Findings

For the design section (current state + desired state analysis):
htmlgraph plan set-section {plan-id} PLAN_DESIGN_CONTENT '<div class="sub-section"><h4>Current State</h4><p>[your analysis of the current codebase state]</p></div><div class="sub-section"><h4>Desired End State</h4><p>[what the plan achieves]</p></div><div class="sub-section"><h4>Relevant Patterns</h4><ul style="list-style:disc;padding-left:18px"><li>[pattern 1]</li><li>[pattern 2]</li></ul></div>'

For each slice that needs updates:
htmlgraph plan set-slice {plan-id} {slice-number} \
  --files "file1.go, file2.go" \
  --deps "Slice #N (reason)" \
  --tests "Unit: specific test. Integration: specific test."

For unresolved design questions:
htmlgraph plan add-question {plan-id} "Question text?" \
  --options "option1:explanation of tradeoff,option2:explanation of tradeoff" \
  --description "Why this matters for the implementation"

## Rules
- Be specific. "Add tests" is not useful. "Unit test that ErrNotFound includes ID prefix hint" is useful.
- Only flag real issues. Don't manufacture concerns.
- If a slice looks correct, don't comment on it.
- Focus on things the plan author might have missed, not style preferences.
```

---

## Codex Prompt: Feasibility Checker

The codex-operator runs in a sandbox and can execute code. Use it to validate that the plan's proposed code will actually work.

```
## Task: Feasibility Check of CRISPI Plan
**Plan:** .htmlgraph/plans/{plan-id}.html

## Step 1: Read the Plan
Read the plan HTML file. Extract:
- The structure outline (Section B): function signatures, type definitions
- Each vertical slice: files to create/edit

## Step 2: Validate Code Structure

For each function signature in the outline:
1. Check if the package exists: ls the directory
2. Check if referenced types exist: grep for type definitions
3. Check for naming conflicts: grep for functions with the same name
4. Verify import paths are correct

## Step 3: Scaffold and Compile

Create a minimal scaffold of the proposed changes (just signatures, no implementation):
- Create stub functions that match the outline
- Run: go build ./...
- If build fails, the outline has errors — report them

## Step 4: Validate File References

For each file mentioned in the slices:
- Does it exist? If not, is it marked as "new"?
- Are the line ranges / function names accurate?
- Are there other files that would need changes (missed by the plan)?

Grep for callers of any functions being modified — find files the plan missed.

## Step 5: Write Findings

For the outline section:
htmlgraph plan set-section {plan-id} PLAN_OUTLINE_CONTENT '<h4>Validated Signatures</h4><pre><code class="language-go">[corrected signatures if any]</code></pre><p>[notes on what compiled vs what didn't]</p>'

For slices with incorrect file references:
htmlgraph plan set-slice {plan-id} {slice-number} \
  --files "corrected-file1.go, corrected-file2.go, missed-file3.go"

For feasibility concerns:
htmlgraph plan add-question {plan-id} "Feasibility concern text?" \
  --options "proceed:explanation,redesign:explanation" \
  --description "What the validation found"

## Rules
- Only report actual compilation errors or missing references, not style issues.
- Clean up any scaffolded code after validation — don't leave stubs.
- If everything compiles and references check out, report "No feasibility issues found."
```

---

## Step 2: Open the Enriched Plan

After both reviewers complete:

```bash
htmlgraph plan open <plan-id>
```

The plan now contains:
- **Section A (Design)**: Populated with current state, desired state, patterns (from gemini)
- **Section B (Outline)**: Validated signatures and compilation results (from codex)
- **Section C (Slices)**: Updated files, deps, and test strategies (from both)
- **Section D (Questions)**: New design questions surfaced by the reviewers

---

## Step 3: Wait for Human Finalization

```bash
htmlgraph plan wait <plan-id> --timeout 1h
```

This blocks until the human:
1. Reviews the AI-enriched plan in their browser
2. Approves or revises each section
3. Answers all open questions
4. Clicks "Finalize Plan"

---

## Step 4: Read Feedback and Hand Off

After finalization:

```bash
htmlgraph plan read-feedback <plan-id>
```

This returns JSON with all approvals, answers, and comments. Pass the finalized plan to `/htmlgraph:execute` for implementation.

---

## When to Skip Review

Skip this skill when:
- The plan has fewer than 3 slices (too small to benefit from multi-AI review)
- The plan is a pure cleanup task with no design decisions
- Time pressure requires immediate execution

---

## Related Skills

- **[/htmlgraph:plan](/htmlgraph:plan)** — Generate the plan (runs BEFORE this skill)
- **[/htmlgraph:execute](/htmlgraph:execute)** — Execute the finalized plan (runs AFTER this skill)
- **[/htmlgraph:parallel-status](/htmlgraph:parallel-status)** — Monitor execution progress
