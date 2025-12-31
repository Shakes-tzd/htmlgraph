# Archived Skills

This directory contains skills that have been deprecated or consolidated into other skills.

## parallel-orchestrator (Archived 2025-12-31)

**Status:** Consolidated into `htmlgraph-tracker` (now "HtmlGraph Workflow Skill")

**Reason:** Orchestration and delegation are core parts of the HtmlGraph workflow, not separate concerns. Having two skills created confusion about when to use which.

**What changed:**
- Orchestrator directives merged into htmlgraph-tracker as "Core Responsibility #1"
- Parallel workflow (6-phase process) added as subsection
- Single unified skill now handles: tracking, orchestration, delegation, and parallel coordination
- Auto-activation still works (session start)
- All trigger keywords preserved

**Migration:**
- No action needed - htmlgraph-tracker now includes all parallel-orchestrator functionality
- Skills that referenced parallel-orchestrator should reference htmlgraph-tracker instead
- All SDK methods (`plan_parallel_work`, `aggregate_parallel_results`, etc.) unchanged

**See:** `.claude/skills/htmlgraph-tracker/SKILL.md` for the unified skill
