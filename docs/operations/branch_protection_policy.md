# Branch Protection Policy Enforcement

**Status:** Blueprint / Interface Definition
**Issue:** #658

## 1. Source of Truth
The canonical configuration for branch protection is stored in:
`temp_branch_protection.json` (to be moved to `governance/` in the Docs Hub).

## 2. Enforcement Flow

### Drift Detection (Monitor)
- A scheduled CI check or manual audit script compares the GitHub API response for `branches/main/protection` against the local JSON policy.
- If any discrepancy is found (e.g., `allow_force_pushes: true`), the check MUST fail.

### Remediation (Re-Apply)
- A dedicated maintenance script (using `gh api`) applies the policy from the JSON file to the repository.
- This operation must be **idempotent**.

## 3. Required State (Security Baseline)

| Parameter | Required Value |
|-----------|----------------|
| `allow_force_pushes` | `false` |
| `allow_deletions` | `false` |
| `required_approving_review_count` | `>= 1` |
| `required_status_checks.strict` | `true` |
| `required_status_checks.contexts` | `ci`, `e2e-tests`, `lint`, `security-scan` |

## 4. Verification Artifacts
Every re-apply or audit event must produce a summary:
- `audit_report.json`
- Exit code 0 (Match) or 1 (Drift/Failure)
