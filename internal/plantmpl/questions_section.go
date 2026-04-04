package plantmpl

import (
	"fmt"
	"io"
)

// QuestionsSection renders the open questions and decision cards zone.
type QuestionsSection struct {
	Cards []DecisionCard
}

// DecisionCard represents a single decision point requiring human input.
type DecisionCard struct {
	ID        string
	Text      string
	Options   []string
	Selected  string
	Rationale string
}

// Render writes the questions section zone placeholder.
func (q *QuestionsSection) Render(w io.Writer) error {
	_, err := fmt.Fprint(w, "<!-- questions-section zone placeholder -->")
	return err
}
