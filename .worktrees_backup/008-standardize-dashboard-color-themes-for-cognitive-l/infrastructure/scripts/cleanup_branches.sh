#!/usr/bin/env bash
# Cleanup-Skript für merged Feature-Branches
# Governance: CDB_GOVERNANCE.md (Repo-Hygiene)

set -euo pipefail

DAYS_OLD="${1:-30}"
DRY_RUN="${DRY_RUN:-true}"

echo "========================================="
echo "🧹 Branch Cleanup (Merged Branches)"
echo "========================================="
echo "Age threshold: ${DAYS_OLD} days"
echo "Mode: $([ "$DRY_RUN" = "true" ] && echo "DRY-RUN" || echo "LIVE")"
echo ""

# Check if we're in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: Not a git repository" >&2
  exit 1
fi

# Fetch latest
echo "📥 Fetching latest from gitlab..."
git fetch gitlab --prune

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: ${CURRENT_BRANCH}"
echo ""

# Find merged branches (local)
echo "🔍 Finding merged local branches (older than ${DAYS_OLD} days)..."
MERGED_LOCAL=()
while IFS= read -r branch; do
  # Skip main/master
  if [[ "$branch" == "main" || "$branch" == "master" ]]; then
    continue
  fi

  # Skip current branch
  if [[ "$branch" == "$CURRENT_BRANCH" ]]; then
    continue
  fi

  # Check if merged into main
  if git merge-base --is-ancestor "refs/heads/${branch}" gitlab/main 2>/dev/null; then
    # Check age (last commit date)
    LAST_COMMIT_DATE=$(git log -1 --format=%ct "refs/heads/${branch}")
    CURRENT_DATE=$(date +%s)
    AGE_DAYS=$(( (CURRENT_DATE - LAST_COMMIT_DATE) / 86400 ))

    if [ "$AGE_DAYS" -ge "$DAYS_OLD" ]; then
      MERGED_LOCAL+=("${branch} (${AGE_DAYS} days old)")
    fi
  fi
done < <(git for-each-ref --format='%(refname:short)' refs/heads/)

# Find merged remote branches
echo "🔍 Finding merged remote branches (older than ${DAYS_OLD} days)..."
MERGED_REMOTE=()
while IFS= read -r branch; do
  # Remove 'gitlab/' prefix
  branch_name="${branch#gitlab/}"

  # Skip main/master/HEAD
  if [[ "$branch_name" == "main" || "$branch_name" == "master" || "$branch_name" == "HEAD" ]]; then
    continue
  fi

  # Check if merged
  if git merge-base --is-ancestor "refs/remotes/${branch}" gitlab/main 2>/dev/null; then
    LAST_COMMIT_DATE=$(git log -1 --format=%ct "refs/remotes/${branch}")
    CURRENT_DATE=$(date +%s)
    AGE_DAYS=$(( (CURRENT_DATE - LAST_COMMIT_DATE) / 86400 ))

    if [ "$AGE_DAYS" -ge "$DAYS_OLD" ]; then
      MERGED_REMOTE+=("${branch_name} (${AGE_DAYS} days old)")
    fi
  fi
done < <(git for-each-ref --format='%(refname:short)' refs/remotes/gitlab/)

# Display results
echo ""
echo "========================================="
echo "📋 Summary"
echo "========================================="
echo ""
echo "Local merged branches (${#MERGED_LOCAL[@]}):"
if [ ${#MERGED_LOCAL[@]} -eq 0 ]; then
  echo "  (none)"
else
  printf '  - %s\n' "${MERGED_LOCAL[@]}"
fi

echo ""
echo "Remote merged branches (${#MERGED_REMOTE[@]}):"
if [ ${#MERGED_REMOTE[@]} -eq 0 ]; then
  echo "  (none)"
else
  printf '  - %s\n' "${MERGED_REMOTE[@]}"
fi

# Confirmation prompt
if [ ${#MERGED_LOCAL[@]} -eq 0 ] && [ ${#MERGED_REMOTE[@]} -eq 0 ]; then
  echo ""
  echo "✓ No branches to cleanup!"
  exit 0
fi

if [ "$DRY_RUN" = "true" ]; then
  echo ""
  echo "ℹ️  DRY-RUN mode: No branches were deleted."
  echo "To actually delete, run: DRY_RUN=false $0 ${DAYS_OLD}"
  exit 0
fi

echo ""
read -p "⚠️  Delete these branches? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

# Delete local branches
if [ ${#MERGED_LOCAL[@]} -gt 0 ]; then
  echo ""
  echo "🗑️  Deleting local branches..."
  for branch_info in "${MERGED_LOCAL[@]}"; do
    branch="${branch_info%% (*}"
    echo "  - Deleting: ${branch}"
    git branch -d "${branch}" || echo "    ⚠️  Failed to delete ${branch}"
  done
fi

# Delete remote branches
if [ ${#MERGED_REMOTE[@]} -gt 0 ]; then
  echo ""
  echo "🗑️  Deleting remote branches..."
  for branch_info in "${MERGED_REMOTE[@]}"; do
    branch="${branch_info%% (*}"
    echo "  - Deleting: gitlab/${branch}"
    git push gitlab --delete "${branch}" || echo "    ⚠️  Failed to delete gitlab/${branch}"
  done
fi

echo ""
echo "✅ Cleanup completed!"
