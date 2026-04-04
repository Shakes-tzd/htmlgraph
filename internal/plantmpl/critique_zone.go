package plantmpl

import (
	"fmt"
	"html/template"
	"io"
)

// CritiqueZone renders the multi-model critique section containing
// assumption verification, model critiques, synthesis, and risk analysis.
type CritiqueZone struct {
	Assumptions     []AssumptionResult
	GeminiCritique  template.HTML
	CopilotCritique template.HTML
	Synthesis       template.HTML
	RiskTable       []RiskRow
}

// AssumptionResult represents a verified or falsified assumption.
type AssumptionResult struct {
	Text     string
	Badge    string // "verified", "unknown", "falsified"
	Evidence string
}

// RiskRow represents a single row in the risk assessment table.
type RiskRow struct {
	Risk       string
	Severity   string
	Mitigation string
}

// Render writes the critique zone placeholder.
func (c *CritiqueZone) Render(w io.Writer) error {
	_, err := fmt.Fprint(w, "<!-- critique-zone zone placeholder -->")
	return err
}
