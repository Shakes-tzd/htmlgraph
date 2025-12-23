# HtmlGraph Scripts

Utility scripts for development, deployment, and maintenance.

---

## 🚀 Deployment

### deploy-all.sh

**Flexible deployment automation with multiple modes.**

**Usage:**
```bash
# Full release
./scripts/deploy-all.sh 0.7.1

# Documentation only (commit + push)
./scripts/deploy-all.sh --docs-only

# Build only (no publish)
./scripts/deploy-all.sh --build-only

# Skip PyPI publish
./scripts/deploy-all.sh 0.7.1 --skip-pypi

# Preview what would happen
./scripts/deploy-all.sh --dry-run

# Show help
./scripts/deploy-all.sh --help
```

**Available Flags:**
- `--docs-only` - Only commit and push to git (skip build/publish)
- `--build-only` - Only build package (skip git/publish/install)
- `--skip-pypi` - Skip PyPI publishing step
- `--skip-plugins` - Skip plugin update steps
- `--dry-run` - Show what would happen without executing
- `--help` - Show help message

**What it does (7 steps):**
1. **Git Push** - Pushes commits and tags to origin/main
2. **Build Package** - Creates wheel and source distributions
3. **Publish to PyPI** - Uploads package to PyPI
4. **Local Install** - Installs latest version locally
5. **Update Claude Plugin** - Runs `claude plugin update htmlgraph`
6. **Update Gemini Extension** - Updates version in gemini-extension.json
7. **Update Codex Skill** - Checks for Codex and updates if present

**Prerequisites:**
- Set `PyPI_API_TOKEN` in `.env` file
- Version numbers already updated in:
  - `pyproject.toml`
  - `src/python/htmlgraph/__init__.py`
  - `packages/claude-plugin/.claude-plugin/plugin.json`
  - `packages/gemini-extension/gemini-extension.json`
- Git tag created: `git tag v0.7.1`

**Environment Variables:**
```bash
# .env file
PyPI_API_TOKEN=pypi-YOUR_TOKEN_HERE
```

**Example Workflow:**
```bash
# 1. Update versions
vim pyproject.toml  # Set version = "0.7.1"
vim src/python/htmlgraph/__init__.py  # Set __version__ = "0.7.1"
vim packages/claude-plugin/.claude-plugin/plugin.json  # Set version
vim packages/gemini-extension/gemini-extension.json  # Set version

# 2. Commit and tag
git add -A
git commit -m "chore: bump version to 0.7.1"
git tag v0.7.1
git push origin main --tags

# 3. Deploy
./scripts/deploy-all.sh 0.7.1
```

**Output:**
- Colored output with success/error indicators
- Progress reporting for each step
- Verification of installation and versions
- Links to verify deployment on PyPI

---

## 📝 Documentation Sync

### sync_memory_files.py

**Synchronize AI agent memory files across platforms.**

Ensures platform-specific files (CLAUDE.md, GEMINI.md, CODEX.md) properly reference the central AGENTS.md documentation.

**Usage:**

**Check synchronization status:**
```bash
python scripts/sync_memory_files.py --check
```

**Generate platform-specific file:**
```bash
# Generate GEMINI.md
python scripts/sync_memory_files.py --generate gemini

# Generate CLAUDE.md
python scripts/sync_memory_files.py --generate claude

# Generate CODEX.md
python scripts/sync_memory_files.py --generate codex

# Overwrite existing file
python scripts/sync_memory_files.py --generate gemini --force
```

**Synchronize all files:**
```bash
python scripts/sync_memory_files.py
```

**What it checks:**
- ✅ AGENTS.md exists (required)
- ✅ Platform files reference AGENTS.md
- ✅ All documentation is consistent

**Platform Files:**
- `AGENTS.md` - Central AI agent documentation (required)
- `CLAUDE.md` - Claude Code / Anthropic Claude specific
- `GEMINI.md` - Google Gemini specific
- `CODEX.md` - GitHub Codex specific

**File Structure:**
```
project/
├── AGENTS.md         # Central documentation (SDK, API, CLI, deployment)
├── CLAUDE.md         # → References AGENTS.md + Claude-specific notes
├── GEMINI.md         # → References AGENTS.md + Gemini-specific notes
├── CODEX.md          # → References AGENTS.md + Codex-specific notes
└── scripts/
    └── sync_memory_files.py
```

**Why This Matters:**

1. **Single Source of Truth**: Core documentation lives in AGENTS.md
2. **Platform Flexibility**: Platform-specific notes in separate files
3. **Easy Maintenance**: Update once in AGENTS.md, not 3+ times
4. **Consistency**: All platforms reference same SDK/API docs

**Example Output:**
```
🔍 Checking memory files...

Status:
  ✅ GEMINI.md references AGENTS.md
  ✅ CLAUDE.md references AGENTS.md
  ✅ AGENTS.md exists

✅ All files are properly synchronized!
```

---

## 🛠️ Best Practices

### When to Use Each Script

| Task | Script | Frequency |
|------|--------|-----------|
| Release new version | `deploy-all.sh` | Every release |
| Add new platform support | `sync_memory_files.py --generate` | Once per platform |
| Check doc consistency | `sync_memory_files.py --check` | After editing docs |
| Verify release | Manual (PyPI, plugins) | Every release |

### Pre-Release Checklist

Before running `deploy-all.sh`:

- [ ] All tests pass: `uv run pytest`
- [ ] Documentation updated
- [ ] Version bumped in all files
- [ ] Changes committed to git
- [ ] Git tag created: `git tag vX.Y.Z`
- [ ] PyPI token in `.env`
- [ ] Memory files synced: `python scripts/sync_memory_files.py --check`

### Post-Release Checklist

After running `deploy-all.sh`:

- [ ] Verify PyPI: https://pypi.org/project/htmlgraph/
- [ ] Test local install: `python -c "import htmlgraph; print(htmlgraph.__version__)"`
- [ ] Test Claude plugin: `claude plugin list | grep htmlgraph`
- [ ] Check GitHub release: https://github.com/Shakes-tzd/htmlgraph/releases
- [ ] Update release notes

---

## 🔧 Troubleshooting

### deploy-all.sh

**PyPI token not found:**
```bash
# Create .env file
echo "PyPI_API_TOKEN=pypi-YOUR_TOKEN_HERE" > .env
source .env
```

**Git push failed:**
```bash
# Check remote
git remote -v

# Force push (only if safe!)
git push origin main --force --tags
```

**Build failed:**
```bash
# Clean old builds
rm -rf dist/

# Rebuild
uv build
```

**Plugin update failed:**
```bash
# Manual update
claude plugin update htmlgraph

# Check plugin status
claude plugin list
```

### sync_memory_files.py

**AGENTS.md not found:**
```bash
# Create AGENTS.md first
# See docs/SDK_FOR_AI_AGENTS.md for template
```

**Platform file doesn't reference AGENTS.md:**
```bash
# Regenerate file
python scripts/sync_memory_files.py --generate <platform> --force

# Or manually add reference to top of file:
# → See [AGENTS.md](./AGENTS.md) for complete documentation
```

---

## 📚 Related Documentation

- **AGENTS.md** - AI agent SDK documentation
- **CLAUDE.md** - Project vision and architecture
- **GEMINI.md** - Gemini-specific integration
- **docs/SDK_FOR_AI_AGENTS.md** - Complete SDK guide
- **RELEASE_NOTES_0.7.0.md** - Latest release notes

---

## 🤝 Contributing

To add a new script:

1. Create script in `scripts/`
2. Make it executable: `chmod +x scripts/your_script.sh`
3. Add documentation to this README
4. Test on clean install
5. Submit PR

---

**Last Updated:** December 22, 2025
**HtmlGraph Version:** 0.7.0
