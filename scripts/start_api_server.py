#!/usr/bin/env python3
"""Start FastAPI server with correct database path for development."""

from pathlib import Path

from htmlgraph.api.main import create_app

# Use project's database
db_path = str(Path(__file__).parent / ".htmlgraph" / "index.sqlite")
app = create_app(db_path=db_path)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000, reload=True)
