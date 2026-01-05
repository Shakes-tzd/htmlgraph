#!/usr/bin/env python3
"""Complete feature feat-1b4eb0c7 in HtmlGraph."""

from htmlgraph import SDK

sdk = SDK(agent="claude-error-cmd")

# Complete the error-analysis command feature
feature = sdk.features.complete("feat-1b4eb0c7")

print(f"✅ Feature completed: {feature.id}")
print(f"   Title: {feature.title}")
print(f"   Status: {feature.status}")
