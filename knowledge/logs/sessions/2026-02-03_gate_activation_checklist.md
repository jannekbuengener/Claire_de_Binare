# Deterministic Gate Activation Checklist - 2026-02-03

## Status: READY FOR ACTIVATION

### Implementation Complete ✅
- [x] Job `deterministic-gate` added to `.github/workflows/ci.yaml` (lines 282-301)
- [x] Python version aligned to 3.11 (test matrix baseline - lowest supported)
- [x] Redundant pip install removed (pytest already in requirements-dev.txt)
- [x] Explicit `pytest -q tests/` command (no markers, triggers gate)
- [x] Job integrated into `build-summary` dependencies
- [x] Job added to summary output

### Job Configuration (Final)
```yaml
deterministic-gate:
  name: Deterministic Gate (full collection)  # ← Required status check name
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'  # Match test matrix baseline
    - run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - run: pytest -q tests/  # ← Explicit tests/ activates gate
```

### Design Validation ✅

#### ✅ Job Name Correct
- **GitHub Branch Protection uses**: `name: Deterministic Gate (full collection)`
- **NOT** the job key: `deterministic-gate:`
- Status check to add: **"Deterministic Gate (full collection)"** (exact match)

#### ✅ Python Version Aligned
- Test matrix: `['3.11', '3.12']`
- Gate uses: `3.11` (baseline - lowest supported)
- **Rationale**: Gate enforces minimum baseline, not latest features
- Prevents "passes in gate, fails in test matrix" inconsistency

#### ✅ Dependencies Non-Redundant
- `requirements-dev.txt` contains: `pytest==7.4.4`, `pytest-cov==4.1.0`
- No duplicate `pip install pytest pytest-cov` needed
- Single source of truth for test dependencies

#### ✅ Gate Activation Guaranteed
- Command: `pytest -q tests/` (explicit path)
- conftest.py check: `if "tests" not in args: return False`
- Result: `"tests" in config.args` → Gate enabled ✅

---

## NEXT STEP (CRITICAL): Activate Required Status Check

### GitHub Repository Settings
1. Navigate to: **Settings** → **Branches** → **main**
2. Find: **Branch protection rules for main**
3. Enable: **Require status checks to pass before merging**
4. Search for: `Deterministic Gate (full collection)`
5. **Add** this check to required list

### Important Notes
- Status check name appears AFTER first CI run on a PR
- If not visible yet: Create a test PR, wait for CI, then add check
- Once added: **No PR can merge** without gate passing

---

## Verification Steps

### 1. Local Test (Before Push)
```bash
# Simulate gate behavior:
pytest -q tests/

# Expected output:
# - Gate enabled message (if verbose)
# - ~360 collected tests
# - ~48 skipped (e2e, local_only without containers)
# - 254+ passed (threshold check)
# - Exit code 0 if pass, 1 if gate fails
```

### 2. Test PR Workflow
1. Create test branch: `git checkout -b test/deterministic-gate`
2. Make trivial change (e.g., update this checklist)
3. Push and create PR
4. Watch CI: **Deterministic Gate (full collection)** should appear
5. Verify: Job runs `pytest -q tests/` (check logs)
6. Verify: Gate activation message in pytest output (if verbose)
7. Verify: Exit code matches pass/fail (0 = pass, 1 = fail)

### 3. Branch Protection Activation
1. After test PR shows the status check
2. Go to Settings → Branches → main
3. Add `Deterministic Gate (full collection)` to required checks
4. Verify: "Required" badge appears next to check name

### 4. Enforcement Test
1. Create PR that intentionally fails tests (comment out a test)
2. Verify: Gate fails with exit code 1
3. Verify: GitHub blocks merge with "Required status check failed"
4. Revert change, verify: Gate passes, merge allowed

---

## Expected Behavior After Activation

### Gate Thresholds (conftest.py:255-257, 328-333)
```python
TOTAL_MIN_PASS = 254  # Minimum passing tests
E2E_EXPECTED_COUNT = 5  # E2E tests from test_smoke_pipeline.py
```

### Gate Checks
1. **Total Pass**: `total_pass >= 254`
2. **E2E Collection**: `e2e_total == 5` (collected, not necessarily run)
3. **E2E Pass**: `e2e_pass == 5` (if run, must all pass)

### Pass Scenarios
- ✅ 254+ tests pass, 5 E2E tests collected (skipped OK if no containers)
- ✅ 300+ tests pass, 5 E2E tests run and pass (full local run)

### Fail Scenarios
- ❌ <254 tests pass (regression in unit/integration tests)
- ❌ E2E tests not collected (test file missing/renamed)
- ❌ E2E tests collected but <5 pass (if containers available)

---

## Rollback Plan (If Needed)

### If Gate Blocks Legitimate PRs
1. **Quick Fix**: Remove from required status checks temporarily
2. **Investigate**: Check actual pass counts in CI logs
3. **Recalibrate**: Update `TOTAL_MIN_PASS` in conftest.py:257
4. **Re-enable**: Add back to required checks

### If Gate Threshold Needs Adjustment
```python
# tests/conftest.py:257
# Old:
TOTAL_MIN_PASS = 254

# New (example if codebase evolved):
TOTAL_MIN_PASS = 260  # Update to current baseline
```

### Emergency Bypass (Discouraged)
- Admin override: Merge PR without status check (requires admin permissions)
- **Only use for**: Critical hotfixes where gate failure is investigated separately
- **Always**: Create follow-up issue to fix gate or recalibrate threshold

---

## Success Criteria

### Technical
- [x] Job exists in ci.yaml
- [x] Job runs `pytest -q tests/` (explicit path)
- [x] Python 3.11 (test matrix baseline)
- [x] No redundant dependencies
- [x] Integrated into build-summary

### Process
- [ ] Test PR created and CI passes
- [ ] Status check appears in GitHub
- [ ] Status check added to branch protection
- [ ] Enforcement tested (fail scenario blocks merge)

### Policy
- [ ] Green CI = 254+ tests pass (auditable)
- [ ] No silent gate bypass
- [ ] Required before merge to main

---

## Documentation Updates Needed

### 1. Update README or CONTRIBUTING.md
```markdown
## CI Requirements

All PRs to `main` must pass:
- Lint (Ruff)
- Format (Black)
- Type Check (mypy)
- Tests (Python 3.11 + 3.12 matrix)
- **Deterministic Gate (254+ tests pass)** ← Add this
- Security scans (Gitleaks, Trivy, Bandit)

The Deterministic Gate ensures consistent test baseline across all PRs.
```

### 2. Update conftest.py Comment
```python
# tests/conftest.py:255
# Issue #430: Threshold reflects CI baseline enforced by required status check
# Updated: 2026-02-03 - Enforced via .github/workflows/ci.yaml:deterministic-gate
TOTAL_MIN_PASS = 254
```

---

## Related Files
- **CI Workflow**: `.github/workflows/ci.yaml:282-301`
- **Gate Logic**: `tests/conftest.py:255-337`
- **Evidence**: `knowledge/logs/sessions/2026-02-03_deterministic_gate_fix.md`
- **Test Evidence**: `knowledge/logs/sessions/2026-02-03_test_execution_evidence.md`

---

## Final Status

**Implementation**: ✅ COMPLETE
**Testing**: ⏳ PENDING (awaiting test PR)
**Activation**: ⏳ PENDING (awaiting branch protection update)

**Ready for**: Test PR creation and branch protection activation

**Once activated**: Green CI badge = policy-compliant, auditable, enforceable baseline
