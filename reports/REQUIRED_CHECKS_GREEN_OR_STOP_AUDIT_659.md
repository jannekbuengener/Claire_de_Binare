# Required Checks „Green or Stop“ Audit Report (Issue #659)

**Date:** 2026-01-29
**Auditor:** Jules (AI Software Engineer)
**Verdict:** ❌ **FAIL**

## 1. Executive Summary

The audit of the branch protection rules and CI/CD workflow configuration revealed significant discrepancies between the intended security posture ("Green or Stop") and the actual configuration. While status checks are enabled, the names used in the branch protection settings do not match the actual job names in the modern workflows, and several critical checks are missing or bypassable.

## 2. Status Check Mapping & Validation

| Intended Context Name | Status in `temp_branch_protection.json` | Actual Workflow Job Name | Trigger Condition | Match |
| :--- | :---: | :--- | :--- | :---: |
| `ci` | ✅ | `ci` (in `ci.yml`) | `pull_request` (paths) | ✅ |
| `ai/review` | ✅ | `ai/review` (in `ai-review-router.yml`) | `pull_request` | ✅ |
| `Check Delivery Gate` | ❌ (Missing) | `Check Delivery Gate` (in `delivery-gate.yml`) | `pull_request` | ❌ |
| `Linting (Ruff)` | ❌ (`lint`) | `Linting (Ruff)` (in `ci.yaml`) | `pull_request` (paths-ignore) | ❌ |
| `e2e-paper-trading` | ❌ (`e2e-tests`) | `e2e-paper-trading` (in `e2e-tests.yml`) | `pull_request` (paths) | ❌ |
| `Secret Scanning (Gitleaks)` | ❌ (`security-scan`) | `Secret Scanning (Gitleaks)` (in `ci.yaml`) | `pull_request` (paths-ignore) | ❌ |
| `Container Scan (Trivy)` | ❌ (`security-scan`) | `Container Scan (Trivy)` (in `ci.yaml`) | `pull_request` (paths-ignore) | ❌ |
| `Core Duplicates Guard` | ❌ (Missing) | `Core Duplicates Guard` (in `ci.yaml`) | `pull_request` (paths-ignore) | ❌ |

**Findings:**
- **Case Sensitivity & Naming:** Branch protection uses generic names like `lint` and `security-scan` which do not match the specific names in `ci.yaml` (e.g., `Linting (Ruff)`).
- **Missing Checks:** `Check Delivery Gate` and `Core Duplicates Guard` are not enforced at the branch level.

## 3. Branch Protection Policy Check

| Requirement | Current Status (`temp_branch_protection.json`) | Verdict |
| :--- | :--- | :---: |
| Require status checks to pass | `strict: true` | ✅ PASS |
| Do not allow bypassing (Admins) | `enforce_admins: false` | ❌ FAIL |
| Force-push deactivated | `allow_force_pushes: false` | ✅ PASS |

**Findings:**
- `enforce_admins` MUST be set to `true` to ensure no one can bypass the governance gate.

## 4. Workflow Reality & Bypass Paths

### 4.1 Path Filter Leaks
- **Issue:** `e2e-tests.yml` does not trigger on `core/**` changes. This means changes to the core logic can be merged without running E2E tests, even if they are required (they will stay "Pending" or skip depending on GitHub settings).
- **Issue:** Docs-only PRs (`README.md`) skip `ci.yaml` and `ci.yml` due to `paths-ignore`/`paths`. In a "Strict" configuration, this blocks merging for documentation changes unless "dummy" checks are implemented.

### 4.2 Skip/Neutral Guards
- **Issue:** `delivery-gate.yml` exits with success if the `DELIVERY_APPROVED.yaml` file is missing.
- **Issue:** `type-check`, `security-audit`, and `dependency-audit` use `continue-on-error: true`, meaning they do not effectively block a merge even if they find issues.

## 5. Negative Test Evidence

- **Lint Failure:** Verified locally that `ruff` correctly identifies errors (e.g., `F841` unused variable).
- **Core Guard Failure:** Verified locally that `scripts/check_core_duplicates.py` correctly blocks forbidden directory structures.

## 6. Required Actions (Fixes)

1. **Update `temp_branch_protection.json`**:
   - Set `enforce_admins: true`.
   - Update `contexts` to match exact job names: `["ci", "ai/review", "Check Delivery Gate", "Linting (Ruff)", "e2e-paper-trading", "Secret Scanning (Gitleaks)", "Container Scan (Trivy)", "Core Duplicates Guard"]`.
2. **Fix `e2e-tests.yml`**:
   - Add `core/**` to the trigger paths.
3. **Harmonize CI Workflows**:
   - Merge or clearly separate `ci.yml` and `ci.yaml` to avoid redundant runs and conflicting path logic.
4. **Enforce Audits**:
   - Remove `continue-on-error: true` for jobs that should be mandatory for "Green or Stop" (e.g., type checking).

## 7. Evidence Log
- Local Ruff output: `::error ... F841 Local variable 'b' is assigned to but never used`
- Local Core Guard output: `CI-Guard FAILED FORBIDDEN: core duplicate at services/test_service/core`
