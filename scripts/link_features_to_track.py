#!/usr/bin/env python3
"""Link all features to the htmlgraph-dev track."""

import re
from pathlib import Path

features_dir = Path(".htmlgraph/features")
track_id = "htmlgraph-dev"

# Find all feature HTML files
feature_files = list(features_dir.glob("feature-*.html"))

print(f"Found {len(feature_files)} feature files")

for feature_file in feature_files:
    content = feature_file.read_text(encoding="utf-8")

    # Check if already has data-track-id
    if "data-track-id=" in content:
        print(f"  ⏭️  {feature_file.name} - already has track-id")
        continue

    # Find the <article> tag and add data-track-id
    # Pattern: <article id="..." data-type="feature" ...>
    # We want to add data-track-id after data-type
    pattern = r'(<article[^>]*data-type="feature")'
    replacement = r'\1\n             data-track-id="htmlgraph-dev"'

    updated_content = re.sub(pattern, replacement, content)

    if updated_content == content:
        print(f"  ⚠️  {feature_file.name} - pattern not matched")
        continue

    # Write back
    feature_file.write_text(updated_content, encoding="utf-8")
    print(f"  ✅ {feature_file.name} - linked to {track_id}")

print("\n✓ All features linked to htmlgraph-dev track")
