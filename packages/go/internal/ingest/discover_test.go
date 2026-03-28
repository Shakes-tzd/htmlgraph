package ingest

import (
	"testing"
)

func TestDecodeProjectPath(t *testing.T) {
	tests := []struct {
		encoded  string
		expected string
	}{
		{
			encoded:  "-Users-shakes-DevProjects-htmlgraph",
			expected: "/Users/shakes/DevProjects/htmlgraph",
		},
		{
			encoded:  "-Users-alice-code-myapp",
			expected: "/Users/alice/code/myapp",
		},
		{
			encoded:  "-home-bob-projects-foo",
			expected: "/home/bob/projects/foo",
		},
		{
			encoded:  "",
			expected: "",
		},
		// Dashes in directory names are indistinguishable from path separators
		// in Claude's encoding — "foo-bar" encodes as "-foo-bar" just like
		// "/foo/bar" would, so the decode is a best-effort reconstruction.
		{
			encoded:  "-Users-shakes-DevProjects-my-project",
			expected: "/Users/shakes/DevProjects/my/project",
		},
	}

	for _, tt := range tests {
		t.Run(tt.encoded, func(t *testing.T) {
			got := decodeProjectPath(tt.encoded)
			if got != tt.expected {
				t.Errorf("decodeProjectPath(%q) = %q, want %q", tt.encoded, got, tt.expected)
			}
		})
	}
}

func TestFilterByGitRemote(t *testing.T) {
	files := []SessionFile{
		{SessionID: "sess-1", Project: "htmlgraph", GitRemoteURL: "https://github.com/owner/htmlgraph.git"},
		{SessionID: "sess-2", Project: "htmlgraph", GitRemoteURL: "https://github.com/owner/htmlgraph.git"},
		{SessionID: "sess-3", Project: "other-project", GitRemoteURL: "https://github.com/owner/other.git"},
		{SessionID: "sess-4", Project: "no-remote", GitRemoteURL: ""},
	}

	t.Run("filters to matching remote only", func(t *testing.T) {
		got := FilterByGitRemote(files, "https://github.com/owner/htmlgraph.git")
		if len(got) != 2 {
			t.Fatalf("got %d files, want 2", len(got))
		}
		for _, sf := range got {
			if sf.GitRemoteURL != "https://github.com/owner/htmlgraph.git" {
				t.Errorf("unexpected remote %q in result", sf.GitRemoteURL)
			}
		}
	})

	t.Run("returns all when targetRemote is empty", func(t *testing.T) {
		got := FilterByGitRemote(files, "")
		if len(got) != len(files) {
			t.Fatalf("got %d files, want %d", len(got), len(files))
		}
	})

	t.Run("excludes sessions with empty remote URL", func(t *testing.T) {
		got := FilterByGitRemote(files, "https://github.com/owner/other.git")
		if len(got) != 1 {
			t.Fatalf("got %d files, want 1", len(got))
		}
		if got[0].SessionID != "sess-3" {
			t.Errorf("got session %q, want sess-3", got[0].SessionID)
		}
	})

	t.Run("returns empty when no match", func(t *testing.T) {
		got := FilterByGitRemote(files, "https://github.com/owner/nonexistent.git")
		if len(got) != 0 {
			t.Fatalf("got %d files, want 0", len(got))
		}
	})

	t.Run("handles empty input slice", func(t *testing.T) {
		got := FilterByGitRemote(nil, "https://github.com/owner/htmlgraph.git")
		if len(got) != 0 {
			t.Fatalf("got %d files, want 0", len(got))
		}
	})
}
