# CDB Research Validation Pilot Spec v1

**Status:** SPECIFICATION_ONLY / PLANNED (#4272)
**Parent:** #4263
**Schema:** [`cdb.research_validation_pilot.v1`](../contracts/cdb_research_validation_pilot.v1.schema.json)
**Example:** [`examples/cdb_research_validation_pilot_valid.json`](../contracts/examples/cdb_research_validation_pilot_valid.json)
**Validator:** `tools/research_validation/pilot_spec_cross_contract.py`
**Live-Readiness:** NO-GO

## Purpose

Define a deterministic, versioned, machine-checkable pilot specification for
**exactly three** Research-to-Hermes strategy candidates. This slice describes a
future end-to-end validation run completely. It does **not** execute the pilot,
fetch provider data, invent EvidencePackets, or emit Decision verdicts.

## Three candidates

| `candidate_key` | Required sources | Intent |
|---|---|---|
| `breakout` | Binance + CoinMarketCap | Time-causal breakout hypothesis with external read-only regime context |
| `liquidity_or_volume_filter` | Binance + CoinMarketCap | Deterministic liquidity/volume filter excluding thin markets |
| `on_chain_regime_filter` | Token Terminal + Bigdata.com | On-chain regime filter with separate narrative research context |

All three candidates share:

- the same Wave-1/2/3 contract versions
- the same `validation-research-v1` profile
- the same security / integrity / Hermes gate path
- the same Execution Economics Gross-to-Net SSOT
- baseline + pessimistic liquidity/delay scenarios

No source receives special gate rights. Source adapters have no validation or
decision authority. Hermes remains orchestrator-only. TickerSage is visualization
only.

## Common contract path

For every candidate the planned path is:

1. `cdb.research_brief.v1`
2. `cdb.source_evidence.v1` (UNTRUSTED_INPUT / public market data)
3. `cdb.strategy_candidate.v1`
4. `cdb.validation_manifest.v1`
5. `cdb.research_security_gate.v1`
6. `cdb.hermes_orchestration_run.v1`
7. `cdb.candidate_evidence.v1` (expected slot only; NOT_RUN)
8. `cdb.decision_record.v1` (expected slot only; NOT_RUN)
9. `cdb.candidate_registry_entry.v1` / allowed transition (planned; no auto-promotion)

## Data, time, and provenance

- All timestamps UTC
- `research_cutoff`, `data_cutoff`, `decision_time`, `signal_bar_time`, and
  `earliest_execution_time` are separated
- No datum with `as_of` after `decision_time`
- Provider, surface/endpoint, identifiers, query parameters, and API version are
  bound in the pilot; dataset snapshot hashes remain `PENDING_BINDING` until a
  future real fetch
- Missing / partial / delayed / revised / unavailable data are fail-closed
- Provider-response provenance stays separate from SourceEvidence
- No credentials or account data in artifacts
- Token Terminal HTTP 200 with nonempty `errors` is not Source-PASS
- Bigdata Search/Retrieval remains UNTRUSTED_INPUT and cannot replace numeric
  validation evidence

## Execution economics and stress scenarios

Reuse SSOT: [`EXECUTION_ECONOMICS_GROSS_TO_NET_V1.md`](../contracts/EXECUTION_ECONOMICS_GROSS_TO_NET_V1.md)

Required components for all candidates:

- fees
- spread
- slippage
- fill assumptions
- reject assumptions
- latency_or_delay
- funding when relevant (else explicit N/A)

Scenarios:

| Scenario | Rule |
|---|---|
| `baseline` | All friction explicit or justified N/A; no silent zero costs |
| `pessimistic_liquidity_and_delay` | Higher spread, higher slippage, stricter fill/liquidity, additional delay, no positive price improvement |

The pilot defines parameters and computation path only. It does **not** invent
numeric results.

## Expected artifacts / no fake evidence

The pilot instantiates planned artifact **slots** with status `PLANNED` /
`NOT_RUN` / `PENDING_BINDING`.

Wave-1 `candidate_evidence` and `decision_record` schemas do not provide an
honest executed NOT_RUN packet. Therefore this slice does **not** commit fake
PASS/FAIL/PAPER_CANDIDATE fixtures. Expected refs are modeled inside the pilot
contract instead.

Forbidden in this slice:

- Invented backtest / PnL / drawdown / hit-rate values
- Invented provider responses
- Invented hashes for allegedly fetched datasets
- A PASS-looking EvidencePacket without an executed run

## TickerSage boundary

- Role: visualization of already produced results only
- `validation_authority: false`
- `decision_authority: false`
- Must not mutate metrics, weights, verdicts, or lifecycle transitions
- Public site retrieved 2026-08-01 shows analysis/heatmap UI; **no official API
  contract** found → human visualization option only

## Official external docs (retrieved 2026-08-01)

| Provider | Source used | Key binding for pilot |
|---|---|---|
| Binance | Official GitHub spot REST docs (`rest-api.md`); developers.binance.com HTML JS-blocked | Public `NONE` market data: klines/trades/aggTrades/depth; no TRADE/USER_DATA |
| CoinMarketCap | Official API docs landing | Historical OHLCV, pairs, global metrics; ID mapping; plan-dependent availability |
| Token Terminal | Official project historical metrics docs | Partial success + `errors` array; bearer auth; project/metric/chain/product bindings |
| Bigdata.com | Official REST introduction + docs index | Distinguish Search vs Research Agent vs Workflows; pilot uses REST Search |
| TickerSage | Public site | No API contract; visualization only |

CDB canon and CDB contracts remain leading over external docs.

## Authority and safety

All authority flags are false. LR remains **NO-GO**. Board `trade-capable` is
not Live-Go. Pilot status does not authorize Paper, Live, capital, risk bypass,
Hermes live authority, automatic promotion, productive DB writes, or ML/RL.

## Non-goals

- Pilot execution
- Productive market / on-chain / research fetches
- API keys or account data
- Hermes / worker / cloud runtime start
- TickerSage programmatic integration
- Gainium / Hugging Face as validation evidence
- ML / RL surfaces
- Merge / `cdb-local-ci` publish / Parent #4263 close
