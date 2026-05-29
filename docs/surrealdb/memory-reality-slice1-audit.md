# Memory Reality Slice 1 Audit — model / read / gate before any write path

**Status**: Slice 1 deliverable (audit only)  
**Authority**: Epic [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606)  
**Slice**: `#2606 Memory Reality Slice 1: model/read/gate audit before any write path`  
**Repo HEAD at audit**: `f023b6ef` (branch baseline)  
**Guardrail**: LR remains `NO-GO`. Board stage `trade-capable` is not live-go. No memory write in this slice.

---

## 1. Purpose

This document records the **as-built** state of scoped agent memory: contract docs, SurrealDB schema draft, read-path tools, MCP surface, tests, and write-gate readiness. It is the gate artifact before any Memory-Write slice is planned.

**Non-goals (this slice)**: memory write, DB apply/migration, productive SurrealDB writes, epic closure, vector search, compression.

---

## 2. Executive verdict

| Question | Verdict |
| --- | --- |
| Is the memory **model** doc ↔ schema aligned? | **Yes** — `scoped-agent-memory-model-v1.md` matches `agent_memory` in `context_intelligence_v0.surql`. |
| Is the **epic #2606 body** aligned? | **No (stale)** — field names and memory-type count differ from canon. |
| Is **read** implemented? | **Yes, in-memory only** at the domain layer; MCP can opt into DB via `adapter_config_path` but CI proves dispatch with mocks, not live `agent_memory` rows. |
| Is **write** gated in code? | **Partial (Slice 5, §19)** — in-memory `memory_write_gate.py` fail-closed harness; `PERSIST_ALLOWED=False`; no DB/MCP/importer write path. MCP read tools remain read-only. |
| Safe to plan Memory-Write next? | **Partial** — Slices 2–6 delivered (contract, DB read proof, gate harness, local write smoke); production write path + `audit_observation` persistence remain #2703/#2704. |

---

## 3. Reconcile decisions (Slice 1 — no runtime change)

These decisions are recorded for downstream slices. **No producer/validator or MCP behavior was changed in Slice 1.**

| ID | Decision | Rationale |
| --- | --- | --- |
| R1 | **Canonical field names** = schema + `scoped-agent-memory-model-v1.md`: `memory_id`, `scope`, `namespace`, `memory_type`, `content`, `source_refs`, `evidence_refs`, `confidence`, `ttl` (seconds), `expires_at`, `stale_after`, `superseded_by`, `created_by`, `created_at`. | Schema and v1 doc agree; epic body uses obsolete names. |
| R2 | **Epic #2606 body Pflichtfelder list is stale** — do not implement `agent_id`, singular `source_ref`, or `supersedes`. Use `created_by`, `source_refs`, `superseded_by`. | Live issue text predates Wave-1 reconcile. |
| R3 | **Memory types (canon)** = 6: `working_memory`, `semantic_memory`, `episodic_memory`, `procedural_memory`, `preference_memory`, `risk_memory`. Epic body lists 4 and omits `preference_memory`, `risk_memory`. | v1 doc §3. |
| R4 | **`ttl` unit** = seconds in schema and v1 doc. `memory_read._is_stale_by_ttl` uses **`ttl_days`** (days). MCP `_normalize_memory_row` copies `ttl` → `ttl_days` **without conversion** — treat as **known defect**; fix in Slice 3, not Slice 1. | Prevents silent wrong stale flags on DB-backed reads. |
| R5 | **`memory_id` strategy (planned, not implemented)** = UUIDv5 over canonical string `scope|namespace|memory_type|content_hash` where `content_hash` = SHA256 of normalized content (sorted-key JSON or raw UTF-8 per `core/replay/canonical_json.py` pattern). Namespace constant TBD in Slice 2. | Align with `core.utils.uuid_gen` (`generate_decision_pk`, `compute_event_pk`). |
| R6 | **Scope identity** = `scope` + `namespace` required on write (future); read `by_scope` matches exact `scope` string. `agent` in read contract = `created_by` in schema (MCP normalizer maps). | Unscoped/global writes forbidden in v1 doc §9. |
| R7 | **DB-backed claims** only when `metadata.source` is derived from adapter (`derive_guarded_source_label`); never from caller `source` / `brain_source`. | #2605 / #2461 source-honesty. |
| R8 | **Write channel** must be **new** surface (not `cdb_context_memory_get`); cannot pass read-only `PermissionGuard` without explicit Human-GO + audit design (Slice 4). | `permission_guard.py` registry is read-only only. |

---

## 4. Memory model inventory

### 4.1 Memory types (documentation)

| `memory_type` | In v1 doc | In epic #2606 body | In schema enum enforcement |
| --- | --- | --- | --- |
| `working_memory` | Yes | Yes | No (string field only) |
| `semantic_memory` | Yes | Yes | No |
| `episodic_memory` | Yes | Yes | No |
| `procedural_memory` | Yes | Yes | No |
| `preference_memory` | Yes | No | No |
| `risk_memory` | Yes | No | No |

### 4.2 `agent_memory` fields

| Field | v1 doc (required) | `context_intelligence_v0.surql` | `memory_read.py` contract | MCP `_normalize_memory_row` |
| --- | --- | --- | --- | --- |
| `memory_id` | implied | Yes, UNIQUE index | Yes | pass-through |
| `scope` | Yes | Yes | Yes | pass-through |
| `namespace` | Yes | Yes | No (not in reader) | pass-through |
| `memory_type` | Yes | Yes | Yes | pass-through |
| `content` | Yes | Yes | Yes | pass-through |
| `source_refs` | Yes (array) | Yes | Yes | pass-through |
| `evidence_refs` | Yes (array) | Yes | Yes | pass-through |
| `confidence` | Yes | Yes | No in normalize output | pass-through |
| `ttl` | Yes (seconds) | Yes (int) | Uses `ttl_days` instead | **`ttl` → `ttl_days` (no ÷86400)** |
| `expires_at` | Yes if ttl>0 | Yes | Not used in reader stale logic | pass-through |
| `stale_after` | Yes (doc §8) | Yes | Not used in reader | pass-through |
| `superseded_by` | Yes | Yes | Yes (`superseded`) | pass-through |
| `created_by` | Yes | Yes | Uses `agent` | **`created_by` → `agent`** |
| `created_at` | Yes | Yes | Yes | pass-through |
| `agent_id` | — | — | — | **Epic body only (stale)** |
| `topic` / `topics` | — | — | Yes (fixture contract) | empty defaults for DB rows |
| `artifact_refs` / `decision_refs` | — | — | Yes (fixture contract) | empty defaults for DB rows |

### 4.3 Related tables (read path)

| Table | Read tool | DB-backed MCP | Notes |
| --- | --- | --- | --- |
| `evidence_ref` | `evidence_lookup.py` | `cdb_context_evidence_resolve` | Schema normalize `validates`→`claim_refs`, etc. |
| `claim` | `claim_resolver.py` | `cdb_context_claim_resolve` | `by_topic` empty for pure schema rows |
| `decision_event` | `decision_history_query.py` | `cdb_context_decision_history` | `human_go` field in schema, not memory write |
| `agent_memory` | `memory_read.py` | `cdb_context_memory_get` | See TTL drift |
| `shared_memory` | — | — | Not in v0 surql draft |

---

## 5. Docs vs schema vs code vs tests — drift matrix

| Drift | Severity | Owner slice |
| --- | --- | --- |
| Epic body field names (`agent_id`, `source_ref`, `supersedes`) | High (misleading) | Doc/issue update (human) |
| Epic lists 4 memory types vs 6 in canon | Medium | Doc/issue update |
| `ttl` seconds vs `ttl_days` in reader + normalizer | **High (wrong stale if DB-backed)** | Slice 3 |
| No `memory_id` generator | High (blocks write) | Slice 2 |
| No schema ASSERT/PERMISSIONS/TTL trigger | Medium | Post-write design |
| Issue validation cites missing test files | Low | Epic body update |
| `test_mcp_wave14_surrealdb_mode` mocks DB; no CI real DB memory proof | Medium | Slice 3 |
| `stale_knowledge_scan.py` in-memory bundle only | Low (Wave-16) | Later |

---

## 6. Read-path findings

### 6.1 Domain layer (`tools/surrealdb/`)

All Wave-14 readers declare: **no DB, no writes, in-memory records only**.

| Module | Entry | Modes | Stale / trust |
| --- | --- | --- | --- |
| `memory_read.py` | `read_memory_v1` | `by_scope`, `by_topic`, `by_artifact`, `by_decision`, `by_agent`, `by_freshness`, `by_memory_type` | `stale` flag, `ttl_days`, `superseded_by`; trust: weak → source_backed |
| `evidence_lookup.py` | `lookup_evidence_v1` | 8 modes | strength + stale + blocking_missing |
| `claim_resolver.py` | `resolve_claims_v1` | 7 modes | disputed/stale/invalidated; missing_evidence_blocker |
| `trust_summary.py` | `build_trust_summary_v1` | scope required | composite score; `trust_level=blocked` ≠ Human-GO |
| `decision_history_query.py` | `query_decision_history_v1` | multiple | superseded/invalidated lists |
| `decision_replay_builder.py` | `build_decision_replay_v1` | replay modes | chain assembly, in-memory |

### 6.2 MCP layer

| Tool | Handler | Default source | DB opt-in |
| --- | --- | --- | --- |
| `cdb_context_memory_get` | `handle_cdb_context_memory_get` | `in_memory` | `adapter_config_path` → `SELECT * FROM agent_memory` |
| `cdb_context_evidence_resolve` | … | `in_memory` | yes |
| `cdb_context_claim_resolve` | … | `in_memory` | yes |
| `cdb_context_trust_summary` | … | `in_memory` | yes (4 tables) |

**Source honesty**: `derive_guarded_source_label` ignores caller-supplied `source`, `brain_source`, `metadata.source`. Allowed: `in_memory`, `surrealdb-local`, `surrealdb-local-unavailable`.

### 6.3 Tests (actual paths)

| Epic / doc reference | Actual location |
| --- | --- |
| `test_memory_read.py` | **Missing** — use `tests/unit/surrealdb/test_wave14_services_v1.py` |
| `test_evidence_lookup.py` | **Missing** — same file |
| `test_trust_summary.py` | **Missing** — same file |
| DB mode | `tests/unit/tools/mcp/test_mcp_wave14_surrealdb_mode.py` (mocked adapter) |
| Slice 1 characterization | `tests/unit/surrealdb/test_memory_read_characterization.py` |

---

## 7. Write-gate findings

> **Slice 5 update (§19):** Human-GO write gate design + in-memory harness delivered in `memory_write_gate.py`. This section records the Slice 1 baseline; see §19 for current gate state.

| Gate (v1 doc / ownership) | Implemented? | Notes |
| --- | --- | --- |
| Scoped write (`scope` + `namespace`) | **Slice 5 (gate only)** | `validate_memory_record()` + scope match in gate; no write API |
| `source_refs` + `evidence_refs` required | **Slice 2 + 5** | Contract validator + gate block on violation |
| Human-GO for memory write | **Slice 5 (gate only)** | `MemoryWriteAuthorization` + `GO-YYYY-MM-DD[-suffix]` token; dry-run only |
| Audit trail on write | **Slice 5 envelope only** | Gate `audit` block; DB `audit_observation` persistence = #2703 |
| Fail-closed without GO | **Slice 5** | `blocked_*` statuses; `PERSIST_ALLOWED=False` |
| Cross-agent write ban | Doc only | |
| No backflow to Git/Postgres/runtime | Doc + gate | Gate has no persistence side effects |

**Human-GO (Slice 5):** explicit operator-supplied `MemoryWriteAuthorization` out-of-band; `DELIVERY_APPROVED.yaml` and `decision_event.human_go` do **not** authorize memory writes. See `docs/surrealdb/memory-write-gate-v1.md`.

---

## 8. ID / TTL / stale / supersession

### 8.1 Deterministic `memory_id`

- **Present**: `core.utils.uuid_gen` — `generate_uuid` (uuid5), `generate_decision_pk`, `compute_event_pk`, SHA256 snapshot hashes.
- **Absent**: `generate_memory_id` or equivalent.
- **Planned** (R5): uuid5 over `scope|namespace|memory_type|content_hash`.

### 8.2 TTL / freshness

| Layer | Behavior |
| --- | --- |
| v1 doc | `ttl` in seconds; `expires_at` when ttl>0; expired = stale, not deleted |
| Schema | `ttl`, `expires_at`, `stale_after` fields, no DB trigger |
| `memory_read` | `ttl_days` + age from `created_at` in days; ignores `expires_at` |
| MCP normalizer | `ttl` → `ttl_days` 1:1 |
| `stale_knowledge_scan` | In-memory bundles; can emit TTL-expired findings when `expires_at` provided in bundle |

### 8.3 Supersession

- **Schema**: `superseded_by` string on `agent_memory`.
- **Read**: records with `superseded_by` marked `superseded` trust level; not auto-resolved to chain end.
- **Write**: supersede chain creation not implemented.

---

## 9. Evidence / trust

- Memory without `evidence_refs` → `weak` trust in `memory_read`; not rejected on read.
- `claim_resolver` sets `missing_evidence_blocker` for supported claims without evidence.
- `trust_summary` can mark `blocked` for blocking_missing evidence; **does not grant Human-GO**.
- **Fake DB-backed risk**: mitigated for MCP `metadata.source`; **not** mitigated if agent cites memory content without calling tools.

---

## 10. MCP surface dependencies (#2605)

Relevant #2605 outcomes for #2606:

- Read-only registry + `PermissionGuard` — memory tools exempt from SQL keyword scan on record content.
- `adapter_config_path` explicit opt-in; localhost-only adapter.
- Source forgery tests in `test_mcp_wave14_surrealdb_mode.py` (forged `brain_source` must not upgrade metadata).
- Operator-dependent: live SurrealDB with seeded `agent_memory` for real `source=surrealdb-local` proof.

---

## 11. Risk register (Slice 1)

| Risk | Likelihood | Impact | Mitigation slice |
| --- | --- | --- | --- |
| Fake DB-backed memory claims (caller `source`) | Low at MCP boundary | High | Enforced today via `derive_guarded_source_label` |
| `ttl` unit bug on DB path | High if DB used | High | Slice 3 fix + tests |
| Stale memory treated as truth | Medium | High | Read already flags; briefing must honor warnings |
| Non-deterministic `memory_id` on write | N/A until write | High | Slice 2 |
| Human-GO bypass | Low today (no write) | Critical | Slice 4 |
| Tests pass only in-memory | High | Medium | Slice 3 local_only proof |
| Epic/doc drift misleads implementers | High | Medium | R1–R2, this audit |

---

## 12. Recommended #2606 slice roadmap

| Slice | Name | Deliverable |
| --- | --- | --- |
| **1** (this) | Model/read/gate audit | This doc + characterization tests |
| 2 | Deterministic memory ID + validation contracts | `generate_memory_id`, reject invalid records (no DB write) |
| 3 | DB read proof + TTL unit fix | local_only SurrealDB smoke for `agent_memory` |
| 4 | Human-GO write gate design + harness | fail-closed tests, audit field spec |
| 5 | Minimal local-only write smoke | only after Human-GO + Slices 2–4 |

---

## 13. Slice 1 artifacts

| Artifact | Path |
| --- | --- |
| Audit (this file) | `docs/surrealdb/memory-reality-slice1-audit.md` |
| Characterization tests | `tests/unit/surrealdb/test_memory_read_characterization.py` |
| Canon model | `docs/surrealdb/scoped-agent-memory-model-v1.md` |
| Schema draft | `infrastructure/surrealdb/context_intelligence_v0.surql` |

---

## 14. Validation commands (Slice 1)

```bash
pytest tests/unit/surrealdb/test_memory_read_characterization.py tests/unit/surrealdb/test_wave14_services_v1.py -v
pytest tests/unit/tools/mcp/test_mcp_wave14_tools.py tests/unit/tools/mcp/test_mcp_wave14_surrealdb_mode.py tests/unit/tools/mcp/test_permission_guard.py -v
ruff check tools/surrealdb/memory_read.py tools/mcp/context_evidence_memory_tools.py tests/unit/surrealdb/test_memory_read_characterization.py
```

---

## 15. Stop conditions (for any future write slice)

Stop and do not implement write if:

- TTL unit drift (R4) unfixed and DB-backed read is in scope.
- No `memory_id` generator and validation contract (Slice 2).
- No recorded Human-GO mechanism and audit trail design (Slice 4).
- No real DB read proof when claiming `surrealdb-local` for memory (Slice 3).
- LR or operator has not explicitly authorized memory write experiment.

---

## 16. Slice 2 addendum

**Slice 2 delivered**: `2606-memory-slice2-contracts`  
**Repo HEAD at delivery**: see PR for commit SHA  
**Date**: 2026-05-29

### 16.1 What was built

| Artifact | Path |
| --- | --- |
| `memory_contract.py` | `tools/surrealdb/memory_contract.py` |
| Unit tests | `tests/unit/surrealdb/test_memory_contract.py` |

### 16.2 R5 finalized (memory_id spec)

R5 from Slice 1 (planned, not implemented) is now implemented:

| Property | Value |
| --- | --- |
| Algorithm | UUIDv5 (`uuid.uuid5`) |
| Namespace constant | `MEMORY_ID_NAMESPACE = uuid.UUID("b4e1d2c3-a5f6-4780-9bcd-ef0123456789")` |
| Name string | `{scope}\|{namespace}\|{memory_type}\|{created_by}\|{content_hash}\|{source_refs_fingerprint}` |
| `content_hash` | SHA256 of `content.strip().encode("utf-8")` |
| `source_refs_fingerprint` | `canonical_hash(sorted(set(source_refs)))` from `core/replay/canonical_json.py` |
| **NOT in ID** | `created_at`, `ttl`, `confidence`, `evidence_refs` |

### 16.3 Validator contract (v1)

`validate_memory_record(raw, *, strict=True)`:

- Required: `scope`, `namespace`, `memory_type`, `content`, `source_refs`, `evidence_refs`, `confidence`, `ttl`, `created_by`, `created_at`
- `memory_type`: one of 6 CANONICAL_MEMORY_TYPES (lowercased)
- `source_refs` / `evidence_refs`: non-empty list of non-empty strings
- `confidence`: float in [0.0, 1.0]
- `ttl`: int ≥ 0 (seconds); if ttl > 0 → `expires_at` required and must be strictly after `created_at`
- Optional: `superseded_by` (non-empty if present), `stale_after` (int ≥ 0), `comment`
- `strict=True`: rejects unknown fields
- If `memory_id` present: must match computed value
- If `memory_id` absent: computed and attached

Canon names enforced: `created_by` (NOT `agent_id`), `source_refs` (NOT `source_ref`), `superseded_by` (NOT `supersedes`).

### 16.4 Test coverage (Slice 2)

76 unit tests in `tests/unit/surrealdb/test_memory_contract.py`:
- ID determinism and stability (3 tests)
- ID sensitivity to all 6 identity fields (6 parametrized)
- ID insensitivity to `created_at`, `confidence`/`ttl`, `evidence_refs`
- `compute_content_hash`: determinism, strip, length, sensitivity
- `compute_source_refs_fingerprint`: order-insensitive, deduplicating, deterministic, sensitive
- Valid record: memory_id added, memory_type normalized, fields preserved
- Missing required fields: 10 parametrized
- Empty `evidence_refs` / `source_refs`
- Confidence out of range: 4 parametrized; edge values 0.0/1.0 pass
- TTL contract: ttl=0 OK without `expires_at`; ttl>0 fails without `expires_at`, fails if `expires_at` ≤ `created_at`
- `stale_after`: valid and negative
- `superseded_by`: valid, empty string, whitespace
- Unknown memory_type
- Unknown extra field strict/non-strict
- `memory_id` mismatch
- `validate_memory_id_matches_record`: correct / wrong / missing

### 16.5 No-changes list (Slice 2)

- `memory_read.py` — unchanged
- `core/utils/uuid_gen.py` — unchanged
- MCP tools — unchanged
- SurrealDB schema / Docker / infrastructure — unchanged
- `DELIVERY_APPROVED.yaml` — unchanged
- LR verdict remains NO-GO

### 16.6 Remaining gaps after Slice 2

| Gap | Slice |
| --- | --- |
| TTL unit drift (`ttl` seconds vs `ttl_days` in reader) | **Slice 3 (closed in-memory)** |
| DB-backed memory read proof | Follow-up slice (not Slice 3 scope) |
| Human-GO write gate design | Slice 4 |
| Memory write implementation | Slice 5 (only after Human-GO + Slices 2–4) |

---

## 17. Slice 3 addendum

**Slice 3 delivered:** `2606-memory-slice3-ttl-freshness`  
**Date:** 2026-05-29

### 17.1 What was built

| Artifact | Path |
| --- | --- |
| Freshness classifier | `classify_memory_freshness()` in `tools/surrealdb/memory_contract.py` |
| Reader TTL fix | `tools/surrealdb/memory_read.py` — uses contract helper, optional `now=` |
| MCP normalizer fix | `tools/mcp/context_evidence_memory_tools.py` — no `ttl` → `ttl_days` copy |
| Unit tests | `tests/unit/surrealdb/test_memory_freshness.py` (15 tests) |
| Characterization update | `tests/unit/surrealdb/test_memory_read_characterization.py` |

### 17.2 R4 closed (in-memory proof)

| Before | After |
| --- | --- |
| Reader used `ttl_days` + wall-clock age in days | Reader uses `expires_at`, `ttl` (seconds), `stale_after`, optional legacy `ttl_days` |
| MCP copied `ttl` → `ttl_days` 1:1 | Schema `ttl` passes through unchanged |
| Fake-fresh records when `ttl=3600` meant 3600 days | Canonical seconds + `expires_at` classification |

**Canon:** `ttl` is seconds; `expires_at` authoritative when present; `stale_after` is seconds since `created_at`. Stale/expired records are **marked**, not filtered.

**Injectable time:** `read_memory_v1(..., now=)` for deterministic tests; production default `cdb_utcnow()`.

**Legacy shim:** Reader fixtures with only `ttl_days` (no `ttl`/`expires_at`) still work with reason `legacy_ttl_days` (e.g. `wave14_v1.json`).

### 17.3 Test coverage (Slice 3)

15 unit tests in `test_memory_freshness.py` plus updated characterization tests:
- fresh / expired / stale_after / superseded / explicit stale
- legacy `ttl_days` only
- derived expiry from `ttl` seconds when `expires_at` absent
- reader marks expired without filtering
- MCP normalizer preserves `ttl` seconds
- guardrail: no `datetime.now()` in `memory_read.py`

### 17.4 No-changes list (Slice 3)

- No DB access, no SurrealDB runtime, no Docker/infra
- No memory write, no MCP registry changes
- `stale_knowledge_scan.py` unchanged (already uses `expires_at`)
- `DELIVERY_APPROVED.yaml` unchanged
- LR remains NO-GO

### 17.5 Remaining gaps after Slice 3

| Gap | Follow-up |
| --- | --- |
| DB-backed memory read proof (`surrealdb-local`) | Separate slice / local_only |
| Human-GO write gate design | Slice 4 |
| Memory write implementation | Slice 5 |

---

## 18. Slice 4 addendum — DB-backed memory read proof (#2606)

**Delivered:** read-only proof helper, contract-compliant fixtures, opt-in local smoke.

### 18.1 Proof helper

| Artifact | Role |
| --- | --- |
| `tools/surrealdb/memory_db_read_proof.py` | `prove_agent_memory_db_read_v1()` — adapter SELECT → strip importer metadata → `validate_memory_record(strict=False)` → `classify_memory_freshness` → optional `read_memory_v1` cross-check |

Evidence bundle fields: `source` / `adapter_status`, `record_count`, `memory_ids`, aggregated `evidence_refs`, per-record `freshness`, `limitations`, read-only `approval_semantics`.

### 18.2 Fixtures and local gate

| Artifact | Role |
| --- | --- |
| `tests/fixtures/surrealdb/memory_db_proof/` | Contract-compliant `agent_memories.jsonl` (fresh + expired) + `evidence_refs.jsonl`; `memory_id` via `generate_memory_id()` |
| `tests/local/surrealdb/memory_db_proof_helpers.py` | Run-scoped materialize/seed/cleanup (Wave-14 pattern, local-dev only) |
| Env gate | `CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1` (separate from Wave-14 smoke) |

Local proof command:

```powershell
$env:CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE = "1"
pytest -v -m local_only tests/local/surrealdb/test_memory_db_read_proof.py
```

### 18.3 Tests

| File | Marker | CI |
| --- | --- | --- |
| `tests/unit/surrealdb/test_memory_db_read_proof.py` | `unit` | yes (mock adapter) |
| `tests/local/surrealdb/test_memory_db_read_proof.py` | `local_only` | no (opt-in) |

Proven behaviors: DB read → `source=surrealdb-local` (helper + MCP), contract validation pass, UUIDv5 `memory_id` match, freshness fresh vs expired, forged caller `source` ignored on MCP path.

### 18.4 #2691 optional-field correction

The local-only DB smoke initially exposed a schemafull SurrealDB mismatch:
missing optional `agent_memory.stale_after` values were treated as `NONE` and
rejected by `TYPE int`. Runtime verification then exposed the same optional-field
class for `superseded_by` (`NONE` rejected by `TYPE string`).

Correction:

- `stale_after` is `option<int>` in `context_intelligence_v0.surql`.
- `superseded_by` is `option<string>` in `context_intelligence_v0.surql`.
- `validate_memory_record()` accepts explicit `None` for both optional fields.
- Tests cover missing and `None` values, plus schema declarations.

Post-fix local-only smoke result: `CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1 pytest
tests/local/surrealdb/test_memory_db_read_proof.py -q` passed (`1 passed, 1
skipped`) against `surrealdb-local`.

### 18.5 No-changes list (Slice 4)

- No memory write feature, no MCP write, no Docker/runtime-stack changes
- Wave-14 pre-contract fixture unchanged
- LR remains NO-GO

### 18.6 Remaining gaps after Slice 4

| Gap | Follow-up |
| --- | --- |
| Human-GO write gate design | Slice 5 / separate Human-GO slice |
| Memory write implementation | After Human-GO + write gate |

---

## 19. Slice 5 addendum — Human-GO write gate design + harness (#2606)

**Delivered:** in-memory gate module, contract doc, unit tests. No persistence.

### 19.1 Gate module

| Artifact | Role |
| --- | --- |
| `tools/surrealdb/memory_write_gate.py` | `MemoryWriteAuthorization`, `evaluate_memory_write_gate()` |
| `docs/surrealdb/memory-write-gate-v1.md` | Human-GO representation, audit fields, DELIVERY_APPROVED boundary |

Gate properties:

- `PERSIST_ALLOWED = False` (module constant; never true in Slice 5)
- Fail-closed block reasons: `no_authorization`, `no_human_go`, `contract_violation`, `scope_mismatch`, `missing_evidence`, `agent_self_asserted_go`, `supersede_requires_target`
- Pass status: `approved_dry_run` only
- Reuses `validate_memory_record()` from Slice 2; no changes to read path or MCP registry

### 19.2 Human-GO boundary

| Authorizing | Memory write? |
| --- | --- |
| `MemoryWriteAuthorization` with valid `human_go_token` | Gate may pass dry-run only |
| `DELIVERY_APPROVED.yaml` | No |
| Agent record fields `human_go` / `human_go_token` | Forbidden |

### 19.3 Tests

| File | Marker | CI |
| --- | --- | --- |
| `tests/unit/surrealdb/test_memory_write_gate.py` | `unit` | yes |

Proven behaviors: block without GO, block on scope mismatch, block on contract violation, block on supersede without target, dry-run pass with valid auth, harness never calls write executor.

### 19.4 No-changes list (Slice 5)

- No memory write feature, no DB write, no MCP write, no Docker/runtime changes
- `memory_read.py`, `memory_db_read_proof.py`, importer unchanged
- LR remains NO-GO

### 19.5 Remaining gaps after Slice 5

| Gap | Follow-up |
| --- | --- |
| Minimal local-only write smoke | Slice 6 (only after gate + operator GO) |
| MCP write surface | Out of scope until explicit design slice |
| Production audit_observation persistence | Future slice after write smoke |

---

## 20. Slice 6 addendum — local-only gated write smoke (#2694)

**Delivered:** gated localhost UPSERT smoke executor, `local_only` integration test, unit tests with mock SQL. No MCP write. No `PERSIST_ALLOWED` flip.

### 20.1 Write smoke module

| Artifact | Role |
| --- | --- |
| `tools/surrealdb/memory_db_write_smoke.py` | `execute_gated_local_memory_write_v1()`, env + gate fail-closed |
| `docs/surrealdb/memory-write-gate-v1.md` §8 | Operator-GO + env contract |

Properties:

- Requires `CDB_RUN_REAL_SURREALDB_MEMORY_WRITE=1` **and** `gate_status == approved_dry_run`
- `persist_allowed` remains `false` in gate envelope; runtime permission is env + operator GO only
- Writes: one `evidence_ref` + one `agent_memory` via `MemoryDbProofSqlClient.upsert_create()` (localhost)
- Scope prefix: `memory_db_write_smoke:<run_tag>` (distinct from Slice 4 read proof scope)
- Audit envelope: `human_go_token` never serialized; `write_status: written_local_only`

### 20.2 Tests

| File | Marker | CI |
| --- | --- | --- |
| `tests/unit/surrealdb/test_memory_db_write_smoke.py` | `unit` | yes (mock SQL) |
| `tests/local/surrealdb/test_memory_db_write_smoke.py` | `local_only` | no (opt-in DB) |

Proven (unit): gate blocked → zero `upsert_create`; env missing → no write; gate pass + env → two UPSERTs.

Proven (local, opt-in): gated UPSERT → `prove_agent_memory_db_read_v1` scope match → `finally` DELETE.

### 20.3 No-changes list (Slice 6)

- `memory_write_gate.py` module constant unchanged (`PERSIST_ALLOWED = False`)
- No MCP write tools, no BLUE/RED, no trading/risk/execution path
- LR remains NO-GO

### 20.4 Remaining gaps after Slice 6

| Gap | Follow-up |
| --- | --- |
| Productive memory write / importer default path | Future slice after sustained smoke evidence |
| MCP write surface | Explicit design slice |
| Production `audit_observation` persistence | After write path ratified |

---

## 21. Slice 7 addendum — Memory Write Path v1 (#2703)

**Delivered:** operator orchestration, audit_observation materialization, local audit persist (env-gated), runbook. No `agent_memory` write via path v1. `PERSIST_ALLOWED` unchanged.

### 21.1 Modules

| Artifact | Role |
| --- | --- |
| `tools/surrealdb/memory_write_path_v1.py` | `run_memory_write_path_v1()` dry_run + audit_persist_local |
| `tools/surrealdb/audit_observation_from_gate.py` | Gate audit → `audit_observation` row |
| `docs/surrealdb/memory-write-path-v1-runbook.md` | Operator runbook + evidence template |

### 21.2 Tests

| File | Marker | CI |
| --- | --- | --- |
| `tests/unit/surrealdb/test_memory_write_path_v1.py` | `unit` | yes |
| `tests/unit/surrealdb/test_audit_observation_from_gate.py` | `unit` | yes |

Proven: dry_run zero SQL; audit persist env-gated; blocked without GO; no raw token in gate envelope; audit_observation UPSERT only.

### 21.3 Remaining gaps after Slice 7

| Gap | Follow-up |
| --- | --- |
| MCP write surface (dry-run intent tool) | #2704 |
| Parent closure audit | #2705 |
| Productive memory write / PERSIST_ALLOWED flip | Separate maintainer GO |

---

## Provenance

| Source | Role |
| --- | --- |
| `docs/surrealdb/scoped-agent-memory-model-v1.md` | Contract |
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Schema draft |
| `tools/surrealdb/memory_read.py` | Read implementation |
| `tools/mcp/context_evidence_memory_tools.py` | MCP + normalization |
| `tools/mcp/surrealdb_adapter_factory.py` | Source honesty |
| `tools/mcp/permission_guard.py` | Read-only enforcement |
| `core/utils/uuid_gen.py` | ID patterns |
| GitHub issue #2606 | Epic (body partially stale) |
