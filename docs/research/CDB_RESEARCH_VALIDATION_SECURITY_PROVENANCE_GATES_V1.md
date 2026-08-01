# CDB Research Validation — Security, Provenance & Integrity Gates v1

**Status:** Wave-3 contract surface (#4271 / RV-08)
**Parent:** #4263
**Depends on:** Wave-1 + Wave-2 (#4264–#4269, #4283)
**Mode:** Docs + JSON Schema + synthetic fixture + read-only cross-contract helpers
**Live-Readiness:** NO-GO
**Board stage:** `trade-capable` ≠ Live-Go

## Purpose

Define a versioned, machine-checkable **Security / Provenance / Integrity** gate
contract for the Research-to-Hermes pipeline. External research content is
**UNTRUSTED_INPUT**. Missing provenance, missing hashes, prompt-injection
suspicion, or sensitive-data suspicion must fail closed.

This surface does **not** implement scanners, plugins, or runtime enforcement.
It specifies the gate record and fail-closed invariants that later
implementations must satisfy.

## Separation of concerns

| Surface | Owns | Does not own |
|---|---|---|
| `cdb.source_evidence.v1` | Normalized untrusted source claims + content hash | Security gate verdict |
| `cdb.research_security_gate.v1` (this) | Untrusted handling, injection, secrets, provenance, integrity, Codex Security disposition | Validation PASS / PAPER_CANDIDATE / Live-Go |
| `cdb.candidate_evidence.v1` | ARVP / validation gate outcomes | Security authority |
| `cdb.decision_record.v1` | REJECT / REVISE / PARK / PAPER_CANDIDATE | Security scan execution |

Integrity proves **unchangedness and lineage**, not semantic correctness.
Security `PASS` is never validation authority and never promotion.

## Contract artifact

| Artifact | Path |
|---|---|
| Schema | [`docs/contracts/cdb_research_security_gate.v1.schema.json`](../contracts/cdb_research_security_gate.v1.schema.json) |
| Valid fixture | [`docs/contracts/examples/cdb_research_security_gate_valid.json`](../contracts/examples/cdb_research_security_gate_valid.json) |
| Cross-contract helper | [`tools/research_validation/security_gates_cross_contract.py`](../../tools/research_validation/security_gates_cross_contract.py) |
| Unit tests | [`tests/unit/contracts/test_research_validation_security_gates.py`](../../tests/unit/contracts/test_research_validation_security_gates.py) |

## Untrusted content

1. All external research content is classified `UNTRUSTED_INPUT`.
2. External content is **data**, never agent, system, or tool instructions.
3. Embedded prompt instructions must not alter priorities, scope, or tool rights.
4. Original source payload, normalized claim payload, and security findings remain
   separate objects/fields (no silent merge that erases provenance).
5. Suspicious content yields `BLOCKED` or `REVIEW_REQUIRED` — never silent
   redaction-to-`PASS`.

## Sensitive data

Forbidden in research artifacts, logs, and gate records as raw values:

- Secrets, tokens, passwords, private keys, live credentials
- Account balances, personal account data, unreleased user data

Rules:

- Artifacts and logs must not contain raw sensitive values.
- Redaction documents `{field_path, data_class}` only — never the secret value.
- Leak suspicion blocks handoff fail-closed (`BLOCKED` / `FAIL`).

## Provenance

Every source bound into a security gate must include:

| Field | Rule |
|---|---|
| `source_id` | Stable ID (`se-…` or equivalent source key) |
| `provider` | Adapter / provider name |
| `locator` | Reference / URL / locator string (no secrets) |
| `content_hash` | `sha256:[64 hex]` over canonical content |

Bindings:

- ResearchBrief, SourceEvidence, and Candidate version must be linkable by ID + hash.
- Derived artifacts reference inputs via IDs and hashes.
- Non-reproducible or unattributable sources cannot produce valid evidence.
- Wall-clock metadata (`retrieved_at`, `evaluated_at`) must not destabilize a
  canonical content hash of the research payload.

## Integrity

Hashes bind:

- Candidate version content
- ValidationManifest identity / content
- Code / head reference (`code_head_ref` + `code_head_sha`)
- Dataset references
- Result artifacts

Drift rules:

- Head, code, candidate, manifest, or dataset drift **invalidates** prior
  evidence for PASS / PAPER_CANDIDATE eligibility.
- Missing hash or provenance gaps prevent security `PASS` and prevent
  downstream `PAPER_CANDIDATE`.
- Integrity ≠ semantic correctness.

## Codex Security review gate (spec only)

Codex Security is a **review gate before later implementation approval**.

| Rule | Value |
|---|---|
| Scope | Necessary repo / diff / dependency surface only |
| May do | Block, emit findings with severity + evidence + surface + disposition |
| Must not | Live-Go, risk bypass, capital GO, validation PASS, auto-promotion |
| This slice | Spec + schema fields only — **no scanner execution or integration** |

Allowed review statuses in the gate record:

`NOT_RUN | PENDING | PASS | WARNING | FAIL | BLOCKED | REVIEW_REQUIRED`

A missing required Codex Security disposition cannot become overall `PASS`.

## Required check categories

| `check_id` | Category | Fail-closed note |
|---|---|---|
| `untrusted_input_classification` | untrusted_input | Must be `UNTRUSTED_INPUT` |
| `prompt_injection_resistance` | prompt_injection | Suspicion → not overall PASS |
| `sensitive_data_exclusion` | sensitive_data | Suspicion → not overall PASS |
| `source_provenance_complete` | provenance | Missing source fields → reject |
| `artifact_hash_bindings` | integrity | Missing hashes → reject |
| `head_and_dataset_integrity` | integrity | Drift → evidence invalid |
| `codex_security_review` | supply_chain | Spec gate; disposition required |
| `read_only_enforcement` | read_only | Write/live actions forbidden |

## Verdicts

Allowed: `PASS | WARNING | FAIL | BLOCKED | REVIEW_REQUIRED`

Fail-closed:

1. Missing required check cannot become `PASS`.
2. Any check verdict `FAIL`, `BLOCKED`, or `REVIEW_REQUIRED` cannot yield
   overall `PASS`.
3. `WARNING` requires an explicit limitation **and** disposition.
4. Free-form text alone is never a valid gate record.
5. Injection or secret suspicion cannot yield overall `PASS`.

## Authority boundaries (const false / NO-GO)

```text
research_apps_validation_authority = false
hermes_live_authority = false
automatic_strategy_promotion = false
security_integrity_implies_semantic_correctness = false
paper_candidate_is_live_go = false
real_money_go = false
risk_bypass = false
productive_db_writes = false
plugin_installation = false
```

## Pipeline placement

```text
SourceEvidence (UNTRUSTED_INPUT)
        |
        v
[Security / Provenance / Integrity Gate]  <-- this contract
        |  PASS|WARNING → may proceed to validation orchestration
        |  FAIL|BLOCKED|REVIEW_REQUIRED → handoff blocked
        v
ValidationManifest → Candidate Evidence → DecisionRecord
```

Security gate `PASS` does **not** imply validation `PASS` or `PAPER_CANDIDATE`.

## Non-goals

- No security scanner implementation
- No plugin installation / external app calls
- No secret or account-data access
- No Hermes orchestration (#4270) or pilot spec (#4272)
- No CI / branch-protection / authenticator work
- No runtime, trading, risk, or execution changes
- No merge / issue closure in the delivery slice

## Safety boundaries

- LR-Status: **NO-GO**
- Board `trade-capable` ≠ Live-Go
- `PAPER_CANDIDATE` ≠ Live-Go
- Security / integrity PASS ≠ semantic correctness
- Security / integrity PASS ≠ validation authority

## Related

- Pipeline canon: [`CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md`](CDB_RESEARCH_TO_HERMES_PIPELINE_CANON_V1.md)
- Contract inventory: [`docs/contracts/CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md`](../contracts/CDB_RESEARCH_VALIDATION_CONTRACTS_V1.md)
- Source adapters: [`CDB_RESEARCH_SOURCE_ADAPTER_CONTRACTS_V1.md`](CDB_RESEARCH_SOURCE_ADAPTER_CONTRACTS_V1.md)
