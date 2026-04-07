package hooks

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// writePluginJSON creates a plugin.json with the given version in a temporary
// directory and returns the plugin root path.
func writePluginJSON(t *testing.T, version string) string {
	t.Helper()
	root := t.TempDir()
	dir := filepath.Join(root, ".claude-plugin")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatalf("mkdir .claude-plugin: %v", err)
	}
	data, err := json.Marshal(map[string]string{"version": version})
	if err != nil {
		t.Fatalf("marshal plugin.json: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dir, "plugin.json"), data, 0o644); err != nil {
		t.Fatalf("write plugin.json: %v", err)
	}
	return root
}

func TestVersionMismatchWarning_Match(t *testing.T) {
	root := writePluginJSON(t, "0.48.1")
	t.Setenv("CLAUDE_PLUGIN_ROOT", root)

	origCLI := CLIVersion
	CLIVersion = "0.48.1"
	defer func() { CLIVersion = origCLI }()

	if got := versionMismatchWarning(); got != "" {
		t.Errorf("expected no warning for matching versions, got %q", got)
	}
}

func TestVersionMismatchWarning_Mismatch(t *testing.T) {
	root := writePluginJSON(t, "0.47.0")
	t.Setenv("CLAUDE_PLUGIN_ROOT", root)

	origCLI := CLIVersion
	CLIVersion = "0.48.1"
	defer func() { CLIVersion = origCLI }()

	got := versionMismatchWarning()
	if got == "" {
		t.Error("expected a mismatch warning, got empty string")
	}
	if want := "CLI v0.48.1 != plugin v0.47.0"; !containsString(got, want) {
		t.Errorf("warning %q does not contain %q", got, want)
	}
}

func TestVersionMismatchWarning_DevCLI(t *testing.T) {
	root := writePluginJSON(t, "0.47.0")
	t.Setenv("CLAUDE_PLUGIN_ROOT", root)

	origCLI := CLIVersion
	CLIVersion = "dev"
	defer func() { CLIVersion = origCLI }()

	if got := versionMismatchWarning(); got != "" {
		t.Errorf("expected no warning for dev CLI, got %q", got)
	}
}

func TestVersionMismatchWarning_DevPlugin(t *testing.T) {
	root := writePluginJSON(t, "dev")
	t.Setenv("CLAUDE_PLUGIN_ROOT", root)

	origCLI := CLIVersion
	CLIVersion = "0.48.1"
	defer func() { CLIVersion = origCLI }()

	if got := versionMismatchWarning(); got != "" {
		t.Errorf("expected no warning for dev plugin, got %q", got)
	}
}

func TestVersionMismatchWarning_NoPluginRoot(t *testing.T) {
	t.Setenv("CLAUDE_PLUGIN_ROOT", "")

	origCLI := CLIVersion
	CLIVersion = "0.48.1"
	defer func() { CLIVersion = origCLI }()

	if got := versionMismatchWarning(); got != "" {
		t.Errorf("expected no warning when CLAUDE_PLUGIN_ROOT is unset, got %q", got)
	}
}

// containsString reports whether s contains sub.
func containsString(s, sub string) bool {
	return len(s) >= len(sub) && func() bool {
		for i := 0; i <= len(s)-len(sub); i++ {
			if s[i:i+len(sub)] == sub {
				return true
			}
		}
		return false
	}()
}
