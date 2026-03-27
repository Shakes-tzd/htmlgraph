# YOLO Autonomous Development Mode

You are running in YOLO mode — autonomous development with enforced quality guardrails.
Permission prompts are disabled. You must self-enforce quality at every step.

## Mandatory Workflow for Each Feature

### Step 0 — Work Item (BEFORE anything else)
1. Create: `htmlgraph feature create "title"`
2. Start: Record the active feature for attribution
3. Isolate: Use a git worktree for each feature — never edit main directly

### Step 1 — Research
- Search for existing libraries, tested patterns, prior art
- Check project dependencies before adding new ones
- Log findings in a spike if substantial

### Step 2 — Spec
Write acceptance criteria before coding:
- What problem does this solve?
- Measurable acceptance criteria
- API surface / interface sketch

### Step 3 — Tests First (TDD)
Write failing tests before implementation:
- Unit tests for core logic
- Integration test for happy path
- Tests must compile and fail before you write implementation

### Step 4 — Implement
- Functions: <50 lines | Modules: <500 lines
- DRY: search for existing utilities before creating new ones
- KISS: simplest solution that passes tests
- YAGNI: only what is needed now
- Separation of concerns: one purpose per module

### Step 5 — Quality Gate (MANDATORY before any commit)
Python: `uv run ruff check --fix && uv run ruff format && uv run mypy src/ && uv run pytest`
Go: `cd packages/go && go build ./... && go vet ./... && go test ./...`
Do NOT commit with failures.

### Step 6 — UI Validation (if UI changes)
Use Chrome DevTools MCP or Playwright MCP to screenshot and validate:
- Layout correctness
- Readability
- Responsive behavior

### Step 7 — Diff Review
Run `git diff --stat` before committing. Every change must belong to this feature.
Use `git add -p` — never `git add -A`.

### Step 8 — Commit and Complete
Commit with descriptive message. Mark feature done in HtmlGraph.

## Budget Limits

### Advisory (slow down and review)
- 10 files changed per feature
- 300 new lines per feature

### Hard limit (STOP and split into sub-features)
- 20 files changed per feature
- 600 new lines per feature

If approaching the advisory limit, review whether the scope is correct.
If hitting the hard limit, STOP — create sub-features and split the work.

## Code Health Rules
- No function >50 lines
- No module >500 lines
- No duplication — extract shared helpers
- No TODO comments in committed code
- No debug print statements in commits
- Prefer O(n) algorithms; document when higher complexity is unavoidable

## What YOLO Mode Does NOT Mean
- Does NOT mean skip research
- Does NOT mean commit broken code
- Does NOT mean ignore test failures
- Does NOT mean bypass code review
- It means: no permission prompts, but FULL quality enforcement
