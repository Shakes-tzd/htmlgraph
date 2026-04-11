# Plan: Agent-Agnostic Lazy Session Registration

## Context

HtmlGraph's attribution chain (work item → session → commit) breaks when the session-start hook fails to fire. This happens when Claude Code sessions restart without triggering hooks, and will always happen for non-Claude agents (Codex, Gemini) that have no hook integration.

The fix: every CLI command self-heals by detecting the agent, resolving a session ID, and registering it on-the-fly. This also positions HtmlGraph as a multi-agent observability tool — not just a Claude Code plugin.

**Features:** feat-17a993f0 (AgentResolver), feat-2043d0b4 (EnsureSession guard), feat-76121073 (parent concept)

---

## Implementation

### Step 1: New package `internal/agent/`

**File: `internal/agent/detect.go`**

Two exported functions:

```go
type Info struct {
    ID    string // "claude-code", "codex", "gemini", "human"
    Model string // from env if available
}

func Detect() Info
// Priority: HTMLGRAPH_AGENT_ID env → CLAUDECODE=1 → fallback "human"
// Future: add CODEX_*, GEMINI_* detection as those CLIs are integrated

func ResolveSessionID() string
// Priority: HTMLGRAPH_SESSION_ID env → CLAUDE_SESSION_ID env (normalized)
//         → .active-session file → generate "cli-<PID>-<timestamp>"
```

Move `NormaliseSessionID()` (UUID extraction regex) from `internal/hooks/runner.go` into `internal/agent/detect.go` to avoid import cycles. Have `runner.go` call `agent.NormaliseSessionID()`.

**File: `internal/agent/detect_test.go`** — table-driven tests for each detection path.

### Step 2: EnsureSession guard

**File: `internal/agent/ensure.go`**

```go
func EnsureSession(database *sql.DB, projectDir string) (string, error)
```

Flow:
1. `ResolveSessionID()` → get session ID
2. `Detect()` → get agent info
3. If ID starts with `"cli-"` → skip DB, return (human/transient)
4. `SELECT COUNT(*) FROM sessions WHERE session_id = ?` — hot path (<1ms, indexed PK)
5. If exists → `os.Setenv("HTMLGRAPH_SESSION_ID", id)`, return
6. If missing → `INSERT OR IGNORE` minimal session row + write `.active-session` + `os.Setenv`

Minimal session row: `session_id`, `agent_assigned`, `created_at`, `status=active`, `model`, `project_dir`, `git_remote_url`. No git commit hash (saves 10ms).

Export `WriteActiveSession()` and `ReadActiveSession()` from `internal/hooks/session_start.go` so `ensure.go` can call them.

**File: `internal/agent/ensure_test.go`** — tests: session exists (hot path), session missing (cold path), transient ID (no DB).

### Step 3: Wire into CLI via PersistentPreRunE

**File: `cmd/htmlgraph/main.go`**

Add to `rootCmd` before `rootCmd.Execute()`:

```go
rootCmd.PersistentPreRunE = func(cmd *cobra.Command, args []string) error {
    // Skip commands that don't need session context
    switch cmd.Name() {
    case "version", "help", "init", "build", "install-hooks", "setup", "setup-cli":
        return nil
    }
    // Skip hook subtree — hooks manage their own sessions
    for p := cmd; p != nil; p = p.Parent() {
        if p.Name() == "hook" { return nil }
    }

    hgDir, err := findHtmlgraphDir()
    if err != nil { return nil } // not an htmlgraph project

    database, err := db.Open(filepath.Join(hgDir, "htmlgraph.db"))
    if err != nil { return nil } // degrade gracefully
    defer database.Close()

    agent.EnsureSession(database, filepath.Dir(hgDir))
    return nil
}
```

**Why PersistentPreRunE:** No global middleware exists today. Adding `EnsureSession` to 30+ commands individually is fragile. Single insertion point covers all subcommands.

### Step 4: Refactor existing agent detection

**File: `internal/hooks/pretooluse.go`** — Replace `agentIDFromEnv()` with `agent.Detect().ID`

**File: `internal/hooks/runner.go`** — Replace inline `NormaliseSessionID()` with `agent.NormaliseSessionID()`

---

## Files Changed

| File | Type | Description |
|------|------|-------------|
| `internal/agent/detect.go` | New | Agent detection + session ID resolution |
| `internal/agent/detect_test.go` | New | Detection tests |
| `internal/agent/ensure.go` | New | EnsureSession guard |
| `internal/agent/ensure_test.go` | New | Guard tests |
| `cmd/htmlgraph/main.go` | Modify | Add PersistentPreRunE (~15 lines) |
| `internal/hooks/session_start.go` | Modify | Export WriteActiveSession/ReadActiveSession |
| `internal/hooks/pretooluse.go` | Modify | Delegate to agent.Detect().ID |
| `internal/hooks/runner.go` | Modify | Delegate to agent.NormaliseSessionID() |

---

## Performance

| Operation | Budget | Actual |
|-----------|--------|--------|
| Env var checks | <0.1ms | ~0.01ms |
| SQLite open (WAL) | <2ms | ~1ms |
| SELECT COUNT(*) on PK | <1ms | ~0.2ms |
| SQLite close | <0.5ms | ~0.1ms |
| **Total hot path** | **<5ms** | **~1.3ms** |

Cold path (first command in session) adds ~1ms for INSERT.

---

## Key Design Decisions

1. **PersistentPreRunE, not per-command** — single insertion point, all commands covered
2. **Skip hook subtree** — hooks manage their own session lifecycle
3. **Transient "cli-*" IDs skip DB** — human CLI usage doesn't pollute sessions table
4. **INSERT OR IGNORE** — idempotent with existing hook-created sessions
5. **os.Setenv after resolve** — downstream EnvSessionID calls work automatically
6. **New `internal/agent/` package** — avoids import cycles, clean separation from hooks
7. **Minimal session row** — lazy registration creates just enough; SessionStart hook upgrades it

---

## Verification

```bash
# 1. Build and install
go build ./... && go vet ./... && go test ./...
htmlgraph build

# 2. Simulate failed session-start hook
unset HTMLGRAPH_SESSION_ID

# 3. Run a CLI command that needs session context
htmlgraph feature start feat-17a993f0

# 4. Verify session was lazily created
htmlgraph session list | head -5

# 5. Verify attribution chain works
htmlgraph feature complete feat-17a993f0
htmlgraph session show <session-id>
# Should show feat-17a993f0 in "Features Worked On"

# 6. Test human mode (no agent env)
unset CLAUDECODE HTMLGRAPH_SESSION_ID CLAUDE_SESSION_ID
htmlgraph status
# Should work without error

# 7. Performance — hot path <5ms
time htmlgraph find feat-17a993f0
```
