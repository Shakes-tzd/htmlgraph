// Package main — the parent HtmlGraph doorway server.
//
// After the per-project process isolation re-architecture (plan-237fb251),
// the parent server holds ZERO SQLite handles. It serves only three things:
//
//   - the landing SPA (embedded dashboard files)
//   - a tiny JSON API (/api/mode, /api/projects) that reads the registry
//     file only — no DB access
//   - the /p/<id>/* reverse proxy to per-project child processes
//     (registered in serve_parent.go)
//
// All per-project data — features, sessions, events, plans, transcripts
// — is served exclusively by the child process for that project and
// reaches the browser via the child's reverse proxy. There is no
// dispatchByProject, no projectCache, no aggregate stats, no cross-
// project SSE fan-out. This guarantees strict cross-project isolation:
// it is architecturally impossible for a request to project A to observe
// or mutate project B's database, because the parent never touches
// either.
package main

import (
	"net/http"

	"github.com/shakestzd/htmlgraph/internal/registry"
)

// projectSummary is the JSON shape returned by /api/projects entries.
// Fields are sourced exclusively from the registry — no DB access,
// no counts. Counts and per-project data live on the child and are
// fetched via /p/<id>/api/stats.
type projectSummary struct {
	ID           string `json:"id"`
	Name         string `json:"name"`
	Dir          string `json:"dir"`
	LastSeen     string `json:"lastSeen"`
	GitRemoteURL string `json:"gitRemoteURL,omitempty"`
}

// buildGlobalMux constructs the http.ServeMux for the parent doorway
// server. No DB access. Registry JSON only. Per-project data comes from
// the child via /p/<id>/api/*.
func buildGlobalMux() *http.ServeMux {
	mux := http.NewServeMux()

	// /api/mode — dashboard calls this on startup to detect global mode.
	mux.Handle("/api/mode", corsMiddleware(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, map[string]any{"mode": "global"})
	})))

	// /api/projects — registry list only. No DB access. Counts and
	// per-project data come from the child via /p/<id>/api/*.
	mux.Handle("/api/projects", corsMiddleware(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, listRegisteredProjects())
	})))

	// Serve the embedded dashboard SPA (index.html, css/, js/,
	// components/). The frontend calls /api/mode on startup to detect
	// global mode and render the projects landing.
	mux.Handle("/", corsMiddleware(http.FileServer(http.FS(dashboardSub()))))

	return mux
}

// listRegisteredProjects re-reads the registry on each call and returns
// one summary per entry. No filesystem access beyond reading the registry
// JSON. No DB opens. No counts. If the registry file is missing or
// unreadable, returns an empty slice (not an error) so the dashboard
// landing renders an empty state rather than 500.
func listRegisteredProjects() []projectSummary {
	reg, err := registry.Load(registry.DefaultPath())
	if err != nil {
		return []projectSummary{}
	}
	entries := reg.List()
	out := make([]projectSummary, 0, len(entries))
	for _, e := range entries {
		out = append(out, projectSummary{
			ID:           e.ID,
			Name:         e.Name,
			Dir:          e.ProjectDir,
			LastSeen:     e.LastSeen,
			GitRemoteURL: e.GitRemoteURL,
		})
	}
	return out
}
