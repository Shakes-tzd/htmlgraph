package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// buildMinimalValidPlan returns a minimal but structurally valid CRISPI plan HTML.
func buildMinimalValidPlan(planID string) string {
	return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"></head><body>
<div class="plan-content">
<article id="` + planID + `" data-feature-id="feat-xxx" data-status="draft">
<header class="plan-header"><h1>Plan: Test Plan</h1></header>

<!-- ZONE 1: Dependency Graph -->
<section class="dep-graph" data-zone="dependency-graph">
  <div id="graph-data" style="display:none">
    <div data-node="1" data-name="Slice one" data-files="2" data-status="pending" data-deps=""></div>
    <div data-node="2" data-name="Slice two" data-files="1" data-status="pending" data-deps="1"></div>
  </div>
  <svg id="dep-graph-svg" width="100%"></svg>
</section>

<!-- A: Design Discussion -->
<details class="section-card" data-phase="design" data-status="pending">
  <summary><span>A. Design Discussion</span></summary>
  <div class="section-body">
    <div class="approval-row">
      <label><input type="checkbox" data-section="design" data-action="approve"> Approve design</label>
      <textarea data-section="design" data-comment-for="design"></textarea>
    </div>
  </div>
</details>

<!-- B: Structure Outline -->
<details class="section-card" data-phase="outline" data-status="pending">
  <summary><span>B. Structure Outline</span></summary>
  <div class="section-body">
    <div class="approval-row">
      <label><input type="checkbox" data-section="outline" data-action="approve"> Approve API contract</label>
      <textarea data-section="outline" data-comment-for="outline"></textarea>
    </div>
  </div>
</details>

<!-- C: Vertical Slices -->
<details class="section-card" data-phase="slices" data-status="pending">
  <summary><span>C. Vertical Slices</span></summary>
  <div class="section-body">
    <div class="slice-card" data-slice="1" data-slice-name="slice-one" data-status="pending" data-files="2">
      <div class="approval-row">
        <label><input type="checkbox" data-section="slice-1" data-action="approve"> Approve slice</label>
        <textarea data-section="slice-1" data-comment-for="slice-1"></textarea>
      </div>
    </div>
    <div class="slice-card" data-slice="2" data-slice-name="slice-two" data-status="pending" data-files="1">
      <div class="approval-row">
        <label><input type="checkbox" data-section="slice-2" data-action="approve"> Approve slice</label>
        <textarea data-section="slice-2" data-comment-for="slice-2"></textarea>
      </div>
    </div>
  </div>
</details>

<!-- D: Open Questions Recap -->
<details class="section-card" data-phase="questions" data-status="pending">
  <summary><span>D. Open Questions Recap</span></summary>
  <div class="section-body">
    <div class="question-block" data-question="q-foo" data-status="pending">
      <p>What approach?</p>
      <label><input type="radio" name="q-approach" value="a" data-question="q-foo"> Option A</label>
      <label><input type="radio" name="q-approach" value="b" data-question="q-foo"> Option B</label>
    </div>
    <table class="q-table">
      <tbody id="questionsRecap">
        <tr data-recap-for="q-foo"><td>What approach</td><td class="recap-answer">a</td><td></td></tr>
      </tbody>
    </table>
  </div>
</details>

<!-- ZONE 3: Feedback Summary -->
<section class="progress-zone" data-zone="feedback-summary">
  <div class="finalize-area">
    <button class="btn-finalize" id="finalizeBtn" disabled>Finalize Plan</button>
  </div>
</section>

</article>
</div>
<script>
var SECTIONS=/*PLAN_SECTIONS_JSON*/['design','outline','slice-1','slice-2']/*END_PLAN_SECTIONS_JSON*/;
</script>
</body></html>`
}

func writeTempPlan(t *testing.T, dir, planID, content string) string {
	t.Helper()
	plansDir := filepath.Join(dir, "plans")
	if err := os.MkdirAll(plansDir, 0o755); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(plansDir, planID+".html")
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func runValidateAndDecode(t *testing.T, planPath string) planValidation {
	t.Helper()
	result, err := validatePlanHTML(planPath)
	if err != nil {
		t.Fatalf("validatePlanHTML: %v", err)
	}
	// Ensure it round-trips through JSON cleanly.
	data, err := json.Marshal(result)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var out planValidation
	if err := json.Unmarshal(data, &out); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	return out
}

func TestPlanValidate_ValidPlan(t *testing.T) {
	tmpDir := t.TempDir()
	planID := "plan-test-valid"
	writeTempPlan(t, tmpDir, planID, buildMinimalValidPlan(planID))
	planPath := filepath.Join(tmpDir, "plans", planID+".html")

	result := runValidateAndDecode(t, planPath)

	if !result.Valid {
		t.Errorf("expected valid plan, got errors: %v", result.Errors)
	}
	if len(result.Errors) != 0 {
		t.Errorf("expected no errors, got: %v", result.Errors)
	}
	if result.Stats.Slices != 2 {
		t.Errorf("expected 2 slices, got %d", result.Stats.Slices)
	}
	if result.Stats.GraphNodes != 2 {
		t.Errorf("expected 2 graph nodes, got %d", result.Stats.GraphNodes)
	}
}

func TestPlanValidate_MissingFinalizeButton(t *testing.T) {
	tmpDir := t.TempDir()
	planID := "plan-test-no-finalize"
	content := buildMinimalValidPlan(planID)
	// Remove the finalize button.
	content = strings.ReplaceAll(content,
		`<button class="btn-finalize" id="finalizeBtn" disabled>Finalize Plan</button>`,
		"")
	writeTempPlan(t, tmpDir, planID, content)
	planPath := filepath.Join(tmpDir, "plans", planID+".html")

	result := runValidateAndDecode(t, planPath)

	if result.Valid {
		t.Error("expected invalid plan due to missing finalize button")
	}
	if !containsValidationError(result.Errors, "finalizeBtn") {
		t.Errorf("expected error mentioning finalizeBtn, got: %v", result.Errors)
	}
}

func TestPlanValidate_MissingDesignSection(t *testing.T) {
	tmpDir := t.TempDir()
	planID := "plan-test-no-design"
	content := buildMinimalValidPlan(planID)
	// Remove the design section by altering data-phase.
	content = strings.ReplaceAll(content,
		`<details class="section-card" data-phase="design" data-status="pending">`,
		`<details class="section-card" data-phase="REMOVED" data-status="pending">`)
	writeTempPlan(t, tmpDir, planID, content)
	planPath := filepath.Join(tmpDir, "plans", planID+".html")

	result := runValidateAndDecode(t, planPath)

	if result.Valid {
		t.Error("expected invalid plan due to missing design section")
	}
	if !containsValidationError(result.Errors, "design") {
		t.Errorf("expected error mentioning design section, got: %v", result.Errors)
	}
}

func TestPlanValidate_MissingOutlineSection(t *testing.T) {
	tmpDir := t.TempDir()
	planID := "plan-test-no-outline"
	content := buildMinimalValidPlan(planID)
	content = strings.ReplaceAll(content,
		`<details class="section-card" data-phase="outline" data-status="pending">`,
		`<details class="section-card" data-phase="REMOVED" data-status="pending">`)
	writeTempPlan(t, tmpDir, planID, content)
	planPath := filepath.Join(tmpDir, "plans", planID+".html")

	result := runValidateAndDecode(t, planPath)

	if result.Valid {
		t.Error("expected invalid plan due to missing outline section")
	}
	if !containsValidationError(result.Errors, "outline") {
		t.Errorf("expected error mentioning outline section, got: %v", result.Errors)
	}
}

func TestPlanValidate_SliceGraphMismatch(t *testing.T) {
	tmpDir := t.TempDir()
	planID := "plan-test-mismatch"
	content := buildMinimalValidPlan(planID)
	// Remove one graph node so count doesn't match slice cards.
	content = strings.ReplaceAll(content,
		`<div data-node="2" data-name="Slice two" data-files="1" data-status="pending" data-deps="1"></div>`,
		"")
	writeTempPlan(t, tmpDir, planID, content)
	planPath := filepath.Join(tmpDir, "plans", planID+".html")

	result := runValidateAndDecode(t, planPath)

	if result.Valid {
		t.Error("expected invalid plan due to slice/graph node count mismatch")
	}
	if !containsValidationError(result.Errors, "graph") && !containsValidationError(result.Errors, "mismatch") {
		t.Errorf("expected error mentioning graph mismatch, got: %v", result.Errors)
	}
}

func TestPlanValidate_InvalidStatus(t *testing.T) {
	tmpDir := t.TempDir()
	planID := "plan-test-bad-status"
	content := buildMinimalValidPlan(planID)
	// Replace valid article status with an unknown value.
	content = strings.ReplaceAll(content, `data-status="draft"`, `data-status="bogus-status"`)
	writeTempPlan(t, tmpDir, planID, content)
	planPath := filepath.Join(tmpDir, "plans", planID+".html")

	result := runValidateAndDecode(t, planPath)

	if result.Valid {
		t.Error("expected invalid plan due to invalid status")
	}
	if !containsValidationError(result.Errors, "status") {
		t.Errorf("expected error mentioning status, got: %v", result.Errors)
	}
}

func TestPlanValidate_SliceMissingApprovalCheckbox(t *testing.T) {
	tmpDir := t.TempDir()
	planID := "plan-test-no-checkbox"
	content := buildMinimalValidPlan(planID)
	// Remove the approval checkbox from slice-1.
	content = strings.ReplaceAll(content,
		`<label><input type="checkbox" data-section="slice-1" data-action="approve"> Approve slice</label>`,
		"")
	writeTempPlan(t, tmpDir, planID, content)
	planPath := filepath.Join(tmpDir, "plans", planID+".html")

	result := runValidateAndDecode(t, planPath)

	if result.Valid {
		t.Error("expected invalid plan due to missing approval checkbox on slice")
	}
	if !containsValidationError(result.Errors, "slice-1") {
		t.Errorf("expected error mentioning slice-1, got: %v", result.Errors)
	}
}

func TestPlanValidate_QuestionMissingRecapRow(t *testing.T) {
	tmpDir := t.TempDir()
	planID := "plan-test-no-recap"
	content := buildMinimalValidPlan(planID)
	// Remove the recap row for q-foo.
	content = strings.ReplaceAll(content,
		`<tr data-recap-for="q-foo"><td>What approach</td><td class="recap-answer">a</td><td></td></tr>`,
		"")
	writeTempPlan(t, tmpDir, planID, content)
	planPath := filepath.Join(tmpDir, "plans", planID+".html")

	result := runValidateAndDecode(t, planPath)

	if result.Valid {
		t.Error("expected invalid plan due to missing recap row for question")
	}
	if !containsValidationError(result.Errors, "q-foo") && !containsValidationError(result.Errors, "recap") {
		t.Errorf("expected error mentioning recap row for q-foo, got: %v", result.Errors)
	}
}

func TestPlanValidate_SectionsJSONMismatch(t *testing.T) {
	tmpDir := t.TempDir()
	planID := "plan-test-sections-mismatch"
	content := buildMinimalValidPlan(planID)
	// Change SECTIONS JS array to include a section that doesn't exist in HTML.
	content = strings.ReplaceAll(content,
		`['design','outline','slice-1','slice-2']`,
		`['design','outline','slice-1','slice-2','slice-99']`)
	writeTempPlan(t, tmpDir, planID, content)
	planPath := filepath.Join(tmpDir, "plans", planID+".html")

	result := runValidateAndDecode(t, planPath)

	if result.Valid {
		t.Error("expected invalid plan due to SECTIONS JSON mismatch")
	}
	if !containsValidationError(result.Errors, "slice-99") && !containsValidationError(result.Errors, "SECTIONS") {
		t.Errorf("expected error mentioning SECTIONS mismatch, got: %v", result.Errors)
	}
}

func TestPlanValidate_FileNotFound(t *testing.T) {
	_, err := validatePlanHTML("/nonexistent/plan-missing.html")
	if err == nil {
		t.Error("expected error for missing file")
	}
}

func TestPlanValidate_ValidStatuses(t *testing.T) {
	validStatuses := []string{"draft", "in-review", "finalized"}
	for _, status := range validStatuses {
		t.Run(status, func(t *testing.T) {
			tmpDir := t.TempDir()
			planID := "plan-test-status-" + status
			content := buildMinimalValidPlan(planID)
			content = strings.ReplaceAll(content, `data-status="draft"`, `data-status="`+status+`"`)
			writeTempPlan(t, tmpDir, planID, content)
			planPath := filepath.Join(tmpDir, "plans", planID+".html")

			result := runValidateAndDecode(t, planPath)

			// Status errors should not appear for valid statuses.
			for _, e := range result.Errors {
				if strings.Contains(strings.ToLower(e), "status") {
					t.Errorf("unexpected status error for %q: %s", status, e)
				}
			}
		})
	}
}

// containsValidationError returns true if any element in errs contains substr (case-insensitive).
func containsValidationError(errs []string, substr string) bool {
	lower := strings.ToLower(substr)
	for _, e := range errs {
		if strings.Contains(strings.ToLower(e), lower) {
			return true
		}
	}
	return false
}
