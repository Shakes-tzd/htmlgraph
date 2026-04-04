package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/shakestzd/htmlgraph/internal/models"
	"github.com/shakestzd/htmlgraph/internal/workitem"
	"github.com/spf13/cobra"
)

// finalizeResult holds the output of a plan finalize operation.
type finalizeResult struct {
	TrackID          string
	FeatureIDs       []string
	AlreadyFinalized bool
}

// planFinalizeCmd creates a cobra command for plan finalize.
func planFinalizeCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "finalize <plan-id>",
		Short: "Generate a work item graph from a finalized plan",
		Long: `Read a plan's approved slices and generate the work item graph:
a track, features per approved slice, and edges for dependencies.

Idempotent: re-running on an already-finalized plan is a no-op.

Example:
  htmlgraph plan finalize plan-a1b2c3d4`,
		Args: cobra.ExactArgs(1),
		RunE: func(_ *cobra.Command, args []string) error {
			htmlgraphDir, err := findHtmlgraphDir()
			if err != nil {
				return err
			}
			p, err := workitem.Open(htmlgraphDir, "claude-code")
			if err != nil {
				return fmt.Errorf("open project: %w", err)
			}
			defer p.Close()

			result, err := executePlanFinalize(p, htmlgraphDir, args[0])
			if err != nil {
				return err
			}

			if result.AlreadyFinalized {
				fmt.Printf("Plan %s is already finalized", args[0])
				if result.TrackID != "" {
					fmt.Printf(" (track: %s)", result.TrackID)
				}
				fmt.Println()
				return nil
			}

			fmt.Printf("Created track: %s\n", result.TrackID)
			fmt.Printf("Created %d features\n", len(result.FeatureIDs))
			for _, fid := range result.FeatureIDs {
				fmt.Printf("  %s\n", fid)
			}
			return nil
		},
	}
}

// executePlanFinalize reads a plan, creates a track and features from approved
// slices, wires edges, and marks the plan as finalized. Idempotent.
func executePlanFinalize(p *workitem.Project, htmlgraphDir, planID string) (*finalizeResult, error) {
	planPath := filepath.Join(htmlgraphDir, "plans", planID+".html")

	// Parse plan HTML.
	status, err := parsePlanHTMLStatus(planPath)
	if err != nil {
		return nil, fmt.Errorf("read plan %s: %w", planID, err)
	}

	// Idempotent: if already finalized, find existing track + features and return.
	if status == "finalized" {
		trackID := findTrackForPlan(p, planID)
		featureIDs := findFeaturesForTrack(p, trackID)
		return &finalizeResult{
			TrackID:          trackID,
			FeatureIDs:       featureIDs,
			AlreadyFinalized: true,
		}, nil
	}

	// Parse feedback from the HTML file.
	feedback, err := parseFeedbackFromHTML(planID, planPath)
	if err != nil {
		return nil, fmt.Errorf("read feedback: %w", err)
	}

	// Parse slice metadata from the HTML.
	slices, err := parsePlanSlices(planPath)
	if err != nil {
		return nil, fmt.Errorf("parse slices: %w", err)
	}

	// Filter to approved slices only.
	var approvedSlices []planSlice
	for _, s := range slices {
		sectionKey := fmt.Sprintf("slice-%d", s.num)
		if feedback.SliceApprovals[sectionKey] {
			approvedSlices = append(approvedSlices, s)
		}
	}

	// Extract plan title.
	planTitle := parsePlanTitle(planPath)
	if planTitle == "" {
		planTitle = planID
	}

	// Create track.
	trackNode, err := p.Tracks.Create(planTitle,
		workitem.TrackWithStatus("in-progress"),
	)
	if err != nil {
		return nil, fmt.Errorf("create track: %w", err)
	}

	// Build a map from slice number to feature ID for dependency wiring.
	sliceNumToFeatureID := make(map[int]string, len(approvedSlices))
	var featureIDs []string

	// Create features for each approved slice.
	for _, s := range approvedSlices {
		// Build description from slice comments if available.
		sectionKey := fmt.Sprintf("slice-%d", s.num)
		desc := ""
		if comment, ok := feedback.Comments[sectionKey]; ok && comment != "" {
			desc = comment
		}

		opts := []workitem.FeatureOption{
			workitem.FeatWithTrack(trackNode.ID),
		}
		if desc != "" {
			opts = append(opts, workitem.FeatWithContent(desc))
		}

		featNode, err := p.Features.Create(s.title, opts...)
		if err != nil {
			return nil, fmt.Errorf("create feature for slice %d: %w", s.num, err)
		}

		sliceNumToFeatureID[s.num] = featNode.ID
		featureIDs = append(featureIDs, featNode.ID)

		// Wire bidirectional track <-> feature edges.
		if err := wireTrackEdges(p, featNode.ID, trackNode.ID, s.title); err != nil {
			return nil, fmt.Errorf("wire track edges for %s: %w", featNode.ID, err)
		}
	}

	// Wire blocked_by edges based on slice dependencies.
	for _, s := range approvedSlices {
		featID, ok := sliceNumToFeatureID[s.num]
		if !ok {
			continue
		}
		for _, depNum := range s.depNums {
			depFeatID, ok := sliceNumToFeatureID[depNum]
			if !ok {
				continue // dependency was not approved, skip
			}
			edge := models.Edge{
				TargetID:     depFeatID,
				Relationship: models.RelBlockedBy,
				Title:        depFeatID,
				Since:        time.Now().UTC(),
			}
			if _, err := p.Features.AddEdge(featID, edge); err != nil {
				return nil, fmt.Errorf("wire blocked_by %s -> %s: %w", featID, depFeatID, err)
			}
		}
	}

	// Link plan to track: plan implemented_in track.
	planCol := collectionFor(p, "plan")
	planNode, err := planCol.Get(planID)
	if err == nil {
		edge := models.Edge{
			TargetID:     trackNode.ID,
			Relationship: models.RelImplementedIn,
			Title:        trackNode.ID,
			Since:        time.Now().UTC(),
		}
		_, _ = planCol.AddEdge(planNode.ID, edge)
	}

	// Update plan HTML status to "finalized".
	if err := updatePlanHTMLStatus(planPath, "finalized"); err != nil {
		// Non-fatal: the work items are already created.
		fmt.Fprintf(os.Stderr, "Warning: failed to update plan status: %v\n", err)
	}

	return &finalizeResult{
		TrackID:    trackNode.ID,
		FeatureIDs: featureIDs,
	}, nil
}

// planSlice holds metadata for a single slice parsed from the plan HTML.
type planSlice struct {
	num     int
	name    string // data-slice-name (feature ID or slug)
	title   string // human-readable title from slice-name span
	depNums []int  // dependency slice numbers from data-deps
}

// parsePlanSlices reads slice cards and graph nodes from a plan HTML file.
func parsePlanSlices(planPath string) ([]planSlice, error) {
	f, err := os.Open(planPath)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	doc, err := goquery.NewDocumentFromReader(f)
	if err != nil {
		return nil, err
	}

	// Build dep map from graph nodes: data-node -> data-deps.
	depMap := make(map[int][]int)
	doc.Find("[data-node]").Each(func(_ int, sel *goquery.Selection) {
		nodeStr, _ := sel.Attr("data-node")
		nodeNum, err := strconv.Atoi(nodeStr)
		if err != nil {
			return
		}
		depsStr, _ := sel.Attr("data-deps")
		if depsStr == "" {
			return
		}
		for _, d := range strings.Split(depsStr, ",") {
			d = strings.TrimSpace(d)
			if d == "" {
				continue
			}
			if num, err := strconv.Atoi(d); err == nil {
				depMap[nodeNum] = append(depMap[nodeNum], num)
			}
		}
	})

	// Parse slice cards.
	var slices []planSlice
	doc.Find(".slice-card[data-slice]").Each(func(_ int, sel *goquery.Selection) {
		numStr, _ := sel.Attr("data-slice")
		num, err := strconv.Atoi(numStr)
		if err != nil {
			return
		}

		name, _ := sel.Attr("data-slice-name")
		title := strings.TrimSpace(sel.Find(".slice-name").First().Text())
		if title == "" {
			title = name
		}
		if title == "" {
			title = fmt.Sprintf("Slice %d", num)
		}

		slices = append(slices, planSlice{
			num:     num,
			name:    name,
			title:   title,
			depNums: depMap[num],
		})
	})

	return slices, nil
}

// parsePlanTitle reads the plan title from the <h1> element.
func parsePlanTitle(planPath string) string {
	f, err := os.Open(planPath)
	if err != nil {
		return ""
	}
	defer f.Close()

	doc, err := goquery.NewDocumentFromReader(f)
	if err != nil {
		return ""
	}

	title := strings.TrimSpace(doc.Find("h1").First().Text())
	// Strip "Plan: " prefix if present.
	title = strings.TrimPrefix(title, "Plan: ")
	return title
}

// wireTrackEdges creates bidirectional part_of/contains edges between a
// feature and its track.
func wireTrackEdges(p *workitem.Project, featureID, trackID, featureTitle string) error {
	now := time.Now().UTC()

	// feature -> track (part_of)
	partOf := models.Edge{
		TargetID:     trackID,
		Relationship: models.RelPartOf,
		Title:        trackID,
		Since:        now,
	}
	if _, err := p.Features.AddEdge(featureID, partOf); err != nil {
		return fmt.Errorf("part_of: %w", err)
	}

	// track -> feature (contains)
	contains := models.Edge{
		TargetID:     featureID,
		Relationship: models.RelContains,
		Title:        featureTitle,
		Since:        now,
	}
	if _, err := p.Tracks.AddEdge(trackID, contains); err != nil {
		return fmt.Errorf("contains: %w", err)
	}

	return nil
}

// findFeaturesForTrack returns feature IDs linked to a track via contains edges.
func findFeaturesForTrack(p *workitem.Project, trackID string) []string {
	if trackID == "" {
		return nil
	}
	node, err := p.Tracks.Get(trackID)
	if err != nil {
		return nil
	}
	var ids []string
	for _, edge := range node.Edges[string(models.RelContains)] {
		if strings.HasPrefix(edge.TargetID, "feat-") {
			ids = append(ids, edge.TargetID)
		}
	}
	return ids
}

// findTrackForPlan searches for an existing track linked to the plan via
// an implemented_in edge. Returns the track ID or empty string.
func findTrackForPlan(p *workitem.Project, planID string) string {
	planCol := collectionFor(p, "plan")
	node, err := planCol.Get(planID)
	if err != nil {
		return ""
	}
	for _, edge := range node.Edges[string(models.RelImplementedIn)] {
		if strings.HasPrefix(edge.TargetID, "trk-") {
			return edge.TargetID
		}
	}
	return ""
}
