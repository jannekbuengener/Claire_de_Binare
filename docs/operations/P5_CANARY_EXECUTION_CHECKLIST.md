# P5 Canary Execution Checklist

- Control: `LR-050`
- Status: `NO-GO`
- Last updated: `2026-03-10`

This checklist is a governance mapping document only. It does not authorize live trading.

## 1. Purpose

Map the P5 canary policy to real repository evidence paths and clearly separate implemented controls from still-open blockers.

## 2. Shadow Evidence Anchors

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

## 3. PR1 Hardened Gate Requirements

As of `#1127` PR1, the soak gate evaluation (`soak_gate_eval.py` schema 1.1) enforces:

- `has_live_data_true` — signal flow must be proven during soak
- `orders_approved_eq_0` — risk must approve zero orders
- `risk_blocked_all_true` — risk must block all received orders
- `runtime_mode_verified` — execution service must report `mode == "mock"`
- `kill_switch_precheck_inactive` — circuit breaker must be explicitly `false`
- `execution_status.json` and `risk_status.json` are required artifacts (missing = exit 1)

These checks are in addition to the original shadow-probe invariants (shadow_blocked >= 1, orders_filled == 0, auditable REJECTED probe).

## 4. Current Control Map

| Control | Status | Evidence | Note |
|---------|--------|----------|------|
| LR-001 | IMPLEMENTED | `docs/live-readiness/LR-001-EVIDENCE.md` | Control-specific evidence |
| LR-003 | IMPLEMENTED | `docs/live-readiness/LR-003-EVIDENCE.md` | Control-specific evidence |
| LR-010 | **OPEN** | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Tracking reference only, no dedicated evidence |
| LR-020 | **OPEN** | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Tracking reference only, no dedicated evidence |
| LR-030 | IMPLEMENTED | `docs/evidence/LR-030.md` | Fail-closed gate with PR1 hardening |
| LR-031 | **PARTIAL** | `docs/evidence/LR-031.md` | Gate plumbing implemented, broader metrics comparison still open |
| LR-040 | **OPEN** | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Tracking reference only, no 72h soak evidence |
| LR-041 | **OPEN** | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Tracking reference only, no chaos drill evidence |
| LR-042 | IMPLEMENTED | `docs/evidence/LR-042.md` | Control-specific evidence |

## 5. Current No-Go Reasons

- No committed successful P5 canary run artifact set
- `LR-010`, `LR-020` remain OPEN with no control-specific evidence
- `LR-040`, `LR-041` remain OPEN with no control-specific evidence
- `LR-031` is PARTIAL: gate plumbing done, broader comparison evidence still open
- Controls pointing to `LR-AUDIT-STATUS-2026-03-05.md` are tracking references, not executable proof

## 6. Kill-Switch and Runtime-Mode References

- Kill-switch precheck: `tools/test_pack/runbooks/kill_switch_checklist.md`
- Kill-switch verification in gate: `soak_gate_eval.py` check `kill_switch_precheck_inactive`
- Runtime-mode verification in gate: `soak_gate_eval.py` check `runtime_mode_verified`
- Circuit breaker source: risk service `/status` endpoint field `risk_state.circuit_breaker`
- Runtime-mode source: execution service `/status` endpoint field `mode`

## 7. Related Technical Artifacts

- `reports/shadow_mode/LIVE_TRADING_HUMAN_GATE_CHECKLIST.md`
- `knowledge/logs/sessions/2026-02-03_gate_activation_checklist.md`
- `tools/test_pack/runbooks/kill_switch_checklist.md`
- `scripts/governance/check_branch_protection_drift.py`
- `scripts/lr003_contract_drift_guard.py`
- `tests/resilience/test_fault_injection.py`
- `scripts/drills/lr042_network_latency_packet_loss_runner.py`
- `infrastructure/scripts/soak_gate_eval.py`
- `infrastructure/scripts/build_shadow_evidence_package.py`
- `infrastructure/scripts/generate_evidence_index.py`
- `scripts/governance/check_window_timer_guardrail.py`
