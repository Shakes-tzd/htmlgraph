package main

import (
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"html"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/shakestzd/htmlgraph/internal/htmlparse"
	"github.com/spf13/cobra"
)

//go:embed templates/plan-template.html
var planTemplateFS embed.FS

// planCmdWithExtras builds the standard workitem commands for plans,
// then adds CRISPI-specific subcommands: generate, open, wait, read-feedback.
func planCmdWithExtras() *cobra.Command {
	cmd := workitemCmd("plan", "plans")
	cmd.AddCommand(planGenerateCmd())
	cmd.AddCommand(planOpenCmd())
	cmd.AddCommand(planWaitCmd())
	cmd.AddCommand(planReadFeedbackCmd())
	return cmd
}

// planGenerateCmd scaffolds a plan HTML file from a feature or track ID.
func planGenerateCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "generate <feature-or-track-id>",
		Short: "Scaffold a plan HTML file from a feature or track",
		Args:  cobra.ExactArgs(1),
		RunE: func(_ *cobra.Command, args []string) error {
			return runPlanGenerate(args[0])
		},
	}
}

func runPlanGenerate(sourceID string) error {
	htmlgraphDir, err := findHtmlgraphDir()
	if err != nil {
		return err
	}

	resolved, err := resolveID(htmlgraphDir, sourceID)
	if err != nil {
		return fmt.Errorf("resolve %s: %w", sourceID, err)
	}
	nodePath := resolveNodePath(htmlgraphDir, resolved)
	if nodePath == "" {
		return fmt.Errorf("work item %q not found", resolved)
	}

	info, err := parseNodeForPlan(nodePath)
	if err != nil {
		return fmt.Errorf("parse work item: %w", err)
	}

	planID := derivePlanID(info.title)
	plansDir := filepath.Join(htmlgraphDir, "plans")
	if err := os.MkdirAll(plansDir, 0o755); err != nil {
		return fmt.Errorf("create plans dir: %w", err)
	}
	outPath := filepath.Join(plansDir, planID+".html")

	tmplData, err := planTemplateFS.ReadFile("templates/plan-template.html")
	if err != nil {
		return fmt.Errorf("read plan template: %w", err)
	}

	graphNodes, sliceCards, sectionsJSON, totalSections := buildPlanSections(nodePath)

	content := applyPlanTemplateVars(string(tmplData), planTemplateVars{
		PlanID:        planID,
		FeatureID:     resolved,
		Title:         info.title,
		Description:   info.description,
		Date:          time.Now().UTC().Format("2006-01-02"),
		GraphNodes:    graphNodes,
		SliceCards:    sliceCards,
		SectionsJSON:  sectionsJSON,
		TotalSections: totalSections,
	})

	if err := os.WriteFile(outPath, []byte(content), 0o644); err != nil {
		return fmt.Errorf("write plan: %w", err)
	}

	fmt.Println(outPath)
	return nil
}

// planOpenCmd opens a plan in the browser.
func planOpenCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "open <plan-id>",
		Short: "Open a plan in the browser",
		Args:  cobra.ExactArgs(1),
		RunE: func(_ *cobra.Command, args []string) error {
			return runPlanOpen(args[0])
		},
	}
}

func runPlanOpen(planID string) error {
	htmlgraphDir, err := findHtmlgraphDir()
	if err != nil {
		return err
	}

	if isServerRunning("http://localhost:8080") {
		url := "http://localhost:8080/plans/" + planID + ".html"
		return openBrowser(url)
	}

	planPath := filepath.Join(htmlgraphDir, "plans", planID+".html")
	if _, err := os.Stat(planPath); err != nil {
		return fmt.Errorf("plan %q not found at %s", planID, planPath)
	}
	return openBrowser(planPath)
}

// planWaitCmd blocks until a plan is finalized.
func planWaitCmd() *cobra.Command {
	var timeout time.Duration

	cmd := &cobra.Command{
		Use:   "wait <plan-id>",
		Short: "Block until a plan is finalized",
		Args:  cobra.ExactArgs(1),
		RunE: func(_ *cobra.Command, args []string) error {
			return runPlanWait(args[0], timeout)
		},
	}
	cmd.Flags().DurationVar(&timeout, "timeout", time.Hour, "Maximum wait time (e.g. 30m, 1h)")
	return cmd
}

func runPlanWait(planID string, timeout time.Duration) error {
	htmlgraphDir, err := findHtmlgraphDir()
	if err != nil {
		return err
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	fmt.Printf("Waiting for plan %s to be finalized", planID)

	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			fmt.Println()
			return fmt.Errorf("timeout: plan %s was not finalized within %s", planID, timeout)
		case <-ticker.C:
			finalized, err := checkPlanFinalized(htmlgraphDir, planID)
			if err != nil {
				fmt.Print(".")
				continue
			}
			if finalized {
				fmt.Println("\nPlan finalized.")
				return nil
			}
			fmt.Print(".")
		}
	}
}

// checkPlanFinalized returns true when the plan's status is "finalized".
// Prefers the live API; falls back to reading the HTML file directly.
func checkPlanFinalized(htmlgraphDir, planID string) (bool, error) {
	if isServerRunning("http://localhost:8080") {
		status, err := fetchPlanStatusFromAPI(planID)
		if err == nil {
			return status == "finalized", nil
		}
	}

	planPath := filepath.Join(htmlgraphDir, "plans", planID+".html")
	status, err := parsePlanHTMLStatus(planPath)
	if err != nil {
		return false, err
	}
	return status == "finalized", nil
}

// fetchPlanStatusFromAPI calls GET /api/plans/{id}/status and returns the status.
func fetchPlanStatusFromAPI(planID string) (string, error) {
	url := "http://localhost:8080/api/plans/" + planID + "/status"
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(url) //nolint:gosec,noctx
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("API returned %d", resp.StatusCode)
	}
	var result struct {
		Status string `json:"status"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}
	return result.Status, nil
}

// ---- plan template helpers --------------------------------------------------

type planNodeInfo struct {
	title       string
	description string
}

// parseNodeForPlan reads a work item HTML file and returns its title and description.
func parseNodeForPlan(nodePath string) (planNodeInfo, error) {
	data, err := os.ReadFile(nodePath)
	if err != nil {
		return planNodeInfo{}, err
	}
	return extractPlanNodeInfo(string(data)), nil
}

// extractPlanNodeInfo extracts title and description from raw HTML using
// simple string scanning — keeps this file free of goquery import.
func extractPlanNodeInfo(html string) planNodeInfo {
	info := planNodeInfo{}

	if start := strings.Index(html, "<h1>"); start >= 0 {
		rest := html[start+4:]
		if end := strings.Index(rest, "</h1>"); end >= 0 {
			info.title = strings.TrimSpace(rest[:end])
		}
	}

	if s := strings.Index(html, `data-content`); s >= 0 {
		rest := html[s:]
		if p := strings.Index(rest, "<p>"); p >= 0 {
			rest2 := rest[p+3:]
			if e := strings.Index(rest2, "</p>"); e >= 0 {
				info.description = strings.TrimSpace(rest2[:e])
			}
		}
	}

	return info
}

type planTemplateVars struct {
	PlanID        string
	FeatureID     string
	Title         string
	Description   string
	Date          string
	GraphNodes    string // HTML for <!--PLAN_GRAPH_NODES-->
	SliceCards    string // HTML for <!--PLAN_SLICE_CARDS-->
	SectionsJSON  string // JS array literal for /*PLAN_SECTIONS_JSON*/
	TotalSections string // integer string for <!--PLAN_TOTAL_SECTIONS-->
}

// applyPlanTemplateVars replaces placeholder values in the template HTML
// with real values from the source work item.
func applyPlanTemplateVars(tmpl string, v planTemplateVars) string {
	tmpl = strings.ReplaceAll(tmpl, "plan-webhook-support", v.PlanID)
	tmpl = strings.ReplaceAll(tmpl, "feat-xxx", v.FeatureID)
	// Ensure article uses id= (htmlparse expects it), fixing any stale data-plan-id= from cache.
	tmpl = strings.Replace(tmpl, `data-plan-id="`+v.PlanID+`"`, `id="`+v.PlanID+`"`, 1)
	tmpl = strings.ReplaceAll(tmpl, "Plan: Webhook Support", "Plan: "+v.Title)
	tmpl = strings.ReplaceAll(tmpl, "Webhook Support", v.Title)

	const sampleDesc = "HTTP POST notifications for HtmlGraph events with retry and config management."
	if v.Description != "" {
		tmpl = strings.ReplaceAll(tmpl, sampleDesc, v.Description)
	}

	tmpl = strings.ReplaceAll(tmpl, "2026-04-01", v.Date)

	if v.GraphNodes != "" {
		tmpl = strings.ReplaceAll(tmpl, "<!--PLAN_GRAPH_NODES-->", v.GraphNodes)
	}
	if v.SliceCards != "" {
		tmpl = strings.ReplaceAll(tmpl, "<!--PLAN_SLICE_CARDS-->", v.SliceCards)
	}
	if v.TotalSections != "" {
		tmpl = strings.ReplaceAll(tmpl, "<!--PLAN_TOTAL_SECTIONS-->", v.TotalSections)
	}
	if v.SectionsJSON != "" {
		// Replace the default array between the JS markers.
		const start = "/*PLAN_SECTIONS_JSON*/"
		const end = "/*END_PLAN_SECTIONS_JSON*/"
		if si := strings.Index(tmpl, start); si >= 0 {
			if ei := strings.Index(tmpl[si:], end); ei >= 0 {
				tmpl = tmpl[:si+len(start)] + v.SectionsJSON + tmpl[si+ei:]
			}
		}
	}

	return tmpl
}

// planFeature holds the data needed to render one slice card and graph node.
type planFeature struct {
	num   int
	id    string
	title string
}

// buildPlanSections parses the source node for "contains" edges and generates
// graph node HTML, slice card HTML, sections JSON, and total section count.
// Falls back to empty strings (leaving template placeholders intact) on any error.
func buildPlanSections(nodePath string) (graphNodes, sliceCards, sectionsJSON, totalSections string) {
	node, err := htmlparse.ParseFile(nodePath)
	if err != nil {
		return
	}

	containsEdges := node.Edges["contains"]
	if len(containsEdges) == 0 {
		return
	}

	features := make([]planFeature, 0, len(containsEdges))
	for i, edge := range containsEdges {
		title := strings.TrimSpace(edge.Title)
		if title == "" {
			title = edge.TargetID
		}
		// Truncate overly long edge titles for display.
		if len(title) > 60 {
			title = title[:57] + "..."
		}
		features = append(features, planFeature{num: i + 1, id: edge.TargetID, title: title})
	}

	// Build graph nodes HTML.
	var gnBuf strings.Builder
	for _, f := range features {
		gnBuf.WriteString(fmt.Sprintf(
			`    <div data-node="%d" data-name="%s" data-files="0" data-status="pending" data-deps=""></div>`+"\n",
			f.num, html.EscapeString(f.title),
		))
	}
	graphNodes = gnBuf.String()

	// Build slice cards HTML.
	var scBuf strings.Builder
	for _, f := range features {
		n := f.num
		scBuf.WriteString(fmt.Sprintf(
			`    <div class="slice-card" data-slice="%d" data-slice-name="%s" data-status="pending" data-files="0">`+"\n",
			n, html.EscapeString(f.id),
		))
		scBuf.WriteString(fmt.Sprintf(
			`      <div class="slice-header"><span class="slice-num">#%d</span><span class="slice-name">%s</span><span class="badge badge-pending" data-badge-for="slice-%d">Pending</span></div>`+"\n",
			n, html.EscapeString(f.title), n,
		))
		scBuf.WriteString(fmt.Sprintf(
			`      <div class="slice-meta"><span>%s</span></div>`+"\n",
			html.EscapeString(f.id),
		))
		scBuf.WriteString("      <h4>Test Strategy</h4>\n")
		scBuf.WriteString("      <ul><li>Add test strategy here</li></ul>\n")
		scBuf.WriteString(`      <p style="font-size:.8rem;color:var(--text-muted);margin-top:6px">Dependencies: none</p>` + "\n")
		scBuf.WriteString(fmt.Sprintf(
			`      <div class="approval-row"><label><input type="checkbox" data-section="slice-%d" data-action="approve"> Approve slice</label><textarea data-section="slice-%d" data-comment-for="slice-%d" placeholder="Comments on slice %d..."></textarea></div>`+"\n",
			n, n, n, n,
		))
		scBuf.WriteString("    </div>\n")
	}
	sliceCards = scBuf.String()

	// Build sections JSON array: ["design","outline","slice-1","slice-2",...]
	sections := []string{"design", "outline"}
	for _, f := range features {
		sections = append(sections, fmt.Sprintf("slice-%d", f.num))
	}
	sectionStrs := make([]string, len(sections))
	for i, s := range sections {
		sectionStrs[i] = `"` + s + `"`
	}
	sectionsJSON = "[" + strings.Join(sectionStrs, ",") + "]"
	totalSections = fmt.Sprintf("%d", len(sections))
	return
}

// derivePlanID builds a kebab-case plan file ID from the work item title.
func derivePlanID(title string) string {
	if title == "" {
		return "plan-untitled"
	}
	slug := strings.ToLower(title)
	var b strings.Builder
	prevDash := false
	for _, r := range slug {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			b.WriteRune(r)
			prevDash = false
		} else if !prevDash {
			b.WriteRune('-')
			prevDash = true
		}
	}
	result := strings.Trim(b.String(), "-")
	if len(result) > 40 {
		result = strings.TrimRight(result[:40], "-")
	}
	return "plan-" + result
}

// ---- browser / server helpers -----------------------------------------------

// isServerRunning returns true when a GET to baseURL succeeds within 500ms.
func isServerRunning(baseURL string) bool {
	client := &http.Client{Timeout: 500 * time.Millisecond}
	resp, err := client.Get(baseURL) //nolint:gosec,noctx
	if err != nil {
		return false
	}
	resp.Body.Close()
	return resp.StatusCode < 500
}

// openBrowser opens the given URL or file path in the default OS browser.
func openBrowser(target string) error {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "darwin":
		cmd = exec.Command("open", target)
	case "linux":
		cmd = exec.Command("xdg-open", target)
	default:
		fmt.Println(target)
		return nil
	}
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("open browser: %w", err)
	}
	return nil
}
