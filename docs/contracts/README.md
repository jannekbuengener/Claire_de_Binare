# Contracts (`docs/contracts/`)

Repo-backed JSON/YAML schemas und Contract-Dokumente für Messages, Replay und Context Tooling.

## Layout

| Area | Path | Notes |
|---|---|---|
| Message schemas | `market_data.schema.json`, `signal.schema.json`, … | CI/validation |
| Context tooling | [`context_tooling/`](context_tooling/) | MCP evidence contracts |
| Examples | [`examples/`](examples/) | Valid/invalid fixtures |
| Replay | [`REPLAY_CONTRACTS_AND_DETERMINISM.md`](REPLAY_CONTRACTS_AND_DETERMINISM.md) | Determinism rules |
| Profitability | `profitability_candidate_contract.v1.schema.json`, `profitability_evidence_packet.v1.schema.json` | Strategy candidate and evidence packet research contracts |
| Profitability data quality | `profitability_dataset_quality_report.v1.schema.json` | Dataset quality gate report for candidate validation |

## Related canon (not duplicated here)

| Domain | Canonical path |
|---|---|
| Strategy contracts (narrative) | [`knowledge/contracts/README.md`](../../knowledge/contracts/README.md) |
| Runtime decision bundle | [`core/contracts/`](../../core/contracts/) (`decision_contract_v1`) |
| Market state (risk input) | [`docs/governance/MARKET_STATE_CONTRACT_V1.md`](../governance/MARKET_STATE_CONTRACT_V1.md) |

## SSOT boundary

Contracts definieren Verhalten; sie ersetzen weder LR-Verdikt noch Board-Stage. LR **NO-GO**.
