# STUB MODE Governance Audit (#634)

## Baseline Status: FAIL
**Date:** 2025-01-24
**Verdict:** FAIL (Pre-Fix)

Current CI/CD infrastructure allowed "STUB MODE" (using mock data/services) on protected branches (`main`, etc.) without hard failure when secrets were missing. Some workflows even hardcoded STUB mode or provided automatic fallbacks to insecure dummy secrets.

## 1. Findings: STUB/MOCK Mode Usage

| File | Context | Logic | Role |
| :--- | :--- | :--- | :--- |
| `.github/workflows/e2e-tests.yml` | `Decide E2E mode` | `SMTP_*` check sets `mode=STUB` if secrets missing. | Sets STUB mode |
| `.github/workflows/e2e-tests.yml` | `Missing secrets (HARD FAIL)` | Fails if STUB on `main` or `schedule`. | Guard (Incomplete: missing `release/*`, `soak/*`, `shadow/*`) |
| `.github/workflows/e2e.yml` | `.env` creation | `WS_SOURCE=stub` hardcoded. | Hardcoded STUB mode |
| `.github/workflows/e2e.yml` | `Create CI secrets` | Hardcoded dummy secrets (`ci-REDIS_PASSWORD`, etc.). | Fallback Secrets |
| `.github/workflows/shadow-soak-evidence.yml` | `Create CI secrets` | Fallback to `ci-*` values if secrets are missing. | Fallback Secrets |
| `.github/workflows/shadow-soak-evidence.yml` | `deterministic override` | `MOCK_TRADING: "true"` and `WS_SOURCE: stub` hardcoded. | Hardcoded STUB mode |
| `services/execution/config.py` | Python Config | `MOCK_TRADING` defaults to `true`. | System Default Safety |

## 2. Protected Context Definition
According to policy, the following contexts are considered **protected**:
- `main`
- `release/*`
- `soak/*`
- `shadow/*`
- Branches with Branch-Protection (e.g. via `temp_branch_protection.json`)

## 3. Evidence: Policy Violations

### A) Incomplete Guard in `e2e-tests.yml`
The current guard only blocks `main` and `schedule`:
```yaml
      - name: ❌ Missing secrets on protected context (HARD FAIL)
        if: |
          steps.e2e_mode.outputs.mode == 'STUB' &&
          (github.ref == 'refs/heads/main' || github.event_name == 'schedule')
```
Branches like `release/v1.0` or `soak/test-1` would pass in STUB mode.

### B) Hardcoded STUB in `e2e.yml`
This workflow runs on `push` to `main` but uses stubs without any check for real secrets:
```yaml
      - name: Create .env file
        run: |
          cat > .env << EOF
          WS_SOURCE=stub
          ...
```

### C) Automatic Fallbacks in `shadow-soak-evidence.yml`
This workflow provides "Fake Green" by using dummy secrets when real ones are missing, even when running on a schedule (protected):
```yaml
      - name: Create CI secrets
        run: |
          REDIS_VAL="${{ secrets.REDIS_PASSWORD != '' && secrets.REDIS_PASSWORD || 'ci-redis-password' }}"
```

## 4. Fix Strategy
1. **Unify Guard Logic:** Implement a robust branch/context check.
2. **Remove Fallbacks:** Ensure workflows fail early if required secrets are missing in protected contexts.
3. **Explicit Opt-in:** Allow STUB mode only via `workflow_dispatch` with an explicit `allow_stub: true` input on non-protected branches.

## 5. Evidence: Verified Logic
The guard logic has been verified using a simulator (`tools/test_ci_guards.sh`).

### Test Results:
```text
Running CI Guard Logic Tests...
--------------------------------------------------------------------------------
✅ [OK]    STUB | refs/heads/main | push | stub=false | labels=[] -> BLOCK
✅ [OK]    STUB | refs/heads/release/v1 | push | stub=false | labels=[] -> BLOCK
✅ [OK]    STUB | refs/heads/soak/test | push | stub=false | labels=[] -> BLOCK
✅ [OK]    STUB | refs/heads/shadow/v1 | push | stub=false | labels=[] -> BLOCK
✅ [OK]    STUB | refs/heads/any | schedule | stub=false | labels=[] -> BLOCK
✅ [OK]    STUB | refs/heads/feat/xyz | push | stub=false | labels=[] -> BLOCK
✅ [OK]    STUB | refs/heads/feat/xyz | workflow_dispatch | stub=true | labels=[] -> ALLOW
✅ [OK]    STUB | refs/heads/feat/xyz | pull_request | stub=false | labels=[allow-stub] -> ALLOW
✅ [OK]    STUB | refs/heads/main | workflow_dispatch | stub=true | labels=[] -> BLOCK
✅ [OK]    REAL | refs/heads/main | push | stub=false | labels=[] -> ALLOW
--------------------------------------------------------------------------------
Summary: ALL TESTS PASSED
```

## 6. Post-Fix Status: PASS
**Date:** 2025-01-24
**Verdict:** PASS (Post-Fix)

All identified workflows have been updated with strict guards.

### Implementation Traceability:

| Workflow | Guard Step (Decision) | Hard-Fail Step |
| :--- | :--- | :--- |
| `.github/workflows/e2e-tests.yml` | `Decide E2E mode (REAL vs STUB)` | `❌ Missing secrets or forbidden STUB (HARD FAIL)` |
| `.github/workflows/e2e.yml` | `Decide E2E mode (REAL vs STUB)` | `❌ Missing secrets or forbidden STUB (HARD FAIL)` |
| `.github/workflows/shadow-soak-evidence.yml` | `Decide E2E mode (REAL vs STUB)` | `❌ Missing secrets or forbidden STUB (HARD FAIL)` |

### Final Policy Enforcement:
1.  **Hard Fail on Missing Secrets:** All E2E workflows (`e2e.yml`, `e2e-tests.yml`, `shadow-soak-evidence.yml`) now check for the presence of ALL critical secrets (`MEXC`, `REDIS`, `POSTGRES`, `GRAFANA`, `SMTP`) before deciding the mode. If a secret is missing, `mode` is set to `STUB`.
2.  **Protected Branches:** STUB mode is strictly forbidden on `main`, `release/*`, `soak/*`, `shadow/*`, and scheduled runs. Any missing secret in these contexts triggers a job failure.
3.  **Opt-in for Dev:** STUB mode is only allowed on non-protected branches if explicitly opted-in via `workflow_dispatch` input `allow_stub: true` or the `allow-stub` label on Pull Requests.
4.  **No Hardcoded Stubs:** Hardcoded `WS_SOURCE: stub` in `shadow-soak-evidence.yml` was replaced with a conditional based on the verified `e2e_mode`.
5.  **Evidence of Logic:** The guard logic has been verified via simulation and proven to block unauthorized stub runs while allowing authorized ones.
