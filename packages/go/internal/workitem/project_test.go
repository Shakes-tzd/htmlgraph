package workitem_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/shakestzd/htmlgraph/internal/htmlparse"
	"github.com/shakestzd/htmlgraph/internal/models"
	"github.com/shakestzd/htmlgraph/internal/workitem"
)

// newTestProject creates a Project rooted in a temp dir with the required subdirectories.
func newTestProject(t *testing.T) *workitem.Project {
	t.Helper()
	dir := t.TempDir()
	for _, sub := range []string{"features", "bugs", "spikes", "tracks", "sessions", "plans", "specs"} {
		if err := os.MkdirAll(filepath.Join(dir, sub), 0o755); err != nil {
			t.Fatalf("mkdir %s: %v", sub, err)
		}
	}
	p, err := workitem.Open(dir, "test-agent")
	if err != nil {
		t.Fatalf("workitem.Open: %v", err)
	}
	t.Cleanup(func() { _ = p.Close() })
	return p
}

// ---------------------------------------------------------------------------
// Feature CRUD
// ---------------------------------------------------------------------------

func TestFeatureCreate(t *testing.T) {
	p := newTestProject(t)

	feat, err := p.Features.Create("User Authentication",
		workitem.FeatWithPriority("high"),
		workitem.FeatWithTrack("trk-test"),
		workitem.FeatWithSteps("Design schema", "Implement API", "Add tests"),
		workitem.FeatWithContent("<p>Auth feature for multi-tenant</p>"),
	)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	// Verify returned node
	if !strings.HasPrefix(feat.ID, "feat-") {
		t.Errorf("ID prefix: got %q, want feat-*", feat.ID)
	}
	if feat.Title != "User Authentication" {
		t.Errorf("Title: got %q", feat.Title)
	}
	if feat.Type != "feature" {
		t.Errorf("Type: got %q", feat.Type)
	}
	if string(feat.Priority) != "high" {
		t.Errorf("Priority: got %q", feat.Priority)
	}
	if string(feat.Status) != "todo" {
		t.Errorf("Status: got %q", feat.Status)
	}
	if feat.TrackID != "trk-test" {
		t.Errorf("TrackID: got %q", feat.TrackID)
	}
	if feat.AgentAssigned != "test-agent" {
		t.Errorf("AgentAssigned: got %q", feat.AgentAssigned)
	}
	if len(feat.Steps) != 3 {
		t.Fatalf("Steps count: got %d, want 3", len(feat.Steps))
	}
	if feat.Steps[0].Description != "Design schema" {
		t.Errorf("Step[0]: got %q", feat.Steps[0].Description)
	}

	// Verify HTML file exists on disk
	htmlPath := filepath.Join(p.FeaturesDir(), feat.ID+".html")
	if _, err := os.Stat(htmlPath); err != nil {
		t.Fatalf("HTML file not found: %v", err)
	}
}

func TestFeatureCreateEmptyTitle(t *testing.T) {
	p := newTestProject(t)
	_, err := p.Features.Create("")
	if err == nil {
		t.Error("expected error for empty title")
	}
}

func TestFeatureGet(t *testing.T) {
	p := newTestProject(t)

	created, err := p.Features.Create("Get Test Feature",
		workitem.FeatWithPriority("low"),
	)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	got, err := p.Features.Get(created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}

	if got.ID != created.ID {
		t.Errorf("ID mismatch: got %q, want %q", got.ID, created.ID)
	}
	if got.Title != "Get Test Feature" {
		t.Errorf("Title: got %q", got.Title)
	}
	if string(got.Priority) != "low" {
		t.Errorf("Priority: got %q", got.Priority)
	}
}

func TestFeatureList(t *testing.T) {
	p := newTestProject(t)

	_, _ = p.Features.Create("Feat A", workitem.FeatWithPriority("high"))
	_, _ = p.Features.Create("Feat B", workitem.FeatWithPriority("low"))
	_, _ = p.Features.Create("Feat C", workitem.FeatWithPriority("high"))

	// List all
	all, err := p.Features.List()
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("List all: got %d, want 3", len(all))
	}

	// Filter by priority
	high, err := p.Features.List(workitem.WithPriority("high"))
	if err != nil {
		t.Fatalf("List high: %v", err)
	}
	if len(high) != 2 {
		t.Errorf("List high: got %d, want 2", len(high))
	}
}

func TestFeatureListWithStatus(t *testing.T) {
	p := newTestProject(t)

	f1, _ := p.Features.Create("Active Feature")
	_, _ = p.Features.Create("Todo Feature")
	_, _ = p.Features.Start(f1.ID)

	inProg, err := p.Features.List(workitem.WithStatus("in-progress"))
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(inProg) != 1 {
		t.Errorf("in-progress count: got %d, want 1", len(inProg))
	}
}

func TestFeatureDelete(t *testing.T) {
	p := newTestProject(t)

	feat, _ := p.Features.Create("Delete Me")
	if err := p.Features.Delete(feat.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}

	_, err := p.Features.Get(feat.ID)
	if err == nil {
		t.Error("expected error after delete")
	}
}

// ---------------------------------------------------------------------------
// Feature Lifecycle
// ---------------------------------------------------------------------------

func TestFeatureStartComplete(t *testing.T) {
	p := newTestProject(t)

	feat, _ := p.Features.Create("Lifecycle Test",
		workitem.FeatWithSteps("Step 1", "Step 2"),
	)

	// Start
	started, err := p.Features.Start(feat.ID)
	if err != nil {
		t.Fatalf("Start: %v", err)
	}
	if string(started.Status) != "in-progress" {
		t.Errorf("after Start: status = %q", started.Status)
	}

	// Complete
	done, err := p.Features.Complete(feat.ID)
	if err != nil {
		t.Fatalf("Complete: %v", err)
	}
	if string(done.Status) != "done" {
		t.Errorf("after Complete: status = %q", done.Status)
	}
	for i, step := range done.Steps {
		if !step.Completed {
			t.Errorf("step %d not completed after Complete", i)
		}
	}
}

// ---------------------------------------------------------------------------
// Round-trip: create -> write HTML -> parse -> verify
// ---------------------------------------------------------------------------

func TestFeatureRoundTrip(t *testing.T) {
	p := newTestProject(t)

	feat, err := p.Features.Create("Round Trip Feature",
		workitem.FeatWithPriority("critical"),
		workitem.FeatWithTrack("trk-roundtrip"),
		workitem.FeatWithSteps("Alpha", "Beta"),
		workitem.FeatWithContent("<p>Round trip test</p>"),
	)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	// Re-parse the HTML file with the internal parser
	path := filepath.Join(p.FeaturesDir(), feat.ID+".html")
	parsed, err := htmlparse.ParseFile(path)
	if err != nil {
		t.Fatalf("ParseFile: %v", err)
	}

	assertEqual(t, "ID", parsed.ID, feat.ID)
	assertEqual(t, "Title", parsed.Title, "Round Trip Feature")
	assertEqual(t, "Type", parsed.Type, "feature")
	assertEqual(t, "Status", string(parsed.Status), "todo")
	assertEqual(t, "Priority", string(parsed.Priority), "critical")
	assertEqual(t, "TrackID", parsed.TrackID, "trk-roundtrip")
	assertEqual(t, "AgentAssigned", parsed.AgentAssigned, "test-agent")

	if len(parsed.Steps) != 2 {
		t.Fatalf("Steps count: got %d, want 2", len(parsed.Steps))
	}
	assertEqual(t, "Step[0]", parsed.Steps[0].Description, "Alpha")
	assertEqual(t, "Step[1]", parsed.Steps[1].Description, "Beta")

	if !strings.Contains(parsed.Content, "Round trip test") {
		t.Errorf("Content missing expected text: %q", parsed.Content)
	}
}

func TestFeatureWithEdgesRoundTrip(t *testing.T) {
	p := newTestProject(t)

	feat, err := p.Features.Create("Edge Feature",
		workitem.FeatWithEdge("blocks", "feat-other"),
	)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	path := filepath.Join(p.FeaturesDir(), feat.ID+".html")
	parsed, err := htmlparse.ParseFile(path)
	if err != nil {
		t.Fatalf("ParseFile: %v", err)
	}

	edges, ok := parsed.Edges["blocks"]
	if !ok || len(edges) == 0 {
		t.Fatal("no 'blocks' edges found after round-trip")
	}
	assertEqual(t, "edge target", edges[0].TargetID, "feat-other")
}

// ---------------------------------------------------------------------------
// Bug CRUD
// ---------------------------------------------------------------------------

func TestBugCreate(t *testing.T) {
	p := newTestProject(t)

	bug, err := p.Bugs.Create("Login broken on Safari",
		workitem.BugWithPriority("critical"),
		workitem.BugWithReproSteps("Open Safari", "Click login"),
	)
	if err != nil {
		t.Fatalf("Create bug: %v", err)
	}
	if !strings.HasPrefix(bug.ID, "bug-") {
		t.Errorf("ID prefix: got %q, want bug-*", bug.ID)
	}
	if bug.Type != "bug" {
		t.Errorf("Type: got %q", bug.Type)
	}

	// Verify file
	path := filepath.Join(p.BugsDir(), bug.ID+".html")
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("HTML file not found: %v", err)
	}
}

func TestBugRoundTrip(t *testing.T) {
	p := newTestProject(t)
	bug, _ := p.Bugs.Create("Bug RT", workitem.BugWithPriority("high"))

	parsed, err := htmlparse.ParseFile(filepath.Join(p.BugsDir(), bug.ID+".html"))
	if err != nil {
		t.Fatalf("ParseFile: %v", err)
	}
	assertEqual(t, "Type", parsed.Type, "bug")
	assertEqual(t, "Priority", string(parsed.Priority), "high")
}

// ---------------------------------------------------------------------------
// Spike CRUD
// ---------------------------------------------------------------------------

func TestSpikeCreate(t *testing.T) {
	p := newTestProject(t)

	spike, err := p.Spikes.Create("Investigate caching",
		workitem.SpikeWithType("technical"),
		workitem.SpikeWithFindings("Redis is the best option"),
	)
	if err != nil {
		t.Fatalf("Create spike: %v", err)
	}
	if !strings.HasPrefix(spike.ID, "spk-") {
		t.Errorf("ID prefix: got %q, want spk-*", spike.ID)
	}
	if spike.Type != "spike" {
		t.Errorf("Type: got %q", spike.Type)
	}
}

func TestSpikeSetFindings(t *testing.T) {
	p := newTestProject(t)

	spike, _ := p.Spikes.Create("Investigation")
	updated, err := p.Spikes.SetFindings(spike.ID, "Found the root cause")
	if err != nil {
		t.Fatalf("SetFindings: %v", err)
	}
	if !strings.Contains(updated.Content, "Found the root cause") {
		t.Errorf("Content: got %q", updated.Content)
	}

	// Verify round-trip
	parsed, _ := htmlparse.ParseFile(filepath.Join(p.SpikesDir(), spike.ID+".html"))
	if !strings.Contains(parsed.Content, "Found the root cause") {
		t.Errorf("Parsed content missing findings: %q", parsed.Content)
	}
}

func TestSpikeGetLatest(t *testing.T) {
	p := newTestProject(t)

	_, _ = p.Spikes.Create("Spike A")
	_, _ = p.Spikes.Create("Spike B")
	_, _ = p.Spikes.Create("Spike C")

	latest, err := p.Spikes.GetLatest("", 2)
	if err != nil {
		t.Fatalf("GetLatest: %v", err)
	}
	if len(latest) != 2 {
		t.Errorf("GetLatest count: got %d, want 2", len(latest))
	}
}

// ---------------------------------------------------------------------------
// Track CRUD
// ---------------------------------------------------------------------------

func TestTrackCreate(t *testing.T) {
	p := newTestProject(t)

	track, err := p.Tracks.Create("Go SDK Port",
		workitem.TrackWithPriority("high"),
		workitem.TrackWithSpec("Port Python SDK to Go"),
		workitem.TrackWithPlanPhases("Phase 1: Models", "Phase 2: Collections"),
	)
	if err != nil {
		t.Fatalf("Create track: %v", err)
	}
	if !strings.HasPrefix(track.ID, "trk-") {
		t.Errorf("ID prefix: got %q, want trk-*", track.ID)
	}
	if len(track.Steps) != 2 {
		t.Errorf("Steps: got %d, want 2", len(track.Steps))
	}
}

func TestTrackRoundTrip(t *testing.T) {
	p := newTestProject(t)
	track, _ := p.Tracks.Create("Track RT", workitem.TrackWithPriority("medium"))

	parsed, err := htmlparse.ParseFile(filepath.Join(p.TracksDir(), track.ID+".html"))
	if err != nil {
		t.Fatalf("ParseFile: %v", err)
	}
	assertEqual(t, "Type", parsed.Type, "track")
	assertEqual(t, "Title", parsed.Title, "Track RT")
}

// ---------------------------------------------------------------------------
// Collection.Filter
// ---------------------------------------------------------------------------

func TestFeatureFilter(t *testing.T) {
	p := newTestProject(t)

	_, _ = p.Features.Create("AAA Feature")
	_, _ = p.Features.Create("BBB Feature")
	_, _ = p.Features.Create("AAA Other")

	filtered, err := p.Features.Filter(func(n *models.Node) bool {
		return strings.Contains(n.Title, "AAA")
	})
	if err != nil {
		t.Fatalf("Filter: %v", err)
	}
	if len(filtered) != 2 {
		t.Errorf("Filter AAA: got %d, want 2", len(filtered))
	}
}

// ---------------------------------------------------------------------------
// ID Generation
// ---------------------------------------------------------------------------

func TestIDGeneration(t *testing.T) {
	p := newTestProject(t)

	f1, _ := p.Features.Create("Feature One")
	f2, _ := p.Features.Create("Feature Two")

	if f1.ID == f2.ID {
		t.Error("two features should have different IDs")
	}
	if !strings.HasPrefix(f1.ID, "feat-") {
		t.Errorf("f1 ID prefix: got %q", f1.ID)
	}
	if !strings.HasPrefix(f2.ID, "feat-") {
		t.Errorf("f2 ID prefix: got %q", f2.ID)
	}
	// IDs should be prefix + 8 hex chars
	parts := strings.SplitN(f1.ID, "-", 2)
	if len(parts) != 2 || len(parts[1]) != 8 {
		t.Errorf("ID format: got %q, want feat-XXXXXXXX", f1.ID)
	}
}

// ---------------------------------------------------------------------------
// Project init validation
// ---------------------------------------------------------------------------

func TestOpenRequiresAgent(t *testing.T) {
	dir := t.TempDir()
	_, err := workitem.Open(dir, "")
	if err == nil {
		t.Error("expected error for empty agent")
	}
}

func TestOpenRequiresProjectDir(t *testing.T) {
	_, err := workitem.Open("", "agent")
	if err == nil {
		t.Error("expected error for empty projectDir")
	}
}

// ---------------------------------------------------------------------------
// Claim / Release / AtomicClaim / Unclaim
// ---------------------------------------------------------------------------

func TestClaimReleaseCycle(t *testing.T) {
	p := newTestProject(t)
	feat, err := p.Features.Create("Claim Test")
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	// Claim
	if err := p.Features.Claim(feat.ID, "sess-001"); err != nil {
		t.Fatalf("Claim: %v", err)
	}

	got, err := p.Features.Get(feat.ID)
	if err != nil {
		t.Fatalf("Get after claim: %v", err)
	}
	assertEqual(t, "AgentAssigned", got.AgentAssigned, "test-agent")
	assertEqual(t, "ClaimedBySession", got.ClaimedBySession, "sess-001")
	if got.ClaimedAt == "" {
		t.Error("ClaimedAt should be set after Claim")
	}

	// Release
	if err := p.Features.Release(feat.ID); err != nil {
		t.Fatalf("Release: %v", err)
	}

	got, err = p.Features.Get(feat.ID)
	if err != nil {
		t.Fatalf("Get after release: %v", err)
	}
	assertEqual(t, "AgentAssigned after release", got.AgentAssigned, "")
	assertEqual(t, "ClaimedBySession after release", got.ClaimedBySession, "")
	assertEqual(t, "ClaimedAt after release", got.ClaimedAt, "")
}

func TestAtomicClaimSuccess(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Atomic Claim Test")

	// First claim should succeed
	if err := p.Features.AtomicClaim(feat.ID, "sess-001"); err != nil {
		t.Fatalf("AtomicClaim: %v", err)
	}

	got, _ := p.Features.Get(feat.ID)
	assertEqual(t, "AgentAssigned", got.AgentAssigned, "test-agent")
	assertEqual(t, "ClaimedBySession", got.ClaimedBySession, "sess-001")
}

func TestAtomicClaimSameAgentSameSession(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Atomic Reclaim Test")

	// Claim once
	_ = p.Features.AtomicClaim(feat.ID, "sess-001")

	// Same agent, same session should succeed (idempotent)
	if err := p.Features.AtomicClaim(feat.ID, "sess-001"); err != nil {
		t.Fatalf("AtomicClaim same agent/session should succeed: %v", err)
	}
}

func TestAtomicClaimDifferentSessionFails(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Atomic Conflict Test")

	// Claim with session-001
	_ = p.Features.AtomicClaim(feat.ID, "sess-001")

	// Different session should fail
	err := p.Features.AtomicClaim(feat.ID, "sess-002")
	if err == nil {
		t.Error("expected error when claiming with different session")
	}
	if !strings.Contains(err.Error(), "already claimed") {
		t.Errorf("error should mention 'already claimed': %v", err)
	}
}

func TestAtomicClaimDifferentAgentFails(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Agent Conflict Test")

	// Claim with test-agent
	_ = p.Features.Claim(feat.ID, "sess-001")

	// Create second Project with different agent, same project dir
	p2, err := workitem.Open(p.ProjectDir, "other-agent")
	if err != nil {
		t.Fatalf("workitem.Open for other-agent: %v", err)
	}
	defer p2.Close()

	// Different agent should fail
	err = p2.Features.AtomicClaim(feat.ID, "sess-002")
	if err == nil {
		t.Error("expected error when claiming with different agent")
	}
	if !strings.Contains(err.Error(), "already claimed") {
		t.Errorf("error should mention 'already claimed': %v", err)
	}
}

func TestUnclaim(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Unclaim Test")

	// Claim then unclaim
	_ = p.Features.Claim(feat.ID, "sess-001")

	if err := p.Features.Unclaim(feat.ID); err != nil {
		t.Fatalf("Unclaim: %v", err)
	}

	got, _ := p.Features.Get(feat.ID)
	// Unclaim preserves AgentAssigned but clears claim metadata
	assertEqual(t, "AgentAssigned preserved", got.AgentAssigned, "test-agent")
	assertEqual(t, "ClaimedBySession cleared", got.ClaimedBySession, "")
	assertEqual(t, "ClaimedAt cleared", got.ClaimedAt, "")
}

func TestClaimNonexistentFails(t *testing.T) {
	p := newTestProject(t)

	if err := p.Features.Claim("feat-nonexistent", "sess-001"); err == nil {
		t.Error("expected error claiming nonexistent feature")
	}
}

func TestClaimOnBugs(t *testing.T) {
	p := newTestProject(t)
	bug, _ := p.Bugs.Create("Bug Claim Test")

	if err := p.Bugs.Claim(bug.ID, "sess-001"); err != nil {
		t.Fatalf("Claim bug: %v", err)
	}

	got, _ := p.Bugs.Get(bug.ID)
	assertEqual(t, "Bug AgentAssigned", got.AgentAssigned, "test-agent")
	assertEqual(t, "Bug ClaimedBySession", got.ClaimedBySession, "sess-001")
}

func TestClaimOnSpikes(t *testing.T) {
	p := newTestProject(t)
	spike, _ := p.Spikes.Create("Spike Claim Test")

	if err := p.Spikes.Claim(spike.ID, "sess-001"); err != nil {
		t.Fatalf("Claim spike: %v", err)
	}

	got, _ := p.Spikes.Get(spike.ID)
	assertEqual(t, "Spike AgentAssigned", got.AgentAssigned, "test-agent")
}

// ---------------------------------------------------------------------------
// GetActiveWorkItem
// ---------------------------------------------------------------------------

func TestGetActiveWorkItemNoActive(t *testing.T) {
	p := newTestProject(t)

	// Create items but leave them in todo status
	_, _ = p.Features.Create("Todo Feature")
	_, _ = p.Bugs.Create("Todo Bug")

	item, err := workitem.GetActiveWorkItem(p.ProjectDir)
	if err != nil {
		t.Fatalf("GetActiveWorkItem: %v", err)
	}
	if item != nil {
		t.Errorf("expected nil, got %+v", item)
	}
}

func TestGetActiveWorkItemOneActive(t *testing.T) {
	p := newTestProject(t)

	feat, _ := p.Features.Create("Active Feature")
	_, _ = p.Features.Start(feat.ID)

	item, err := workitem.GetActiveWorkItem(p.ProjectDir)
	if err != nil {
		t.Fatalf("GetActiveWorkItem: %v", err)
	}
	if item == nil {
		t.Fatal("expected active work item, got nil")
	}
	assertEqual(t, "WorkItem.ID", item.ID, feat.ID)
	assertEqual(t, "WorkItem.Type", item.Type, "feature")
	assertEqual(t, "WorkItem.Title", item.Title, "Active Feature")
	assertEqual(t, "WorkItem.Status", item.Status, "in-progress")
}

func TestGetActiveWorkItemPrefersFeatures(t *testing.T) {
	p := newTestProject(t)

	// Start a feature and a bug
	feat, _ := p.Features.Create("Active Feature")
	bug, _ := p.Bugs.Create("Active Bug")
	_, _ = p.Features.Start(feat.ID)
	_, _ = p.Bugs.Start(bug.ID)

	// Features are scanned first, so the feature should be returned
	item, err := workitem.GetActiveWorkItem(p.ProjectDir)
	if err != nil {
		t.Fatalf("GetActiveWorkItem: %v", err)
	}
	if item == nil {
		t.Fatal("expected active work item, got nil")
	}
	assertEqual(t, "WorkItem.Type", item.Type, "feature")
}

func TestGetActiveWorkItemFindsBug(t *testing.T) {
	p := newTestProject(t)

	// Only a bug is active
	bug, _ := p.Bugs.Create("Active Bug")
	_, _ = p.Bugs.Start(bug.ID)

	item, err := workitem.GetActiveWorkItem(p.ProjectDir)
	if err != nil {
		t.Fatalf("GetActiveWorkItem: %v", err)
	}
	if item == nil {
		t.Fatal("expected active work item, got nil")
	}
	assertEqual(t, "WorkItem.Type", item.Type, "bug")
	assertEqual(t, "WorkItem.ID", item.ID, bug.ID)
}

func TestGetActiveWorkItemFindsSpike(t *testing.T) {
	p := newTestProject(t)

	// Only a spike is active
	spike, _ := p.Spikes.Create("Active Spike")
	_, _ = p.Spikes.Start(spike.ID)

	item, err := workitem.GetActiveWorkItem(p.ProjectDir)
	if err != nil {
		t.Fatalf("GetActiveWorkItem: %v", err)
	}
	if item == nil {
		t.Fatal("expected active work item, got nil")
	}
	assertEqual(t, "WorkItem.Type", item.Type, "spike")
	assertEqual(t, "WorkItem.ID", item.ID, spike.ID)
}

func TestGetActiveWorkItemEmptyProject(t *testing.T) {
	p := newTestProject(t)

	item, err := workitem.GetActiveWorkItem(p.ProjectDir)
	if err != nil {
		t.Fatalf("GetActiveWorkItem: %v", err)
	}
	if item != nil {
		t.Errorf("expected nil for empty project, got %+v", item)
	}
}

// ---------------------------------------------------------------------------
// EditBuilder
// ---------------------------------------------------------------------------

func TestEditSetStatus(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Edit Status Test")

	err := p.Features.Edit(feat.ID).
		SetStatus("in-progress").
		Save()
	if err != nil {
		t.Fatalf("Edit.SetStatus.Save: %v", err)
	}

	got, _ := p.Features.Get(feat.ID)
	assertEqual(t, "Status", string(got.Status), "in-progress")
}

func TestEditSetDescription(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Edit Desc Test")

	// Content must be in an element (e.g. <p>) to survive HTML round-trip,
	// because the parser reads child elements, not raw text nodes.
	err := p.Features.Edit(feat.ID).
		SetDescription("<p>New description body</p>").
		Save()
	if err != nil {
		t.Fatalf("Edit.SetDescription.Save: %v", err)
	}

	got, _ := p.Features.Get(feat.ID)
	if !strings.Contains(got.Content, "New description body") {
		t.Errorf("Content: got %q", got.Content)
	}
}

func TestEditSetFindings(t *testing.T) {
	p := newTestProject(t)
	spike, _ := p.Spikes.Create("Edit Findings Test")

	err := p.Spikes.Edit(spike.ID).
		SetFindings("Investigation complete: use Redis").
		Save()
	if err != nil {
		t.Fatalf("Edit.SetFindings.Save: %v", err)
	}

	got, _ := p.Spikes.Get(spike.ID)
	if !strings.Contains(got.Content, "Investigation complete: use Redis") {
		t.Errorf("Content: got %q", got.Content)
	}
}

func TestEditAddNote(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Edit Note Test",
		workitem.FeatWithContent("<p>Original content</p>"),
	)

	err := p.Features.Edit(feat.ID).
		AddNote("First note").
		AddNote("Second note").
		Save()
	if err != nil {
		t.Fatalf("Edit.AddNote.Save: %v", err)
	}

	got, _ := p.Features.Get(feat.ID)
	if !strings.Contains(got.Content, "First note") {
		t.Errorf("Content missing first note: %q", got.Content)
	}
	if !strings.Contains(got.Content, "Second note") {
		t.Errorf("Content missing second note: %q", got.Content)
	}
	if !strings.Contains(got.Content, "Original content") {
		t.Errorf("Content missing original: %q", got.Content)
	}
}

func TestEditChainMultipleFields(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Multi Edit Test")

	err := p.Features.Edit(feat.ID).
		SetStatus("in-progress").
		SetPriority("critical").
		SetAgent("new-agent").
		SetTrack("trk-new").
		AddNote("Started work").
		Save()
	if err != nil {
		t.Fatalf("Edit chain Save: %v", err)
	}

	got, _ := p.Features.Get(feat.ID)
	assertEqual(t, "Status", string(got.Status), "in-progress")
	assertEqual(t, "Priority", string(got.Priority), "critical")
	assertEqual(t, "AgentAssigned", got.AgentAssigned, "new-agent")
	assertEqual(t, "TrackID", got.TrackID, "trk-new")
	if !strings.Contains(got.Content, "Started work") {
		t.Errorf("Content missing note: %q", got.Content)
	}
}

func TestEditNonexistentNode(t *testing.T) {
	p := newTestProject(t)

	err := p.Features.Edit("feat-nonexistent").
		SetStatus("done").
		Save()
	if err == nil {
		t.Error("expected error editing nonexistent node")
	}
}

func TestEditDeferredError(t *testing.T) {
	p := newTestProject(t)

	// All chained methods should be no-ops when initial load fails
	err := p.Features.Edit("feat-nonexistent").
		SetStatus("done").
		SetPriority("high").
		AddNote("note").
		SetDescription("desc").
		SetFindings("findings").
		SetAgent("agent").
		SetTrack("trk-x").
		Save()
	if err == nil {
		t.Error("expected error from deferred load failure")
	}
}

func TestEditOnBug(t *testing.T) {
	p := newTestProject(t)
	bug, _ := p.Bugs.Create("Bug Edit Test")

	err := p.Bugs.Edit(bug.ID).
		SetStatus("in-progress").
		AddNote("Investigating").
		Save()
	if err != nil {
		t.Fatalf("Edit bug: %v", err)
	}

	got, _ := p.Bugs.Get(bug.ID)
	assertEqual(t, "Bug status", string(got.Status), "in-progress")
	if !strings.Contains(got.Content, "Investigating") {
		t.Errorf("Bug content: %q", got.Content)
	}
}

// ---------------------------------------------------------------------------
// AddNote (standalone Collection method)
// ---------------------------------------------------------------------------

func TestAddNote(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Note Test",
		workitem.FeatWithContent("<p>Initial</p>"),
	)

	if err := p.Features.AddNote(feat.ID, "First observation"); err != nil {
		t.Fatalf("AddNote: %v", err)
	}

	got, _ := p.Features.Get(feat.ID)
	if !strings.Contains(got.Content, "First observation") {
		t.Errorf("Content missing note: %q", got.Content)
	}
	if !strings.Contains(got.Content, "Initial") {
		t.Errorf("Content lost original: %q", got.Content)
	}
	// Note should include agent name
	if !strings.Contains(got.Content, "test-agent") {
		t.Errorf("Note missing agent: %q", got.Content)
	}
}

func TestAddNoteAppendsMultiple(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Multi Note Test")

	_ = p.Features.AddNote(feat.ID, "Note one")
	_ = p.Features.AddNote(feat.ID, "Note two")
	_ = p.Features.AddNote(feat.ID, "Note three")

	got, _ := p.Features.Get(feat.ID)
	if !strings.Contains(got.Content, "Note one") {
		t.Errorf("Missing note one: %q", got.Content)
	}
	if !strings.Contains(got.Content, "Note two") {
		t.Errorf("Missing note two: %q", got.Content)
	}
	if !strings.Contains(got.Content, "Note three") {
		t.Errorf("Missing note three: %q", got.Content)
	}
}

func TestAddNoteNonexistent(t *testing.T) {
	p := newTestProject(t)
	err := p.Features.AddNote("feat-nonexistent", "note")
	if err == nil {
		t.Error("expected error for nonexistent feature")
	}
}

func TestAddNoteOnBug(t *testing.T) {
	p := newTestProject(t)
	bug, _ := p.Bugs.Create("Bug Note Test")

	if err := p.Bugs.AddNote(bug.ID, "Bug observation"); err != nil {
		t.Fatalf("AddNote bug: %v", err)
	}

	got, _ := p.Bugs.Get(bug.ID)
	if !strings.Contains(got.Content, "Bug observation") {
		t.Errorf("Bug content: %q", got.Content)
	}
}

func TestAddNoteOnSpike(t *testing.T) {
	p := newTestProject(t)
	spike, _ := p.Spikes.Create("Spike Note Test")

	if err := p.Spikes.AddNote(spike.ID, "Spike finding"); err != nil {
		t.Fatalf("AddNote spike: %v", err)
	}

	got, _ := p.Spikes.Get(spike.ID)
	if !strings.Contains(got.Content, "Spike finding") {
		t.Errorf("Spike content: %q", got.Content)
	}
}

// ---------------------------------------------------------------------------
// SetFindings (standalone Collection method)
// ---------------------------------------------------------------------------

func TestSetFindingsReplacesContent(t *testing.T) {
	p := newTestProject(t)
	spike, _ := p.Spikes.Create("Findings Test",
		workitem.SpikeWithFindings("Old findings"),
	)

	if _, err := p.Spikes.SetFindings(spike.ID, "New findings replace old"); err != nil {
		t.Fatalf("SetFindings: %v", err)
	}

	got, _ := p.Spikes.Get(spike.ID)
	if !strings.Contains(got.Content, "New findings replace old") {
		t.Errorf("Content missing new findings: %q", got.Content)
	}
	// Old findings should be gone (replaced, not appended)
	if strings.Contains(got.Content, "Old findings") {
		t.Errorf("Content still has old findings: %q", got.Content)
	}
}

func TestSetFindingsOnFeature(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Feature Findings Test")

	if err := p.Features.SetFindings(feat.ID, "Feature analysis complete"); err != nil {
		t.Fatalf("SetFindings: %v", err)
	}

	got, _ := p.Features.Get(feat.ID)
	if !strings.Contains(got.Content, "Feature analysis complete") {
		t.Errorf("Content: %q", got.Content)
	}
}

func TestSetFindingsNonexistent(t *testing.T) {
	p := newTestProject(t)
	_, err := p.Spikes.SetFindings("spk-nonexistent", "findings")
	if err == nil {
		t.Error("expected error for nonexistent spike")
	}
}

// ---------------------------------------------------------------------------
// Claim round-trip with HTML parsing
// ---------------------------------------------------------------------------

func TestClaimRoundTrip(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Claim RT Test")

	_ = p.Features.Claim(feat.ID, "sess-rt-001")

	// Parse the HTML file directly
	path := filepath.Join(p.FeaturesDir(), feat.ID+".html")
	parsed, err := htmlparse.ParseFile(path)
	if err != nil {
		t.Fatalf("ParseFile: %v", err)
	}

	assertEqual(t, "parsed.AgentAssigned", parsed.AgentAssigned, "test-agent")
	assertEqual(t, "parsed.ClaimedBySession", parsed.ClaimedBySession, "sess-rt-001")
	if parsed.ClaimedAt == "" {
		t.Error("parsed.ClaimedAt should be set")
	}
}

// ---------------------------------------------------------------------------
// Edit round-trip with HTML parsing
// ---------------------------------------------------------------------------

func TestEditRoundTrip(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Edit RT Test")

	_ = p.Features.Edit(feat.ID).
		SetStatus("in-progress").
		SetPriority("high").
		AddNote("Implementation started").
		Save()

	path := filepath.Join(p.FeaturesDir(), feat.ID+".html")
	parsed, err := htmlparse.ParseFile(path)
	if err != nil {
		t.Fatalf("ParseFile: %v", err)
	}

	assertEqual(t, "parsed.Status", string(parsed.Status), "in-progress")
	assertEqual(t, "parsed.Priority", string(parsed.Priority), "high")
	if !strings.Contains(parsed.Content, "Implementation started") {
		t.Errorf("parsed.Content missing note: %q", parsed.Content)
	}
}

// ---------------------------------------------------------------------------
// Collection AddEdge / RemoveEdge
// ---------------------------------------------------------------------------

func TestCollectionAddEdge(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Edge Source")
	target, _ := p.Features.Create("Edge Target")

	updated, err := p.Features.AddEdge(feat.ID, models.Edge{
		TargetID:     target.ID,
		Relationship: models.RelBlocks,
		Title:        target.Title,
	})
	if err != nil {
		t.Fatalf("AddEdge: %v", err)
	}

	edges := updated.Edges[string(models.RelBlocks)]
	if len(edges) != 1 {
		t.Fatalf("expected 1 edge, got %d", len(edges))
	}
	assertEqual(t, "edge target", edges[0].TargetID, target.ID)

	// Re-read from disk to confirm persistence.
	reread, _ := p.Features.Get(feat.ID)
	if len(reread.Edges[string(models.RelBlocks)]) != 1 {
		t.Error("edge not persisted to disk")
	}
}

func TestCollectionRemoveEdge(t *testing.T) {
	p := newTestProject(t)
	feat, _ := p.Features.Create("Edge Source")

	// Add two edges, remove one.
	_, _ = p.Features.AddEdge(feat.ID, models.Edge{
		TargetID: "feat-a", Relationship: models.RelBlocks,
	})
	_, _ = p.Features.AddEdge(feat.ID, models.Edge{
		TargetID: "feat-b", Relationship: models.RelBlocks,
	})

	updated, removed, err := p.Features.RemoveEdge(feat.ID, "feat-a", models.RelBlocks)
	if err != nil {
		t.Fatalf("RemoveEdge: %v", err)
	}
	if !removed {
		t.Error("expected removed=true")
	}
	if len(updated.Edges[string(models.RelBlocks)]) != 1 {
		t.Error("expected 1 remaining edge")
	}

	// Verify disk.
	reread, _ := p.Features.Get(feat.ID)
	if len(reread.Edges[string(models.RelBlocks)]) != 1 {
		t.Error("removal not persisted")
	}

	// Remove non-existent.
	_, removed, err = p.Features.RemoveEdge(feat.ID, "feat-zzz", models.RelBlocks)
	if err != nil {
		t.Fatalf("RemoveEdge nonexistent: %v", err)
	}
	if removed {
		t.Error("expected removed=false for non-existent edge")
	}
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

func assertEqual(t *testing.T, field, got, want string) {
	t.Helper()
	if got != want {
		t.Errorf("%s: got %q, want %q", field, got, want)
	}
}
