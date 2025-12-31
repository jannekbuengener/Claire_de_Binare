#!/usr/bin/env bash
# Rollback-Skript für GitLab Merge Requests
# Governance: CDB_GOVERNANCE.md (Rollback-Fähigkeit)

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <MR-NUMBER>" >&2
  echo "Example: $0 88" >&2
  exit 1
fi

MR_NUMBER="$1"
ROLLBACK_BRANCH="rollback/mr-${MR_NUMBER}"

echo "========================================="
echo "🔄 Rollback MR #${MR_NUMBER}"
echo "========================================="

# Check if we're in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: Not a git repository" >&2
  exit 1
fi

# Fetch latest from remote
echo "📥 Fetching latest from gitlab..."
git fetch gitlab

# Get merge commit for the MR (assumes MR was merged to main)
echo "🔍 Finding merge commit for MR #${MR_NUMBER}..."
MERGE_COMMIT=$(git log --merges --grep="Merge branch.*!${MR_NUMBER}" --format="%H" -n 1 gitlab/main || echo "")

if [ -z "$MERGE_COMMIT" ]; then
  echo "⚠️  Could not find merge commit for MR #${MR_NUMBER}"
  echo "Trying alternative search..."
  MERGE_COMMIT=$(git log --merges --oneline -n 20 gitlab/main | grep -i "mr.*${MR_NUMBER}" | head -n 1 | awk '{print $1}' || echo "")
fi

if [ -z "$MERGE_COMMIT" ]; then
  echo "❌ Error: Could not find merge commit for MR #${MR_NUMBER}" >&2
  echo "Hint: Check if MR was actually merged to main" >&2
  exit 1
fi

echo "✓ Found merge commit: ${MERGE_COMMIT}"

# Create rollback branch from main
echo "🌿 Creating rollback branch: ${ROLLBACK_BRANCH}"
git checkout -b "${ROLLBACK_BRANCH}" gitlab/main

# Revert the merge commit
echo "↩️  Reverting merge commit ${MERGE_COMMIT}..."
git revert -m 1 "${MERGE_COMMIT}" --no-edit

# Push to remote
echo "📤 Pushing rollback branch to gitlab..."
git push -u gitlab "${ROLLBACK_BRANCH}"

echo ""
echo "========================================="
echo "✅ Rollback branch created successfully!"
echo "========================================="
echo ""
echo "Branch: ${ROLLBACK_BRANCH}"
echo "Merge Commit: ${MERGE_COMMIT}"
echo ""
echo "Next steps:"
echo "1. Create MR via GitLab Web UI:"
echo "   https://gitlab.com/jannekbungener/claire_de_binare/-/merge_requests/new?merge_request[source_branch]=${ROLLBACK_BRANCH}"
echo ""
echo "2. Or use git push option (if available):"
echo "   git push gitlab ${ROLLBACK_BRANCH} -o merge_request.create -o merge_request.title=\"Rollback MR #${MR_NUMBER}\""
echo ""
