package main

import (
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/spf13/cobra"
)

func yoloCmd() *cobra.Command {
	var dev, initMode, continueMode bool
	var permMode string

	cmd := &cobra.Command{
		Use:   "yolo",
		Short: "Launch Claude Code in autonomous YOLO mode with development guardrails",
		Long: `Launches Claude Code with bypassPermissions and enforced quality guardrails.

YOLO mode removes permission prompts but enforces code quality at every step:
  - Mandatory TDD workflow (tests before implementation)
  - Quality gate checks before every commit
  - Budget limits to keep features focused
  - Worktree-per-feature isolation

Each session is auto-named with a timestamp for easy identification.`,
		RunE: func(cmd *cobra.Command, args []string) error {
			switch {
			case dev:
				return launchYoloDev(args)
			case initMode:
				return launchYoloInit(args)
			case continueMode:
				return launchYoloContinue(args)
			default:
				return launchYoloDefault(permMode, args)
			}
		},
	}

	cmd.Flags().BoolVar(&dev, "dev", false, "Load plugin from local source (development mode)")
	cmd.Flags().BoolVar(&initMode, "init", false, "Initialize .htmlgraph/ then launch in YOLO mode")
	cmd.Flags().BoolVar(&continueMode, "continue", false, "Resume last YOLO session")
	cmd.Flags().StringVar(&permMode, "permission-mode", "bypassPermissions",
		"Permission mode (bypassPermissions, acceptEdits)")
	return cmd
}

// yoloSessionName returns a unique session name for YOLO mode.
func yoloSessionName() string {
	return fmt.Sprintf("yolo-%s", time.Now().UTC().Format("20060102-150405"))
}

// resolveYoloPromptFile returns the path to yolo-prompt.md inside the plugin config dir.
// Returns empty string if not found (prompt injection is best-effort).
func resolveYoloPromptFile(pluginDir string) string {
	if pluginDir == "" {
		return ""
	}
	path := filepath.Join(pluginDir, "config", "yolo-prompt.md")
	if _, err := os.Stat(path); err != nil {
		return ""
	}
	return path
}

func launchYoloDefault(permMode string, extraArgs []string) error {
	pluginDir := resolvePluginDir()
	projectRoot := ""
	if htmlgraphDir, err := findHtmlgraphDir(); err == nil {
		projectRoot = filepath.Dir(htmlgraphDir)
	}

	sessionName := yoloSessionName()
	yoloPrompt := resolveYoloPromptFile(pluginDir)

	fmt.Printf("Launching Claude Code in YOLO mode (%s)...\n", permMode)
	fmt.Printf("  Session: %s\n", sessionName)
	if yoloPrompt != "" {
		fmt.Printf("  Guardrails: %s\n", yoloPrompt)
	}

	return launchClaude(LaunchOpts{
		Mode:             "yolo",
		SystemPromptDir:  pluginDir,
		SystemPromptFile: yoloPrompt,
		PermissionMode:   permMode,
		Name:             sessionName,
		ExtraArgs:        extraArgs,
		ProjectRoot:      projectRoot,
	})
}

func launchYoloDev(extraArgs []string) error {
	pluginDir := resolvePluginDir()
	if pluginDir == "" {
		return fmt.Errorf("could not resolve Go plugin directory\nAre you running from the project root?")
	}
	if _, err := os.Stat(filepath.Join(pluginDir, ".claude-plugin", "plugin.json")); os.IsNotExist(err) {
		return fmt.Errorf("plugin.json not found at %s\nAre you running from the project root?",
			filepath.Join(pluginDir, ".claude-plugin", "plugin.json"))
	}
	if _, err := os.Stat(filepath.Join(pluginDir, "hooks", "bin", "htmlgraph")); os.IsNotExist(err) {
		return fmt.Errorf("Go hooks binary not found at %s\nBuild with: packages/go-plugin/build.sh",
			filepath.Join(pluginDir, "hooks", "bin", "htmlgraph"))
	}

	projectRoot := ""
	if htmlgraphDir, err := findHtmlgraphDir(); err == nil {
		projectRoot = filepath.Dir(htmlgraphDir)
	}

	fmt.Println("Disabling marketplace htmlgraph plugin...")
	for _, scope := range []string{"htmlgraph@htmlgraph", "htmlgraph@local-marketplace"} {
		exec.Command("claude", "plugin", "disable", scope).Run() //nolint:errcheck
	}

	restoreFn := stubProjectHooks(projectRoot)
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		restoreFn()
		os.Exit(0)
	}()

	sessionName := yoloSessionName()
	yoloPrompt := resolveYoloPromptFile(pluginDir)

	fmt.Printf("Launching Claude Code in YOLO dev mode...\n")
	fmt.Printf("  Plugin: %s\n", pluginDir)
	fmt.Printf("  Session: %s\n", sessionName)

	launchErr := launchClaude(LaunchOpts{
		Mode:             "yolo-dev",
		PluginDir:        pluginDir,
		SystemPromptFile: yoloPrompt,
		PermissionMode:   "bypassPermissions",
		Name:             sessionName,
		ExtraArgs:        extraArgs,
		ProjectRoot:      projectRoot,
	})
	restoreFn()
	return launchErr
}

func launchYoloInit(extraArgs []string) error {
	// Initialize .htmlgraph/ first.
	if err := runInit(nil, nil); err != nil {
		return fmt.Errorf("init failed: %w", err)
	}
	fmt.Println()
	return launchYoloDefault("bypassPermissions", extraArgs)
}

func launchYoloContinue(extraArgs []string) error {
	pluginDir := resolvePluginDir()
	projectRoot := ""
	if htmlgraphDir, err := findHtmlgraphDir(); err == nil {
		projectRoot = filepath.Dir(htmlgraphDir)
	}

	yoloPrompt := resolveYoloPromptFile(pluginDir)

	fmt.Println("Resuming last YOLO session...")

	return launchClaude(LaunchOpts{
		Mode:             "yolo-continue",
		Resume:           true,
		SystemPromptDir:  pluginDir,
		SystemPromptFile: yoloPrompt,
		PermissionMode:   "bypassPermissions",
		ExtraArgs:        extraArgs,
		ProjectRoot:      projectRoot,
	})
}
