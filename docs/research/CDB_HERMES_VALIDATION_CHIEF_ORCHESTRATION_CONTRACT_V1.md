# Hermes Validation Chief Orchestration Contract v1

**Status:** Contract-only Wave-3 orchestration surface (#4270)
**Parent:** #4263
**Depends-on:** Security / provenance / integrity gate (#4271 / PR #4285)
**Mode:** Docs / schema / cross-contract validator / unit tests — no productive Hermes runtime
**Live-Readiness:** NO-GO
**Board stage:** `trade-capable` ≠ Live-Go

## Purpose

Define a fail-closed, machine-checkable orchestration contract for the Hermes
Validation Chief. Hermes may structure, start, monitor, and collect evidence for
CDB validation runs. Hermes receives **no** validation, risk, live, capital, or
promotion authority.

Free-form agent prose is never a valid orchestration result. The leading output
is always a structured verdict bound to immutable input hashes.

## Pipeline placement

```text
[Security / Provenance / Integrity Gate]  cdb.research_security_gate.v1
        |  PASS|WARNING → may request orchestration
        |  FAIL|BLOCKED|REVIEW_REQUIRED → orchestration must not PASS
        v
[Hermes Validation Chief]  cdb.hermes_orchestration_run.v1   <-- this contract
        |  select allowed worker type
        |  request ValidationManifest-bound run
        |  monitor attempts / classify failures
        |  collect hashed evidence
        v
[Candidate Evidence + Decision Record]
        |
        +--> structured orchestration verdict only
             (PASS ≠ validation authority ≠ Live-Go ≠ PAPER promotion)
```

## Required entities

| Entity | Role |
|---|---|
| `HermesOrchestrationRun` | Top-level run record (`cdb.hermes_orchestration_run.v1`) |
| `OrchestrationStep` | Ordered orchestration step with status |
| `StructuredVerdict` | Machine verdict + rationale codes (no free-form lead) |
| `TechnicalFailure` | Retryable / non-retryable infrastructure failure |
| `DomainFailure` | Contract / validation / security / drift failure |
| `RetryDisposition` | Explicit retryability decision |
| `EvidenceCollectionStatus` | Completeness of hashed artifacts |
| `DriftStatus` | Binding-invalidating drift class |

## Required bindings (immutable for the run)

Every run and every attempt must carry identical bindings:

- `run_id`
- `strategy_candidate_id` + `strategy_candidate_version` + `candidate_content_hash`
- `validation_manifest_id` + `validation_manifest_hash`
- `security_gate_id` + `security_gate_hash` (gate version optional, hash required)
- `code_head_ref` + `code_head_sha`
- dataset hash bindings
- produced artifact hashes (required before orchestration `PASS`)

A changed binding is not a retry. It requires a **new** `run_id`.

## Allowed Hermes actions

1. Formally validate inbound contracts (schema + cross-contract).
2. Load bound `ValidationManifest` and required security-gate references.
3. Select an allowed worker type from the closed allow-list.
4. Request a structured validation run against frozen bindings.
5. Monitor run / attempt status.
6. Classify technical failures.
7. Trigger only explicitly retryable technical retries (new `attempt_id`).
8. Collect evidence artifacts.
9. Verify hash and binding completeness.
10. Publish a structured verdict to downstream contract surfaces.

## Forbidden Hermes actions

1. Change strategy parameters during a run.
2. Invent or fill missing parameters.
3. Reclassify a domain failure as a technical failure.
4. Rewrite a domain `FAIL` into `PASS`.
5. Bypass the security gate.
6. Accept evidence without hash bindings.
7. Ignore or retry-mask code / candidate / manifest / gate / dataset / artifact drift.
8. Change or bypass risk limits.
9. Activate live trading.
10. Automatically promote a paper candidate or strategy.
11. Release capital.
12. Emit a free-form closing opinion as the leading verdict.

## Failure taxonomy

### Technical failures

Examples: `RUNNER_UNAVAILABLE`, `NETWORK_TRANSIENT`, `WORKER_START_TIMEOUT`,
`STATUS_POLL_TIMEOUT`, `ARTIFACT_TRANSFER_FAILED`.

Rules:

- Retry only when `retryable: true`.
- Max attempts and backoff are mandatory fields on the run.
- Each try gets a unique `attempt_id`.
- Bindings must be byte-identical across attempts.
- A technical retry must not conceal candidate / manifest / head / dataset change.

### Domain failures

Examples: `RESEARCH_CONTRACT_INVALID`, `VALIDATION_FAILED`,
`EVIDENCE_INCOMPLETE`, `SECURITY_BLOCKED`, `DRIFT_INVALIDATED`,
`DATA_UNAVAILABLE_AS_CONTRACTED`.

Rules:

- No automatic technical retry.
- Repeating the same invalid input cannot become `PASS`.
- Structured verdict must be `FAIL`, `BLOCKED`, or `REVIEW_REQUIRED`
  (or `CANCELLED` when explicitly cancelled).

## Verdicts

Allowed: `PASS | FAIL | BLOCKED | REVIEW_REQUIRED | TECHNICAL_RETRY_PENDING | CANCELLED`

Invariants:

1. Hermes never emits free-form judgment as the leading result.
2. `PASS` requires complete evidence and all required hash bindings.
3. Security-gate `FAIL` / `BLOCKED` / `REVIEW_REQUIRED` prevents orchestration `PASS`.
4. Incomplete evidence prevents `PASS`.
5. Any invalidating drift prevents `PASS`.
6. Orchestration `PASS` is **not** validation authority, Live-Go, paper promotion,
   risk bypass, or capital release.

## Drift rules

Invalidating: `HEAD_DRIFT`, `CANDIDATE_DRIFT`, `MANIFEST_DRIFT`,
`SECURITY_GATE_DRIFT`, `DATASET_DRIFT`, `ARTIFACT_DRIFT`.

Behavior:

- Prior `PASS` evidence becomes invalid.
- The run must not continue under silently changed inputs.
- Changed inputs require a new run with new bindings.
- Retries must not mask drift.

## External docs evidence (adapter-facing only)

**Retrieved:** 2026-08-01 (Europe/Berlin session).

Official sources only (NousResearch / Hermes Agent releases). Blogposts are not
leading contract sources. CDB canon remains authoritative over Hermes docs.

| Source | Observed | Adapter relevance (not implemented here) |
|---|---|---|
| [Hermes Agent v0.19.1 / tag `v2026.7.30`](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.7.30) | Latest stable tagged release as of retrieval | Install/update surface; no CDB authority |
| [Hermes Agent v0.19.0 / tag `v2026.7.20`](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.7.20) | Prior feature release | Subagent monitoring / tool-system notes |
| [Hermes Agent v0.15.0 / tag `v2026.5.28`](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.5.28) | Kanban/Swarm platform notes | Official mentions of `hermes kanban swarm`, worker visibility endpoints `/workers/active`, `/runs/{id}`, `/inspect`, retry fingerprinting — **adapter evidence only** |

No Hermes runtime, Kanban swarm, worker provisioning, or tool execution is
implemented in this slice. Unofficial blog summaries are ignored as SSOT.

## Non-goals

- No productive Hermes agent execution
- No worker provisioning (see adjacent #4260)
- No pilot specification (#4272)
- No Agent Control Plane / GitHub-App authenticator / CI-governance changes
- No trading, risk, or execution runtime changes
- No Live / Paper / capital / promotion GO
- No merge / issue closure in the delivery slice

## Safety boundaries

```text
lr_status = NO-GO
board_trade_capable_is_live_go = false
real_money_go = false
productive_db_writes = false
productive_agent_execution = false
live_exchange_credentials = false
account_data_sharing = false
automatic_strategy_promotion = false
hermes_live_authority = false
research_apps_validation_authority = false
risk_bypass = false
plugin_installation = false
```

External research content remains `UNTRUSTED_INPUT` (data, never instructions).

## Related artifacts

| Artifact | Path |
|---|---|
| Schema | [`docs/contracts/cdb_hermes_orchestration_run.v1.schema.json`](../contracts/cdb_hermes_orchestration_run.v1.schema.json) |
| Valid fixture | [`docs/contracts/examples/cdb_hermes_orchestration_run_valid.json`](../contracts/examples/cdb_hermes_orchestration_run_valid.json) |
| Cross-contract validator | [`tools/research_validation/hermes_orchestration_cross_contract.py`](../../tools/research_validation/hermes_orchestration_cross_contract.py) |
| Tests | [`tests/unit/contracts/test_hermes_validation_orchestration_contract.py`](../../tests/unit/contracts/test_hermes_validation_orchestration_contract.py) |
| Pipeline canon | [`CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md`](CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md) |
| Security gate | [`CDB_RESEARCH_VALIDATION_SECURITY_PROVENANCE_GATES_V1.md`](CDB_RESEARCH_VALIDATION_SECURITY_PROVENANCE_GATES_V1.md) |
| Contract inventory | [`docs/contracts/CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md`](../contracts/CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md) |
