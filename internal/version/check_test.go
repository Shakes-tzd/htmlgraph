package version

import "testing"

func TestIsNewer(t *testing.T) {
	tests := []struct {
		latest  string
		current string
		want    bool
	}{
		{"0.49.0", "0.48.1", true},
		{"0.48.1", "0.48.1", false},
		{"0.48.0", "0.48.1", false},
		{"1.0.0", "0.99.9", true},
		{"0.49.0", "v0.48.1", true},
		{"v0.49.0", "0.48.1", true},
		{"0.48.2", "0.48.1", true},
		{"0.48.1", "0.49.0", false},
		{"", "0.48.1", false},
		{"0.48.1", "", true},
	}
	for _, tc := range tests {
		got := isNewer(tc.latest, tc.current)
		if got != tc.want {
			t.Errorf("isNewer(%q, %q) = %v, want %v", tc.latest, tc.current, got, tc.want)
		}
	}
}

func TestParseSemver(t *testing.T) {
	tests := []struct {
		v    string
		want [3]int
	}{
		{"1.2.3", [3]int{1, 2, 3}},
		{"v1.2.3", [3]int{1, 2, 3}},
		{"0.48.1", [3]int{0, 48, 1}},
		{"1.0", [3]int{1, 0, 0}},
		{"", [3]int{0, 0, 0}},
		{"abc", [3]int{0, 0, 0}},
	}
	for _, tc := range tests {
		got := parseSemver(tc.v)
		if got != tc.want {
			t.Errorf("parseSemver(%q) = %v, want %v", tc.v, got, tc.want)
		}
	}
}
