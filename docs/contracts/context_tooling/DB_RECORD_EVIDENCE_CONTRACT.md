# DB-record evidence contract (context / tooling claims)

| Field | Value |
| --- | --- |
| Status | **active** |
| Version | `db-record-evidence-contract/v1` |
| Issue | [#2851](https://github.com/jannekbuengener/Claire_de_Binare/issues/2851) |
| Parent meta | [#2847](https://github.com/jannekbuengener/Claire_de_Binare/issues/2847) |
| Validator | [`tools/surrealdb/db_record_evidence_contract.py`](../../../tools/surrealdb/db_record_evidence_contract.py) |
| JSON Schema | [`docs/contracts/db_record_evidence_claim.v1.schema.json`](../db_record_evidence_claim.v1.schema.json) |
| Invocation bundle (#2850) | [`TOOL_INVOCATION_JSON_EVIDENCE.md`](TOOL_INVOCATION_JSON_EVIDENCE.md) |

## Purpose

Agents and harnesses need a single SSOT for when a **context/tooling claim** may be cited as **DB-backed** (`surrealdb-local`) versus **repo-only**, **in-memory fixture**, or **accepted limitation** (fail-closed `missing_*` paths).

This contract complements (does not replace):

- [`agents/AGENTS.md`](../../../agents/AGENTS.md) § Brain Evidence Gate
- [`knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](../../../knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md)
- [`tools/mcp/memory_output_contract.py`](../../../tools/mcp/memory_output_contract.py) (MCP response envelope)
- [`tools/surrealdb/claim_evidence_at_rest.py`](../../../tools/surrealdb/claim_evidence_at_rest.py) (DB row integrity)
- Live invocation harness: [`tools/surrealdb/context_live_invocation_harness.py`](../../../tools/surrealdb/context_live_invocation_harness.py)

## Safety boundaries

- LR remains **NO-GO** ([`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../live-readiness/LR-AUDIT-STATUS-2026-03-05.md)).
- Board stage `trade-capable` is **not** live-go.
- `PERSIST_ALLOWED=False` and `MUTATION_ALLOWED=False` on agent surfaces (default).
- No productive SurrealDB writes from this contract.
- Caller-supplied `brain_source`, `brain_status`, or `metadata.source` is **not** DB evidence ([#2638](https://github.com/jannekbuengener/Claire_de_Binare/issues/2638); `derive_guarded_source_label()`).

## Required claim fields (v1)

| Field | Role |
| --- | --- |
| `claim_id` | Stable identifier for the claim instance |
| `claim_type` | e.g. `context_tooling_benchmark`, `brain_evidence_block`, `wave14_read` |
| `claim_text_or_summary` | Human-readable summary (no secrets) |
| `producer_tool` | MCP/bridge/CLI tool that produced evidence |
| `tool_invocation_id_or_hash` | Invocation correlation (hash or stable id) |
| `query_or_lookup_fingerprint` | Query/command fingerprint (SurrealQL, adapter op, or bridge path) |
| `record_source` | `surrealdb-local`, `surrealdb-local-unavailable`, `in_memory`, `repo-only` |
| `record_ids` | List of record IDs (may be empty when not DB-backed) |
| `record_hashes_or_content_fingerprints` | Content fingerprints when IDs omitted |
| `record_timestamps_or_freshness_signal` | Freshness hint (excluded from `determinism_hash`) |
| `repo_crosscheck` | Path/symbol/commit or narrative crosscheck |
| `source_priority` | Which layer won: `live_github`, `repo_files`, `surrealdb_context`, `ledger_snapshots`, `fallback` |
| `trust_classification` | Outcome class (see below) |
| `limitations` | Explicit non-proof statements |
| `redaction_summary` | What was redacted (no raw secrets) |
| `determinism_hash` | `canonical_hash` over stable claim subset |

Optional: `schema_version` = `db-record-evidence-contract/v1`.

## Source priority (authoritative order)

Higher wins; fail-closed on conflict:

1. **live_github** — issues, PRs, checks, branches
2. **repo_files** — governance, code, contracts, runbooks
3. **surrealdb_context** — guarded adapter + record evidence only
4. **ledger_snapshots** — e.g. `CURRENT_STATUS.md` (not live truth)
5. **fallback** — explicit limitations only

## Trust classifications

| `trust_classification` | Meaning | DB-backed claim allowed? |
| --- | --- | --- |
| `valid_db_backed` | Tool/query + record ID or hash from guarded adapter | **Yes** (still not live-go) |
| `partial` | Degraded/unavailable adapter or incomplete proof | No |
| `repo_only` | Repo/GitHub evidence only | No |
| `in_memory_fixture` | Inline/harness/fixture records | No |
| `accepted_limitation` | Fail-closed `missing_*` (harness PASS_WITH_LIMITS) | No |
| `invalid_fake_db` | Caller-forged source without adapter proof | No |

### Valid DB-backed (all required)

- `record_source` = `surrealdb-local`
- Non-empty `producer_tool` and (`query_or_lookup_fingerprint` or `tool_invocation_id_or_hash`)
- Non-empty `record_ids` **or** `record_hashes_or_content_fingerprints`
- No reliance on caller-only keys (`brain_source`, `metadata.source`, etc.) as sole evidence
- `trust_classification` = `valid_db_backed` and consistent `determinism_hash`

### Repo-only

- `record_source` = `repo-only`
- `repo_crosscheck` present (path/symbol/commit or explicit limitation text)
- `trust_classification` = `repo_only`
- No assertion of verified SurrealDB record proof

### Accepted limitation (PASS_WITH_LIMITS)

Maps to harness fail-closed codes (must match harness):

- `missing_evidence_records`
- `missing_claim_records`
- `missing_memory_records`
- `missing_decision_events`
- `missing_records`
- `missing_bundle`

Ratification: [`docs/evidence/context_tooling/CDB_PASS_WITH_LIMITS_RATIFICATION_2026-06-03.md`](../../evidence/context_tooling/CDB_PASS_WITH_LIMITS_RATIFICATION_2026-06-03.md).

- `trust_classification` = `accepted_limitation`
- `limitations` must reference at least one code above
- **Not** a verified DB-backed claim

## Determinism

`determinism_hash` = SHA-256 of canonical JSON ([`core/replay/canonical_json.py`](../../../core/replay/canonical_json.py)) over the claim **excluding**:

- `determinism_hash`
- `record_timestamps_or_freshness_signal`

Wall-clock values must not affect the hash.

## Redaction

Forbidden raw substrings in claim body and `redaction_summary` (case-insensitive), including:

`SURREAL_PASS`, `SURREAL_USER`, `Authorization`, `Basic `, `Bearer `, and assignment forms such as `password=`, `api_key=`, `secret=`, `token=`.

Use `redact_for_summary()` in the validator for safe logging.

## JSON export compatibility (#2850 — not implemented here)

Issue [#2850](https://github.com/jannekbuengener/Claire_de_Binare/issues/2850) may emit benchmark JSON using this schema:

- File: `docs/contracts/db_record_evidence_claim.v1.schema.json`
- Examples: `docs/contracts/examples/db_record_evidence_*.json`
- Stable field names in this document are the export contract; no generator in #2851.

## Validation

```bash
python -m pytest tests/unit/surrealdb/test_db_record_evidence_contract.py -q
```

Harness regression (unchanged):

```bash
make context-live-invoke
make context-live-invoke-full
```

## Trust thresholds (operator levels)

For `cdb_context_trust_summary` / briefing trust synthesis, operator-facing
`HIGH` | `MEDIUM` | `LOW` | `BLOCKED` rules are defined in
[`CDB_CONTEXT_TRUST_THRESHOLD_CONTRACT.md`](CDB_CONTEXT_TRUST_THRESHOLD_CONTRACT.md)
(Issue [#2856](https://github.com/jannekbuengener/Claire_de_Binare/issues/2856)).
Trust levels do not override DB-record evidence rules above.

## Related Wave-14 tables

Evidence/claim/memory/decision record shapes: `tests/unit/surrealdb/wave14_contract_constants.py` and `infrastructure/surrealdb/context_intelligence_v0.surql`.
