#!/usr/bin/env python3
"""Minimal test hook to capture exact stdin input from Claude Code."""

import json
import sys
from datetime import datetime
from pathlib import Path

# Read stdin
try:
    data = json.load(sys.stdin)
except Exception as e:
    data = {"parse_error": str(e)}

# Log everything we receive
log_file = Path(".htmlgraph/raw-hook-input.jsonl")
log_file.parent.mkdir(parents=True, exist_ok=True)

with open(log_file, "a") as f:
    f.write(
        json.dumps(
            {
                "timestamp": datetime.now().isoformat(),
                "keys": list(data.keys()) if isinstance(data, dict) else "not_dict",
                "full_data": data,
            }
        )
        + "\n"
    )

# Return success
print(json.dumps({"continue": True}))
sys.exit(0)
