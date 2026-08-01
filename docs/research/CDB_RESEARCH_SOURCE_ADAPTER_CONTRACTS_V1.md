# CDB Research Source Adapter Contracts v1

**Status:** Wave-2 contract surface (#4267)
**Parent:** #4263
**Depends on:** Wave-1 contracts (PR #4278 / `54de13d`)
**Mode:** Schemas + docs + synthetic fixtures only
**Live-Readiness:** NO-GO

## Purpose

Normalize heterogeneous research sources into a single read-only
`cdb.source_evidence.v1` envelope. Sources remain **UNTRUSTED_INPUT**. They never
issue PASS/FAIL, PAPER_CANDIDATE, Live-Go, or promotion decisions.

## Shared SourceEvidence contract

Schema: [`docs/contracts/cdb_source_evidence.v1.schema.json`](../contracts/cdb_source_evidence.v1.schema.json)

Required fields:

| Field | Rule |
|---|---|
| `schema_version` | `cdb.source_evidence.v1` |
| `evidence_id` | `se-…` |
| `source_type` | one of six adapter profiles |
| `source_reference` | synthetic or read-only reference string |
| `retrieved_at` | ISO-8601 |
| `observation_window` | `{start,end}` |
| `claim` / `claim_type` | observation/metric/narrative/hypothesis/preset/reference |
| `uncertainty` | non-empty |
| `missing_data` | explicit list; empty allowed but never reinterpreted as success |
| `conflict_state` | `NONE` / `MARKED_CONFLICT` / `UNRESOLVED` |
| `provenance` | adapter profile + `retrieval_mode=read_only` + `synthetic_fixture=true` for fixtures |
| `content_hash` | `sha256:…` |
| `trust_classification` | const `UNTRUSTED_INPUT` |
| `validation_authority` | const `false` |
| `decision_authority` | const `false` |
| `contains_secrets` | const `false` |
| `contains_account_data` | const `false` |

## Adapter profiles (capabilities / non-authority)

| Source | `source_type` | Allowed outputs | Explicitly not |
|---|---|---|---|
| Binance | `binance` | candles, trades, spot/futures reference, mark/index/premium as `MARKET_OBSERVATION` / `METRIC` | live credentials, order placement, PASS/FAIL |
| CoinMarketCap | `coinmarketcap` | global regime, derivatives, macro events, narratives | validation authority |
| Token Terminal | `token_terminal` | protocol metrics, chain activity, fundamental trends | truth resolution of conflicts |
| Bigdata.com | `bigdata_com` | news/research/macro narratives with source-backed claims | inventing resolved consensus |
| Gainium | `gainium` | strategy presets / indicator families / parameter **ideas** (`PRESET_IDEA`) | validated parameters |
| Hugging Face | `hugging_face` | papers/datasets/research references (`RESEARCH_REFERENCE` / `HYPOTHESIS_MATERIAL`) | ML/RL into CDB |

## Invariants

- Research content is always `UNTRUSTED_INPUT`.
- Missing data is listed in `missing_data`; never treated as null-success.
- Conflicting sources use `MARKED_CONFLICT` / `UNRESOLVED`; adapters do not invent resolution.
- Foreign backtests are `HYPOTHESIS_MATERIAL` only.
- SourceEvidence must never set PASS, FAIL, or PAPER_CANDIDATE.
- No secrets, account data, API keys, or productive credentials in fixtures or candidates.

## Producer / Consumer

| Role | Responsibility |
|---|---|
| Producer (future adapter / human research) | Emit valid SourceEvidence; mark uncertainty/conflicts/missing |
| Consumer (Candidate Compiler) | Consume as untrusted input only |
| Non-consumers | Risk, Execution, Live gates, Hermes promotion |

## Failure paths (fail-closed)

| Condition | Result |
|---|---|
| Authority flags true | Schema reject |
| Secrets/account flags true | Schema reject |
| Missing timestamp/claim/uncertainty/provenance/hash | Schema reject |
| Claim type used as validation verdict | Schema reject |
| Conflict presented as safe resolved claim | Docs + validator reject path |

## Non-goals

- No runtime adapter implementation
- No external API calls from product code
- No API key configuration / plugin installation
- No validation or decision authority for sources

## Related

- Compiler: [`CDB_STRATEGY_CANDIDATE_COMPILER_V1.md`](CDB_STRATEGY_CANDIDATE_COMPILER_V1.md)
- Registry: [`CDB_GITHUB_CANDIDATE_REGISTRY_V1.md`](CDB_GITHUB_CANDIDATE_REGISTRY_V1.md)
- Canon: [`CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md`](CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md)
