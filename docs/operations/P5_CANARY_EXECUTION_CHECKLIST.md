# P5 Canary Execution Checklist

- Control: `LR-050`
- Status: `NO-GO`
- Last updated: `2026-03-20`

This checklist is a governance mapping document only. It does not authorize live trading.

## 1. Purpose

Map the P5 canary policy to real repository evidence paths and clearly separate:

- shadow-prereq evidence
- committed P5 core artifacts
- implemented controls from still-open blockers

## 2. Shadow Prereq Evidence Anchors

- `LR-030` (shadow mode zero-execution hard gate)
  - `docs/evidence/LR-030.md`
  - `tests/unit/services/test_execution_shadow_gate.py`
  - `tests/integration/test_execution_pipeline.py`
  - `.github/workflows/shadow-soak-evidence.yml`
  - `infrastructure/scripts/soak_gate_eval.py` — fail-closed gate (schema 1.1)
  - `infrastructure/scripts/generate_evidence_index.py`
  - `infrastructure/scripts/build_shadow_evidence_package.py`
- `LR-031` (shadow metrics comparison)
  - `docs/evidence/LR-031.md`
  - `infrastructure/scripts/generate_evidence_index.py`
  - `infrastructure/scripts/soak_gate_eval.py`
  - `infrastructure/scripts/build_shadow_evidence_package.py`
  - `tests/test_generate_evidence_index.py`
  - `tests/unit/scripts/test_soak_gate_eval.py`
  - `tests/unit/scripts/test_build_shadow_evidence_package.py`

Within these anchors:

- `shadow` names the probe / intent / evidence path
- the canonical runtime-mode field remains `execution_status.mode`
- for the current P5 / shadow-prereq path, the required runtime-mode value is `mock`

## 3. PR1 Hardened Gate Requirements

As of `#1127` PR1, the soak gate evaluation (`soak_gate_eval.py` schema 1.1) enforces:

- `has_live_data_true` — signal flow must be proven during soak
- `orders_approved_eq_0` — risk must approve zero orders
- `risk_blocked_all_true` — risk must block all received orders
- `runtime_mode_verified` — execution service must report `execution_status.mode == "mock"` for the current P5 / shadow-prereq path
- `kill_switch_precheck_inactive` — circuit breaker must be explicitly `false`
- `execution_status.json` and `risk_status.json` are required artifacts (missing = exit 1)

These checks are in addition to the original shadow-probe invariants (shadow_blocked >= 1, orders_filled == 0, auditable REJECTED probe).
The workflow terms `full|lean` refer to soak / collection profile labels and are not runtime-mode values.

## 4. Current Control Map

| Control | Status | Evidence | Note |
|---------|--------|----------|------|
| LR-001 | IMPLEMENTED | `docs/live-readiness/LR-001-EVIDENCE.md` | Control-specific evidence |
| LR-003 | IMPLEMENTED | `docs/live-readiness/LR-003-EVIDENCE.md` | Control-specific evidence |
| LR-010 | IMPLEMENTED | `docs/live-readiness/LR-010-EVIDENCE.md` | Control-specific evidence 2026-03-19: unit tests for circuit breakers, risk engine core, edge cases |
| LR-020 | IMPLEMENTED | `docs/live-readiness/LR-020-EVIDENCE.md` | Tier-1 CI tests + Tier-2 live-stack run (FILLED). Historical run: precondition gating not explicit pre-run (see evidence doc §5). Prechecks now automated fail-closed in capture script schema 1.2. |
| LR-030 | IMPLEMENTED | `docs/evidence/LR-030.md` | Fail-closed gate with PR1 hardening |
| LR-031 | IMPLEMENTED | `docs/evidence/LR-031.md` | Comparison layer implemented, thresholds calibrated, verdict PASS |
| LR-040 | IMPLEMENTED | `docs/evidence/LR-040.md` | Gate evaluator + monitoring tooling, no 72h run evidence yet |
| LR-041 | IMPLEMENTED | `docs/evidence/LR-041.md` | Deterministic Redis/Postgres restart recovery drill, runner merged, local drill evidence passed |
| LR-042 | IMPLEMENTED | `docs/evidence/LR-042.md` | Control-specific evidence |

## 5. Current No-Go Reasons

- No committed successful P5 canary run artifact set
- `LR-020` now has control-specific evidence (Tier-1 CI + Tier-2 live-stack run); the original Tier-2 run's operational preconditions (kill-switch state, runtime mode) were not explicitly verified pre-run — only inferable ex post from run outcome (see `docs/live-readiness/LR-020-EVIDENCE.md` §5). These prechecks are now automated and fail-closed in the capture script (schema 1.2); this does not alter the historical run artifact and does not constitute P5 approval.
- `LR-040` is IMPLEMENTED but no 72h soak run evidence exists yet (PASS requires actual run)
- `LR-031` is IMPLEMENTED: comparison layer calibrated and PASS verified (2026-03-16)

## 6. Runtime-Mode and Kill-Switch Semantics

- Normative source: `governance/p5_canary_readiness.yaml`
- Canonical runtime-mode field: `execution_status.mode`
- Required runtime-mode value for the current P5 / shadow-prereq path: `mock`
- `shadow` is reserved for probe / intent / evidence semantics and is not the canonical runtime-mode value
- `full|lean` are soak / collection profile labels and are not runtime-mode values
- Kill-switch precheck: `docs/operations/KILL_SWITCH_OPERATOR_CHECKLIST.md`
- Kill-switch verification in gate: `soak_gate_eval.py` check `kill_switch_precheck_inactive`
- Circuit breaker source: risk service `/status` endpoint field `risk_state.circuit_breaker`

## 7. P5 Core Artifact Contract

Committed P5 core artifacts are separate from optional shadow-prereq evidence.

Normative root:

- `reports/p5_canary/<YYYY-MM-DD>/`

Required committed P5 core files:

- `manifest.json`
- `prestart_evidence_lock.yaml`
- `decision_record.yaml`
- `endpoints/execution_status.json`
- `endpoints/risk_status.json`
- `endpoints/kill_switch_status.json`
- `lr040/lr040_soak_gate_eval.json`

Optional reused shadow-prereq evidence:

- `shadow_prereq/manifest.json`
- `shadow_prereq/package_manifest.json`

## 8. Related Technical Artifacts

- `reports/shadow_mode/LIVE_TRADING_HUMAN_GATE_CHECKLIST.md` (historical — incident gate 2026-02-03, not current prestart gate; see §9)
- `knowledge/logs/sessions/2026-02-03_gate_activation_checklist.md`
- `docs/operations/KILL_SWITCH_OPERATOR_CHECKLIST.md`
- `scripts/governance/check_branch_protection_drift.py`
- `scripts/lr003_contract_drift_guard.py`
- `tests/resilience/test_fault_injection.py`
- `scripts/drills/lr042_network_latency_packet_loss_runner.py`
- `infrastructure/scripts/soak_gate_eval.py`
- `infrastructure/scripts/build_shadow_evidence_package.py`
- `infrastructure/scripts/generate_evidence_index.py`
- `scripts/governance/check_window_timer_guardrail.py`

## 9. Prestart Pack

When all NO-GO blockers are resolved, the operator MUST complete the prestart evidence lock
before any P5 canary start attempt:

- Template: `docs/operations/P5_PRESTART_PACK.md`
- This document backs the compensating controls defined in `governance/p5_canary_readiness.yaml`:
  - `prestart_evidence_lock`
  - `canonical_runtime_mode_precheck`
  - `decision_record_before_start`
  - `no_code_or_config_change_after_prestart_lock`
- Stack anchor: BLUE (`infrastructure/compose/compose.blue.yml`) — kill-switch at Port 8002,
  execution at Port 8003, risk at Port 8002.
- A completed, committed instance of the Prestart Pack is a required artifact before any P5 start.
- P5 start remains blocked (NO-GO) until LR-040 72h PASS and a committed canary artifact set exist.
