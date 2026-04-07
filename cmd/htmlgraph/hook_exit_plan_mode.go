package main

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/shakestzd/htmlgraph/internal/hooks"
	"github.com/shakestzd/htmlgraph/internal/planyaml"
	"github.com/shakestzd/htmlgraph/internal/workitem"
)

// handleExitPlanMode handles the PostToolUse ExitPlanMode event. It finds the
// most recently modified markdown file in .htmlgraph/plans/, parses it into a
// best-effort CRISPI YAML plan, saves it, and suggests a review command.
//
// This handler lives in cmd/htmlgraph (not internal/hooks) because the hooks
// package must not import workitem (spike creation policy). The markdown-to-YAML
// conversion uses workitem.GenerateID and planyaml.NewPlan/Save.
func handleExitPlanMode(event *hooks.CloudEvent, database *sql.DB, projectDir string) (*hooks.HookResult, error) {
	plansDir := filepath.Join(projectDir, ".htmlgraph", "plans")

	mdPath, err := mostRecentMarkdownFile(plansDir)
	if err != nil {
		hooks.LogError("exit-plan-mode", event.SessionID, fmt.Sprintf("no markdown plan found: %v", err))
		return &hooks.HookResult{Continue: true}, nil
	}

	data, err := os.ReadFile(mdPath)
	if err != nil {
		hooks.LogError("exit-plan-mode", event.SessionID, fmt.Sprintf("cannot read %s: %v", mdPath, err))
		return &hooks.HookResult{Continue: true}, nil
	}

	title, description := extractPlanTitleFromMarkdown(string(data))
	if title == "" {
		title = strings.TrimSuffix(filepath.Base(mdPath), ".md")
	}

	planID := workitem.GenerateID("plan", title)
	plan := planyaml.NewPlan(planID, title, description)

	slices := parseMarkdownToSlices(string(data))
	plan.Slices = slices

	if err := os.MkdirAll(plansDir, 0o755); err != nil {
		hooks.LogError("exit-plan-mode", event.SessionID, fmt.Sprintf("mkdir plans: %v", err))
		return &hooks.HookResult{Continue: true}, nil
	}

	yamlPath := filepath.Join(plansDir, planID+".yaml")
	if err := planyaml.Save(yamlPath, plan); err != nil {
		hooks.LogError("exit-plan-mode", event.SessionID, fmt.Sprintf("save YAML: %v", err))
		return &hooks.HookResult{Continue: true}, nil
	}

	commitPlanChange(yamlPath, fmt.Sprintf("plan(%s): auto-convert from plan mode — %s", planID, title))

	suggestion := fmt.Sprintf(
		"Plan mode output converted to CRISPI YAML: %s\nRun: htmlgraph plan review %s",
		yamlPath, planID)

	return &hooks.HookResult{
		Continue:          true,
		AdditionalContext: suggestion,
	}, nil
}

// mostRecentMarkdownFile returns the path to the most recently modified .md
// file in the given directory. Returns an error if no markdown files exist.
func mostRecentMarkdownFile(dir string) (string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return "", fmt.Errorf("read plans dir: %w", err)
	}

	var bestPath string
	var bestTime time.Time

	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".md") {
			continue
		}
		info, err := e.Info()
		if err != nil {
			continue
		}
		if info.ModTime().After(bestTime) {
			bestTime = info.ModTime()
			bestPath = filepath.Join(dir, e.Name())
		}
	}

	if bestPath == "" {
		return "", fmt.Errorf("no .md files in %s", dir)
	}
	return bestPath, nil
}

// extractPlanTitleFromMarkdown extracts the first H1 heading as the plan
// title and the first non-heading paragraph after it as the description.
func extractPlanTitleFromMarkdown(content string) (title, description string) {
	lines := strings.Split(content, "\n")
	titleFound := false

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		if !titleFound && strings.HasPrefix(trimmed, "# ") {
			title = strings.TrimSpace(strings.TrimPrefix(trimmed, "# "))
			titleFound = true
			continue
		}

		if titleFound && description == "" && trimmed != "" && !strings.HasPrefix(trimmed, "#") {
			description = trimmed
			break
		}
	}
	return title, description
}

// mdFilePathPattern matches file paths mentioned in markdown text. Looks for
// paths with slashes or common source file extensions.
var mdFilePathPattern = regexp.MustCompile(`(?:^|\s)([\w./\-]+\.(?:go|py|ts|tsx|js|jsx|yaml|yml|json|html|css|sql|sh|toml|mod))`)

// parseMarkdownToSlices parses markdown headings and their content into
// PlanSlice structs. Each H2 or H3 heading becomes a slice. Bullet lists
// under headings populate the "what" field. File paths mentioned in text
// populate the "files" field. Defaults: effort=M, risk=Med, approved=false.
func parseMarkdownToSlices(content string) []planyaml.PlanSlice {
	lines := strings.Split(content, "\n")
	var slices []planyaml.PlanSlice

	var currentTitle string
	var currentWhat []string
	var currentFiles []string
	filesSeen := map[string]bool{}
	sliceNum := 0

	flushSlice := func() {
		if currentTitle == "" {
			return
		}
		sliceNum++
		what := strings.Join(currentWhat, "\n")
		if what == "" {
			what = currentTitle
		}
		slices = append(slices, planyaml.PlanSlice{
			ID:       workitem.GenerateID("feat", currentTitle),
			Num:      sliceNum,
			Title:    currentTitle,
			What:     strings.TrimSpace(what),
			Files:    currentFiles,
			Effort:   "M",
			Risk:     "Med",
			Approved: false,
		})
		currentTitle = ""
		currentWhat = nil
		currentFiles = nil
		filesSeen = map[string]bool{}
	}

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)

		// Detect H2/H3 headings as slice boundaries.
		if strings.HasPrefix(trimmed, "## ") || strings.HasPrefix(trimmed, "### ") {
			flushSlice()
			currentTitle = strings.TrimSpace(strings.TrimLeft(trimmed, "# "))
			continue
		}

		// Skip H1 (plan title).
		if strings.HasPrefix(trimmed, "# ") {
			continue
		}

		// Accumulate bullet items as "what" content.
		if strings.HasPrefix(trimmed, "- ") || strings.HasPrefix(trimmed, "* ") {
			item := strings.TrimSpace(trimmed[2:])
			currentWhat = append(currentWhat, item)
		} else if trimmed != "" && currentTitle != "" {
			currentWhat = append(currentWhat, trimmed)
		}

		// Extract file paths.
		for _, match := range mdFilePathPattern.FindAllStringSubmatch(line, -1) {
			if len(match) > 1 && !filesSeen[match[1]] {
				filesSeen[match[1]] = true
				currentFiles = append(currentFiles, match[1])
			}
		}
	}

	flushSlice()
	return slices
}
