# CDB Agent Run Evidence v1

Status: Canonical contract (pilot store)
Schema id: `cdb.agent_run_evidence.v1`
Issue: [#4256](https://github.com/jannekbuengener/Claire_de_Binare/issues/4256)
Parent: [#4249](https://github.com/jannekbuengener/Claire_de_Binare/issues/4249)

## Purpose

Deterministic, redacted, fail-closed **execution evidence** for a governed agent
run. This is **not** Final-CI, **not** `cdb-local-ci`, **not** Completeness,
**not** Approval, **not** Merge authority, and **not** Live-Go.

## Surfaces

| Artifact | Path |
|---|---|
| Schema | [`docs/contracts/cdb_agent_run_evidence.v1.schema.json`](../cdb_agent_run_evidence.v1.schema.json) |
| Examples | [`docs/contracts/examples/agent_run_evidence/`](../examples/agent_run_evidence/) |
| Emitter / Store / Verifier | `tools/agent_control/evidence/` |
| CLI | `python -m tools.agent_control evidence …` |

## Relation to #4253 snapshot

`evidence snapshot` / legacy `evidence --run-id … --state …` remains the
dispatcher **lifecycle snapshot** (`cdb.agent_dispatch_evidence_snapshot.v1`)
and explicitly claims `not_agent_run_evidence_bundle_v1`.

The #4256 bundle is produced by `evidence emit` (or `evidence --run … --state …`).

## Determinism

- Canonicalization: JCS / RFC 8785 via `tools.agent_execution_contract.jcs`
- Digest: SHA-256 (`sha256:<hex>`), digest field excluded from hash material
- Evidence-ID derived from run/attempt/contract/provider/idempotency bindings
- Re-emission of an unchanged run is byte-identical
- No new wall-clock timestamps are introduced at emit time

## Provenance trust classes

- `control_plane_observed`
- `provider_reported`
- `agent_reported`
- `derived`

Provider/agent reports are never presented as self-observed control-plane truth.

## Redaction

Input trust is **untrusted**. Secret-bearing keys/values are structurally
removed or emission aborts with `EVIDENCE_SECRET_DETECTED`. Masking with `***`
alone never yields PASS.

## Pilot store

Optional JSONL under `artifacts/agent-control/evidence/agent_run_evidence.v1.jsonl`
(only when `--store` is passed). Atomic temp+fsync+replace, single-writer lock,
idempotent same id+digest, fail-closed on digest collision. Runtime store is not
committed to the repository. End-to-end Cursor pilot remains [#4258](https://github.com/jannekbuengener/Claire_de_Binare/issues/4258).

## Authority limits

Bundles always assert:

- not Final-CI / not `cdb-local-ci`
- not Completeness Review
- not Approval
- not Merge authority / merge readiness
- not Live-Go

## CLI

```text
python -m tools.agent_control evidence snapshot --run <ID> --state <PATH>
python -m tools.agent_control evidence emit --run <ID> --state <PATH> [--store <JSONL>]
python -m tools.agent_control evidence verify --bundle <PATH>
python -m tools.agent_control evidence verify --store <JSONL>
python -m tools.agent_control evidence show --run <ID> --store <JSONL>
python -m tools.agent_control evidence --run-id <ID> --state <PATH>   # snapshot alias
python -m tools.agent_control evidence --run <ID> --state <PATH>      # emit entry
```

`--state` is required for emit/snapshot because the run record is the only
authoritative bound input; no hidden state source is invented.
