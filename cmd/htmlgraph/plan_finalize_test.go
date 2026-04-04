package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/shakestzd/htmlgraph/internal/workitem"
)

// buildTestPlanHTML creates a minimal plan HTML with configurable slices
// and approval state. Each slice entry has a slice number, a name (feature ID
// or slug), a title, and dependency numbers (comma-separated).
type testSlice struct {
	num   int
	name  string // feature ID stored in data-slice-name
	title string
	deps  string // comma-separated node numbers
}

func buildTestPlanHTML(planID, featureID, title, status string, slices []testSlice) string {
	var sb strings.Builder
	sb.WriteString(`<!DOCTYPE html><html><body>`)
	sb.WriteString(`<article id="` + planID + `" data-feature-id="` + featureID + `" data-status="` + status + `">`)
	sb.WriteString(`<header><h1>Plan: ` + title + `</h1></header>`)

	// Graph nodes
	for _, s := range slices {
		sb.WriteString(`<div data-node="`)
		sb.WriteString(testItoa(s.num))
		sb.WriteString(`" data-name="`)
		sb.WriteString(s.title)
		sb.WriteString(`" data-deps="`)
		sb.WriteString(s.deps)
		sb.WriteString(`"></div>`)
	}

	// Slice cards
	for _, s := range slices {
		sb.WriteString(`<div class="slice-card" data-slice="`)
		sb.WriteString(testItoa(s.num))
		sb.WriteString(`" data-slice-name="`)
		sb.WriteString(s.name)
		sb.WriteString(`">`)
		sb.WriteString(`<div class="slice-header"><span class="slice-name">`)
		sb.WriteString(s.title)
		sb.WriteString(`</span></div>`)
		sb.WriteString(`<div class="approval-row"><label><input type="checkbox" data-section="slice-`)
		sb.WriteString(testItoa(s.num))
		sb.WriteString(`" data-action="approve"> Approve</label>`)
		sb.WriteString(`<textarea data-section="slice-`)
		sb.WriteString(testItoa(s.num))
		sb.WriteString(`" data-comment-for="slice-`)
		sb.WriteString(testItoa(s.num))
		sb.WriteString(`" placeholder="Comments..."></textarea></div>`)
		sb.WriteString(`</div>`)
	}

	sb.WriteString(`</article></body></html>`)
	return sb.String()
}

// testItoa is a tiny helper to avoid importing strconv in tests.
func testItoa(n int) string {
	if n == 0 {
		return "0"
	}
	var digits []byte
	for n > 0 {
		digits = append([]byte{byte('0' + n%10)}, digits...)
		n /= 10
	}
	return string(digits)
}

// setupFinalizeTestProject creates a temporary .htmlgraph directory with a plan
// HTML file and returns the project and htmlgraph dir path.
func setupFinalizeTestProject(t *testing.T, planID string, planHTML string) (*workitem.Project, string) {
	t.Helper()
	dir := t.TempDir()

	// Create subdirectories
	for _, sub := range []string{"plans", "tracks", "features"} {
		if err := os.MkdirAll(filepath.Join(dir, sub), 0o755); err != nil {
			t.Fatalf("mkdir %s: %v", sub, err)
		}
	}

	// Write plan HTML
	planPath := filepath.Join(dir, "plans", planID+".html")
	if err := os.WriteFile(planPath, []byte(planHTML), 0o644); err != nil {
		t.Fatalf("write plan html: %v", err)
	}

	p, err := workitem.Open(dir, "test-agent")
	if err != nil {
		t.Fatalf("open project: %v", err)
	}
	t.Cleanup(func() { p.Close() })

	return p, dir
}

func TestPlanFinalize_CreatesTrackAndFeatures(t *testing.T) {
	planID := "plan-test-finalize"
	slices := []testSlice{
		{num: 1, name: "slice-auth", title: "Authentication", deps: ""},
		{num: 2, name: "slice-api", title: "API Layer", deps: "1"},
		{num: 3, name: "slice-ui", title: "UI Components", deps: "1,2"},
	}

	html := buildTestPlanHTML(planID, "feat-source", "Test Finalize", "draft", slices)
	p, htmlgraphDir := setupFinalizeTestProject(t, planID, html)

	// Mark all slices as approved in the HTML (checked attribute).
	planPath := filepath.Join(htmlgraphDir, "plans", planID+".html")
	data, err := os.ReadFile(planPath)
	if err != nil {
		t.Fatalf("read plan: %v", err)
	}
	// Add checked to all approval checkboxes.
	content := strings.ReplaceAll(string(data), `data-action="approve"`, `data-action="approve" checked`)
	if err := os.WriteFile(planPath, []byte(content), 0o644); err != nil {
		t.Fatalf("write plan: %v", err)
	}

	result, err := executePlanFinalize(p, htmlgraphDir, planID)
	if err != nil {
		t.Fatalf("executePlanFinalize: %v", err)
	}

	// Verify track was created.
	if result.TrackID == "" {
		t.Fatal("expected a track ID, got empty string")
	}
	if !strings.HasPrefix(result.TrackID, "trk-") {
		t.Errorf("track ID should start with trk-, got %q", result.TrackID)
	}

	// Verify features were created (one per approved slice).
	if len(result.FeatureIDs) != 3 {
		t.Errorf("expected 3 features, got %d", len(result.FeatureIDs))
	}

	// Verify track node exists on disk.
	trackPath := filepath.Join(htmlgraphDir, "tracks", result.TrackID+".html")
	if _, err := os.Stat(trackPath); err != nil {
		t.Errorf("track file not found: %v", err)
	}

	// Verify feature files exist on disk.
	for _, fid := range result.FeatureIDs {
		featPath := filepath.Join(htmlgraphDir, "features", fid+".html")
		if _, err := os.Stat(featPath); err != nil {
			t.Errorf("feature file %s not found: %v", fid, err)
		}
	}

	// Verify plan status was updated to "finalized".
	updatedData, err := os.ReadFile(planPath)
	if err != nil {
		t.Fatalf("read updated plan: %v", err)
	}
	if !strings.Contains(string(updatedData), `data-status="finalized"`) {
		t.Error("plan status should be updated to finalized")
	}
}

func TestPlanFinalize_OnlyApprovedSlices(t *testing.T) {
	planID := "plan-partial-approve"
	slices := []testSlice{
		{num: 1, name: "slice-yes", title: "Approved Slice", deps: ""},
		{num: 2, name: "slice-no", title: "Not Approved Slice", deps: "1"},
	}

	html := buildTestPlanHTML(planID, "feat-partial", "Partial Approve", "draft", slices)
	p, htmlgraphDir := setupFinalizeTestProject(t, planID, html)

	// Only approve slice-1, not slice-2.
	planPath := filepath.Join(htmlgraphDir, "plans", planID+".html")
	data, err := os.ReadFile(planPath)
	if err != nil {
		t.Fatalf("read plan: %v", err)
	}
	content := string(data)
	// Add checked only to slice-1's checkbox.
	content = strings.Replace(content,
		`data-section="slice-1" data-action="approve"`,
		`data-section="slice-1" data-action="approve" checked`, 1)
	if err := os.WriteFile(planPath, []byte(content), 0o644); err != nil {
		t.Fatalf("write plan: %v", err)
	}

	result, err := executePlanFinalize(p, htmlgraphDir, planID)
	if err != nil {
		t.Fatalf("executePlanFinalize: %v", err)
	}

	// Only 1 feature should be created (the approved one).
	if len(result.FeatureIDs) != 1 {
		t.Errorf("expected 1 feature for 1 approved slice, got %d", len(result.FeatureIDs))
	}
}

func TestPlanFinalize_Idempotent(t *testing.T) {
	planID := "plan-idempotent"
	slices := []testSlice{
		{num: 1, name: "slice-one", title: "First Slice", deps: ""},
	}

	html := buildTestPlanHTML(planID, "feat-idem", "Idempotent Test", "draft", slices)
	p, htmlgraphDir := setupFinalizeTestProject(t, planID, html)

	// Approve all slices.
	planPath := filepath.Join(htmlgraphDir, "plans", planID+".html")
	data, err := os.ReadFile(planPath)
	if err != nil {
		t.Fatalf("read plan: %v", err)
	}
	content := strings.ReplaceAll(string(data), `data-action="approve"`, `data-action="approve" checked`)
	if err := os.WriteFile(planPath, []byte(content), 0o644); err != nil {
		t.Fatalf("write plan: %v", err)
	}

	// First finalize.
	result1, err := executePlanFinalize(p, htmlgraphDir, planID)
	if err != nil {
		t.Fatalf("first finalize: %v", err)
	}

	// Second finalize should return same result without creating duplicates.
	result2, err := executePlanFinalize(p, htmlgraphDir, planID)
	if err != nil {
		t.Fatalf("second finalize: %v", err)
	}

	if result2.TrackID != result1.TrackID {
		t.Errorf("idempotent finalize should return same track: got %q vs %q", result2.TrackID, result1.TrackID)
	}
	if len(result2.FeatureIDs) != len(result1.FeatureIDs) {
		t.Errorf("idempotent finalize should return same features: got %d vs %d", len(result2.FeatureIDs), len(result1.FeatureIDs))
	}
	if !result2.AlreadyFinalized {
		t.Error("second finalize should report AlreadyFinalized=true")
	}
}

func TestPlanFinalize_AlreadyFinalizedSkips(t *testing.T) {
	planID := "plan-already-done"
	slices := []testSlice{
		{num: 1, name: "slice-a", title: "A", deps: ""},
	}

	// Create plan with status already "finalized".
	html := buildTestPlanHTML(planID, "feat-done", "Already Done", "finalized", slices)
	p, htmlgraphDir := setupFinalizeTestProject(t, planID, html)

	result, err := executePlanFinalize(p, htmlgraphDir, planID)
	if err != nil {
		t.Fatalf("executePlanFinalize: %v", err)
	}

	if !result.AlreadyFinalized {
		t.Error("should report already finalized")
	}
}
