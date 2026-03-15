# Code Hygiene - Mandatory Quality Standards

**CRITICAL: Always fix ALL errors with every commit, regardless of when they were introduced.**

## Philosophy

Maintaining clean, error-free code is non-negotiable. Every commit should reduce technical debt, not accumulate it.

## Rules

1. **Fix All Errors Before Committing**
   - Run all linters (ruff, mypy) before every commit
   - Fix ALL errors, even pre-existing ones from previous sessions
   - Never commit with unresolved type errors, lint warnings, or test failures

2. **No "I'll Fix It Later" Mentality**
   - Errors compound over time
   - Pre-existing errors are YOUR responsibility when you touch related code
   - Clean as you go - leave code better than you found it

3. **Deployment Blockers**
   - The `deploy-all.sh` script blocks on:
     - Mypy type errors
     - Ruff lint errors
     - Test failures
   - This is intentional - maintain quality gates

4. **Why This Matters**
   - **Prevents Error Accumulation** - Small issues don't become large problems
   - **Better Code Hygiene** - Clean code is easier to maintain
   - **Faster Development** - No time wasted debugging old errors
   - **Professional Standards** - Production-grade code quality

## Workflow

```bash
# Before every commit:
1. uv run ruff check --fix
2. uv run ruff format
3. uv run mypy src/
4. uv run pytest

# Only commit when ALL checks pass
git commit -m "..."
```

**Remember: Fixing errors immediately is faster than letting them accumulate.**

## Module Size & Complexity Standards

### Line Count Limits

| Metric | Target | Warning | Fail (new code) |
|--------|--------|---------|------------------|
| Module | 200-500 lines | >300 lines | >500 lines |
| Function | 10-20 lines | >30 lines | >50 lines |
| Class | 100-200 lines | >200 lines | >300 lines |

### Principles

1. **Single Responsibility**: Each module should have one clear purpose describable in one sentence
2. **No Duplication**: Check `src/python/htmlgraph/utils/` for shared utilities before writing new ones
3. **Prefer Existing Dependencies**: Check `pyproject.toml` and stdlib before custom implementations
4. **Import Direction**: Dependencies flow one way (services -> models, never models -> services)

### Enforcement

- **Script**: `python scripts/check-module-size.py` checks all modules against limits
- **Pre-commit**: Runs automatically on changed files
- **Grandfathered modules**: 15 existing modules >1000 lines are tracked but not blocking (see `scripts/check-module-size.py` for list)
- **Ratchet rule**: Any modification to a grandfathered module must not increase its line count
- **Refactoring track**: See `docs/tracks/MODULE_REFACTORING_TRACK.md` for planned splits

### Quick Commands

```bash
# Check all modules
python scripts/check-module-size.py

# Check only changed files
python scripts/check-module-size.py --changed-only

# Summary table of oversized modules
python scripts/check-module-size.py --summary

# JSON output for CI
python scripts/check-module-size.py --json

# Strict mode (warnings = failures)
python scripts/check-module-size.py --fail-on-warning
```
