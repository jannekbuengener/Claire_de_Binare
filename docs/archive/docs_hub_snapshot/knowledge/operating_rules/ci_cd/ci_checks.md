# CI Checks Documentation

## Core Guard

**Purpose:** Prevents core duplicates and secrets.py proliferation

**Workflow:** `.github/workflows/core-guard.yml`

**Script:** `scripts/check_core_duplicates.py`

**Tests:** `tests/unit/scripts/test_check_core_duplicates.py`

**When it runs:**
- All PRs to `main`
- All pushes to `main`
- Manual trigger via `workflow_dispatch`

**Rules enforced:**

1. **No core duplicates:**
   - Forbidden: `services/*/core/**` directories
   - Only `core/` at repo root is allowed
   - Example violation: `services/signal/core/utils.py`

2. **Single secrets.py:**
   - Allowed: `core/domain/secrets.py` only
   - Forbidden: Any other `secrets.py` files
   - Example violation: `services/risk/secrets.py`

**Exit codes:**
- `0` - All checks passed
- `1` - Violations detected

**Output format:**
```
✅ CI-Guard PASSED
```
or
```
❌ CI-Guard FAILED
  FORBIDDEN: core duplicate at services/signal/core
  FORBIDDEN: secrets.py at services/risk/secrets.py
```

**How to fix violations:**

1. **Core duplicate:**
   - Move code from `services/*/core/` to `core/`
   - Update imports to use central `core/` module
   - Remove service-specific core directory

2. **secrets.py duplicate:**
   - Consolidate secrets into `core/domain/secrets.py`
   - Use centralized secret reading
   - Remove service-specific secrets.py

**Maintenance:**

- **Owner:** @jannekbuengener, @copilot
- **Required check:** Yes (blocks PRs when failing)
- **Bypass:** Not recommended (violates governance)

**Related:**
- Issue #415: Re-enable core-guard job
- PR #399: Temporary disablement during CI recovery
- Issue #355: CI/CD back to green epic
