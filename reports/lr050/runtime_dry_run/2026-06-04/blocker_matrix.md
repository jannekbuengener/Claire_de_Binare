# Blocker Matrix

Status vocabulary:
- `proven`
- `partial`
- `blocker_before_live`
- `not_tested`

| Checkpoint | Status | Evidence | Note |
| --- | --- | --- | --- |
| Effective safe flags before execution-path command | proven | `effective_config_redacted.json` | current shell overrides absent; repo defaults stay safe |
| `MOCK_TRADING=true` default resolves `mock_builtin` | proven | repo reads in `external_adapter_registry.py`, `compose.blue.yml`, `services/execution/config.py` | default adapter selection is repo-backed |
| `DRY_RUN=true` direct executor branch | proven | `execution_dry_run_evidence.md` | direct `LiveExecutor(dry_run=True)` harness returned `DRY_RUN_*` result with `client_is_none=true` |
| `TRADING_MODE=staged` is not accepted as dry-run proof | proven | repo reads in `core/config/trading_mode.py`, `services/execution/service.py`, `LR-050-VENUE-AUDIT.md` | active execution path does not wire `TRADING_MODE` |
| `MEXC_TESTNET=true` is not accepted as non-send proof | proven | `LR-050-DRY-RUN-PROOF.md`, `LR-050-VENUE-AUDIT.md`, `core/clients/mexc.py` | testnet path is still exchange-capable when dry-run/mock are off |
| Execution-service shadow gate | proven | targeted pytest | `SHADOW_BLOCKED` path exercised in unit set |
| Execution-service kill-switch gate | proven | targeted pytest | `KILL_SWITCH_BLOCKED` and fail-closed error path exercised |
| Risk-service kill-switch HTTP endpoints | proven | targeted pytest | activate / deactivate / status all green with repo-local basetemp |
| Risk-side contract enforcement | proven | targeted pytest | strict contract identity and kill-switch block behavior green |
| Order-builder full runtime path | partial | `order_builder_dry_run_evidence.md` | adjacent contract and gate logic exercised; full runtime builder path not run |
| Running BLUE stack effective env with unknown overrides | not_tested | intentionally withheld | no Docker / service boot in `#2951` slice |
| Venue / testnet / WS endpoint semantics external verification | blocker_before_live | `LR-050-VENUE-AUDIT.md` | repo-only inventory; external semantics unproven |
| Canary numeric caps and symbols | blocker_before_live | `LR-050-RISK-LIMITS.md`, `LR-050-CANARY-PLAN.md` | remain `TBD_BLOCKER_BEFORE_LIVE` |
| Receiver proof / operator receipt | blocker_before_live | `LR-050-OBSERVABILITY-GATES.md`, `LR-050-CANARY-PLAN.md` | no runtime receipt artifact on `main` |
| Exact Human Approval for live capital | blocker_before_live | `LR-050-HUMAN-APPROVAL.md` | still absent |
| LR global verdict uplift | blocker_before_live | `LR-AUDIT-STATUS-2026-03-05.md`, `LR-050-FINAL-RECONCILE.md` | LR remains `NO-GO` |
