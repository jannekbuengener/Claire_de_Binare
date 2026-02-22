# Runbook: Merge Policy — CI Gate Configuration

## Overview

This runbook documents the GitHub settings that enforce the
"No Human Review" policy. CI is the sole merge gate.

See [no_human_review_policy.md](../governance/no_human_review_policy.md)
for the policy rationale.

## Current State (as of 2026-02-23)

Settings match the policy. No changes needed unless something drifted.

## Required GitHub Settings

### Branch Protection (main)

Apply via GitHub UI (Settings > Branches > main) or CLI:

```bash
# Set required status checks (strict: branch must be up to date)
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["ci (Unit/Integration + Lint gesammelt)"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews=null \
  --field restrictions=null \
  --field required_conversation_resolution=true \
  --field allow_force_pushes=false \
  --field allow_deletions=false
```

### Verify Settings

```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection \
  | python -m json.tool
```

Expected output (key fields):

| Field | Expected |
|-------|----------|
| `required_status_checks.strict` | `true` |
| `required_status_checks.contexts` | `["ci (Unit/Integration + Lint gesammelt)"]` |
| `required_approving_review_count` | `0` |
| `enforce_admins.enabled` | `true` |
| `required_conversation_resolution.enabled` | `true` |
| `allow_force_pushes.enabled` | `false` |
| `allow_deletions.enabled` | `false` |

### Disable Human Reviews (if re-enabled accidentally)

```bash
# Remove required_pull_request_reviews entirely:
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_pull_request_reviews \
  --method DELETE

# Or set to 0 approvals:
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_pull_request_reviews \
  --method PATCH \
  --field required_approving_review_count=0
```

### Enable Auto-merge (optional)

```bash
# Enable auto-merge at repo level (PRs merge when checks pass):
gh api repos/jannekbuengener/Claire_de_Binare \
  --method PATCH \
  --field allow_auto_merge=true
```

Then per PR:

```bash
gh pr merge <number> --auto --squash
```

### Adding Required Checks

When a quarantined test is fixed and added to CI:

1. Add the job to `.github/workflows/ci.yml`
2. Update branch protection to include the new check context:

```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_status_checks \
  --method PATCH \
  --field strict=true \
  --field contexts='["ci (Unit/Integration + Lint gesammelt)", "<new-check-name>"]'
```

3. Remove the test from the quarantine table in `no_human_review_policy.md`

## Rollback: Re-enable Human Reviews

If the policy is reverted:

```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection/required_pull_request_reviews \
  --method PATCH \
  --field required_approving_review_count=1
```

Document the change in [BRANCH_PROTECTION_LOG.md](../governance/BRANCH_PROTECTION_LOG.md).
