package hooks

import "testing"

func TestCheckBashCwdGuard(t *testing.T) {
	tests := []struct {
		name    string
		tool    string
		cmd     string
		blocked bool
	}{
		{"bare cd blocks", "Bash", "cd packages/go && go build ./...", true},
		{"bare cd with spaces blocks", "Bash", "cd  packages/go && go test", true},
		{"subshell allowed", "Bash", "(cd packages/go && go build ./...)", false},
		{"no cd allowed", "Bash", "go build ./...", false},
		{"absolute path cd blocks", "Bash", "cd /tmp/foo && ls", true},
		{"cd alone no &&", "Bash", "cd packages/go", false},
		{"non-Bash tool ignored", "Read", "cd packages/go && cat file", false},
		{"empty command allowed", "Bash", "", false},
		{"semicolon cd allowed", "Bash", "echo hi; cd foo", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			event := &CloudEvent{
				ToolName:  tt.tool,
				ToolInput: map[string]any{"command": tt.cmd},
			}
			result := checkBashCwdGuard(event)
			if tt.blocked && result == "" {
				t.Errorf("expected block for %q, got allow", tt.cmd)
			}
			if !tt.blocked && result != "" {
				t.Errorf("expected allow for %q, got block: %s", tt.cmd, result)
			}
		})
	}
}
