# System Invariants
**Claire de Binare (CDB) Trading System**

**Version:** 1.0
**Status:** Active
**Last Updated:** 2026-02-09
**Canonical Location:** `Claire_de_Binare_Docs/knowledge/governance/SYSTEM_INVARIANTS.md`

---

## 1. Purpose & Scope

**What This Document Is:**
This document defines non-negotiable system contracts that govern CDB's deterministic behavior. Each invariant is enforced by tests, schemas, CI gates, database constraints, or guards. These invariants exist in code/docs/tests and are canonized here for human+agent readability.

**What This Is NOT:**
This is not a redesign proposal, implementation guide, or "nice to have" requirements list. Changes to invariants require updating both this document and their enforcement mechanisms. No invariant appears here without concrete references.

**Cross-Repo References:**
- Source-of-truth enforcement (tests, code, CI, schemas): Working Repo (`Claire_de_Binare`)
- Governance specs (LR-004-SPEC, META-001, LR-006-EVIDENCE): Working Repo (`Claire_de_Binare/docs/live-readiness/`)
- This document: Docs Hub (`Claire_de_Binare_Docs/knowledge/governance/`)

---

## 2. Definitions

**Deterministic**: Same inputs always produce same outputs. No probabilistic gates, no time-dependent randomness in decision logic.

**Fail-Closed**: Default action is BLOCK/REJECT unless all required checks explicitly PASS. Prevents false positives.

**Gate**: A conditional checkpoint that blocks progression unless criteria met. Examples: CI gates, trade placement gates, delivery gates.

**Contract**: Formal specification of interface behavior (schemas, message formats, API signatures). Protected by drift guards.

**Drift**: Unauthorized or unintended change to protected contract files. Detected via SHA256 fingerprints.

**Trace**: Artefact-based record of decision with replay-verifiable inputs, versions, constraints, and rationale.

---

## 3. Invariants

### INV-001: Fail-Closed Trade Decisions

**Statement:** Trade decisions MUST default to BLOCK unless ALL required checks explicitly PASS.

**Rationale:** Prevents false positives (unauthorized trades) which have higher impact than false negatives (missed trades).

**Enforcement:**
- Test: `tests/contract/test_decision_contract.py::test_decision_allow` (baseline ALLOW requires all checks)
- Code: `services/risk/service.py::decide_trade()` returns `DECISION_BLOCK` by default
- Spec: Working Repo `services/risk/README.md` documents "Default: BLOCK. Allow only if A ∧ B ∧ C"

**References:**
- Working Repo: `tests/contract/test_decision_contract.py` (16 deterministic tests)
- Working Repo: `services/risk/README.md` §Decision Contract 0/1 v1
- Working Repo: `services/risk/service.py::decide_trade()`

---

### INV-002: Risk-First Hierarchy

**Statement:** Risk Manager MUST gate all orders before Execution Service processes them. Execution CANNOT bypass Risk.

**Rationale:** Risk controls are the critical safety layer. Execution without risk validation violates fail-closed principle.

**Enforcement:**
- Architecture: Working Repo `services/risk/README.md` documents stream topology (signals → Risk → orders → Execution)
- Healthcheck: Working Repo `infrastructure/compose/healthchecks-strict.yml` (Execution depends_on Risk service_healthy)
- Docker: Working Repo `infrastructure/compose/base.yml` defines service dependencies

**References:**
- Working Repo: `services/risk/README.md` (architecture diagram flowchart lines 16-21)
- Working Repo: `infrastructure/compose/healthchecks-strict.yml::cdb_execution.depends_on`
- Working Repo: `infrastructure/compose/base.yml`

---

### INV-003: Deterministic Decision Ordering

**Statement:** Risk checks MUST execute in fixed hierarchical order: Safety/Anomaly → Data Freshness → Regime → Signal Thresholds → Portfolio Limits.

**Rationale:** First-fail semantics ensure higher-priority blockers (panic, stale data) take precedence over lower-priority ones (signal quality).

**Enforcement:**
- Test: `test_decision_first_fail_panic_wins`, `test_decision_first_fail_stale_wins_over_regime`
- Test: `test_decision_first_fail_regime_wins_over_signal`, `test_decision_first_fail_drawdown_wins_over_exposure`
- Code: Working Repo `services/risk/service.py::decide_trade()` implements fixed check sequence

**References:**
- Working Repo: `tests/contract/test_decision_contract.py::test_decision_first_fail_*` (4 ordering tests)
- Working Repo: `services/risk/README.md` §Decision Contract (First-Fail Reihenfolge line 52)
- Working Repo: `services/risk/service.py::decide_trade()`

---

### INV-004: Reason Code Determinism

**Statement:** All BLOCKED decisions MUST return an explicit reason code from the canonical taxonomy (RC_001-RC_022 for risk, RC_B001-RC_B402 for tasks).

**Rationale:** Enables deterministic replay, audit trails, and automated post-mortem analysis without speculation.

**Enforcement:**
- Test: 8 RC_* tests (`test_decision_rc_001_regime_block`, `test_decision_rc_002_panic_*`, `test_decision_rc_003_stale`, `test_decision_rc_004_data_silence`, `test_decision_rc_010_signal_thresholds`, `test_decision_rc_020_daily_drawdown`, `test_decision_rc_021_exposure`, `test_decision_rc_022_slippage`)
- Schema: Working Repo `docs/live-readiness/LR-004-SPEC.md` §5 defines RC_B taxonomy
- Guard: Working Repo `scripts/lr004_completion_guard.py` validates blocked_reason_code against taxonomy

**References:**
- Working Repo: `tests/contract/test_decision_contract.py` (8 RC_* tests)
- Working Repo: `services/risk/reason_codes.py` (8 RC constants)
- Working Repo: `docs/live-readiness/LR-004-SPEC.md` §5.2 Taxonomy Table
- Working Repo: `scripts/lr004_completion_guard.py::validate_blocked_reason_code()`

---

### INV-005: Trade Placement Human Gate

**Statement:** Delivery gate (`governance/DELIVERY_APPROVED.yaml`) MUST be approved by a human before merges to main. Only humans may modify this file (Constitution §4.2).

**Rationale:** Humans retain ultimate control over code reaching production. Prevents autonomous agent drift into unsafe states.

**Enforcement:**
- CI: Working Repo `.github/workflows/delivery-gate.yml` blocks PRs if `delivery.approved != true`
- Guard: Workflow fails with exit code 1 if not approved
- Exception: Labels `docs-only`, `ci-only`, `emergency` bypass gate

**References:**
- Working Repo: `governance/DELIVERY_APPROVED.yaml` (approved: true/false)
- Working Repo: `.github/workflows/delivery-gate.yml`
- Working Repo: `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md` §3 Delivery Gates

---

### INV-006: Live Trading Authorization Gate

**Statement:** Live trading MUST require successful 72-hour validation before FULL authorization level. Paper-only mode is enforced until validation passes.

**Rationale:** Prevents untested strategies from accessing real capital. Requires proof of operational correctness.

**Enforcement:**
- Code: Working Repo `services/risk/live_trading_gate.py::authorize_level()` validates test completion
- Code: Working Repo `services/validation/gate_evaluator.py::evaluate()` checks thresholds (min_orders=10, min_fill_rate=0.45)
- Spec: Working Repo `docs/live-readiness/LR-007-SPEC.md` defines 72-hour validation requirements

**References:**
- Working Repo: `services/risk/live_trading_gate.py::authorize_level()`
- Working Repo: `services/validation/gate_evaluator.py::GateThresholds`
- Working Repo: `docs/live-readiness/LR-007-SPEC.md`

---

### INV-007: Contract Drift Protection (Fingerprint Guard)

**Statement:** Four protected contract files MUST NOT change without updating LR-003 fingerprint. CI blocks drift automatically.

**Protected Files:**
1. `docs/contracts/market_data.schema.json`
2. `docs/contracts/signal.schema.json`
3. `services/risk/reason_codes.py`
4. `tests/contract/test_decision_contract.py`

**Rationale:** Breaking contract changes risk inter-service communication failures. Fingerprint guard makes drift visible and intentional.

**Enforcement:**
- Guard: Working Repo `scripts/lr003_contract_drift_guard.py --check` computes SHA256, compares to fingerprint
- CI: Working Repo `.github/workflows/contracts.yml` runs guard, blocks on exit code 1
- Fingerprint: Working Repo `docs/live-readiness/LR-003-FINGERPRINT.json` stores combined SHA256

**References:**
- Working Repo: `scripts/lr003_contract_drift_guard.py::check_drift()`
- Working Repo: `docs/live-readiness/LR-003-FINGERPRINT.json`
- Working Repo: `docs/live-readiness/LR-003-EVIDENCE.md`
- Working Repo: `.github/workflows/contracts.yml`

---

### INV-008: Schema Strictness (additionalProperties: false)

**Statement:** Inter-service message contracts MUST set `additionalProperties: false` in JSON schemas. Undefined fields are rejected.

**Rationale:** Prevents schema drift via undocumented fields. Forces explicit schema versioning for new fields.

**Enforcement:**
- Schema: Working Repo `docs/contracts/market_data.schema.json::additionalProperties: false`
- Schema: Working Repo `docs/contracts/signal.schema.json::additionalProperties: false`
- Test: Working Repo `tests/contract/test_decision_contract.py` validates contract compliance
- CI: Working Repo `.github/workflows/contracts.yml` validates schemas

**References:**
- Working Repo: `docs/contracts/market_data.schema.json` line 6
- Working Repo: `docs/contracts/signal.schema.json` line 6
- Working Repo: `.github/workflows/contracts.yml`

---

### INV-009: Schema Version Immutability

**Statement:** Message `schema_version` field MUST be const (e.g., "v1.0"). Breaking changes require new schema file with incremented version.

**Rationale:** Enables runtime schema negotiation and backward compatibility detection.

**Enforcement:**
- Schema: Working Repo `docs/contracts/market_data.schema.json::schema_version: {const: "v1.0"}`
- Schema: Working Repo `docs/contracts/signal.schema.json::schema_version: {const: "v1.0"}`
- CI: Working Repo `.github/workflows/contracts.yml` validates schema syntax

**References:**
- Working Repo: `docs/contracts/market_data.schema.json::properties.schema_version` line 17
- Working Repo: `docs/contracts/signal.schema.json::properties.schema_version`

---

### INV-010: No Secrets in Decision Traces

**Statement:** Decision traces MUST use config hashes or Tresor references instead of inline secrets (API keys, passwords, credentials).

**Rationale:** Traces are stored in Git. Inline secrets create leak risk. Config hashes preserve replay-verifiability without exposing sensitive data.

**Enforcement:**
- Specification: Working Repo `docs/live-readiness/LR-006-EVIDENCE.md` AC14 "No Tresor-Zone References"
- Example: LR-006-EVIDENCE.md Example 1 uses `config_hash: "sha256:..."` instead of inline config
- Policy: Working Repo `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md` §4 No-Secrets-Guarantee

**References:**
- Working Repo: `docs/live-readiness/LR-006-EVIDENCE.md` §AC14 line 307
- Working Repo: `docs/live-readiness/LR-006-EVIDENCE.md` Example 1 line 46 (config_hash usage)
- Working Repo: `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md` §4 Capabilities line 68

---

### INV-011: Artefact-Based Traceability

**Statement:** All decision traces MUST use strict artefact reference format: `git:<sha>:<path>#L<start>-L<end>`, `snapshot://<path>@<timestamp>`, `sha256:<hash>`.

**Rationale:** Machine-readable references enable automated replay verification. No ambiguous "see file X" references.

**Enforcement:**
- Specification: Working Repo `docs/live-readiness/LR-006-EVIDENCE.md` §AC8-AC9
- Example: All three traces in LR-006-EVIDENCE.md use strict format
- Policy: Working Repo `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md` §4 Artefakt-Referenzen

**References:**
- Working Repo: `docs/live-readiness/LR-006-EVIDENCE.md` Examples 1-3 (evidence field format)
- Working Repo: `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md` §4 line 66

---

### INV-012: Git-Native Task State (No GitHub API)

**Statement:** LR task state MUST be stored in Git-native YAML files (`LR-*-STATE.yaml`). No dependency on GitHub Issues API or UI.

**Rationale:** GitHub API is external dependency with rate limits, authentication, and UI inconsistencies. Git-native state is deterministic and audit-capable via `git log`.

**Enforcement:**
- Specification: Working Repo `docs/live-readiness/LR-004-SPEC.md` §1 Purpose
- Manifest: Working Repo `docs/live-readiness/LR-TASKS.yaml` (canonical task list)
- Guard: Working Repo `scripts/lr004_completion_guard.py` validates STATE files against manifest
- CI: Working Repo `.github/workflows/ci.yaml` runs validation on every PR/push

**References:**
- Working Repo: `docs/live-readiness/LR-004-SPEC.md` §3 Task Manifest
- Working Repo: `docs/live-readiness/LR-TASKS.yaml`
- Working Repo: `scripts/lr004_completion_guard.py::validate_state_files()`
- Working Repo: `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md` §2 line 17

---

### INV-013: Terminal States Only (DONE/BLOCKED)

**Statement:** LR task state MUST be exactly DONE or BLOCKED. No intermediate states (IN_PROGRESS, PENDING, etc.).

**Rationale:** Binary terminal states eliminate ambiguity. Tasks are either complete (evidence file + criteria met) or blocked (reason code + resolution needed).

**Enforcement:**
- Schema: Working Repo `docs/live-readiness/LR-004-SPEC.md` §4.4 (status enum: DONE | BLOCKED)
- Guard: Working Repo `scripts/lr004_completion_guard.py` Rule V009 validates enum
- Policy: Working Repo `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md` §4 Terminal States Only

**References:**
- Working Repo: `docs/live-readiness/LR-004-SPEC.md` §4.4 Field Specifications line 150
- Working Repo: `scripts/lr004_completion_guard.py::validate_status_enum()`
- Working Repo: `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md` §4

---

### INV-014: Conditional Field Atomicity (DONE ⊕ BLOCKED)

**Statement:** DONE state MUST have completion_timestamp + completion_author (blocked_* fields null). BLOCKED state MUST have blocked_reason_code + blocked_reason_text + blocked_since (completion_* fields null). No mixing.

**Rationale:** Prevents invalid states like "DONE but still blocked" or "BLOCKED but has completion_timestamp". Atomic state transitions only.

**Enforcement:**
- Schema: Working Repo `docs/live-readiness/LR-004-SPEC.md` §4.2-4.3 (conditional requirements)
- Guard: Working Repo `scripts/lr004_completion_guard.py` Rules V010-V011 (DONE/BLOCKED completeness)
- Specification: Working Repo `docs/live-readiness/LR-004-SPEC.md` §7.2-7.3 State Transition Rules

**References:**
- Working Repo: `docs/live-readiness/LR-004-SPEC.md` §4.4 Conditional Requirements line 160
- Working Repo: `scripts/lr004_completion_guard.py::validate_done_state()`, `validate_blocked_state()`
- Working Repo: `docs/live-readiness/LR-004-SPEC.md` §7.2-7.3

---

### INV-015: Service Dependency Health Ordering

**Statement:** Execution Service MUST NOT start until Risk Service is healthy. Enforced via Docker healthcheck dependencies.

**Rationale:** Execution without risk validation violates fail-closed principle. Health ordering ensures correct startup sequence.

**Enforcement:**
- Docker: Working Repo `infrastructure/compose/healthchecks-strict.yml::cdb_execution.depends_on.cdb_risk.condition: service_healthy`
- Healthcheck: Risk service validates Redis/Postgres connectivity before reporting healthy
- Base: Working Repo `infrastructure/compose/base.yml` defines base service structure

**References:**
- Working Repo: `infrastructure/compose/healthchecks-strict.yml::cdb_execution.depends_on`
- Working Repo: `infrastructure/compose/base.yml`

---

### INV-016: Database Runtime Invariants (CHECK Constraints)

**Statement:** PostgreSQL schema MUST enforce invariants via CHECK constraints. Examples: `signal_type IN ('buy', 'sell')`, `confidence >= 0 AND confidence <= 1`, `size > 0`, `filled_size <= size`.

**Rationale:** DB layer enforcement prevents invalid data from entering persistence layer. Fail-closed at runtime.

**Enforcement:**
- Schema: Working Repo `infrastructure/database/schema.sql` (CHECK constraints on all tables)
- Runtime: PostgreSQL rejects INSERT/UPDATE violating constraints
- Examples: Lines 26-34 (signals), 77-78 (orders)

**References:**
- Working Repo: `infrastructure/database/schema.sql` lines 26-34 (signals table constraints)
- Working Repo: `infrastructure/database/schema.sql` lines 77-78 (orders table constraints)

---

### INV-017: Reason Code Taxonomy Completeness

**Statement:** Blocked task reason codes MUST be from canonical taxonomy RC_B001-RC_B402 (15 codes defined). Unknown codes are rejected.

**Rationale:** Enables structured analysis of blockers. Taxonomy enforces consistency across tasks and agents.

**Enforcement:**
- Schema: Working Repo `docs/live-readiness/LR-004-SPEC.md` §5.2 defines 15 RC_B codes
- Guard: Working Repo `scripts/lr004_completion_guard.py` Rule V013 validates against hardcoded taxonomy
- Specification: Working Repo `docs/live-readiness/LR-004-SPEC.md` §5.4 Selection Guidelines

**References:**
- Working Repo: `docs/live-readiness/LR-004-SPEC.md` §5.2 Taxonomy Table lines 177-195
- Working Repo: `scripts/lr004_completion_guard.py::VALID_REASON_CODES`
- Working Repo: `docs/live-readiness/LR-004-SPEC.md` §5.4

---

### INV-018: Manifest Immutability (Append-Only)

**Statement:** LR task manifest (`LR-TASKS.yaml`) is append-only. task_id is immutable once added. Tasks marked DONE remain in manifest permanently.

**Rationale:** Historical record of all tasks. Prevents "hiding" incomplete work by deleting manifest entries.

**Enforcement:**
- Specification: Working Repo `docs/live-readiness/LR-004-SPEC.md` §3.4 Manifest Rules (Immutability + Append-Only)
- Guard: Working Repo `scripts/lr004_completion_guard.py` Rule V002 detects duplicate task_ids
- Policy: PR review required for manifest changes

**References:**
- Working Repo: `docs/live-readiness/LR-004-SPEC.md` §3.4 Manifest Rules lines 74-80
- Working Repo: `scripts/lr004_completion_guard.py::validate_manifest()`
- Working Repo: `docs/live-readiness/LR-TASKS.yaml`

---

### INV-019: Deterministic Replay-Verifiability

**Statement:** Decision traces MUST be replay-verifiable from artefacts alone without code re-execution. Trace includes input_set + version_set + constraint_set + evidence artefacts.

**Rationale:** Enables post-mortem analysis, audit compliance, and incident explainability without access to running system.

**Enforcement:**
- Specification: Working Repo `docs/live-readiness/LR-006-EVIDENCE.md` (Example 1 includes full replay walkthrough)
- Walkthrough: Lines 83-147 demonstrate manual replay verification
- Policy: Working Repo `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md` §4 Replay-Fähige Decisions

**References:**
- Working Repo: `docs/live-readiness/LR-006-EVIDENCE.md` §Replay Verification Walkthrough lines 83-147
- Working Repo: `docs/live-readiness/META-001-GOVERNANCE_FOUNDATION.md` §4 line 63
- Working Repo: `docs/live-readiness/LR-006-EVIDENCE.md` §AC4

---

### INV-020: No Confidence-Based Gating

**Statement:** Signal confidence field MUST be informational only. Trade decisions MUST NOT gate on probabilistic confidence scores.

**Rationale:** Deterministic thresholds (pct_change, volume) are replay-verifiable. Confidence scores introduce probabilistic non-determinism.

**Enforcement:**
- Code: Working Repo `services/risk/service.py::decide_trade()` does not reference confidence field
- Contract: Working Repo `services/risk/README.md` §Decision Contract "Confidence ist kein Gate"
- Model: Working Repo `services/signal/models.py` defines confidence as optional informational field

**References:**
- Working Repo: `services/risk/README.md` line 54 (Confidence ist kein Gate)
- Working Repo: `services/risk/service.py::decide_trade()`
- Working Repo: `services/signal/models.py` (Signal dataclass)

---

## 4. Canonical Map

| Invariant | Primary Enforcing Artefact |
|-----------|----------------------------|
| INV-001: Fail-Closed Trade Decisions | `tests/contract/test_decision_contract.py` (16 tests) |
| INV-002: Risk-First Hierarchy | `infrastructure/compose/healthchecks-strict.yml` |
| INV-003: Deterministic Decision Ordering | `tests/contract/test_decision_contract.py::test_decision_first_fail_*` |
| INV-004: Reason Code Determinism | `services/risk/reason_codes.py` + 8 RC_* tests |
| INV-005: Trade Placement Human Gate | `.github/workflows/delivery-gate.yml` |
| INV-006: Live Trading Authorization Gate | `services/risk/live_trading_gate.py` |
| INV-007: Contract Drift Protection | `scripts/lr003_contract_drift_guard.py` + LR-003-FINGERPRINT.json |
| INV-008: Schema Strictness | `docs/contracts/*.schema.json::additionalProperties: false` |
| INV-009: Schema Version Immutability | `docs/contracts/*.schema.json::schema_version: {const: "v1.0"}` |
| INV-010: No Secrets in Decision Traces | `docs/live-readiness/LR-006-EVIDENCE.md` AC14 |
| INV-011: Artefact-Based Traceability | `docs/live-readiness/LR-006-EVIDENCE.md` Examples 1-3 |
| INV-012: Git-Native Task State | `scripts/lr004_completion_guard.py` + LR-TASKS.yaml |
| INV-013: Terminal States Only | `scripts/lr004_completion_guard.py::validate_status_enum()` |
| INV-014: Conditional Field Atomicity | `scripts/lr004_completion_guard.py` Rules V010-V011 |
| INV-015: Service Dependency Health Ordering | `infrastructure/compose/healthchecks-strict.yml` |
| INV-016: Database Runtime Invariants | `infrastructure/database/schema.sql` CHECK constraints |
| INV-017: Reason Code Taxonomy Completeness | `docs/live-readiness/LR-004-SPEC.md` §5.2 + lr004_completion_guard.py |
| INV-018: Manifest Immutability | `docs/live-readiness/LR-004-SPEC.md` §3.4 |
| INV-019: Deterministic Replay-Verifiability | `docs/live-readiness/LR-006-EVIDENCE.md` Example 1 walkthrough |
| INV-020: No Confidence-Based Gating | `services/risk/README.md` + decide_trade() implementation |

**Note:** All paths in Canonical Map refer to Working Repo (`Claire_de_Binare`) unless explicitly prefixed.

---

## 5. Change Policy

**Invariant Modification Requirements:**

1. **Update References:** All file paths, test names, and enforcement mechanisms referenced in the invariant entry must be updated to reflect changes.

2. **Enforcement Verification:** All enforcement mechanisms (tests, CI gates, guards, constraints) must pass after change. No drift allowed.

3. **LR-003 Fingerprint Implications:** If invariant change touches protected files (`market_data.schema.json`, `signal.schema.json`, `reason_codes.py`, `test_decision_contract.py`), LR-003 fingerprint MUST be regenerated via Working Repo `scripts/lr003_contract_drift_guard.py --generate`.

4. **Proof of Enforcement:** Change PR must include evidence that:
   - Tests still pass (or new tests added if invariant strengthened)
   - CI gates enforced (no bypass)
   - Documentation updated (this file + referenced specs)

5. **Human Approval Required:** Invariant changes require explicit human review and approval (delivery gate §4.2). Autonomous agents cannot modify invariants without human sign-off.

**Adding New Invariants:**

- New invariant MUST have concrete enforcement (test/schema/CI/guard)
- New invariant MUST have file path references (no vague "see docs")
- New invariant MUST align with fail-closed, deterministic principles

**Removing Invariants:**

- Removal requires same rigor as addition: update enforcement, update references, human approval
- Removal without replacement requires explicit rationale (security, technical limitation, policy change)

---

**End of System Invariants v1.0**
