package db

import (
	"database/sql"
	"fmt"
	"time"

	"github.com/shakestzd/htmlgraph/internal/models"
)

// UpsertFeatureFile inserts a feature_file row or updates last_seen on conflict.
// The UNIQUE constraint is (feature_id, file_path), so re-touching the same file
// within the same feature just refreshes the timestamp and operation.
func UpsertFeatureFile(db *sql.DB, ff *models.FeatureFile) error {
	_, err := db.Exec(`
		INSERT INTO feature_files
			(id, feature_id, file_path, operation, session_id,
			 first_seen, last_seen, created_at)
		VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
		ON CONFLICT(feature_id, file_path) DO UPDATE SET
			last_seen  = CURRENT_TIMESTAMP,
			operation  = excluded.operation,
			session_id = excluded.session_id`,
		ff.ID, ff.FeatureID, ff.FilePath, ff.Operation, nullStr(ff.SessionID),
	)
	if err != nil {
		return fmt.Errorf("upsert feature_file %s/%s: %w", ff.FeatureID, ff.FilePath, err)
	}
	return nil
}

// ListFilesByFeature returns all file paths recorded for a feature.
func ListFilesByFeature(db *sql.DB, featureID string) ([]models.FeatureFile, error) {
	rows, err := db.Query(`
		SELECT id, feature_id, file_path, operation,
		       COALESCE(session_id, ''),
		       first_seen, last_seen, created_at
		FROM feature_files
		WHERE feature_id = ?
		ORDER BY last_seen DESC`, featureID)
	if err != nil {
		return nil, fmt.Errorf("list files for feature %s: %w", featureID, err)
	}
	defer rows.Close()
	return scanFeatureFiles(rows)
}

// ListFeaturesByFile returns all features that have touched a given file path.
func ListFeaturesByFile(db *sql.DB, filePath string) ([]models.FeatureFile, error) {
	rows, err := db.Query(`
		SELECT id, feature_id, file_path, operation,
		       COALESCE(session_id, ''),
		       first_seen, last_seen, created_at
		FROM feature_files
		WHERE file_path = ?
		ORDER BY last_seen DESC`, filePath)
	if err != nil {
		return nil, fmt.Errorf("list features for file %s: %w", filePath, err)
	}
	defer rows.Close()
	return scanFeatureFiles(rows)
}

// scanFeatureFiles reads rows into a slice of FeatureFile.
func scanFeatureFiles(rows *sql.Rows) ([]models.FeatureFile, error) {
	var out []models.FeatureFile
	for rows.Next() {
		var ff models.FeatureFile
		var firstSeen, lastSeen, createdAt string
		if err := rows.Scan(
			&ff.ID, &ff.FeatureID, &ff.FilePath, &ff.Operation,
			&ff.SessionID, &firstSeen, &lastSeen, &createdAt,
		); err != nil {
			continue
		}
		ff.FirstSeen, _ = time.Parse("2006-01-02 15:04:05", firstSeen)
		ff.LastSeen, _ = time.Parse("2006-01-02 15:04:05", lastSeen)
		ff.CreatedAt, _ = time.Parse("2006-01-02 15:04:05", createdAt)
		out = append(out, ff)
	}
	return out, rows.Err()
}
