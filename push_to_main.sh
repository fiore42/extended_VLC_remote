#!/bin/bash

# Ensure a commit message is provided
if [ -z "$1" ]; then
    echo "❌ ERROR: You must provide a commit message."
    echo "Usage: ./push_to_main.sh \"Your commit message here\""
    exit 1
fi

COMMIT_MSG="$1"

# Ensure we are on the 'dev' branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "dev" ]; then
    echo "❌ ERROR: You must be on 'dev' to run this script."
    exit 1
fi

# Step 1: Commit any pending changes in dev
if ! git diff --quiet || ! git diff --staged --quiet; then
    echo "📌 Committing changes in dev..."
    git add .
    git commit -m "$COMMIT_MSG"
else
    echo "✅ No new changes to commit in dev."
fi

# Step 2: Push dev to GitHub
echo "🚀 Pushing dev branch to GitHub..."
git push origin dev

# Step 3: Switch to main
echo "🔄 Switching to main branch..."
git checkout main
git pull origin main  # Ensure main is up-to-date

# Step 4: Merge dev into main
echo "🔄 Merging dev into main..."
git merge dev --no-edit

# Step 5: Push main to GitHub
echo "🚀 Pushing main branch to GitHub..."
git push origin main

# Step 6: Switch back to dev
echo "🔄 Switching back to dev..."
git checkout dev

echo "✅ All done! dev → main → dev complete."
