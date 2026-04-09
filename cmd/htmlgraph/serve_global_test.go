package main

import (
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/shakestzd/htmlgraph/internal/registry"
)

// globalTestProject creates a tmpdir project with a .htmlgraph dir and a
// SQLite DB that has the minimum schema used by the dashboard handlers
// (features, sessions, messages, agent_events). Populates a few rows.
func globalTestProject(t *testing.T, features, bugs, spikes int) string {
	t.Helper()
	tmp := t.TempDir()
	hgDir := filepath.Join(tmp, ".htmlgraph")
	if err := os.MkdirAll(hgDir, 0o755); err != nil {
		t.Fatal(err)
	}
	dbPath := filepath.Join(hgDir, "htmlgraph.db")
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatal(err)
	}
	schema := []string{
		`CREATE TABLE features (
			id TEXT PRIMARY KEY,
			type TEXT NOT NULL,
			title TEXT NOT NULL DEFAULT '',
			status TEXT NOT NULL DEFAULT 'todo',
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE TABLE sessions (
			session_id TEXT PRIMARY KEY,
			status TEXT DEFAULT 'completed',
			is_subagent INTEGER DEFAULT 0,
			metadata TEXT
		)`,
		`CREATE TABLE messages (
			id INTEGER PRIMARY KEY,
			session_id TEXT,
			model TEXT,
			input_tokens INTEGER DEFAULT 0,
			output_tokens INTEGER DEFAULT 0,
			cache_read_tokens INTEGER DEFAULT 0,
			timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE TABLE agent_events (
			id INTEGER PRIMARY KEY,
			session_id TEXT,
			event_type TEXT,
			timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
		)`,
	}
	for _, s := range schema {
		if _, err := db.Exec(s); err != nil {
			t.Fatalf("schema: %v", err)
		}
	}
	insert := func(kind string, n int) {
		for i := 0; i < n; i++ {
			_, err := db.Exec("INSERT INTO features (id, type, title) VALUES (?, ?, ?)",
				kind+string(rune('a'+i)), kind, kind+" title")
			if err != nil {
				t.Fatal(err)
			}
		}
	}
	insert("feature", features)
	insert("bug", bugs)
	insert("spike", spikes)
	db.Close()
	return tmp
}

// setupGlobalRegistry points registry.DefaultPath at a tmpdir file and
// registers the given project dirs. Returns the registry file path. Note
// that registry.DefaultPath is resolved via os.UserHomeDir so we need to
// override HOME — t.Setenv handles cleanup automatically.
func setupGlobalRegistry(t *testing.T, projectDirs ...string) string {
	t.Helper()
	home := t.TempDir()
	t.Setenv("HOME", home)
	regPath := registry.DefaultPath()
	if err := os.MkdirAll(filepath.Dir(regPath), 0o755); err != nil {
		t.Fatal(err)
	}
	reg, _ := registry.Load(regPath)
	for _, dir := range projectDirs {
		reg.Upsert(dir, filepath.Base(dir), "")
	}
	if err := reg.Save(); err != nil {
		t.Fatal(err)
	}
	return regPath
}

// expectedID returns the 8-char SHA256 prefix of dir, matching the ID
// format the registry uses for stable project identity.
func expectedID(dir string) string {
	h := sha256.Sum256([]byte(dir))
	return hex.EncodeToString(h[:])[:8]
}

// TestModeEndpoint_Single verifies runServer's /api/mode returns
// {"mode":"single"}. We don't start the full runServer (it needs a DB);
// instead we hit a freshly-constructed handler directly.
func TestModeEndpoint_Single(t *testing.T) {
	// The single-mode route is registered inline in runServer, so we
	// replicate the exact handler here and assert its response shape.
	// This keeps the test independent of runServer's DB lifecycle.
	h := corsMiddleware(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, map[string]any{"mode": "single"})
	}))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest("GET", "/api/mode", nil))
	var body map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["mode"] != "single" {
		t.Errorf("mode: got %v, want single", body["mode"])
	}
}

func TestModeEndpoint_Global(t *testing.T) {
	p1 := globalTestProject(t, 2, 1, 0)
	p2 := globalTestProject(t, 1, 0, 1)
	setupGlobalRegistry(t, p1, p2)

	srv := httptest.NewServer(buildGlobalMux())
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/api/mode")
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var body map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatal(err)
	}
	if body["mode"] != "global" {
		t.Errorf("mode: got %v, want global", body["mode"])
	}
	projects, ok := body["projects"].([]any)
	if !ok {
		t.Fatalf("projects missing or wrong type: %+v", body)
	}
	if len(projects) != 2 {
		t.Errorf("expected 2 projects, got %d", len(projects))
	}
}

func TestProjectsEndpoint_StableIDs(t *testing.T) {
	p1 := globalTestProject(t, 0, 0, 0)
	setupGlobalRegistry(t, p1)

	srv := httptest.NewServer(buildGlobalMux())
	defer srv.Close()

	fetch := func() []projectSummary {
		resp, err := http.Get(srv.URL + "/api/projects")
		if err != nil {
			t.Fatal(err)
		}
		defer resp.Body.Close()
		var out []projectSummary
		if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
			t.Fatal(err)
		}
		return out
	}

	first := fetch()
	second := fetch()
	if len(first) != 1 || len(second) != 1 {
		t.Fatalf("expected 1 entry each call, got %d, %d", len(first), len(second))
	}
	if first[0].ID != second[0].ID {
		t.Errorf("ID not stable: first=%s second=%s", first[0].ID, second[0].ID)
	}
	if first[0].ID != expectedID(p1) {
		t.Errorf("ID mismatch: got %s, want %s", first[0].ID, expectedID(p1))
	}
}

func TestFeaturesEndpoint_ProjectQueryParam(t *testing.T) {
	p1 := globalTestProject(t, 2, 0, 0)
	p2 := globalTestProject(t, 0, 3, 0)
	setupGlobalRegistry(t, p1, p2)

	srv := httptest.NewServer(buildGlobalMux())
	defer srv.Close()

	// Missing ?project returns 400.
	resp, _ := http.Get(srv.URL + "/api/features")
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("missing ?project: got %d, want 400", resp.StatusCode)
	}
	resp.Body.Close()

	// Unknown project returns 404.
	resp, _ = http.Get(srv.URL + "/api/features?project=deadbeef")
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("unknown project: got %d, want 404", resp.StatusCode)
	}
	resp.Body.Close()

	// Valid project returns 200.
	resp, _ = http.Get(srv.URL + "/api/features?project=" + expectedID(p1))
	if resp.StatusCode != http.StatusOK {
		t.Errorf("valid project: got %d, want 200", resp.StatusCode)
	}
	resp.Body.Close()
}

func TestGlobalServer_RegistryRefresh(t *testing.T) {
	p1 := globalTestProject(t, 0, 0, 0)
	regPath := setupGlobalRegistry(t, p1)

	srv := httptest.NewServer(buildGlobalMux())
	defer srv.Close()

	// First fetch — one project.
	resp, _ := http.Get(srv.URL + "/api/projects")
	var first []projectSummary
	json.NewDecoder(resp.Body).Decode(&first)
	resp.Body.Close()
	if len(first) != 1 {
		t.Fatalf("first fetch: expected 1, got %d", len(first))
	}

	// Register a second project without restarting the server.
	p2 := globalTestProject(t, 0, 0, 0)
	reg, _ := registry.Load(regPath)
	reg.Upsert(p2, filepath.Base(p2), "")
	if err := reg.Save(); err != nil {
		t.Fatal(err)
	}

	// Second fetch — should now include both projects.
	resp, _ = http.Get(srv.URL + "/api/projects")
	var second []projectSummary
	json.NewDecoder(resp.Body).Decode(&second)
	resp.Body.Close()
	if len(second) != 2 {
		t.Errorf("after refresh: expected 2, got %d", len(second))
	}
}

// TestGlobalServer_NoMigrations ensures hitting the global server routes
// never mutates a project DB's schema.
func TestGlobalServer_NoMigrations(t *testing.T) {
	p1 := globalTestProject(t, 1, 1, 1)
	setupGlobalRegistry(t, p1)

	dbPath := filepath.Join(p1, ".htmlgraph", "htmlgraph.db")
	before := readTableNames(t, dbPath)

	srv := httptest.NewServer(buildGlobalMux())
	defer srv.Close()

	http.Get(srv.URL + "/api/projects")
	http.Get(srv.URL + "/api/mode")
	http.Get(srv.URL + "/api/features?project=" + expectedID(p1))
	http.Get(srv.URL + "/api/stats?project=" + expectedID(p1))
	http.Get(srv.URL + "/api/projects/all/stats")

	after := readTableNames(t, dbPath)
	if len(before) != len(after) {
		t.Errorf("schema changed: before=%v after=%v", before, after)
	}
}
