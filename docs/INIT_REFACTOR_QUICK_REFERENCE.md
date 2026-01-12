# Init Command Refactoring - Quick Reference

**Status:** ❌ **BROKEN** - `cli_legacy.py` deleted but still imported
**Priority:** 🔴 **CRITICAL** - Command will crash at runtime
**Effort:** 9-14 hours (1-2 days)

---

## Problem

`InitCommand.execute()` in `core.py:397-412` imports non-existent `cli_legacy.py`:

```python
def execute(self) -> CommandResult:
    """Initialize the .htmlgraph directory."""
    from htmlgraph import cli_legacy  # ❌ ModuleNotFoundError

    args = argparse.Namespace(...)
    cli_legacy.cmd_init(args)  # ❌ Function doesn't exist

    return CommandResult(text="Initialized .htmlgraph directory")
```

---

## Quick Fix (DO THIS NOW)

Replace with temporary implementation:

```python
def execute(self) -> CommandResult:
    """Initialize the .htmlgraph directory."""
    from pathlib import Path
    from htmlgraph.config import HtmlGraphConfig
    from htmlgraph.db.schema import HtmlGraphDB

    # Temporary implementation until full refactor
    base_dir = Path(self.dir)
    htmlgraph_dir = base_dir / ".htmlgraph"

    # Create directories
    config = HtmlGraphConfig(graph_dir=htmlgraph_dir)
    config.ensure_directories()

    # Initialize database
    db_path = htmlgraph_dir / "htmlgraph.db"
    db = HtmlGraphDB(str(db_path))

    return CommandResult(
        success=True,
        text=f"Initialized .htmlgraph at {self.dir}"
    )
```

---

## Full Solution

### 1. Create Operations Module

**File:** `src/python/htmlgraph/cli/operations/initialization.py`

**Functions to implement:**

```python
# Main entry point
def initialize_htmlgraph(config: InitConfig, verbose: bool = False) -> CommandResult

# Core operations
def create_directory_structure(base_dir: Path, include_events_keep: bool = True) -> dict[str, Path]
def initialize_database(db_path: Path, skip_analytics_cache: bool = False) -> tuple[bool, str]
def create_default_config_files(htmlgraph_dir: Path, install_hooks: bool = False) -> dict[str, Path]

# Git integration
def update_gitignore(project_dir: Path, patterns: list[str] | None = None) -> tuple[bool, str]
def install_git_hooks(project_dir: Path, force: bool = False, dry_run: bool = False) -> dict[str, tuple[bool, str]]

# Validation
def validate_init_prerequisites(base_dir: Path, install_hooks: bool = False) -> list[str]
def verify_initialization(htmlgraph_dir: Path, check_database: bool = True) -> tuple[bool, list[str]]

# Interactive
def run_interactive_wizard(base_dir: Path) -> InitConfig
```

### 2. Update InitCommand

**File:** `src/python/htmlgraph/cli/core.py`

```python
def execute(self) -> CommandResult:
    """Initialize the .htmlgraph directory."""
    from htmlgraph.cli.operations import initialize_htmlgraph, run_interactive_wizard

    # Run interactive wizard if requested
    if self.interactive:
        config = run_interactive_wizard(Path(self.dir))
    else:
        config = InitConfig(
            dir=self.dir,
            install_hooks=self.install_hooks,
            interactive=self.interactive,
            no_index=self.no_index,
            no_update_gitignore=self.no_update_gitignore,
            no_events_keep=self.no_events_keep,
        )

    return initialize_htmlgraph(config, verbose=True)
```

### 3. Write Tests

**File:** `tests/cli/operations/test_initialization.py`

Key tests:
- `test_create_directory_structure_creates_all_dirs`
- `test_initialize_database_creates_schema`
- `test_update_gitignore_appends_patterns`
- `test_install_git_hooks_creates_symlinks`
- `test_validate_init_prerequisites_detects_conflicts`
- `test_verify_initialization_detects_incomplete_setup`
- `test_initialize_htmlgraph_full_workflow`
- `test_initialize_htmlgraph_with_hooks`

---

## What Init Should Do

1. **Create directories:**
   - `.htmlgraph/features/`
   - `.htmlgraph/sessions/`
   - `.htmlgraph/events/`
   - `.htmlgraph/spikes/`
   - `.htmlgraph/tracks/`
   - `.htmlgraph/bugs/`
   - `.htmlgraph/chores/`
   - `.htmlgraph/archives/`
   - `.htmlgraph/logs/errors/`

2. **Initialize databases:**
   - `htmlgraph.db` (unified event database)
   - `index.sqlite` (analytics cache, optional)

3. **Create config files:**
   - `agents.json` (agent registry)
   - `hooks-config.json` (if `--install-hooks`)

4. **Update .gitignore** (unless `--no-update-gitignore`):
   - `.htmlgraph/index.sqlite*`
   - `.htmlgraph/sessions/*.jsonl`
   - `.htmlgraph/events/*.jsonl`
   - `.htmlgraph/parent-activity.json`
   - `.htmlgraph/logs/errors/`

5. **Install git hooks** (if `--install-hooks`):
   - `post-commit`
   - `post-checkout`
   - `post-merge`
   - `pre-push`

---

## Dependencies

### Internal Modules (Already Exist)
- `htmlgraph.config.HtmlGraphConfig` - Directory management
- `htmlgraph.db.schema.HtmlGraphDB` - Database creation
- `htmlgraph.hooks.installer.HookInstaller` - Hook installation
- `htmlgraph.cli.models.InitConfig` - Configuration model ✅

### Standard Library Only
- `pathlib` - Directory operations
- `sqlite3` - Database creation
- `json` - Config files
- `shutil` - File copying
- `subprocess` - Git commands

---

## Testing Checklist

**Unit Tests:**
- [ ] Directory structure creation
- [ ] Database initialization
- [ ] Config file creation
- [ ] Gitignore updates
- [ ] Hook installation
- [ ] Prerequisites validation
- [ ] Initialization verification
- [ ] Interactive wizard

**Integration Tests:**
- [ ] Full initialization workflow
- [ ] Initialization with hooks
- [ ] Re-initialization (idempotent)
- [ ] Error handling

**Manual Testing:**
- [ ] `htmlgraph init`
- [ ] `htmlgraph init --install-hooks`
- [ ] `htmlgraph init --interactive`
- [ ] `htmlgraph init --no-index`
- [ ] `htmlgraph init --no-update-gitignore`

---

## Success Criteria

✅ No crashes (fixes ModuleNotFoundError)
✅ Creates all required directories
✅ Initializes databases correctly
✅ Updates .gitignore appropriately
✅ Installs hooks (when requested)
✅ Clear user feedback
✅ Graceful error handling
✅ >90% test coverage
✅ Zero type errors
✅ Zero lint warnings

---

## Timeline

| Phase | Effort | Description |
|-------|--------|-------------|
| **Quick Fix** | 15 min | Stop crashes immediately |
| **Implementation** | 4-6 hrs | Create operations module |
| **Testing** | 3-4 hrs | Unit + integration tests |
| **Integration** | 1-2 hrs | Update InitCommand |
| **Documentation** | 1-2 hrs | Docstrings + guides |
| **TOTAL** | 9-14 hrs | 1-2 days focused work |

---

## Reference Documents

- **Full Plan:** `INIT_COMMAND_REFACTORING_PLAN.md` (detailed analysis)
- **This Guide:** `INIT_REFACTOR_QUICK_REFERENCE.md` (quick reference)
- **Model:** `src/python/htmlgraph/cli/models.py:120-138` (InitConfig)
- **Current Code:** `src/python/htmlgraph/cli/core.py:397-412` (InitCommand)

---

## Commands for Development

```bash
# Apply quick fix
vim src/python/htmlgraph/cli/core.py

# Create operations module
mkdir -p src/python/htmlgraph/cli/operations
touch src/python/htmlgraph/cli/operations/__init__.py
touch src/python/htmlgraph/cli/operations/initialization.py

# Create tests
mkdir -p tests/cli/operations
touch tests/cli/operations/__init__.py
touch tests/cli/operations/test_initialization.py

# Run tests
uv run pytest tests/cli/operations/ -v

# Type check
uv run mypy src/python/htmlgraph/cli/operations/

# Lint
uv run ruff check --fix src/python/htmlgraph/cli/operations/

# Test manually
uv run htmlgraph init --help
uv run htmlgraph init
uv run htmlgraph init --install-hooks
```
