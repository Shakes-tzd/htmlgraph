package main

import (
	"fmt"
	"html"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/shakestzd/htmlgraph/internal/workitem"
	"github.com/spf13/cobra"
)

// planCreateFromTopicCmd creates a CRISPI plan HTML directly from a topic,
// without requiring a pre-existing track or feature.
func planCreateFromTopicCmd() *cobra.Command {
	var description string
	cmd := &cobra.Command{
		Use:   "create <title>",
		Short: "Create an interactive plan from a topic",
		Long: `Create a CRISPI plan HTML file from a title and optional description.

Unlike 'plan generate' (which scaffolds from an existing work item), this
creates a standalone plan for design-first workflows. Add slices with
'plan add-slice', questions with 'plan add-question', then review and finalize.

Example:
  htmlgraph plan create "Auth Middleware Rewrite" --description "Rewrite for compliance"`,
		Args: cobra.ExactArgs(1),
		RunE: func(_ *cobra.Command, args []string) error {
			htmlgraphDir, err := findHtmlgraphDir()
			if err != nil {
				return err
			}
			planID, err := createPlanFromTopic(htmlgraphDir, args[0], description)
			if err != nil {
				return err
			}
			planPath := filepath.Join(htmlgraphDir, "plans", planID+".html")
			fmt.Println(planPath)
			return nil
		},
	}
	cmd.Flags().StringVar(&description, "description", "", "plan description")
	return cmd
}

// createPlanFromTopic generates a CRISPI plan HTML file from a topic title.
// Returns the plan ID (e.g. plan-a1b2c3d4).
func createPlanFromTopic(htmlgraphDir, title, description string) (string, error) {
	if title == "" {
		return "", fmt.Errorf("plan title must not be empty")
	}

	planID := workitem.GenerateID("plan", title)
	plansDir := filepath.Join(htmlgraphDir, "plans")
	if err := os.MkdirAll(plansDir, 0o755); err != nil {
		return "", fmt.Errorf("create plans dir: %w", err)
	}

	tmplData, err := planTemplateFS.ReadFile("templates/plan-template.html")
	if err != nil {
		return "", fmt.Errorf("read plan template: %w", err)
	}

	date := time.Now().UTC().Format("2006-01-02")
	content := applyPlanTemplateVars(string(tmplData), planTemplateVars{
		PlanID:      planID,
		FeatureID:   "",
		Title:       title,
		Description: description,
		Date:        date,
	})

	// Remove the feat-xxx placeholder since this plan has no linked feature.
	content = strings.ReplaceAll(content, `data-feature-id="feat-xxx"`, `data-feature-id=""`)
	// Clean up default sections JSON for an empty plan (just design + outline).
	content = replaceSectionsJSON(content, `["design","outline"]`)

	outPath := filepath.Join(plansDir, planID+".html")
	if err := os.WriteFile(outPath, []byte(content), 0o644); err != nil {
		return "", fmt.Errorf("write plan: %w", err)
	}

	return planID, nil
}

// replaceSectionsJSON replaces the PLAN_SECTIONS_JSON block with new content.
func replaceSectionsJSON(content, newJSON string) string {
	const start = "/*PLAN_SECTIONS_JSON*/"
	const end = "/*END_PLAN_SECTIONS_JSON*/"
	si := strings.Index(content, start)
	if si < 0 {
		return content
	}
	ei := strings.Index(content[si:], end)
	if ei < 0 {
		return content
	}
	return content[:si+len(start)] + newJSON + content[si+ei:]
}

// ---- plan add-slice ---------------------------------------------------------

// planAddSliceCmd adds a new vertical slice to an existing plan.
func planAddSliceCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "add-slice <plan-id> <title>",
		Short: "Add a vertical slice to a plan",
		Long: `Add a new slice card and graph node to an existing plan.

The slice is assigned the next available number. Use set-slice to
update its test strategy, dependencies, and files afterward.

Example:
  htmlgraph plan add-slice plan-a1b2c3d4 "Implement error handling"`,
		Args: cobra.ExactArgs(2),
		RunE: func(_ *cobra.Command, args []string) error {
			htmlgraphDir, err := findHtmlgraphDir()
			if err != nil {
				return err
			}
			return addSliceToPlan(htmlgraphDir, args[0], args[1])
		},
	}
}

// addSliceToPlan injects a new slice card and graph node into a plan HTML file.
func addSliceToPlan(htmlgraphDir, planID, sliceTitle string) error {
	planPath := filepath.Join(htmlgraphDir, "plans", planID+".html")
	data, err := os.ReadFile(planPath)
	if err != nil {
		return fmt.Errorf("plan %q not found: %w", planID, err)
	}
	content := string(data)

	// Determine next slice number by counting existing data-slice= attributes.
	nextNum := 1
	for i := 1; ; i++ {
		if !strings.Contains(content, fmt.Sprintf(`data-slice="%d"`, i)) {
			nextNum = i
			break
		}
	}

	escapedTitle := html.EscapeString(sliceTitle)

	// Build graph node HTML.
	graphNode := fmt.Sprintf(
		`    <div data-node="%d" data-name="%s" data-status="pending" data-deps=""></div>`,
		nextNum, escapedTitle,
	)

	// Build slice card HTML.
	sliceCard := buildSliceCardHTML(nextNum, escapedTitle)

	// Inject graph node before PLAN_GRAPH_NODES marker.
	if strings.Contains(content, "<!--PLAN_GRAPH_NODES-->") {
		content = strings.Replace(content, "<!--PLAN_GRAPH_NODES-->",
			graphNode+"\n    <!--PLAN_GRAPH_NODES-->", 1)
	}

	// Inject slice card before PLAN_SLICE_CARDS marker.
	if strings.Contains(content, "<!--PLAN_SLICE_CARDS-->") {
		content = strings.Replace(content, "<!--PLAN_SLICE_CARDS-->",
			sliceCard+"\n    <!--PLAN_SLICE_CARDS-->", 1)
	}

	// Update sections JSON to include the new slice.
	content = addSliceToSectionsJSON(content, nextNum)

	// Update total sections and meta.
	content = updatePlanCounts(content, nextNum)

	if err := os.WriteFile(planPath, []byte(content), 0o644); err != nil {
		return err
	}

	fmt.Printf("Added slice #%d: %s\n", nextNum, sliceTitle)
	return nil
}

func buildSliceCardHTML(num int, escapedTitle string) string {
	var b strings.Builder
	b.WriteString(fmt.Sprintf(
		`    <div class="slice-card" data-slice="%d" data-slice-name="" data-status="pending">`+"\n",
		num,
	))
	b.WriteString(fmt.Sprintf(
		`      <div class="slice-header"><span class="slice-num">#%d</span><span class="slice-name">%s</span><span class="badge badge-pending" data-badge-for="slice-%d">Pending</span></div>`+"\n",
		num, escapedTitle, num,
	))
	b.WriteString("      <h4>Test Strategy</h4>\n")
	b.WriteString("      <ul><li>Add test strategy here</li></ul>\n")
	b.WriteString(`      <p style="font-size:.8rem;color:var(--text-muted);margin-top:6px">Dependencies: none</p>` + "\n")
	b.WriteString(fmt.Sprintf(
		`      <div class="approval-row"><label><input type="checkbox" data-section="slice-%d" data-action="approve"> Approve slice</label><textarea data-section="slice-%d" data-comment-for="slice-%d" placeholder="Comments on slice %d..."></textarea></div>`+"\n",
		num, num, num, num,
	))
	b.WriteString("    </div>")
	return b.String()
}

// addSliceToSectionsJSON adds a new slice entry to the SECTIONS array.
func addSliceToSectionsJSON(content string, sliceNum int) string {
	const start = "/*PLAN_SECTIONS_JSON*/"
	const end = "/*END_PLAN_SECTIONS_JSON*/"
	si := strings.Index(content, start)
	if si < 0 {
		return content
	}
	afterStart := content[si+len(start):]
	ei := strings.Index(afterStart, end)
	if ei < 0 {
		return content
	}

	currentJSON := strings.TrimSpace(afterStart[:ei])
	newEntry := fmt.Sprintf(`"slice-%d"`, sliceNum)

	// Insert before the closing bracket.
	if idx := strings.LastIndex(currentJSON, "]"); idx >= 0 {
		inner := strings.TrimSpace(currentJSON[1:idx])
		if inner == "" {
			currentJSON = "[" + newEntry + "]"
		} else {
			currentJSON = "[" + inner + "," + newEntry + "]"
		}
	}

	return content[:si+len(start)] + currentJSON + content[si+len(start)+ei:]
}

// updatePlanCounts updates the total section count displays in the plan HTML.
func updatePlanCounts(content string, maxSlice int) string {
	totalSections := 2 + maxSlice // design + outline + slices
	totalStr := fmt.Sprintf("%d", totalSections)

	// Update the totalSections and pendingCount spans.
	// These appear as: <strong id="totalSections">N</strong>
	// and <strong id="pendingCount">N</strong>
	for _, id := range []string{"totalSections", "pendingCount"} {
		marker := fmt.Sprintf(`<strong id="%s">`, id)
		if idx := strings.Index(content, marker); idx >= 0 {
			after := content[idx+len(marker):]
			if end := strings.Index(after, "</strong>"); end >= 0 {
				content = content[:idx+len(marker)] + totalStr + content[idx+len(marker)+end:]
			}
		}
	}
	return content
}
