package main

import (
	"os"
	"path/filepath"
	"testing"
)

func writeCritiquePlan(t *testing.T, dir, planID, html string) {
	t.Helper()
	plansDir := filepath.Join(dir, "plans")
	if err := os.MkdirAll(plansDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(plansDir, planID+".html"), []byte(html), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestCritique_ComplexityGateLow(t *testing.T) {
	dir := t.TempDir()
	planID := "plan-small"
	html := `<!DOCTYPE html><html><body>
		<article id="plan-small" data-status="draft"><header><h1>Plan: Small</h1></header>
		<div class="slice-card" data-slice="1" data-status="pending">
		  <div class="slice-header"><span class="slice-name">Slice One</span></div>
		</div>
		</article></body></html>`
	writeCritiquePlan(t, dir, planID, html)

	out, err := extractCritiqueData(dir, planID)
	if err != nil {
		t.Fatalf("extractCritiqueData: %v", err)
	}
	if out.CritiqueWarranted {
		t.Error("expected critique_warranted=false for 1 slice")
	}
	if out.Complexity != "low" {
		t.Errorf("complexity = %q, want low", out.Complexity)
	}
	if out.SliceCount != 1 {
		t.Errorf("slice_count = %d, want 1", out.SliceCount)
	}
}

func TestCritique_ComplexityGateMedium(t *testing.T) {
	dir := t.TempDir()
	planID := "plan-medium"
	html := `<!DOCTYPE html><html><body>
		<article id="plan-medium" data-status="draft"><header><h1>Plan: Medium</h1></header>
		<div class="slice-card" data-slice="1" data-status="pending"><div class="slice-header"><span class="slice-name">S1</span></div></div>
		<div class="slice-card" data-slice="2" data-status="pending"><div class="slice-header"><span class="slice-name">S2</span></div></div>
		<div class="slice-card" data-slice="3" data-status="pending"><div class="slice-header"><span class="slice-name">S3</span></div></div>
		<div class="slice-card" data-slice="4" data-status="pending"><div class="slice-header"><span class="slice-name">S4</span></div></div>
		</article></body></html>`
	writeCritiquePlan(t, dir, planID, html)

	out, err := extractCritiqueData(dir, planID)
	if err != nil {
		t.Fatalf("extractCritiqueData: %v", err)
	}
	if !out.CritiqueWarranted {
		t.Error("expected critique_warranted=true for 4 slices")
	}
	if out.Complexity != "medium" {
		t.Errorf("complexity = %q, want medium", out.Complexity)
	}
}

func TestCritique_SliceExtraction(t *testing.T) {
	dir := t.TempDir()
	planID := "plan-slices"
	html := `<!DOCTYPE html><html><body>
		<article id="plan-slices" data-status="draft"><header><h1>Plan: Slices Test</h1></header>
		<div data-node="1" data-name="First" data-status="pending" data-deps=""></div>
		<div data-node="2" data-name="Second" data-status="pending" data-deps="1"></div>
		<div class="slice-card" data-slice="1" data-status="pending">
		  <div class="slice-header"><span class="slice-name">First Slice</span></div>
		</div>
		<div class="slice-card" data-slice="2" data-status="pending">
		  <div class="slice-header"><span class="slice-name">Second Slice</span></div>
		</div>
		</article></body></html>`
	writeCritiquePlan(t, dir, planID, html)

	out, err := extractCritiqueData(dir, planID)
	if err != nil {
		t.Fatal(err)
	}
	if len(out.Slices) != 2 {
		t.Fatalf("slices = %d, want 2", len(out.Slices))
	}
	if out.Slices[0].Title != "First Slice" {
		t.Errorf("slice 1 title = %q", out.Slices[0].Title)
	}
	if out.Slices[1].Title != "Second Slice" {
		t.Errorf("slice 2 title = %q", out.Slices[1].Title)
	}
	if len(out.Slices[1].Dependencies) != 1 || out.Slices[1].Dependencies[0] != 1 {
		t.Errorf("slice 2 deps = %v, want [1]", out.Slices[1].Dependencies)
	}
}

func TestCritique_TitleAndStatus(t *testing.T) {
	dir := t.TempDir()
	planID := "plan-meta"
	html := `<!DOCTYPE html><html><body>
		<article id="plan-meta" data-status="in-review"><header><h1>Plan: Meta Test</h1></header>
		</article></body></html>`
	writeCritiquePlan(t, dir, planID, html)

	out, err := extractCritiqueData(dir, planID)
	if err != nil {
		t.Fatal(err)
	}
	if out.Title != "Meta Test" {
		t.Errorf("title = %q, want Meta Test", out.Title)
	}
	if out.Status != "in-review" {
		t.Errorf("status = %q, want in-review", out.Status)
	}
}

func TestClassifyComplexity(t *testing.T) {
	cases := []struct {
		count      int
		wantLevel  string
		wantCrit   bool
	}{
		{0, "low", false},
		{2, "low", false},
		{3, "medium", true},
		{5, "medium", true},
		{6, "high", true},
		{10, "high", true},
	}
	for _, tc := range cases {
		level, crit := classifyComplexity(tc.count)
		if level != tc.wantLevel || crit != tc.wantCrit {
			t.Errorf("classifyComplexity(%d) = (%q, %v), want (%q, %v)",
				tc.count, level, crit, tc.wantLevel, tc.wantCrit)
		}
	}
}
