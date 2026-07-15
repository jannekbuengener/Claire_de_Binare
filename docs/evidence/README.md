# Evidence (`docs/evidence/`)

Scope-local evidence indices and audit artifacts. **Evidence ≠ Live-Readiness Go.**

## Sub-areas

| Path | Purpose |
|---|---|
| [`reports/`](reports/) | Reviewed, versioned historical/scope-local reports |
| [`runtime-runs/`](runtime-runs/) | Reviewed runtime-run snapshots |
| [`context_tooling/README.md`](context_tooling/README.md) | Context/MCP benchmark #2 ratification (#2847) |
| [`evidence_harvester_to_profitability_packet_mapping.md`](evidence_harvester_to_profitability_packet_mapping.md) | Harvester-to-Profitability Evidence Packet field mapping (#3380) |
| Shadow / soak (index) | [`SHADOW_SOAK_RUN_INDEX.md`](SHADOW_SOAK_RUN_INDEX.md) — linked from [`docs/index.md`](../index.md) |

## Rules

- PASS / FAIL here applies to the scoped run or benchmark, not repo-wide LR verdict.
- Offline replay/smoke artifacts do not authorize live capital.
- Generators write to `artifacts/reports/` or `artifacts/evidence-runs/`; promotion into this tree is explicit and reviewed.
- Prefer GitHub Actions run URLs + committed artifacts for audit trails.

## SSOT boundary

LR **NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
