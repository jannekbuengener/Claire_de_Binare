# Memory Write Path v1 — Operator Runbook

**Issue**: [#2703](https://github.com/jannekbuengener/Claire_de_Binare/issues/2703)  
**Parent**: [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606)  
**Status**: Gated operator path (dry-run default; local audit persist opt-in)  
**Guardrail**: No productive `agent_memory` write. LR remains NO-GO.

---

## 1. Purpose

Provide a repeatable, audited operator surface for memory write **intent**
evaluation. The path wraps [`memory_write_gate.py`](../../tools/surrealdb/memory_write_gate.py)
and optionally persists gate evaluations to `audit_observation` on localhost only.

This path does **not** replace Slice 6 local write smoke (`memory_db_write_smoke.py`)
for `agent_memory` UPSERT proof.

---

## 2. Surface boundaries

| Surface | Role | Writes |
| --- | --- | --- |
| `memory_write_gate.py` | Human-GO gate evaluation | None |
| `memory_write_path_v1.py` (this runbook) | Operator orchestration | `audit_observation` only (opt-in local) |
| `memory_db_write_smoke.py` | Slice 6 local smoke | `evidence_ref` + `agent_memory` (separate GO) |
| `context_importer.py` | Bulk import | Out of scope; not default write path |

`PERSIST_ALLOWED` in `memory_write_gate.py` remains **`False`**.

---

## 3. Modes

| Mode | SQL | Env required |
| --- | --- | --- |
| `dry_run` (default) | None | None |
| `audit_persist_local` | UPSERT one `audit_observation` | `CDB_PERSIST_MEMORY_WRITE_GATE_AUDIT=1` |

Both modes require valid Human-GO authorization for gate pass. Blocked gate → no SQL.

---

## 4. Operator prerequisites

1. Explicit maintainer Human-GO for the scoped write intent (issue-linked).
2. Valid `MemoryWriteAuthorization` with `human_go_token` matching `GO-YYYY-MM-DD[-suffix]`.
3. Token supplied via secure env (e.g. `CDB_MEMORY_WRITE_HUMAN_GO_TOKEN`) — **never log raw token**.
4. Local SurrealDB at `127.0.0.1:8010` only when using `audit_persist_local`.
5. Run-scoped cleanup for any local audit rows (DELETE by `observation_id`).

---

## 5. Environment variables

| Variable | Required for | Notes |
| --- | --- | --- |
| `CDB_MEMORY_WRITE_HUMAN_GO_TOKEN` | Operator auth assembly | Never log; not serialized in audit rows |
| `CDB_PERSIST_MEMORY_WRITE_GATE_AUDIT` | `audit_persist_local` | Must be `1`; orthogonal to Slice 6 write flag |
| `CDB_RUN_REAL_SURREALDB_MEMORY_WRITE` | Slice 6 smoke only | Not used by write path v1 |

---

## 6. Evidence pack template

Session evidence for a write-path operator run should include:

```text
- Date/time (UTC)
- Git commit SHA
- Issue ref (#2703 / #2606)
- Mode: dry_run | audit_persist_local
- gate_status (blocked_* | approved_dry_run)
- path_status (evaluated_only | audit_persisted_local)
- observation_id (if audit persist)
- memory_id (if known)
- pytest unit evidence (paths below)
- Explicit: no agent_memory write via path v1
- LR: NO-GO unchanged
```

---

## 7. Validation (CI-safe)

```bash
pytest tests/unit/surrealdb/test_memory_write_path_v1.py -v
pytest tests/unit/surrealdb/test_audit_observation_from_gate.py -v
pytest tests/unit/surrealdb/test_memory_write_gate.py -v
ruff check tools/surrealdb/memory_write_path_v1.py tools/surrealdb/audit_observation_from_gate.py
```

---

## 8. subject_ref convention (v0-draft)

When `memory_id` is known, materialized rows use:

`subject_ref = agent_memory:{memory_id}`

When blocked before contract validation, fallback:

`subject_ref = audit_observation:unknown_subject`

---

## Provenance

| Source | Role |
| --- | --- |
| `docs/surrealdb/memory-write-gate-v1.md` | Gate contract |
| `docs/surrealdb/audit-observation-model-v1.md` | Observation type catalog |
| `tools/surrealdb/memory_write_path_v1.py` | Implementation |
