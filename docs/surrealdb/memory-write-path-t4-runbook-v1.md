# Memory Write Path T4 Runbook v1 (#2758)

**Issue:** [#2758](https://github.com/jannekbuengener/Claire_de_Binare/issues/2758)  
**Parent:** [#2606](https://github.com/jannekbuengener/Claire_de_Binare/issues/2606)  
**Contract:** [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md)  
**Status:** G4 scaffold — **NOT ACTIVATED** (mock-only; `PERSIST_ALLOWED=False`)  
**LR:** NO-GO (unchanged)

---

## 1. Purpose

Operator reference for the **T4 agent_memory write path scaffold** delivered in
#2758. This runbook documents fail-closed behavior, mandatory
`audit_observation` ordering, and proof CLI usage. It does **not** authorize
productive `agent_memory` UPSERT, `PERSIST_ALLOWED` flips, or MCP mutation.

---

## 2. Preflight read order

1. [`productive-memory-audit-trail-v1.md`](productive-memory-audit-trail-v1.md)
2. [`memory-write-gate-v1.md`](memory-write-gate-v1.md)
3. [`productive-memory-write-readiness-runbook-v1.md`](productive-memory-write-readiness-runbook-v1.md)
4. [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
5. [`CURRENT_STATUS.md`](../../CURRENT_STATUS.md)

---

## 3. Code surfaces

| Surface | Path | Role |
| --- | --- | --- |
| T4 orchestrator | `tools/surrealdb/memory_write_path_t4.py` | HG-W gate chain; mock sink only |
| T4 proof CLI | `tools/surrealdb/audit_trail_t4_proof.py` | Read-only matrix; write stub refused |
| Gate (unchanged) | `tools/surrealdb/memory_write_gate.py` | `PERSIST_ALLOWED=False` |

### Modes

| Mode | Behavior |
| --- | --- |
| `dry_run` (default) | Gate evaluation only; `path_status=evaluated_only` |
| `agent_memory_persist_productive` | Mock sink + HG-W + env; audit first; memory blocked while `PERSIST_ALLOWED=False` |

### Env gate

- `CDB_PERSIST_PRODUCTIVE_AGENT_MEMORY=1` required for productive-mode mock path
- Orthogonal to `PERSIST_ALLOWED` (code constant remains `False` in #2758 scope)

### Human-GO tier

- **HG-W required** for `agent_memory_persist_productive`
- HG-P and HG-L are refused with `code=hg_w_required`
- HG-P remains valid for T3 productive audit path only (#2747)

---

## 4. Mandatory persist order

When productive mode is invoked (mock scaffold):

1. `evaluate_memory_write_gate()` → `approved_dry_run`
2. `materialize_audit_observation_from_gate()`
3. `audit_observation_row_is_redacted()` check
4. Mock `upsert_audit_observation`
5. **Only if** `PERSIST_ALLOWED=True` (future G3 track): mock `upsert_agent_memory`

In #2758 scaffold, step 5 never runs; response includes
`agent_memory_written=false` and `path_status=mock_persisted_audit_only`.

---

## 5. Proof CLI

```bash
# Env structure only (no network)
python -m tools.surrealdb.audit_trail_t4_proof --check-env-only

# Read-only endpoint matrix (requires governed T3/T4 endpoint env)
python -m tools.surrealdb.audit_trail_t4_proof

# Write proof row — REFUSED until G3 + HG-W operator track
python -m tools.surrealdb.audit_trail_t4_proof --write-proof-row
```

`--write-proof-row` returns matrix with `write_proof_row_status=refused` and
`write_proof_row_blocked_code=g3_track_required`.

---

## 6. CI validation

```bash
pytest tests/unit/surrealdb/test_memory_write_path_t4.py \
  tests/unit/surrealdb/test_audit_trail_t4_proof_contract.py \
  tests/unit/surrealdb/test_memory_write_gate.py \
  tests/unit/surrealdb/test_memory_write_path_v1.py \
  tests/unit/surrealdb/test_memory_write_path_productive.py \
  tests/unit/surrealdb/test_audit_observation_from_gate.py \
  tests/unit/tools/mcp/test_memory_write_intent_tool.py -q

ruff check tools/surrealdb/memory_write_path_t4.py \
  tools/surrealdb/audit_trail_t4_common.py \
  tools/surrealdb/audit_trail_t4_proof.py \
  tests/unit/surrealdb/test_memory_write_path_t4.py \
  tests/unit/surrealdb/test_audit_trail_t4_proof_contract.py
```

---

## 7. Rollback

| Layer | Procedure |
| --- | --- |
| Code | Revert #2758 PR — constants remain fail-closed |
| Mock proof rows | N/A in scaffold (no real DB writes) |
| Future operator proof | DELETE by `observation_id` + `memory_id` + proof scope tag; document in session log |

---

## 8. Non-goals (#2758)

- No `PERSIST_ALLOWED` flip
- No productive `agent_memory` UPSERT on governed endpoint
- No MCP mutation enablement
- No #2606 epic close
- No LR upgrade

Full PASS on #2606 criterion 6 requires separate Maintainer HG-W operator track
(G3 flip + governed endpoint proof).
