package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"github.com/spf13/cobra"
)

// critiqueOutput is the structured JSON output from plan critique.
type critiqueOutput struct {
	PlanID            string          `json:"plan_id"`
	Title             string          `json:"title"`
	Description       string          `json:"description,omitempty"`
	Status            string          `json:"status"`
	Complexity        string          `json:"complexity"`
	SliceCount        int             `json:"slice_count"`
	CritiqueWarranted bool            `json:"critique_warranted"`
	Slices            []critiqueSlice `json:"slices,omitempty"`
	Questions         []critiqueQ     `json:"questions,omitempty"`
	DesignSummary     string          `json:"design_summary,omitempty"`
}

type critiqueSlice struct {
	Number       int      `json:"number"`
	Title        string   `json:"title"`
	Status       string   `json:"status"`
	Dependencies []int    `json:"dependencies"`
	TestStrategy string   `json:"test_strategy,omitempty"`
}

type critiqueQ struct {
	ID     string `json:"id"`
	Text   string `json:"text"`
	Answer string `json:"answer,omitempty"`
	Status string `json:"status"`
}

// planCritiqueCmd extracts plan content for AI critique.
func planCritiqueCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "critique <plan-id>",
		Short: "Extract plan content for AI review",
		Long: `Read a plan and output structured JSON for AI critique.

Complexity-gated: plans with fewer than 3 slices output
critique_warranted=false. The output is designed to be piped to
AI review tools.

Example:
  htmlgraph plan critique plan-a1b2c3d4`,
		Args: cobra.ExactArgs(1),
		RunE: func(_ *cobra.Command, args []string) error {
			htmlgraphDir, err := findHtmlgraphDir()
			if err != nil {
				return err
			}
			return runPlanCritique(htmlgraphDir, args[0])
		},
	}
}

func runPlanCritique(htmlgraphDir, planID string) error {
	out, err := extractCritiqueData(htmlgraphDir, planID)
	if err != nil {
		return err
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(out)
}

// extractCritiqueData reads a plan HTML and extracts structured data for critique.
func extractCritiqueData(htmlgraphDir, planID string) (*critiqueOutput, error) {
	planPath := filepath.Join(htmlgraphDir, "plans", planID+".html")
	f, err := os.Open(planPath)
	if err != nil {
		return nil, fmt.Errorf("plan %q not found: %w", planID, err)
	}
	defer f.Close()

	doc, err := goquery.NewDocumentFromReader(f)
	if err != nil {
		return nil, fmt.Errorf("parse plan HTML: %w", err)
	}

	out := &critiqueOutput{PlanID: planID}

	// Extract title and status.
	out.Title = strings.TrimPrefix(strings.TrimSpace(doc.Find("h1").First().Text()), "Plan: ")
	out.Status, _ = doc.Find("article[id]").First().Attr("data-status")
	if out.Status == "" {
		out.Status = "draft"
	}

	// Extract description from design section.
	doc.Find("[data-section='design'] p").Each(func(i int, sel *goquery.Selection) {
		if i == 0 {
			out.Description = strings.TrimSpace(sel.Text())
		}
	})
	if out.Description == "" {
		out.Description = strings.TrimSpace(doc.Find("section p").First().Text())
	}

	// Extract slices.
	doc.Find(".slice-card[data-slice]").Each(func(_ int, sel *goquery.Selection) {
		numStr, _ := sel.Attr("data-slice")
		num, err := strconv.Atoi(numStr)
		if err != nil {
			return
		}
		status, _ := sel.Attr("data-status")
		if status == "" {
			status = "pending"
		}
		title := strings.TrimSpace(sel.Find(".slice-name").First().Text())
		if title == "" {
			title = fmt.Sprintf("Slice %d", num)
		}

		// Parse dependencies from graph nodes.
		var deps []int
		nodeSelector := fmt.Sprintf("[data-node='%d']", num)
		depsStr, _ := doc.Find(nodeSelector).First().Attr("data-deps")
		for _, d := range strings.Split(depsStr, ",") {
			d = strings.TrimSpace(d)
			if d == "" {
				continue
			}
			if n, err := strconv.Atoi(d); err == nil {
				deps = append(deps, n)
			}
		}

		// Extract test strategy.
		testStrategy := ""
		sel.Find("h4").Each(func(_ int, h4 *goquery.Selection) {
			if strings.TrimSpace(h4.Text()) == "Test Strategy" {
				ul := h4.Next()
				if ul.Is("ul") {
					var items []string
					ul.Find("li").Each(func(_ int, li *goquery.Selection) {
						items = append(items, strings.TrimSpace(li.Text()))
					})
					testStrategy = strings.Join(items, "; ")
				}
			}
		})

		out.Slices = append(out.Slices, critiqueSlice{
			Number:       num,
			Title:        title,
			Status:       status,
			Dependencies: deps,
			TestStrategy: testStrategy,
		})
	})

	// Extract questions.
	doc.Find(".question-block[data-question]").Each(func(_ int, sel *goquery.Selection) {
		qID, _ := sel.Attr("data-question")
		text := strings.TrimSpace(sel.Find("strong").First().Text())
		status := "pending"
		answer := ""

		sel.Find("input[type='radio']").Each(func(_ int, radio *goquery.Selection) {
			if _, checked := radio.Attr("checked"); checked {
				answer, _ = radio.Attr("value")
				status = "answered"
			}
		})

		out.Questions = append(out.Questions, critiqueQ{
			ID:     qID,
			Text:   text,
			Answer: answer,
			Status: status,
		})
	})

	// Extract design summary.
	doc.Find("section h4").Each(func(_ int, sel *goquery.Selection) {
		if strings.TrimSpace(sel.Text()) == "Scope" {
			ul := sel.Next()
			if ul.Is("ul") {
				var items []string
				ul.Find("li").Each(func(_ int, li *goquery.Selection) {
					items = append(items, strings.TrimSpace(li.Text()))
				})
				out.DesignSummary = strings.Join(items, "; ")
			}
		}
	})

	// Complexity gate.
	out.SliceCount = len(out.Slices)
	out.Complexity, out.CritiqueWarranted = classifyComplexity(out.SliceCount)

	return out, nil
}

// classifyComplexity determines plan complexity and whether critique is warranted.
func classifyComplexity(sliceCount int) (complexity string, warranted bool) {
	switch {
	case sliceCount < 3:
		return "low", false
	case sliceCount < 6:
		return "medium", true
	default:
		return "high", true
	}
}
