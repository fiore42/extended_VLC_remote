#!/bin/bash

# Get commit message from argument or use date if empty
COMMIT_MSG="${1:-$(date +'%Y-%m-%d %H:%M:%S')}"

# Check if there are changes to commit
if ! git diff --quiet || ! git diff --staged --quiet; then
    git add .
    git commit -m "$COMMIT_MSG"
    echo "✅ Changes committed: $COMMIT_MSG"
else
    echo "🚀 No changes to commit."
fi

