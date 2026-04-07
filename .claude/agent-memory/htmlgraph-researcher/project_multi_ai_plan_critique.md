---
name: Multi-AI Plan Critique Architecture
description: Current state, gaps, and design options for multi-AI critique of CRISPI plans using Gemini and Codex CLIs
type: project
---

# Multi-AI Plan Critique Architecture

**Track:** trk-bbf223f6 (CRISPI Plan Mode)
**Active spike:** spk-30568afc (Research agentic planning patterns and multi-AI plan critique)
**Completed feature:** feat-9b7cf6ae (Plan review skill — multi-AI critique via gemini and codex operators, status: done)

## What Is Already Implemented

The `plugin/skills/plan/SKILL.md` (lines 267-291) defines a "Plan Review (Optional Multi-AI Critique)" section with two parallel calls:

**1. Design critique via Gemini CLI**
```bash
gemini -p 'Read .htmlgraph/plans/{plan-id}.html. For each slice assess scope, file coverage,
      dependencies, test strategy, and risks.' --yolo --output-format json
# → writes to: htmlgraph plan set-section {plan-id} PLAN_DESIGN_CONTENT '<p>...</p>'
```

**2. Feasibility check via Codex CLI**
```bash
codex exec 'Read .htmlgraph/plans/{plan-id}.html. For each function signature: check package
      exists, types exist, no naming conflicts. Scaffold stubs and run go build ./...' --full-auto --json
# → reports compilation errors via: htmlgraph plan set-section {plan-id} PLAN_OUTLINE_CONTENT
# → adds questions via: htmlgraph plan add-question {plan-id} '...' --options '...'
```

After both complete: `htmlgraph plan open`, `htmlgraph plan wait`, `htmlgraph plan read-feedback`.

**Skip condition:** Plans with fewer than 3 slices or pure cleanup tasks skip multi-AI critique.

## Role Assignment (Orchestrator Directives)

From `orchestrator-directives-skill/SKILL.md`:
- **Gemini** → design/scope/risk critique (FREE, 2M tokens/min, wide context)
- **Codex** → implementation feasibility (sandboxed, can run `go build`, 70% cheaper than Claude)
- **Copilot** → git/GitHub operations (not used for plan critique)
- **Claude Opus** → architecture decisions requiring deep reasoning (not used here)

## Gaps and Open Questions (as of 2026-04-03)

1. **No Copilot role in plan critique.** Copilot could contribute GitHub-aware critique: PR history, existing issues, open PRs that conflict. Not currently wired in.

2. **Output parsing is undefined.** The skill says "write findings via `htmlgraph plan set-section`" but doesn't specify how to parse Gemini JSON output or Codex NDJSON into HTML content. The plan skill leaves this to the orchestrator's judgment.

3. **Gemini noise on startup.** Gemini CLI emits extension/MCP error lines to stderr (hooks.json format, clasp import). These must be filtered before treating output as meaningful.

4. **Codex stale symlink.** Non-fatal error at start: `failed to stat skills entry htmlgraph-tracker (symlink)`. Doesn't affect execution but pollutes output.

5. **No Copilot critique role defined.** The orchestrator directives only assign Copilot to git ops. For plan critique, there's no established pattern for using Copilot's code-review capabilities on plan HTML.

6. **Multi-AI parallelism mechanics.** The skill specifies parallel Bash calls but doesn't specify how to synthesize conflicting signals (Gemini says design is sound, Codex finds compilation errors — which surfaces first? how are they merged into the plan HTML?).

## Potential Architecture Patterns

**Pattern A: Two-role parallel critique (current)**
- Gemini: scope/risk/design
- Codex: compilation/feasibility
- Results merged by orchestrator into plan sections

**Pattern B: Three-role critique**
- Gemini: scope/risk/design  
- Codex: compilation/feasibility
- Copilot: GitHub context (related PRs, issues, history)
- Adds GitHub signal but increases complexity and cost

**Pattern C: Sequential refinement**
- Gemini first (design), Codex second (feasibility after design is validated)
- Slower but Codex gets cleaner context
- Better for catching design-level errors before feasibility checking

**Pattern D: Adversarial critique**
- Gemini plays "devil's advocate" (find flaws)
- Codex plays "implementer's advocate" (find what works)
- Surfaces tension between design ideals and implementation constraints

**Why:** The spike (spk-30568afc) is actively researching which pattern fits CRISPI's spatial-first, ADHD-accessibility design goals.

**How to apply:** When asked to implement plan critique, use Pattern A as baseline (already documented in SKILL.md). Escalate to Pattern B or D only if the track's open questions (trk-bbf223f6) are resolved in favor of multi-role critique.
