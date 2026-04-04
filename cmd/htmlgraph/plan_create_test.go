package main

import (
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

func TestRunPlanCreateFromTopic(t *testing.T) {
	dir := t.TempDir()
	plansDir := filepath.Join(dir, "plans")
	if err := os.MkdirAll(plansDir, 0o755); err != nil {
		t.Fatal(err)
	}

	planID, err := createPlanFromTopic(dir, "Auth Middleware Rewrite", "Rewrite auth for compliance")
	if err != nil {
		t.Fatalf("createPlanFromTopic: %v", err)
	}

	// Verify hex8 format.
	matched, _ := regexp.MatchString(`^plan-[0-9a-f]{8}$`, planID)
	if !matched {
		t.Errorf("plan ID %q does not match hex8 format", planID)
	}

	// Verify file exists.
	planPath := filepath.Join(plansDir, planID+".html")
	data, err := os.ReadFile(planPath)
	if err != nil {
		t.Fatalf("plan file not found: %v", err)
	}
	html := string(data)

	// Verify title is injected.
	if !strings.Contains(html, "Auth Middleware Rewrite") {
		t.Error("plan HTML missing title")
	}

	// Verify description is injected.
	if !strings.Contains(html, "Rewrite auth for compliance") {
		t.Error("plan HTML missing description")
	}

	// Verify it's a CRISPI plan (has interactive elements).
	if !strings.Contains(html, "data-status=\"draft\"") {
		t.Error("plan HTML missing draft status")
	}
	if !strings.Contains(html, "btn-finalize") {
		t.Error("plan HTML missing finalize button")
	}

	// Verify no track/feature references.
	if strings.Contains(html, "feat-xxx") {
		t.Error("plan HTML still has feat-xxx placeholder")
	}
}

func TestRunPlanAddSlice(t *testing.T) {
	dir := t.TempDir()
	plansDir := filepath.Join(dir, "plans")
	if err := os.MkdirAll(plansDir, 0o755); err != nil {
		t.Fatal(err)
	}

	planID, err := createPlanFromTopic(dir, "Test Plan", "A test plan")
	if err != nil {
		t.Fatalf("createPlanFromTopic: %v", err)
	}

	// Add a slice.
	if err := addSliceToPlan(dir, planID, "Implement error handling"); err != nil {
		t.Fatalf("addSliceToPlan: %v", err)
	}

	// Verify slice exists in HTML.
	planPath := filepath.Join(plansDir, planID+".html")
	data, err := os.ReadFile(planPath)
	if err != nil {
		t.Fatal(err)
	}
	html := string(data)

	if !strings.Contains(html, "Implement error handling") {
		t.Error("plan HTML missing slice title")
	}
	if !strings.Contains(html, `data-slice="1"`) {
		t.Error("plan HTML missing slice-1 marker")
	}

	// Add a second slice.
	if err := addSliceToPlan(dir, planID, "Add tests"); err != nil {
		t.Fatalf("addSliceToPlan second: %v", err)
	}

	data, _ = os.ReadFile(planPath)
	html = string(data)
	if !strings.Contains(html, `data-slice="2"`) {
		t.Error("plan HTML missing slice-2 marker")
	}
}
