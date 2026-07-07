# Main Runtime P2 Test Map

Scope: Issue #3841 (parent #3830).

Machine-readable map:

- `.github/control-plane/generated/agent-main-runtime-test-map.json`
- Contract: `tests/unit/runtime/test_main_runtime_test_map_contract.py`

The map links **behavior → service → test → fixture** for the six required
surfaces (market, regime, signal, risk, execution, validation) plus supplemental
P1 cross-cutting entries.

Guards:

- `coverage: partial` — no complete-coverage claim
- `known_unmapped_runtime_surfaces` lists candles/allocation/ws/db_writer gaps
- missing mappings are explicit findings in contract tests

LR remains **NO-GO**.
