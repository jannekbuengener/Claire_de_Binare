# Deterministic Gate Fix - 2026-02-03

## Session Metadata
- **Timestamp**: 2026-02-03 15:27:53 UTC
- **Branch**: `main`
- **Commit (before)**: `d1a3613398536ea491471bc879da4eacf1fcced7`
- **Issue**: Deterministic Gate not enforced in CI (silent bypass)
- **Fix Type**: Policy enforcement - CI workflow modification

## Problem Statement

### Discovery
After systematic test execution (2026-02-03 15:19:45), discovered that the deterministic gate (Issue #430) is **NEVER enforced in CI**.

### Root Cause
Gate activation logic in `tests/conftest.py:277-291`:
```python
def _should_enable_gate(config) -> bool:
    args = [str(arg).replace("\\", "/").rstrip("/") for arg in config.args]
    if "tests" not in args:  # ← CRITICAL CHECK
        return False
    if config.option.markexpr:
        return False
    return True
```

### CI Configuration
**File**: `.github/workflows/ci.yaml:221`
**Command**: `pytest -v -m "not e2e and not local_only"`
- Uses marker expression → Gate disabled (line 283: `if config.option.markexpr`)

**File**: `.github/workflows/ci.yml:62`
**Command**: `pytest -q`
- No explicit path args → `config.args = []`
- Uses `testpaths = tests` from pytest.ini (implicit)
- `"tests" not in args` → Gate disabled

### Verification
```python
# Test simulation:
config_args_when_pytest_q = []           # CI case
config_args_when_pytest_tests = ['tests'] # Gate-enabled case

should_enable_gate([]) → False          # ❌ CI bypasses gate
should_enable_gate(['tests']) → True    # ✅ Gate would work
```

### Impact
**All CI runs bypass the deterministic gate:**
- Threshold: 254/302 tests must pass (conftest.py:257)
- Actual enforcement: NONE
- Result: Green CI checkmark = **self-deception**

---

## Solution Implemented

### New CI Job: `deterministic-gate`
**File**: `.github/workflows/ci.yaml:282-302`

```yaml
deterministic-gate:
  name: Deterministic Gate (full collection)
  runs-on: ubuntu-latest
  steps:
    - name: Checkout code
      uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

    - name: Setup Python
      uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
      with:
        python-version: '3.12'
        cache: 'pip'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        pip install pytest pytest-cov

    - name: Run deterministic gate
      run: pytest -q tests/
```

### Key Design Decisions

#### ✅ Explicit path: `pytest -q tests/`
- **Not** `pytest -q` (would bypass gate via implicit testpaths)
- **Not** `pytest -m ...` (would bypass gate via markexpr)
- Explicitly passes `tests/` as argument → `"tests" in config.args` → Gate enabled

#### ✅ Full test collection
- No marker filtering
- Collects all 360 tests (including e2e, local_only, etc.)
- E2E tests will be skipped (expected), but gate enforces:
  - `total_pass >= 254` (conftest.py:332)
  - `e2e_total == 5` (conftest.py:328)
  - `e2e_pass == 5` (conftest.py:330)

#### ✅ Python 3.12 (latest stable)
- Matches CI standard (`env.PYTHON_VERSION: '3.12'`)
- Single version to avoid matrix noise in gate enforcement

#### ✅ Positioned after `e2e_happy_path`
- Logical flow: fast tests → slow tests → gate validation
- Runs in parallel with security checks (no blocking dependency)

---

## Integration into CI Pipeline

### Updated Dependencies
**File**: `.github/workflows/ci.yaml:435`
```yaml
build-summary:
  name: Build Summary
  runs-on: ubuntu-latest
  needs: [core-guard, lint, format-check, type-check, test, e2e_happy_path,
          deterministic-gate,  # ← ADDED
          secrets-scan, trivy-scan, security-audit, dependency-audit, docs-check]
```

### Updated Summary Report
**File**: `.github/workflows/ci.yaml:449`
```yaml
echo "- Deterministic Gate: ${{ needs.deterministic-gate.result }}" >> $GITHUB_STEP_SUMMARY
```

---

## Expected Behavior

### When Gate Activates
1. `pytest -q tests/` runs with full test collection
2. conftest.py detects `"tests" in config.args` → `enabled = True`
3. pytest_runtest_logreport counts passed tests
4. pytest_sessionfinish checks:
   - `total_pass >= 254` (TOTAL_MIN_PASS)
   - `e2e_total == 5` (E2E_EXPECTED_COUNT)
   - `e2e_pass == 5` (E2E_EXPECTED_COUNT)
5. **If any check fails**: `session.exitstatus = 1` → CI fails

### Gate Enforcement Points (conftest.py:321-337)
```python
def pytest_sessionfinish(session, exitstatus):
    if not _GATE_STATE.enabled:
        return  # ← Previous CI runs returned here (gate disabled)

    gate_failed = False
    if _GATE_STATE.e2e_total != E2E_EXPECTED_COUNT:
        gate_failed = True
    if _GATE_STATE.e2e_pass != E2E_EXPECTED_COUNT:
        gate_failed = True
    if _GATE_STATE.total_pass < TOTAL_MIN_PASS:
        gate_failed = True

    if gate_failed and session.exitstatus == 0:
        session.exitstatus = 1  # ← Force fail exit code
```

### Current Baseline Expectation
From test execution evidence (2026-02-03 15:19:45):
- **Unit tests**: 155 passed, 14 skipped
- **Integration tests**: 6 passed, 3 skipped
- **Total**: 161 passed (unit + integration CI subset)

**Full collection** (pytest tests/):
- Expected: ~302 tests collected (per conftest.py:255 comment)
- Expected skipped: e2e (containers), local_only, slow, chaos, external (~48 tests)
- Expected passed: >= 254 (TOTAL_MIN_PASS)

**NOTE**: Actual collection count may differ from 302 (codebase evolved since Issue #430). Gate will enforce whatever the current baseline is.

---

## Next Steps

### 1. Immediate: Test the Fix Locally
```bash
# Simulate CI gate behavior:
pytest -q tests/

# Expected:
# - Gate activates (sees "tests" in args)
# - Full collection (360 tests)
# - Skips e2e/local_only (no containers)
# - Reports pass/fail counts
# - Checks gate thresholds
```

### 2. Required: Set as Required Status Check
**GitHub Settings** → Repository → Branches → Branch protection rules → `main`
- Add `Deterministic Gate (full collection)` to required status checks
- This enforces gate before any PR merge to main

### 3. Optional: Recalibrate Threshold
If gate fails in CI due to threshold mismatch:
- Current: 254/302 (set in Issue #430)
- Actual: TBD after first CI run
- Update `TOTAL_MIN_PASS` in conftest.py:257 if needed

### 4. Policy Documentation
Update docs to clarify:
- **Fast CI jobs** (`test`, `e2e_happy_path`) can use markers for optimization
- **Deterministic gate** enforces full collection baseline (no markers)
- Green CI = fast tests pass + gate threshold met

---

## Verification Checklist

- [x] New job added to ci.yaml (lines 282-302)
- [x] Job uses explicit `pytest -q tests/` (not implicit testpaths)
- [x] No marker filtering (no `-m` flag)
- [x] Python 3.12 (latest stable)
- [x] Job added to build-summary needs (line 435)
- [x] Job added to build-summary output (line 449)
- [ ] Test locally: `pytest -q tests/` activates gate
- [ ] Set as required status check in GitHub
- [ ] Monitor first CI run for threshold validation
- [ ] Update conftest.py threshold if needed

---

## Files Changed

### `.github/workflows/ci.yaml`
**Lines 282-302**: New `deterministic-gate` job
**Line 435**: Added to `build-summary` dependencies
**Line 449**: Added to summary output

---

## Outcome

**Before**: CI green = self-deception (gate never enforced)
**After**: CI green = policy-compliant (gate enforces 254+ pass threshold)

**Enforcement**: Once set as required status check, PRs **cannot merge** to main unless:
1. All existing CI jobs pass (lint, test, security, etc.)
2. Deterministic gate passes (254+ tests, 5 e2e tests collected)

**No more silent bypass. Green means green.**

---

## Related Issues
- #430: Deterministic gate implementation
- #427: Gate threshold baseline establishment
- Evidence: knowledge/logs/sessions/2026-02-03_test_execution_evidence.md
