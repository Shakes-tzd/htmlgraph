#!/bin/bash
# Generate API documentation using pdoc

set -e

echo "Generating API documentation with pdoc..."
uv run pdoc htmlgraph -o docs/api-pdoc --docformat google

echo "✅ API docs generated in docs/api-pdoc/"
echo "📖 Open docs/api-pdoc/htmlgraph.html to view"
