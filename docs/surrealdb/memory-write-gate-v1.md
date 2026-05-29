# Memory Write Gate v1 — Human-GO Design & Dry-Run Harness

**Issue**: [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606)  
**Slice**: Memory Reality Slice 5  
**Status**: Design + in-memory harness (no persistence)  
**Guardrail**: No DB write. No MCP write. LR remains NO-GO.

---

## 1. Purpose

Define how a memory write intent is authorized before any future persistence slice.
Slice 5 delivers a **fail-closed gate** and unit-test harness only.

Gate pass means `approved_dry_run` — not authorization to persist.

---

## 2. Human-GO Representation

Memory writes require an explicit operator-supplied `MemoryWriteAuthorization`:

| Field | Required | Notes |
| --- | --- | --- |
| `human_go_token` | yes | Non-empty; pattern `GO-YYYY-MM-DD[-suffix]` |
| `authorized_by` | yes | Human operator id; not agent self-assertion |
| `authorized_at` | yes | ISO-8601 UTC timestamp |
| `scope` | yes | Must match `record.scope` exactly |
| `target_issue` | yes | e.g. `2606` |
| `evidence_refs` | yes | Min 1 non-empty ref |
| `operation` | yes | `create` or `supersede` |

### Not valid as Memory-Write-GO

| Surface | Why |
| --- | --- |
| `DELIVERY_APPROVED.yaml` | Delivery-mode gate only |
| `decision_event.human_go` | Decision context, non-authorizing for memory |
| `context.readiness human_go_required` | Status hint only |
| Record fields `human_go` / `human_go_token` | Agent self-assertion forbidden |

Token shape aligns with `scope_drift_firewall` tests (`GO-2026-05-06`, optional suffix).

---

## 3. Gate Evaluation Order (fail-closed)

1. Authorization present
2. Valid `human_go_token`
3. `authorized_by`, `authorized_at`, `target_issue`, `evidence_refs` present
4. Record must not contain forbidden GO fields
5. `validate_memory_record()` contract pass
6. Authorization scope matches record scope
7. `supersede` operation requires non-empty `superseded_by` on record

Blocked results use `gate_status: blocked_*`. Pass uses `gate_status: approved_dry_run`.

---

## 4. Persistence Guardrails (Slice 5)

- Module constant `PERSIST_ALLOWED = False`
- Envelope always includes `persist_allowed: false`, `dry_run_only: true`
- No importer, SurrealDB adapter, MCP registry, or runtime integration
- Future local-only write smoke (Slice 6) requires separate env gate:
  `CDB_RUN_REAL_SURREALDB_MEMORY_WRITE=1` plus gate pass plus operator GO

---

## 5. Minimum Audit Fields

Each gate envelope includes an `audit` block mapped to future `audit_observation`:

| Field | Required |
| --- | --- |
| `observation_type` | `memory_write_gate_evaluation` |
| `observation_id` | UUIDv5 over canonical gate payload |
| `subject_ref` | `memory_id` when known |
| `message` | Block reason or dry-run approval note |
| `evidence_refs` | Merged record + authorization refs on pass |
| `observed_by` | `memory_write_gate/v1` |
| `observed_at` | ISO timestamp (injectable in tests) |
| `severity` | `blocking` or `info` |
| `related_memory` | `[memory_id]` when known |
| `gate_status` | `blocked_*` or `approved_dry_run` |
| `human_go_token_present` | bool (never log raw token) |
| `authorization_scope` | from authorization |
| `target_issue` | from authorization |

---

## 6. Implementation Surface

| Artifact | Path |
| --- | --- |
| Gate module | `tools/surrealdb/memory_write_gate.py` |
| Unit tests | `tests/unit/surrealdb/test_memory_write_gate.py` |
| Contract validator (reuse) | `tools/surrealdb/memory_contract.py` |
| Audit roadmap | `docs/surrealdb/memory-reality-slice1-audit.md` §19 |

---

## 7. Validation

```bash
pytest tests/unit/surrealdb/test_memory_write_gate.py -v
pytest tests/unit/surrealdb/test_memory_contract.py tests/unit/surrealdb/test_memory_freshness.py tests/unit/surrealdb/test_memory_db_read_proof.py -q
ruff check tools/surrealdb/memory_write_gate.py tests/unit/surrealdb/test_memory_write_gate.py
```

---

## 8. Slice 6 — local-only write smoke (execution)

**Issue**: [#2694](https://github.com/jannekbuengener/Claire_de_Binare/issues/2694)  
**Status**: Gated executor + `local_only` test (no CI DB). LR remains NO-GO.

### Preconditions (all required)

| Layer | Requirement |
| --- | --- |
| Operator prompt | Explicit Operator-GO for Slice 6 local write smoke |
| Gate | `evaluate_memory_write_gate()` → `approved_dry_run` |
| Env | `CDB_RUN_REAL_SURREALDB_MEMORY_WRITE=1` (orthogonal to read flag `CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE`) |
| Module constant | `PERSIST_ALLOWED` stays `False` in `memory_write_gate.py` |
| Runtime | `MemoryDbProofSqlClient` → `127.0.0.1:8010` only |
| Token env | `CDB_MEMORY_WRITE_HUMAN_GO_TOKEN` (`GO-YYYY-MM-DD[-suffix]`) — never log raw value |

### Execution surface

| Artifact | Path |
| --- | --- |
| Write smoke executor | `tools/surrealdb/memory_db_write_smoke.py` |
| Local test | `tests/local/surrealdb/test_memory_db_write_smoke.py` |
| Unit tests (mock SQL) | `tests/unit/surrealdb/test_memory_db_write_smoke.py` |
| Helpers | `tests/local/surrealdb/memory_db_proof_helpers.py` (`memory_db_write_smoke:<tag>` scope) |

Flow: gate pass → env check → UPSERT `evidence_ref` then `agent_memory` → read-back via `prove_agent_memory_db_read_v1` → `finally` DELETE run-scoped rows.

### Validation

```bash
pytest tests/unit/surrealdb/test_memory_db_write_smoke.py -q
ruff check tools/surrealdb/memory_db_write_smoke.py tests/local/surrealdb/test_memory_db_write_smoke.py tests/unit/surrealdb/test_memory_db_write_smoke.py
```

Local-only (after Operator-GO):

```powershell
$env:CDB_RUN_REAL_SURREALDB_MEMORY_WRITE = "1"
$env:CDB_MEMORY_WRITE_HUMAN_GO_TOKEN = "GO-2026-05-29-slice6"
pytest tests/local/surrealdb/test_memory_db_write_smoke.py -q
```

---

## 9. Write Path v1 — operator orchestration (#2703)

**Issue**: [#2703](https://github.com/jannekbuengener/Claire_de_Binare/issues/2703)  
**Status**: Dry-run default; optional localhost `audit_observation` persist.

| Artifact | Path |
| --- | --- |
| Write path orchestrator | `tools/surrealdb/memory_write_path_v1.py` |
| Audit materializer | `tools/surrealdb/audit_observation_from_gate.py` |
| Operator runbook | `docs/surrealdb/memory-write-path-v1-runbook.md` |
| Unit tests | `tests/unit/surrealdb/test_memory_write_path_v1.py` |

Properties:

- Default mode `dry_run`: gate evaluation only, zero SQL
- `audit_persist_local` requires `CDB_PERSIST_MEMORY_WRITE_GATE_AUDIT=1` plus gate pass
- Persists **audit_observation only** — never `agent_memory`
- `PERSIST_ALLOWED` unchanged (`False`)

Validation:

```bash
pytest tests/unit/surrealdb/test_memory_write_path_v1.py tests/unit/surrealdb/test_audit_observation_from_gate.py -v
```

---

## 10. Productive audit trail spec (#2730)

**Issue:** [#2730](https://github.com/jannekbuengener/Claire_de_Binare/issues/2730)  
**Status:** Spec only — **not activated**

The gate module constant **`PERSIST_ALLOWED = False`** remains the current
fail-closed line in code. Local T2 paths (§9, Slice 6 §8) do not constitute a
productive audit trail.

Formal semantics for a future **productive-tier audit trail** (T3) and readiness
gates G0–G4:

- [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md)
- [`productive-memory-write-readiness-runbook-v1.md`](productive-memory-write-readiness-runbook-v1.md)
- [`productive-memory-audit-trail-endpoint-design-v1.md`](productive-memory-audit-trail-endpoint-design-v1.md) (#2735 G1 — design only)

Human-GO tiers (HG-L / HG-P / HG-W) are defined in the contract; local operator
GO does not authorize productive persist or `PERSIST_ALLOWED` flip.

---

## Provenance

| Source | Role |
| --- | --- |
| `docs/surrealdb/productive-memory-audit-trail-v1.md` | T3 audit trail spec (#2730) |
| `docs/surrealdb/productive-memory-audit-trail-endpoint-design-v1.md` | T3 endpoint design (#2735 G1) |
| `docs/surrealdb/scoped-agent-memory-model-v1.md` | Write constraints M5–M7 |
| `docs/surrealdb/context-agent-memory-import-policy-v1.md` | No agent self-GO |
| `tools/surrealdb/scope_drift_firewall.py` | `human_go_token` pattern |
| `tools/surrealdb/memory_db_read_proof.py` | `approval_semantics` pattern |
