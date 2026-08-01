# CDB GitHub-backed Candidate Registry v1

**Status:** Wave-2 contract surface (#4269)
**Parent:** #4263
**Depends on:** Wave-1 DecisionRecord/Evidence; Compiler (#4268)
**Mode:** Repo/artifact registry specs; no productive DB; no runtime automation
**Live-Readiness:** NO-GO

## Purpose

Provide a GitHub-visible, immutable, audit-friendly Candidate Registry as a
**control plane**. GitHub is **not** validation authority and **not** a Live gate.

## Identities (must stay separated)

| Identity | Meaning |
|---|---|
| `issue_id` | Coordination / discussion only |
| `candidate_id` | Stable domain identity (`sc-…`) |
| `candidate_version` | Immutable revision (`vN`) |
| `run_id` | One validation run |
| `evidence_id` | One evidence packet |
| `decision_id` | One DecisionRecord |

Mixing issue/candidate/run IDs is a contract failure.

## Lifecycle

```text
IDEA → SPECIFIED → READY_FOR_VALIDATION → VALIDATING → EVIDENCE_READY
                                              ↓
                         REJECTED | REVISE | PARKED | PAPER_CANDIDATE
```

### Transition rules

| Transition | Requires |
|---|---|
| Any substantive status change | DecisionRecord |
| `VALIDATING` | Candidate version + ValidationManifest |
| `EVIDENCE_READY` | evidence_id, run_id, artifact hashes |
| `PAPER_CANDIDATE` | DecisionRecord + PASS-compatible CandidateEvidence for **exact** same candidate_version (PMR-04) |
| Content change | New immutable version (no silent overwrite) |

### PAPER_CANDIDATE hard rejects

- Missing evidence
- `overall_verdict` in `{FAIL, BLOCKED, INSUFFICIENT_DATA}`
- Identity mismatch across candidate / evidence / decision
- Missing DecisionRecord
- Unsafe `allowed_next_actions` (PMR-03)

`PAPER_CANDIDATE` is **not** Paper-Go, Live-Go, or capital approval.

## DecisionRecord hardening (PMR-03)

`allowed_next_actions` is a narrow safe enum only. Live, capital, risk-bypass, and
auto-promotion actions are schema-invalid in allowed lists.

## Schemas

| Contract | Path |
|---|---|
| Registry entry | [`cdb_candidate_registry_entry.v1.schema.json`](../contracts/cdb_candidate_registry_entry.v1.schema.json) |
| Transition | [`cdb_candidate_transition.v1.schema.json`](../contracts/cdb_candidate_transition.v1.schema.json) |
| Cross-contract validator | [`tools/research_validation/wave2_cross_contract.py`](../../tools/research_validation/wave2_cross_contract.py) |

## Cross-contract binding

Transitions that claim PAPER_CANDIDATE must bind:

`candidate_id`, `candidate_version`, `research_brief_id`, `research_brief_version`/`hash`,
`validation_manifest_id`, `run_id`, `evidence_id`, `evidence_hash`, `decision_id`,
`decision_record_hash`

Relational checks that JSON Schema cannot express are enforced by the Wave-2
validator (no documentation-only safety).

## Producer / Consumer

| Role | Responsibility |
|---|---|
| Producer | Humans / agents writing immutable registry artifacts into repo/PR |
| Consumer | Completeness review, Hermes orchestration (later waves) |
| Non-authority | GitHub Issues as validation truth; Risk/Execution bypass |

## Failure paths

| Condition | Result |
|---|---|
| Silent overwrite of candidate_version | Reject / require new version |
| Status change without DecisionRecord | Reject |
| PAPER without PASS evidence | Reject via validator |
| Issue closed | Registry artifacts remain auditably present |

## Non-goals

- No productive SurrealDB/Postgres registry
- No GitHub App automation in this slice
- No Paper/Live/Capital GO
- No full #4271 security/supply-chain gates

## Related

- SourceEvidence: [`CDB_RESEARCH_SOURCE_ADAPTER_CONTRACTS_V1.md`](CDB_RESEARCH_SOURCE_ADAPTER_CONTRACTS_V1.md)
- Compiler: [`CDB_STRATEGY_CANDIDATE_COMPILER_V1.md`](CDB_STRATEGY_CANDIDATE_COMPILER_V1.md)
- Canon: [`CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md`](CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md)
