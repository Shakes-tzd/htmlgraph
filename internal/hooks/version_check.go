package hooks

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// CLIVersion holds the binary's compiled version string (set via ldflags).
// The main package sets this before any hook handler is invoked so that
// session-start can compare it against the installed plugin version.
var CLIVersion = "dev"

// pluginManifest is a minimal representation of plugin.json used only to
// extract the version field.
type pluginManifest struct {
	Version string `json:"version"`
}

// readPluginVersion reads the plugin version from
// ${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json.
// Returns an empty string when CLAUDE_PLUGIN_ROOT is unset or the file is
// missing / unreadable.
func readPluginVersion() string {
	root := os.Getenv("CLAUDE_PLUGIN_ROOT")
	if root == "" {
		return ""
	}
	data, err := os.ReadFile(filepath.Join(root, ".claude-plugin", "plugin.json"))
	if err != nil {
		return ""
	}
	var manifest pluginManifest
	if err := json.Unmarshal(data, &manifest); err != nil {
		return ""
	}
	return manifest.Version
}

// versionMismatchWarning returns a warning string when the CLI version and
// plugin version differ (and neither is "dev"). Returns an empty string when
// the versions match or when the check is skipped.
func versionMismatchWarning() string {
	cli := CLIVersion
	plugin := readPluginVersion()

	// Skip check when running from a dev build or when the plugin version
	// cannot be determined.
	if cli == "dev" || plugin == "dev" || plugin == "" {
		return ""
	}

	if cli == plugin {
		return ""
	}

	return fmt.Sprintf(
		"HtmlGraph version mismatch: CLI v%s != plugin v%s\nRun `htmlgraph build` to sync, or update the plugin.",
		cli, plugin,
	)
}
