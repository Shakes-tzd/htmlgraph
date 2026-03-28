package hooks

import (
	"os"
	"path/filepath"
	"testing"
)

func TestIsYoloMode(t *testing.T) {
	// Create temp .htmlgraph dir with launch-mode file
	tmpDir := t.TempDir()
	hgDir := filepath.Join(tmpDir, ".htmlgraph")
	os.MkdirAll(hgDir, 0o755)

	// No launch-mode file → not yolo
	if isYoloMode(hgDir) {
		t.Error("expected non-yolo when no launch-mode file")
	}

	// Write yolo launch mode
	os.WriteFile(filepath.Join(hgDir, ".launch-mode"),
		[]byte(`{"mode":"yolo-dev","pid":1234}`), 0o644)
	if !isYoloMode(hgDir) {
		t.Error("expected yolo mode with yolo-dev launch-mode")
	}

	// Write non-yolo launch mode
	os.WriteFile(filepath.Join(hgDir, ".launch-mode"),
		[]byte(`{"mode":"standard","pid":1234}`), 0o644)
	if isYoloMode(hgDir) {
		t.Error("expected non-yolo with standard launch-mode")
	}
}

func TestCheckYoloWorkItemGuard(t *testing.T) {
	tests := []struct {
		name      string
		tool      string
		featureID string
		yolo      bool
		blocked   bool
	}{
		{"write without feature in yolo blocks", "Write", "", true, true},
		{"edit without feature in yolo blocks", "Edit", "", true, true},
		{"write with feature in yolo allows", "Write", "feat-123", true, false},
		{"write without feature outside yolo allows", "Write", "", false, false},
		{"read without feature in yolo allows", "Read", "", true, false},
		{"bash without feature in yolo allows", "Bash", "", true, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := checkYoloWorkItemGuard(tt.tool, tt.featureID, tt.yolo)
			if tt.blocked && result == "" {
				t.Errorf("expected block for tool=%s feature=%q yolo=%v", tt.tool, tt.featureID, tt.yolo)
			}
			if !tt.blocked && result != "" {
				t.Errorf("expected allow for tool=%s feature=%q yolo=%v, got: %s", tt.tool, tt.featureID, tt.yolo, result)
			}
		})
	}
}

func TestCheckYoloCommitGuard(t *testing.T) {
	tests := []struct {
		name      string
		tool      string
		cmd       string
		yolo      bool
		testRan   bool
		blocked   bool
	}{
		{"git commit without tests in yolo blocks", "Bash", "git commit -m 'foo'", true, false, true},
		{"git commit with tests in yolo allows", "Bash", "git commit -m 'foo'", true, true, false},
		{"git commit outside yolo allows", "Bash", "git commit -m 'foo'", false, false, false},
		{"git add in yolo allows", "Bash", "git add file.go", true, false, false},
		{"non-bash ignored", "Read", "git commit", true, false, false},
		{"git commit amend in yolo blocks without tests", "Bash", "git commit --amend", true, false, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			event := &CloudEvent{
				ToolName:  tt.tool,
				ToolInput: map[string]any{"command": tt.cmd},
			}
			result := checkYoloCommitGuard(event, tt.yolo, tt.testRan)
			if tt.blocked && result == "" {
				t.Errorf("expected block for cmd=%q yolo=%v testRan=%v", tt.cmd, tt.yolo, tt.testRan)
			}
			if !tt.blocked && result != "" {
				t.Errorf("expected allow for cmd=%q yolo=%v testRan=%v, got: %s", tt.cmd, tt.yolo, tt.testRan, result)
			}
		})
	}
}

func TestCheckYoloWorktreeGuard(t *testing.T) {
	tests := []struct {
		name    string
		tool    string
		branch  string
		yolo    bool
		blocked bool
	}{
		{"write on main in yolo blocks", "Write", "main", true, true},
		{"write on main in yolo blocks (master)", "Write", "master", true, true},
		{"write on feature branch allows", "Write", "feat-123", true, false},
		{"write on main outside yolo allows", "Write", "main", false, false},
		{"read on main in yolo allows", "Read", "main", true, false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := checkYoloWorktreeGuard(tt.tool, tt.branch, tt.yolo)
			if tt.blocked && result == "" {
				t.Errorf("expected block")
			}
			if !tt.blocked && result != "" {
				t.Errorf("expected allow, got: %s", result)
			}
		})
	}
}

func TestCheckYoloResearchGuard(t *testing.T) {
	tests := []struct {
		name        string
		tool        string
		yolo        bool
		hasResearch bool
		blocked     bool
	}{
		{"write without research in yolo blocks", "Write", true, false, true},
		{"write with research in yolo allows", "Write", true, true, false},
		{"write outside yolo allows", "Write", false, false, false},
		{"read without research allows", "Read", true, false, false},
		{"edit without research in yolo blocks", "Edit", true, false, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := checkYoloResearchGuard(tt.tool, tt.yolo, tt.hasResearch)
			if tt.blocked && result == "" {
				t.Errorf("expected block")
			}
			if !tt.blocked && result != "" {
				t.Errorf("expected allow, got: %s", result)
			}
		})
	}
}

func TestCheckYoloDiffReviewGuard(t *testing.T) {
	tests := []struct {
		name       string
		cmd        string
		yolo       bool
		diffRan    bool
		blocked    bool
	}{
		{"commit without diff in yolo blocks", "git commit -m 'x'", true, false, true},
		{"commit with diff in yolo allows", "git commit -m 'x'", true, true, false},
		{"commit outside yolo allows", "git commit -m 'x'", false, false, false},
		{"non-commit allows", "git add .", true, false, false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			event := &CloudEvent{
				ToolName:  "Bash",
				ToolInput: map[string]any{"command": tt.cmd},
			}
			result := checkYoloDiffReviewGuard(event, tt.yolo, tt.diffRan)
			if tt.blocked && result == "" {
				t.Errorf("expected block")
			}
			if !tt.blocked && result != "" {
				t.Errorf("expected allow, got: %s", result)
			}
		})
	}
}

func TestCheckYoloCodeHealthGuard(t *testing.T) {
	// This guard checks file content length after write — tested via integration
	// Unit test covers the skip conditions
	tests := []struct {
		name    string
		tool    string
		path    string
		yolo    bool
		blocked bool
	}{
		{"non-write allows", "Read", "foo.go", true, false},
		{"outside yolo allows", "Write", "foo.go", false, false},
		{"non-go file allows", "Write", "README.md", true, false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			event := &CloudEvent{
				ToolName:  tt.tool,
				ToolInput: map[string]any{"file_path": tt.path},
			}
			result := checkYoloCodeHealthGuard(event, tt.yolo)
			if tt.blocked && result == "" {
				t.Errorf("expected block")
			}
			if !tt.blocked && result != "" {
				t.Errorf("expected allow, got: %s", result)
			}
		})
	}
}

func TestCheckYoloBudgetGuard(t *testing.T) {
	tests := []struct {
		name    string
		tool    string
		cmd     string
		yolo    bool
		blocked bool
	}{
		{"non-commit allows", "Bash", "git add file.go", true, false},
		{"non-yolo allows", "Bash", "git commit -m 'foo'", false, false},
		{"non-bash allows", "Read", "git commit", true, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			event := &CloudEvent{
				ToolName:  tt.tool,
				ToolInput: map[string]any{"command": tt.cmd},
			}
			result := checkYoloBudgetGuard(event, tt.yolo)
			if tt.blocked && result == "" {
				t.Errorf("expected block")
			}
			if !tt.blocked && result != "" {
				t.Errorf("expected allow, got: %s", result)
			}
		})
	}
}
