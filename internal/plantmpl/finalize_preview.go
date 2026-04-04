package plantmpl

import (
	"fmt"
	"io"
)

// FinalizePreview renders the finalization preview zone showing
// all features ready for dispatch with their approval status.
type FinalizePreview struct {
	Features []PreviewFeature
	TrackID  string
}

// PreviewFeature represents a single feature in the finalize preview.
type PreviewFeature struct {
	Name     string
	Deps     string
	Approved bool
}

// Render writes the finalize preview zone placeholder.
func (fp *FinalizePreview) Render(w io.Writer) error {
	_, err := fmt.Fprint(w, "<!-- finalize-preview zone placeholder -->")
	return err
}
