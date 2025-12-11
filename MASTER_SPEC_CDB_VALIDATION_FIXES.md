# MASTER SPEC – CDB VALIDATION FIXES & MIGRATION PREP
Version: 1.0  
Scope-Date: 2025-12-11

This document is the **single tactical specification** for all work that must be done before the new clean repository can be bootstrapped from the Claire de Binare codebase.

It consolidates:
- Gemini Validation Report (System-Level) – Global Status: BLOCKED  
- Claude Code Validation Report (Deep Technical) – Status: RED – NOT READY FOR MIGRATION

The goal is:
1. Remove all P0 blockers.
2. Prepare the system for the Repo Bootstrap Workflow (as defined in `CDB_WORKFLOWS.md`).
3. Leave a clean, deterministic playground for Claude, Codex and Copilot.

All work derived from this spec MUST respect:
- `CDB_GOVERNANCE.md`
- `CDB_FOUNDATION.md`
- `CDB_WORKFLOWS.md`
- `CDB_INSIGHTS.md`

---

## 0. OPERATING MODES & ROLES

### 0.1 Models & Roles

- **Claude**: Session Lead & Main Executor (Analysis → Plan → Delivery).
- **Codex**: Code-generation specialist. Executes concrete implementation tasks within the boundaries defined here.
- **Gemini**: Already used – source of validation findings, not active executor in this spec.
- **Copilot (GitHub)**: Optional assist for in-file refactors and small code edits, always under human supervision.

### 0.2 Modes

- **Analysis Mode (Default)**: Read-only, no file changes. Used only if new confusion appears.
- **Delivery Mode (Execution)**: Explicitly entered once a task is approved. All edits, branches and commits happen here.

The following sections are written so that **Claude or Codex** can execute them directly in Delivery Mode after human approval.

---

## 1. GLOBAL P0 BLOCKERS – OVERVIEW

These tasks MUST be completed before any Repo Bootstrap / Migration:

1. Fix Governance Paradox (Cleanroom violation).
2. Fix Service Documentation mismatch (missing services in `CDB_FOUNDATION.md`).
3. Resolve critical ENV inconsistencies (`MAX_EXPOSURE_PCT` vs `MAX_TOTAL_EXPOSURE_PCT`, zombie keys).
4. Remove undocumented zombie risk parameter (`CIRCUIT_BREAKER_THRESHOLD_PCT`) and document `MAX_SLIPPAGE_PCT`.
5. Consolidate duplicated `Signal` model across services.
6. Standardise core dependencies (Flask, Redis).
7. Remove legacy/broken services from `docker-compose.yml`.
8. Create the missing `.dockerignore` (orange flag but treated as high priority for migration hygiene).

After all P0 tasks are complete:
- Re-run both validation plans if needed (or at least a focused re-validation) to confirm status is GREEN/YELLOW.
- Then execute the Repo Bootstrap Workflow from `CDB_WORKFLOWS.md` (Repo Bootstrap).

---

## 2. P0-1 – FIX GOVERNANCE PARADOX (CLEANROOM)

### 2.1 Problem

- Canonical governance and workflow documents live in `.claude/` instead of the mandated cleanroom location (backoffice/docs).
- This violates the Cleanroom Mandate from `CDB_GOVERNANCE.md` and is the root of confusion and duplication.

### 2.2 Target State

- All canonical governance, roles and workflow documents are stored under:
  - `backoffice/docs/governance/`
- Any copies in `.claude/` are treated as **non-canonical artifacts** and either:
  - archived under `_archive/` (if still historically interesting), or
  - deleted if pure cache / working copies.

### 2.3 Concrete Tasks

1. **Identify Canonical Governance Files**  
   Examples (names may vary slightly, adjust to actual repo):
   - `CDB_GOVERNANCE.md`
   - `AGENTS.md`
   - `CDB_WORKFLOWS.md`
   - `CDB_FOUNDATION.md`
   - `CDB_INSIGHTS.md`
   - Any `*_GOVERNANCE_AND_RIGHTS.md`
   - Any `*_WORKFLOW_*.md` that are clearly canonical.

2. **Move to Cleanroom**  
   - Create (if not present) directory:
     - `backoffice/docs/governance/`
   - For each canonical file in `.claude/`:
     - If there is NO copy yet in `backoffice/docs/governance/`:
       - Move the file there and keep file name as-is.
     - If there IS already a copy:
       - Compare and merge content (most up-to-date version wins, clearly mark DEPRECATED sections before final removal).

3. **Update References**
   - Search the repo for old paths referencing `.claude/` versions (e.g. `.claude/CDB_GOVERNANCE.md`).
   - Update references so that all models and workflows refer to the `backoffice/docs/governance/` versions.

4. **Cleanup**
   - Remove canonical governance files from `.claude/` after successful migration.
   - Keep `.claude/` only as a working folder for models (if needed), never for canonical law.

### 2.4 Ownership

- **Design/Decision:** Human + Claude (Analysis Mode).
- **Implementation:** Claude or Codex (Delivery Mode).

---

## 3. P0-2 – FIX SERVICE DOCUMENTATION MISMATCH

### 3.1 Problem

- `CDB_FOUNDATION.md` does not fully match the services defined in `docker-compose.yml`.
- Specifically: `cdb_db_writer` and `cdb_paper_runner` are active services in compose but partially missing or misrepresented in the canonical services table.

### 3.2 Target State

- The services table in `CDB_FOUNDATION.md` accurately reflects all active services in `docker-compose.yml`:
  - `cdb_redis`
  - `cdb_postgres`
  - `cdb_prometheus`
  - `cdb_grafana`
  - `cdb_ws`
  - `cdb_core`
  - `cdb_risk`
  - `cdb_execution`
  - `cdb_db_writer`
  - `cdb_paper_runner`
- Any disabled / legacy services (`cdb_rest`, `cdb_signal_gen`) are either:
  - removed from compose, or
  - clearly marked as legacy and not part of Tier-1.

### 3.3 Concrete Tasks

1. **Read Current Compose**  
   - Open `docker-compose.yml`.
   - List all active (non-commented) services.

2. **Update `CDB_FOUNDATION.md` Services Table**  
   - For each active service, ensure a row exists in the services table with:
     - Service ID / name
     - Container name
     - Responsibility
     - Ports
     - Dependencies
     - Security Hardening status
   - Add missing rows for:
     - `cdb_db_writer`
     - `cdb_paper_runner`
   - Remove or move to "Legacy Services" any references to `cdb_rest` or `cdb_signal_gen` (see P0-7).

3. **Align Tier-1 classification**  
   - Ensure that `CDB_FOUNDATION.md` Section 17 (Minimal Artifact Set) lists `cdb_db_writer` and `cdb_paper_runner` correctly, in alignment with the validation findings.

### 3.4 Ownership

- **Design:** Claude (Analysis Mode) referencing `CDB_FOUNDATION.md` and compose.
- **Implementation:** Claude or Codex (Delivery Mode, editing markdown only).

---

## 4. P0-3 – ENV CONSISTENCY: MAX_EXPOSURE VS MAX_TOTAL_EXPOSURE

### 4.1 Problem

- `.env.example` uses `MAX_TOTAL_EXPOSURE_PCT` as the documented limit.
- Multiple Python modules use `MAX_EXPOSURE_PCT` (shorter name).
- This is a critical risk parameter – ambiguity here is unacceptable.

### 4.2 Target State

- Single canonical ENV variable name: `MAX_TOTAL_EXPOSURE_PCT`.
- `MAX_EXPOSURE_PCT` is treated as a **backwards-compatible alias only**, if needed.
- `CDB_FOUNDATION.md` and `.env.example` reflect this clearly.

### 4.3 Concrete Tasks

1. **Standardize Name in Code**
   - Search for `MAX_EXPOSURE_PCT` in the codebase.
   - Replace usages with `MAX_TOTAL_EXPOSURE_PCT` where appropriate.
   - Optionally implement a safe alias layer in configuration modules, e.g.:

   ```python
   # Example in risk_manager/config.py
   max_total_exposure_pct = float(
       os.getenv("MAX_TOTAL_EXPOSURE_PCT") 
       or os.getenv("MAX_EXPOSURE_PCT", "0.30")
   )
   ```

2. **Update `.env.example`**
   - Ensure it defines:
     - `MAX_TOTAL_EXPOSURE_PCT=0.30`
   - Optionally mention `MAX_EXPOSURE_PCT` in a commented line as a deprecated alias, e.g.:

   ```ini
   # MAX_EXPOSURE_PCT is deprecated – use MAX_TOTAL_EXPOSURE_PCT instead.
   ```

3. **Update Documentation**
   - In `CDB_FOUNDATION.md` (Risk parameters / KPIs table):
     - Ensure only `MAX_TOTAL_EXPOSURE_PCT` is listed as canonical.
     - Optionally add a short note on legacy alias.

4. **Sanity Check**
   - Verify that no code path relies solely on `MAX_EXPOSURE_PCT` after refactor.
   - Run unit tests for risk manager and any specific tests that cover exposure logic.

### 4.4 Ownership

- **Design & Implementation:** Codex is well-suited (simple deterministic changes) under Claude’s supervision.

---

## 5. P0-4 – ZOMBIE RISK PARAMETER & SLIPPAGE DOCUMENTATION

### 5.1 Problem

- `CIRCUIT_BREAKER_THRESHOLD_PCT` exists in `.env.example` but is undocumented and not wired into the canonical risk model. It’s a “zombie” parameter.
- `MAX_SLIPPAGE_PCT` is in ENV but not properly documented in the foundational risk documentation.

### 5.2 Target State

- No zombie risk parameters in `.env.example`.
- All risk-related ENV parameters are properly documented in `CDB_FOUNDATION.md`.

### 5.3 Concrete Tasks

1. **Remove Zombie Parameter**
   - Open `.env.example`.
   - Remove `CIRCUIT_BREAKER_THRESHOLD_PCT` (and any related zombie keys that are not used in code or docs).

2. **Document `MAX_SLIPPAGE_PCT`**
   - Confirm where `MAX_SLIPPAGE_PCT` is used (execution, risk, or simulation layer).
   - Add a row for `MAX_SLIPPAGE_PCT` in the risk parameter table in `CDB_FOUNDATION.md`:
     - Name
     - Default value
     - Layer
     - Effect of breach.

3. **ENV vs Code Sync**
   - Ensure the default values in code (if any) match the documented defaults.
   - Prefer using ENV-only configuration for critical risk parameters; if defaults exist in code, align them and document that behaviour.

### 5.4 Ownership

- **Implementation:** Codex for edits to `.env.example` and `CDB_FOUNDATION.md` with Claude supervising.

---

## 6. P0-5 – SIGNAL MODEL CONSOLIDATION (DRY VIOLATION)

### 6.1 Problem

- Two separate `Signal` dataclasses exist:
  - Producer side: `backoffice/services/signal_engine/models.py`
  - Consumer side: `backoffice/services/risk_manager/models.py`
- They share the same shape but are duplicated, violating DRY and governance requirements around clarity.

### 6.2 Target State

- Single canonical `Signal` model defined in a shared module.
- Both services import and use the same class.
- Event schema is maintained and explicit.

### 6.3 Concrete Tasks

1. **Introduce Shared Models Module**
   - Create a new module:
     - `backoffice/services/common/models.py`
   - Move the canonical `Signal` definition there, including `to_dict` and `from_dict` helpers if needed.
   - Optionally also consolidate other clearly shared models over time (e.g. `Order`, `Alert`, `OrderResult`).

2. **Update Producers & Consumers**
   - In `signal_engine/models.py` and `risk_manager/models.py`:
     - Remove duplicate `Signal` definitions.
     - Import `Signal` from `backoffice.services.common.models` (adjust import style to project conventions).

3. **Run Tests**
   - Run unit tests for signal engine and risk manager.
   - Run at least minimal integration/E2E tests covering the `signals` topic.

4. **Documentation**
   - Optionally update `CDB_FOUNDATION.md` (Event Flow & Messaging Model) to explicitly reference the shared `Signal` class as the implementation of the `signals` topic schema.

### 6.4 Ownership

- **Implementation:** Codex is ideal (mechanical refactor) with Claude validating with tests.

---

## 7. P0-6 – DEPENDENCY STANDARDIZATION (FLASK & REDIS)

### 7.1 Problem

- Mixed versions of Flask:
  - `3.0.0` and `3.1.2` across various requirements files.
- Mixed versions of Redis client:
  - `5.0.1` and `7.0.1` across services.
- This undermines reproducibility and can cause runtime issues.

### 7.2 Target State

- Unified versions across all relevant `requirements*.txt` files:
  - Flask → `3.1.2` (latest stable used in the system).
  - Redis → `5.0.1` (stable and tested in the current architecture).

### 7.3 Concrete Tasks

1. **Identify All Requirements Files**
   - `requirements.txt`
   - `requirements-dev.txt`
   - `backoffice/services/*/requirements.txt`
   - `services/cdb_paper_runner/requirements.txt`
   - Any other `requirements-*.txt` files.

2. **Standardise Flask Versions**
   - Replace any `Flask==3.0.0` with `Flask==3.1.2`.
   - Ensure no conflicting Flask versions remain.

3. **Standardise Redis Versions**
   - Replace any `redis==7.0.1` with `redis==5.0.1` (or the decided standard).
   - Ensure all services use the same version.

4. **Run Tests**
   - Run unit tests.
   - Run integration/E2E tests that touch HTTP services and Redis.

### 7.4 Ownership

- **Implementation:** Codex can apply changes safely, followed by Claude to run tests and validate.

---

## 8. P0-7 – REMOVE LEGACY/BROKEN SERVICES FROM COMPOSE

### 8.1 Problem

- `cdb_rest` and `cdb_signal_gen` are legacy/broken services:
  - `cdb_rest` disabled, missing proper entrypoint.
  - `cdb_signal_gen` orphaned and superseded by `cdb_core`.

### 8.2 Target State

- `docker-compose.yml` contains only valid, actively used services.
- Legacy services are removed or moved into a clearly marked legacy file.

### 8.3 Concrete Tasks

1. **Remove from `docker-compose.yml`**
   - Delete the full definitions for `cdb_rest` and `cdb_signal_gen` from the main `docker-compose.yml`.

2. **Optional: Create Legacy Compose (If Needed)**
   - If you want to keep them for history:
     - Create `docker-compose.legacy.yml`.
     - Move their definitions there, clearly marked as non-supported.

3. **Update Documentation**
   - Remove references to these services from any active documentation (`CDB_FOUNDATION.md`, `README`, etc.).
   - If mentioned historically, move them into a "Legacy" subsection.

4. **Sanity Check**
   - Run `docker-compose config` to ensure the compose file is valid.
   - Run tests and/or `systemcheck.py` to confirm all referenced services exist.

### 8.4 Ownership

- **Implementation:** Claude or Codex (simple YAML editing), validated by running `docker-compose config` and tests.

---

## 9. P0-8 – CREATE `.dockerignore`

### 9.1 Problem

- `.dockerignore` is missing.
- This increases build context size, build time and risk of secrets/logs accidentally ending up in images.

### 9.2 Target State

- A `.dockerignore` exists at the repository root and excludes all obvious non-build artifacts.

### 9.3 Suggested `.dockerignore` Baseline

The file should at least contain:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.so
*.egg-info/
*.egg
.build/

# Environments
.venv/
venv/
.env
.env.*
*.env

# Test / tooling caches
.pytest_cache/
.mypy_cache/
.cache/
.coverage
htmlcov/

# Editor / OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# Logs & runtime artefacts
logs/
*.log

# AI tooling / cache dirs
.claude/
.gemini/
.mcp/
```

Adjust paths according to the actual repo layout if needed.

### 9.4 Ownership

- **Implementation:** Claude or Codex, trivial risk.

---

## 10. P1 – HIGH PRIORITY REFACTORS (AFTER P0 IS DONE)

These are not strict blockers but strongly recommended before or shortly after migration.

### 10.1 Import Fallback Refactor

- Replace fragile `try/except` import patterns with a clean, consistent project/module layout and PYTHONPATH configuration.
- Goal: deterministic imports in both local and container environments.

### 10.2 Logging Config Path Parametrisation

- Replace hardcoded `/app/logging_config.json` paths with `LOGGING_CONFIG_PATH` ENV variable.
- Document this in `.env.example` and `CDB_FOUNDATION.md` (config section).

### 10.3 Default Passwords Removal

- Remove default passwords from `execution_service/config.py` and anywhere else.
- Enforce required ENV variables for secrets and fail fast if missing.

### 10.4 Message Schema Versioning

- Add `schema_version` field to all published events (`market_data`, `signals`, `orders`, `order_results`, `alerts`).
- Define default schema version (e.g. `"1.0"`) in shared models.
- Document versioning strategy in `CDB_FOUNDATION.md` under Event Flow.

---

## 11. P2 – NICE-TO-HAVE TASKS (POST-MIGRATION)

### 11.1 ENV Documentation Completion

- Use the ENV matrix from Claude’s validation report to ensure all relevant ENV variables are listed and explained in `.env.example` and/or `CDB_FOUNDATION.md`.

### 11.2 Tier-3 Clarification

- Confirm and document:
  - `mexc_perpetuals.py`
  - `position_sizing.py`
  - `execution_simulator.py`
  - `query_analytics.py`
  - `systemcheck.py`
- Classify clearly as Tier-2 or Tier-3 and reflect this in the docs.

### 11.3 Systemcheck Hardening

- Add tests for `backoffice/scripts/systemcheck.py`.
- Optionally integrate it into CI as a separate job.

---

## 12. EXECUTION ORDER (FOR CLAUDE / CODEX)

### 12.1 Recommended Sequence

1. Load mandatory context:
   - `CDB_GOVERNANCE.md`
   - `CDB_FOUNDATION.md`
   - `CDB_WORKFLOWS.md`
   - `CDB_INSIGHTS.md`

2. Execute P0 tasks in this order:
   1. Governance Paradox fix (Section 2).
   2. Service documentation sync (Section 3).
   3. ENV Exposure consolidation (Section 4).
   4. Zombie param removal + slippage doc (Section 5).
   5. Signal model consolidation (Section 6).
   6. Dependency standardization (Section 7).
   7. Compose legacy cleanup (Section 8).
   8. Create `.dockerignore` (Section 9).

3. Run tests:
   - `pytest -m "not e2e"`
   - Optional: `pytest -m e2e` if Docker stack is up.

4. If tests pass and no new blockers appear:
   - Proceed to Repo Bootstrap Workflow as defined in `CDB_WORKFLOWS.md` (Migration Workflow).

5. After migration:
   - Tackle P1 tasks (Section 10).
   - Then P2 tasks (Section 11) as capacity allows.

---

## 13. USAGE NOTES

- This spec is meant to be handed directly to:
  - **Claude** as the main execution brain.
  - **Codex** as implementation engine for specific, bounded tasks.
- No task in this spec assumes live trading; all work is infrastructure and configuration level.
- All changes must respect the Prime Directive: **Safety over Profit**.
