package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/spf13/cobra"
)

func buildCmd() *cobra.Command {
	var dist bool

	cmd := &cobra.Command{
		Use:   "build",
		Short: "Rebuild the htmlgraph binary",
		Long:  "Rebuild the htmlgraph Go binary using the build script in the plugin directory.",
		RunE: func(cmd *cobra.Command, args []string) error {
			buildScript, err := resolveBuildScript()
			if err != nil {
				return err
			}

			var c *exec.Cmd
			if dist {
				c = exec.Command("sh", buildScript, "--dist")
			} else {
				c = exec.Command("sh", buildScript)
			}
			c.Stdout = os.Stdout
			c.Stderr = os.Stderr
			return c.Run()
		},
	}
	cmd.Flags().BoolVar(&dist, "dist", false, "Build for distribution (bootstrap entry point + binary)")
	return cmd
}

// resolveBuildScript finds build.sh relative to the running binary.
// The binary lives at packages/go-plugin/hooks/bin/htmlgraph;
// build.sh is two levels up at packages/go-plugin/build.sh.
func resolveBuildScript() (string, error) {
	binPath, err := os.Executable()
	if err != nil {
		return "", fmt.Errorf("finding executable path: %w", err)
	}
	binDir := filepath.Dir(binPath)
	script := filepath.Join(binDir, "..", "..", "build.sh")
	abs, err := filepath.Abs(script)
	if err != nil {
		return "", fmt.Errorf("resolving build script path: %w", err)
	}
	if _, err := os.Stat(abs); os.IsNotExist(err) {
		return "", fmt.Errorf("build script not found at %s\nAre you running the binary from packages/go-plugin/hooks/bin/?", abs)
	}
	return abs, nil
}
