package workitem

import (
	"fmt"
	"path/filepath"

	dbpkg "github.com/shakestzd/htmlgraph/internal/db"
)

// Project is the main entry point for interacting with an HtmlGraph project.
type Project struct {
	*Base

	// Collection accessors
	Features *FeatureCollection
	Bugs     *BugCollection
	Spikes   *SpikeCollection
	Tracks   *TrackCollection
	Sessions *SessionCollection
}

// Open creates a new Project instance, opens the SQLite database, and
// initialises all collection accessors.
//
// projectDir must point to a .htmlgraph/ directory.
// agent identifies the calling agent for work attribution.
func Open(projectDir, agent string) (*Project, error) {
	if projectDir == "" {
		return nil, fmt.Errorf("projectDir must not be empty")
	}
	if agent == "" {
		return nil, fmt.Errorf("agent must not be empty")
	}

	dbPath := filepath.Join(projectDir, "htmlgraph.db")
	database, err := dbpkg.Open(dbPath)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	base := &Base{
		ProjectDir: projectDir,
		Agent:      agent,
		DB:         database,
	}

	p := &Project{Base: base}

	p.Features = NewFeatureCollection(base)
	p.Bugs = NewBugCollection(base)
	p.Spikes = NewSpikeCollection(base)
	p.Tracks = NewTrackCollection(base)
	p.Sessions = NewSessionCollection(base)

	return p, nil
}

// Close releases the SQLite database connection.
func (p *Project) Close() error {
	if p.DB != nil {
		return p.DB.Close()
	}
	return nil
}

// FeaturesDir returns the path to the features subdirectory.
func (p *Project) FeaturesDir() string {
	return filepath.Join(p.ProjectDir, "features")
}

// BugsDir returns the path to the bugs subdirectory.
func (p *Project) BugsDir() string {
	return filepath.Join(p.ProjectDir, "bugs")
}

// SpikesDir returns the path to the spikes subdirectory.
func (p *Project) SpikesDir() string {
	return filepath.Join(p.ProjectDir, "spikes")
}

// TracksDir returns the path to the tracks subdirectory.
func (p *Project) TracksDir() string {
	return filepath.Join(p.ProjectDir, "tracks")
}
